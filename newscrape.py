import os
import requests
import datetime
import re
import json
import logging
import argparse
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class NPRScraper:
    def __init__(self, news_count, debug=False):
        # 获取当前工作目录
        current_working_directory = os.getcwd()

        # 创建子目录
        self.log_dir = os.path.join(current_working_directory, 'log')
        self.mp3_dir = os.path.join(current_working_directory, 'mp3')
        self.news_dir = os.path.join(current_working_directory, 'news')
        
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.mp3_dir, exist_ok=True)
        os.makedirs(self.news_dir, exist_ok=True)
        
        # 设置日志文件路径
        logging.basicConfig(filename=os.path.join(self.log_dir, 'scraper_log.log'), level=logging.DEBUG if debug else logging.INFO)
        self.news_count = news_count
        self.debug = debug
        self.daily_news_links = []
        self.news_data = []
        self.status = {
            'setup_driver': False,
            'get_news_links': False,
            'scrape_news_data': False,
            'save_to_json': False
        }
        self.driver = self.setup_driver()

    def setup_driver(self):
        try:
            logging.debug("setup_driver method started")
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--log-level=3')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            driver = webdriver.Chrome(options=options)
            driver.implicitly_wait(20)
            logging.debug("setup_driver method finished successfully")
            self.status['setup_driver'] = True
            return driver
        except Exception as e:
            logging.error(f"Error while setting up driver: {e}")
            logging.debug(f"Error in setup_driver method: {e}")
            return None

    def get_news_links(self):
        try:
            logging.debug("get_news_links method started")
            print("正在访问NPR新闻总目录页面...")
            logging.debug(f"self.driver: {self.driver}")
            self.driver.get("https://www.npr.org/programs/morning-edition/archive")
            print(f"正在获取前 {self.news_count} 条新闻链接...")
            previous_count = 0
            scroll_attempts = 0
            max_attempts = 5  # 最大尝试滚动次数
            while len(self.daily_news_links) < self.news_count and scroll_attempts < max_attempts:
                daily_news_elements = self.driver.find_elements(By.CSS_SELECTOR, '#main-section article section article:nth-child(1) div h3 a')
                new_links = [link.get_attribute('href') for link in daily_news_elements if link.get_attribute('href') not in self.daily_news_links]
                self.daily_news_links.extend(new_links)
                
                if not new_links:
                    scroll_attempts += 1
                else:
                    previous_count += len(new_links)
                    scroll_attempts = 0

                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(5)
                
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, f"#main-section article section article:nth-child({previous_count + 1}) div h3 a"))
                    )
                except Exception as e:
                    logging.error(f"Error while waiting for news links to load: {e}")
                    return

            print(f"成功获取到 {len(self.daily_news_links)} 条新闻链接。")
            if len(self.daily_news_links) < self.news_count:
                logging.warning(f"Could only retrieve {len(self.daily_news_links)} news links, less than the requested {self.news_count}.")
            logging.debug("get_news_links method finished successfully")
            self.status['get_news_links'] = True
        except Exception as e:
            logging.error(f"Error while getting news links: {e}")
            print(f"Error in get_news_links method: {e}")

    def scrape_news_data(self):
        try:
            logging.debug("scrape_news_data method started")
            for idx, link in enumerate(self.daily_news_links, 1):
                print(f"正在处理第 {idx} 条新闻...")
                news_details = self.get_news_details(link)
                if news_details:
                    self.save_news_details(news_details)
                    self.news_data.append(news_details)
                print(f"第 {idx} 条新闻处理完毕。")
            
            print("所有新闻已处理完毕。")
            logging.debug("scrape_news_data method finished successfully")
            self.driver.quit()
            self.status['scrape_news_data'] = True
        except Exception as e:
            logging.error(f"Error while scraping news data: {e}")

    def get_news_details(self, link):
        try:
            logging.debug("get_news_details method started")
            self.driver.get(link)
            
            news_date = self.driver.find_element(By.CSS_SELECTOR, '#story-meta > div.story-meta__one > div > div.dateblock > time').text
            news_date = re.sub(r"(\d{4})(\d{1,2}:\d{1,2})", r"\1 \2", news_date)
            
            match = re.match(r"(\w+ \d+, \d{4})", news_date)
            if match:
                date_part = match.group(1)
                month_name, day, year = date_part.replace(',', '').split()
                formatted_date = datetime.datetime.strptime(f"{day} {month_name} {year}", '%d %B %Y').strftime('%Y%m%d')
            else:
                raise ValueError(f"无法解析日期: {news_date}")
            
            news_summary = self.driver.find_element(By.CSS_SELECTOR, '#storytext > p').text
            news_content_element = self.driver.find_element(By.CSS_SELECTOR, '#main-section > article > div.transcript.storytext')
            news_content = news_content_element.text
            audio_link = self.driver.find_element(By.CSS_SELECTOR, '.audio-tool-download a').get_attribute('href')
            logging.debug("get_news_details method finished successfully")
            return {
                'date': news_date,
                'formatted_date': formatted_date,
                'summary': news_summary,
                'content': news_content,
                'audio_link': audio_link
            }
        except Exception as e:
            logging.error(f"Error while processing news link {link}: {e}")
            return None

    def save_news_details(self, news_details):
        try:
            logging.debug("save_news_details method started")
            audio_filename = f"{news_details['formatted_date']}.mp3"
            audio_path = os.path.join(self.mp3_dir, audio_filename)
            response = requests.get(news_details['audio_link'])
            if response.status_code == 200:
                with open(audio_path, 'wb') as audio_file:
                    audio_file.write(response.content)
            else:
                raise ValueError(f"Error downloading audio file: Invalid response status code {response.status_code}")
            
            summary_file_path = os.path.join(self.news_dir, "summary.txt")
            with open(summary_file_path, 'a+', encoding='utf-8') as summary:
                summary.write(f"日期: {news_details['date']}\n")
                summary.write(f"摘要: {news_details['summary']}\n")
                summary.write(f"音频文件: {audio_filename}\n")
                summary.write("-------------------------------\n")
        except Exception as e:
            logging.error(f"Error occurred while saving news details: {e}")

    def save_to_json(self):
        try:
            logging.debug("save_to_json method started")
            json_file_path = os.path.join(self.news_dir, 'news_data.json')
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.news_data, f, ensure_ascii=False, indent=4)
            logging.info(f"News data saved to {json_file_path} successfully.")
            logging.debug("save_to_json method finished successfully")
            self.status['save_to_json'] = True
        except Exception as e:
            logging.error(f"Error while saving news data to JSON: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='NPR News Scraper')
    parser.add_argument('--news_count', type=int, default=10, help='Number of news to download')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    scraper = NPRScraper(news_count=args.news_count, debug=args.debug)
    scraper.get_news_links()
    scraper.scrape_news_data()
    scraper.save_to_json()
    print("Application Status:", scraper.status)
