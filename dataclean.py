"""
Data Cleaner
Version: 1.1.0
Date: 2023-09-19
Description: A script to clean the scraped news data, handle missing data, and generate summary and word cloud.
1.1.0主要改动:
1. 根据新闻爬取1.3.0的内容，特别是输出文件进行更新。
2. 使用logging.debug替换部分print语句，优化日志记录。
"""

import json
import os
import logging
from datetime import datetime
import wordcloud
from collections import Counter
import matplotlib.pyplot as plt

# 设置日志记录
logging.basicConfig(filename='data_cleaning_log.log', level=logging.INFO)

class DataCleaner:
    def __init__(self, input_file='news_data.json', output_file='d:/tmp/cleaned_data.json', summary_file='d:/tmp/summary.txt', wordcloud_file='d:/tmp/wordcloud.png'):
        self.input_file = input_file
        self.output_file = output_file
        self.summary_file = summary_file
        self.wordcloud_file = wordcloud_file
        self.cleaned_data = []
        self.incomplete_data = []
        self.duplicate_data = []
        
    def load_data(self):
        try:
            with open(self.input_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logging.error(f"{datetime.now()} - Input file {self.input_file} not found.")
            return []
        except json.JSONDecodeError:
            logging.error(f"{datetime.now()} - Error decoding JSON from {self.input_file}.")
            return []
    
    def save_data(self, data, file):
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
            link = item.get('link')
            if link in seen:
                self.duplicate_data.append(item)
                logging.warning(f"{datetime.now()} - Duplicate item found: {link}")
            else:
                seen.add(link)
                unique_data.append(item)
        return unique_data
    
    def check_completeness(self, data):
        complete_data = []
        for item in data:
            if all(item.get(field) for field in ['link', 'date', 'summary', 'content']):
                complete_data.append(item)
            else:
                self.incomplete_data.append(item)
                logging.warning(f"{datetime.now()} - Incomplete item found: {item.get('link')}, Missing Fields: {[field for field in ['link', 'date', 'summary', 'content'] if not item.get(field)]}")
        return complete_data
    
    def clean_data(self):
        raw_data = self.load_data()
        if not raw_data:
            logging.error(f"{datetime.now()} - No data loaded. Exiting.")
            return
        
        logging.debug(f"Raw data: {raw_data}")  # 打印原始数据
        data_without_duplicates = self.check_duplicates(raw_data)
        logging.debug(f"Data without duplicates: {len(data_without_duplicates)} items left")  # 打印去重后的数据数量
        self.cleaned_data = self.check_completeness(data_without_duplicates)
        logging.debug(f"Complete data: {len(self.cleaned_data)} items left")  # 打印完整性检查后的数据数量
    
        self.save_data(self.cleaned_data, self.output_file)
        self.save_data(self.incomplete_data, 'incomplete_data.json')
        self.save_data(self.duplicate_data, 'duplicate_data.json')
        logging.info(f"{datetime.now()} - Data cleaning completed. {len(self.cleaned_data)} items cleaned.")
    
    def validate_data(self, data):
        validated_data = []
        for item in data:
            date = item.get('date')
            try:
                datetime.strptime(date, '%Y-%m-%d')
                validated_data.append(item)
            except ValueError:
                logging.warning(f"{datetime.now()} - Invalid date format in item: {item.get('link')}")
        return validated_data
    
    def user_feedback(self):
        print(f"Data cleaning completed. {len(self.cleaned_data)} items cleaned.")
        print(f"{len(self.incomplete_data)} incomplete items found.")
        print(f"{len(self.duplicate_data)} duplicate items found.")
        logging.info(f"{datetime.now()} - User feedback provided.")
    
    def handle_missing_data(self):
        for idx, item in enumerate(self.cleaned_data):
            missing_fields = [field for field in ['date', 'summary', 'content', 'audio_file'] if not item.get(field)]
            if missing_fields:
                self.cleaned_data[idx]['missing_fields'] = missing_fields
                logging.warning(f"{datetime.now()} - Missing fields {missing_fields} in item {idx}.")
        logging.info(f"{datetime.now()} - Missing data handled.")
    
    def generate_summary_and_wordcloud(self):
        if not self.cleaned_data:
            logging.warning(f"{datetime.now()} - No cleaned data available for generating summary and word cloud.")
            return  # 如果没有清洗过的数据，则直接返回
    
        summary_text = ""
        wordcloud_text = ""
        for item in self.cleaned_data:
            summary_text += f"Date: {item.get('date', 'N/A')}\n"
            summary_text += f"Summary: {item.get('summary', 'N/A')}\n"
            summary_text += "---------------------\n"
            wordcloud_text += item.get('content', '') + " "
        
        with open(self.summary_file, 'w', encoding='utf-8') as summary_file:
            summary_file.write(summary_text)
        if wordcloud_text.strip():  # 检查wordcloud_text是否为空
            wc = wordcloud.WordCloud(width=800, height=400, background_color='white').generate(wordcloud_text)
            wc.to_file(self.wordcloud_file)
            logging.info(f"{datetime.now()} - Summary and word cloud generated.")
        else:
            logging.warning(f"{datetime.now()} - No text available for generating word cloud.")

    def run(self):
        self.clean_data()
        self.cleaned_data = self.validate_data(self.cleaned_data)
        self.handle_missing_data()
        self.user_feedback()
        self.generate_summary_and_wordcloud()
        self.save_data(self.cleaned_data, self.output_file)

DataCleaner().run()
