# Version: Version: 1.6.1
# Description: A script to clean the scraped news data, handle missing data, and generate summary and word cloud.

import json
import os
import re
import logging
from datetime import datetime
import wordcloud
from config_loader import ConfigLoader

class DataCleaner:
    def __init__(self, directory, output_file, wordcloud_file, log_directory, log_filename):
        self.directory = directory
        self.output_file = output_file
        self.wordcloud_file = wordcloud_file
        self.log_directory = log_directory
        self.log_filename = log_filename
        # Ensure log directory exists
        os.makedirs(self.log_directory, exist_ok=True)

        # Setup logging
        logging.basicConfig(
            filename=os.path.join(self.log_directory, self.log_filename),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            encoding='utf-8'
        )
        latest_file = self.get_latest_data_file()
        print(f"latest_file: {latest_file}")
        if not latest_file:
            raise ValueError("No JSON files found in the specified directory.")
        self.input_file = os.path.join(self.directory, latest_file)
        print(f"self.input_file: {self.input_file}")
        self.cleaned_data = []
        self.incomplete_data = []
        self.duplicate_data = []

    def load_data(self):
            all_data = []
            json_files = []  # 提供一个默认值
            try:
                # 获取目录中的所有JSON文件
                json_files = [f for f in os.listdir(self.directory) if os.path.isfile(os.path.join(self.directory, f)) and f.endswith('.json')]
                if not json_files:
                    logging.error(f"{datetime.now()} - No news files found in directory {self.directory}.")
                    print("Error: No news files found. Exiting.")
                    exit()

                # 遍历每个JSON文件并加载数据
                for json_file in json_files:
                    with open(os.path.join(self.directory, json_file), 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        all_data.extend(data)
                        
                logging.info(f"{datetime.now()} - Loaded {len(all_data)} items from directory {self.directory}.")  # <-- 修改部分
                return all_data
            except FileNotFoundError:
                logging.error(f"{datetime.now()} - Input directory {self.directory} not found.")
                return []
            except json.JSONDecodeError:
                logging.error(f"{datetime.now()} - Error decoding JSON from {self.directory}.")
                return []
    
    def save_data(self, data, file):
            if data:  # 检查数据是否为空
                # 确保目标文件夹存在
                os.makedirs(os.path.dirname(file), exist_ok=True)
                try:
                    with open(file, 'w') as f:
                        json.dump(data, f)
                    logging.info(f"{datetime.now()} - Data saved to {file}.")
                except Exception as e:
                    logging.error(f"{datetime.now()} - Error saving data to {file}: {e}")

    def check_duplicates(self, data):
        seen = set()
        unique_data = []
        for item in data:
            audio_link = item.get('audio_link')
            
            if audio_link and audio_link in seen:
                self.duplicate_data.append(item)
                logging.warning(f"{datetime.now()} - Duplicate item found with audio_link: {audio_link}")
            elif audio_link:
                seen.add(audio_link)
                unique_data.append(item)
            else:
                logging.warning(f"{datetime.now()} - Item without audio_link found: {item}")
        return unique_data

    def check_completeness(self, data):
        complete_data = []
        for item in data:
            if all(item.get(field) for field in ['date', 'formatted_date', 'summary', 'content', 'audio_link']):
                complete_data.append(item)
            else:
                self.incomplete_data.append(item)
                logging.warning(f"{datetime.now()} - Incomplete item found: {item.get('audio_link', 'N/A')}, Missing Fields: {[field for field in ['date', 'formatted_date', 'summary', 'content', 'audio_link'] if not item.get(field)]}")
        return complete_data

    def clean_data(self):
        def clean_text(text):
            # 将特殊字符转换为实际字符
            try:
                cleaned_text = text.encode('latin1').decode('unicode_escape')
            except:
                cleaned_text = text
            # 仅保留换行符
            cleaned_text = cleaned_text.replace('\\n', '\n')
            return cleaned_text

        raw_data = self.load_data()
        if not raw_data:
            logging.error(f"{datetime.now()} - No data loaded. Exiting.")
            return
        
        data_without_duplicates = self.check_duplicates(raw_data)
        logging.info(f"{datetime.now()} - After removing duplicates: {len(data_without_duplicates)} items left.")
        
        for item in data_without_duplicates:
            item['summary'] = clean_text(item['summary'])
            item['content'] = clean_text(item['content'])
        
        self.cleaned_data = self.check_completeness(data_without_duplicates)
        logging.info(f"{datetime.now()} - After checking completeness: {len(self.cleaned_data)} items left.")
        
        self.save_data(self.cleaned_data, self.output_file)
        self.save_data(self.incomplete_data, 'incomplete_data.json')
        self.save_data(self.duplicate_data, 'duplicate_data.json')
        logging.info(f"{datetime.now()} - Data cleaning completed. {len(self.cleaned_data)} items cleaned.")


    def validate_data(self, data):
        validated_data = []
        for item in data:
            date = item.get('formatted_date')
            try:
                # 使用formatted_date字段验证日期格式
                datetime.strptime(date, '%Y%m%d')
                validated_data.append(item)
            except ValueError:
                logging.warning(f"{datetime.now()} - Invalid date format in item: {item.get('audio_link', 'N/A')}")
        return validated_data
    
    def user_feedback(self):
        print(f"Data cleaning completed. {len(self.cleaned_data)} items cleaned.")
        print(f"{len(self.incomplete_data)} incomplete items found.")
        print(f"{len(self.duplicate_data)} duplicate items found.")
        logging.info(f"{datetime.now()} - User feedback provided.")
    
    def handle_missing_data(self):
        for idx, item in enumerate(self.cleaned_data):
            missing_fields = [field for field in ['date', 'summary', 'content', 'audio_link'] if not item.get(field)]
            
            # Check if the corresponding MP3 file exists
            mp3_filename = f"{item.get('formatted_date')}.mp3"
            mp3_filepath = os.path.join('mp3', mp3_filename)
            if os.path.exists(mp3_filepath):  # <-- 修改部分：检查MP3文件是否存在
                if 'audio_file' in missing_fields:
                    missing_fields.remove('audio_file')
            
            if missing_fields:
                self.cleaned_data[idx]['missing_fields'] = missing_fields
                logging.warning(f"{datetime.now()} - Missing fields {missing_fields} in item {idx}.")
    
    def generate_summary_and_wordcloud(self):
        if not self.cleaned_data:
            logging.warning(f"{datetime.now()} - No cleaned data available for generating summary and word cloud.")
            return  # 如果没有清洗过的数据，则直接返回

        wordcloud_text = ""
        for item in self.cleaned_data:
            wordcloud_text += item.get('content', '') + " "

        # 去除主持人姓名
        wordcloud_text = re.sub(r'[A-Z\s]+:', '', wordcloud_text)

        # Generate word cloud
        if wordcloud_text.strip():  # 检查wordcloud_text是否为空
            wc = wordcloud.WordCloud(width=800, height=400, background_color='white').generate(wordcloud_text)
            wc.to_file(self.wordcloud_file)
            logging.info(f"{datetime.now()} - Word cloud generated.")
        else:
            logging.warning(f"{datetime.now()} - No text available for generating word cloud.")

    def get_latest_data_file(self):
        pattern = re.compile(r'^\d{6}\.json$')  # 匹配YYYYMM.json格式
        files = [f for f in os.listdir(self.directory) if os.path.isfile(os.path.join(self.directory, f)) and pattern.match(f)]
        files.sort(reverse=True)
        return files[0] if files else None


    def run(self):
        print("Starting data cleaning process...")
        print(f"self.directory: {self.directory}")
        print(f"self.input_file: {self.input_file}")
        # Check if directory exists
        if not os.path.exists(self.directory):
            print(f"Directory {self.directory} not found. Exiting.")
            logging.error(f"Directory {self.directory} not found.")
            return
        
        # Check if input file exists
        if not os.path.exists(self.input_file):
            print(f"Input file {self.input_file} not found. Exiting.")
            logging.error(f"Input file {self.input_file} not found.")
            return

        # Check if input file is empty
        if os.path.getsize(self.input_file) == 0:
            print(f"Input file {self.input_file} is empty. Exiting.")
            logging.error(f"Input file {self.input_file} is empty.")
            return

        self.clean_data()
        self.cleaned_data = self.validate_data(self.cleaned_data)
        self.handle_missing_data()
        self.user_feedback()
        self.generate_summary_and_wordcloud()
        self.save_data(self.cleaned_data, self.output_file)

        print("Data cleaning process completed.")

if __name__ == "__main__":
    try:
        # Load configurations
        config_loader = ConfigLoader()
        configurations = config_loader.load_configurations()

        # 从配置中获取相关参数
        DIRECTORY = configurations['DIRECTORY']
        OUTPUT_FILE = configurations['OUTPUT_FILE']
        WORDCLOUD_FILE = configurations['WORDCLOUD_FILE']
        LOG_DIRECTORY = configurations['LOG_DIRECTORY']
        LOG_FILENAME = configurations['LOG_FILENAME']

        if not os.path.exists(LOG_DIRECTORY):
            os.makedirs(LOG_DIRECTORY)

        cleaner = DataCleaner(DIRECTORY, OUTPUT_FILE, WORDCLOUD_FILE, LOG_DIRECTORY, LOG_FILENAME)

        cleaner.run()

    except Exception as e:
        print(f"Error: {e}")
        logging.error(f"Error occurred: {e}")