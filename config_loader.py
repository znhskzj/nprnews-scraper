#  Version: config_loader.py v1.2.0
#  Description: A centralized configuration loader for extracting and validating settings from the config.env file.

import os
import logging
from dotenv import load_dotenv

class ConfigLoader:
    def __init__(self, config_path='D:/program/nprnews/config.env'):
        self.config_path = config_path
        self.configurations = {}
        # Define configurations and their default values
        self.config_defaults = {
            'WP_USERNAME': None,
            'WP_APP_PASSWORD': None,
            'WP_API_URL': None,
            'PAGE_ID': None,
            'BASE_URL': None,
            'NEWS_COUNT_DEFAULT': None,
            'CHROME_DRIVER_PATH': None,
            'USE_PROXY': 'False',
            'PROXY': None,
            'DIRECTORY': None,
            'OUTPUT_FILE': None,
            'WORDCLOUD_FILE': None,
            'TIME_FRAME': None,
            'LOG_DIRECTORY': None,
            'LOG_FILENAME': None,
            'DEEPL_API_KEY': None,
            'DEEPL_API_URL': None,
            'DEEPL_USAGE_URL': None,
            'TARGET_LANGUAGE': None,
            'CLEANED_DATA_FILE': None,
            'TRANSLATED_DATA_FILE': None,
            'TRANSLATION_LOG_DIRECTORY': None,
            'TRANSLATION_LOG_FILENAME': None,
            'PREFERRED_TRANSLATION_API': None,
            'AZURE_SUBSCRIPTION_KEY': None,
            'AZURE_ENDPOINT_URL': None,
            'AZURE_TRANSLATOR_REGION': None,
            'TEST_MODE': 'True'
        }

    def load_configurations(self):
        if not load_dotenv(self.config_path):
            logging.error("config.env file not found at the specified path. Please provide the configuration file and try again.")
            raise FileNotFoundError("config.env file not found at the specified path.")
        
        # Load configurations into the dictionary
        for key, default in self.config_defaults.items():
            value = os.getenv(key, default)
            if value in ['True', 'False']:
                value = value.lower() == 'true'
            self.configurations[key] = value

            # Add validations here, for example:
            if key.endswith("_DIRECTORY") and value:
                if not os.path.exists(value):
                    logging.warning(f"Directory {value} does not exist. Please check the configuration.")

        # print("Loaded configurations:", self.configurations)
        return self.configurations
