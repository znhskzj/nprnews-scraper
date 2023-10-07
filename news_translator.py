#  Version: news_translator.py v1.6.2
#  Description: A script to translate news data using the DeepL API, with account usage checks and test mode.

import json
import os
import re
import requests
import logging
import uuid
import ast

# Custom modules
from config_loader import ConfigLoader

class AzureTranslator:
    def __init__(self, subscription_key, endpoint, region):
        self.subscription_key = subscription_key
        self.endpoint = endpoint
        self.headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4()),
            'Ocp-Apim-Subscription-Region': region
        }

    def translate(self, text, target_language):
        path = '/translate?api-version=3.0'
        params = '&to=' + target_language
        constructed_url = self.endpoint + path + params

        body = [{'text': text}]
        request = requests.post(constructed_url, headers=self.headers, json=body)
        response = request.json()

        if response and 'translations' in response[0]:
            return response[0]['translations'][0]['text']
        else:
            print("Error from Azure API:", response)
            if 'error' in response:
                print("Azure API Error Message:", response['error'].get('message', 'Unknown error'))
            return None

class DeepLTranslator:
    def __init__(self, api_key, api_url, usage_url):
        self.api_key = api_key
        self.api_url = api_url
        self.usage_url = usage_url
        self.logger = logging.getLogger(__name__)

    def translate(self, text, target_language):
        try:
            payload = {
                "auth_key": self.api_key,
                "text": text,
                "target_lang": target_language
            }
            response = requests.post(self.api_url, data=payload)
            response.raise_for_status()
            return response.json()["translations"][0]["text"]
        except (requests.RequestException, ValueError) as e:
            self.logger.error(f"Error translating with DeepL: {e}")
            return None

    def get_account_usage(self):
        try:
            response = requests.get(self.usage_url, params={"auth_key": self.api_key})
            response.raise_for_status()
            data = response.json()
            remaining_characters = data['character_limit'] - data['character_count']
            self.logger.info(f"Successfully fetched DeepL account usage. Remaining characters: {remaining_characters}")
            return data["character_count"], data["character_limit"]
        except (requests.RequestException, ValueError) as e:
            self.logger.error(f"Error fetching DeepL account usage: {e}")
            return None, None

class NewsTranslator:
    def __init__(self, deepl_translator, azure_translator, preferred_api, target_language, test_mode, input_file, output_file, log_file):
        self.target_language = target_language
        self.input_file = input_file
        self.output_file = output_file
        self.test_mode = test_mode
        self.preferred_api = preferred_api
        self.azure_translator = azure_translator
        self.deepl_translator = deepl_translator

        # Create a dedicated logger for this class
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def protect_names(self, text):
        # 匹配格式为"\nALLCAPSNAME:"或"ALLCAPSNAME:"的名字
        name_pattern = re.compile(r'(\n)?([A-Z\s]+):')
        matches = name_pattern.findall(text)
        
        for i, match in enumerate(matches):
            placeholder = f"NAMEPLACEHOLDER_{i}_END"
            text = text.replace(f"{match[0]}{match[1]}:", f"{match[0]}{placeholder}:")
        
        return text, [match[1] for match in matches]

    def restore_names(self, translated_text, names):
        for i, name in enumerate(names):
            placeholder = f"NAMEPLACEHOLDER_{i}_END"
            translated_text = translated_text.replace(placeholder, name)
        
        return translated_text

    def translate_text(self, text):
        # 保护名字
        protected_text, names = self.protect_names(text)

        # 根据首选API进行翻译
        translators = {
            "MICROSOFT": self.translate_with_azure,
            "DEEPL": self.deepl_translator.translate
            # ... [可以添加其他API的处理]
        }

        translated_text = translators.get(self.preferred_api)(text)
        if not translated_text:
            for api, translator_func in translators.items():
                if api != self.preferred_api:
                    translated_text = translator_func(text)
                    if translated_text:
                        break

        # 如果所有API都失败，返回原始文本
        translated_text = translated_text or text

        # 恢复名字
        translated_text = self.restore_names(translated_text, names)
        return translated_text  
        
    def translate_with_azure(self, text):
        print("Translating text with Azure.")
        self.logger.info("Translating text with Azure.")
        
        try:
            # 使用AzureTranslator进行翻译
            translated_text = self.azure_translator.translate(text, self.target_language)
            
            if not translated_text:
                self.logger.warning(f"Error translating with Azure: No translation returned.")
                return None
            
            return translated_text
            
        except Exception as e:
            self.logger.warning(f"Error translating with Azure: {e}")
            return None

    def run(self):
        print("Starting the translation process...")
        self.logger.info("Starting the translation process.")
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Only check DeepL usage if it's the preferred API
        if self.preferred_api == "DEEPL":
            used_characters, character_limit = self.deepl_translator.get_account_usage()
            if used_characters is None or character_limit is None:
                print("Error fetching account usage. Exiting.")
                self.logger.error("Error fetching account usage.")
                return

            if used_characters >= character_limit:
                print("Monthly character limit reached. Exiting.")
                self.logger.warning("Monthly character limit reached.")
                return

            print(f"Successfully fetched DeepL account usage. Remaining characters: {character_limit - used_characters}")

        for item in data:
            item['summary'] = self.translate_text(item['summary'])
            if not self.test_mode:
                item['content'] = self.translate_text(item['content'])

        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print("Translation completed!")
        self.logger.info(f"Translation completed. Translated data saved to {self.output_file}.")

if __name__ == "__main__":
    config_loader = ConfigLoader()

    try:
        configurations = config_loader.load_configurations()
        print("Azure Endpoint URL from configurations:", configurations['AZURE_ENDPOINT_URL'])
    except FileNotFoundError:
        print("Error: config.env file not found. Exiting.")
        exit()
    except ValueError as e:
        print(f"Error loading configurations: {e}. Exiting.")
        exit()
    
    preferred_translation_api = ast.literal_eval(configurations['PREFERRED_TRANSLATION_API'])
    deepl_translator = DeepLTranslator(configurations['DEEPL_API_KEY'], configurations['DEEPL_API_URL'], configurations['DEEPL_USAGE_URL'])
    azure_translator = AzureTranslator(configurations['AZURE_SUBSCRIPTION_KEY'], configurations['AZURE_ENDPOINT_URL'], configurations['AZURE_TRANSLATOR_REGION'])

    translator = NewsTranslator(
        deepl_translator=deepl_translator,
        azure_translator=azure_translator,
        target_language=configurations['TARGET_LANGUAGE'],
        test_mode=configurations['TEST_MODE'],
        input_file=configurations['CLEANED_DATA_FILE'],
        output_file=configurations['TRANSLATED_DATA_FILE'],
        log_file=os.path.join(configurations['TRANSLATION_LOG_DIRECTORY'], configurations['TRANSLATION_LOG_FILENAME']),
        preferred_api=preferred_translation_api[0]
    )
    translator.run()