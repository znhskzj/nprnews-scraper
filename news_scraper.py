# Version: news_scraper.py v1.6.3
# Description: A script to scrape the latest news articles, extract relevant information, and save it for further processing.

import os
import requests
import datetime
import re
import json
import logging
import argparse
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Custom modules
from config_loader import ConfigLoader

class NPRScraper:
    def __init__(self, configurations, news_count, debug=False):
        self.base_url = configurations['BASE_URL']
        self.chrome_driver_path = configurations['CHROME_DRIVER_PATH']
        self.use_proxy = configurations['USE_PROXY']
        self.proxy = configurations['PROXY']
        current_working_directory = os.getcwd()
        self.log_dir = os.path.join(current_working_directory, 'log')
        self.mp3_dir = os.path.join(current_working_directory, 'mp3')
        self.news_dir = os.path.join(current_working_directory, 'news')
        self.saved_mp3_count = 0  # 新增一个属性来记录成功保存的MP3文件数量

        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.mp3_dir, exist_ok=True)
        os.makedirs(self.news_dir, exist_ok=True)
        
        logging.basicConfig(
            filename=os.path.join(self.log_dir, 'scraper_log.log'), 
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',  # 添加时间戳
            datefmt='%Y-%m-%d %H:%M:%S',  # 时间戳的格式
            encoding='utf-8'  # 设置文件编码为 UTF-8
        )
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
            return None
        
    def fetch_web_page(self, url):
        """
        Modularized function to fetch web pages and handle non-200 responses
        """
        try:
            self.driver.get(url)
            if self.driver.current_url != url:
                logging.error(f"Redirected from {url} to {self.driver.current_url}. May not get desired content.")
        except Exception as e:
            logging.error(f"Error accessing the URL {url}: {str(e)}")
            return False
        return True

    def get_news_links(self):
        try:
            logging.debug("get_news_links method started")
            logging.info(f"用户要求获取 {self.news_count}条新闻")
            print("正在访问NPR新闻总目录页面...")
            if not self.fetch_web_page("https://www.npr.org/programs/morning-edition/archive"):
                raise Exception("Failed to load the news archive page")
            logging.debug(f"self.driver: {self.driver}")
            # self.driver.get("https://www.npr.org/programs/morning-edition/archive")
            print(f"目标：获取前 {self.news_count} 条新闻链接...")
            
            # 先尝试获取页面上已经存在的新闻链接
            daily_news_elements = self.driver.find_elements(By.CSS_SELECTOR, '#main-section article section article:nth-child(1) div h3 a')
            self.daily_news_links.extend([link.get_attribute('href') for link in daily_news_elements])
            # 如果用户请求的新闻数量小于5，只获取所需数量的新闻链接
            if self.news_count <= 5:
                self.daily_news_links = self.daily_news_links[:self.news_count]
                print(f"页面加载完成，已获取 {len(self.daily_news_links)} 条新闻链接。")
                return
            print(f"页面加载完成，已获取 {len(self.daily_news_links)} 条新闻链接。")
            
            scroll_attempts = 0
            links_per_scroll = 5
            max_attempts = (self.news_count // links_per_scroll) + 1  # links_per_scroll 为每次滚动加载的新闻数量

            while len(self.daily_news_links) < self.news_count and scroll_attempts < max_attempts:
                previous_count = len(self.daily_news_links)  # 记录当前已经获取到的新闻链接的数量
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(5)
            
                html = self.driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                for section in soup.select('section.program-show__segments'):
                    link = section.select_one('article:nth-of-type(1) .program-segment__title a')['href']
                    if link not in self.daily_news_links:
                        self.daily_news_links.append(link)
                    
                    if len(self.daily_news_links) >= self.news_count:
                        break
                
                new_links_count = len(self.daily_news_links) - previous_count  # 计算这次滚动后新获取的链接数量
                if new_links_count > 0:
                    print(f"页面已刷新，正在等待新的新闻链接加载... 新获取 {new_links_count} 条新闻链接。")
                    print(f"当前已获取到 {len(self.daily_news_links)} 条新闻链接。")
                
                if len(self.daily_news_links) >= self.news_count:  # 如果已经获取到足够的新闻链接，就跳出循环
                    break

                if new_links_count == 0:  # 如果没有加载到新的新闻链接
                    scroll_attempts += 1

            print(f"成功获取到 {len(self.daily_news_links)} 条新闻链接。")
            logging.debug("get_news_links method finished successfully")
            logging.info(f"实际正确获取新闻条数: {len(self.daily_news_links)}")
            self.status['get_news_links'] = True
        except Exception as e:
            logging.error(f"Error while getting news links: {str(e).splitlines()[0]}")
            print(f"Error in get_news_links method: {e}")
            self.status['get_news_links'] = "Error"
            return None

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
            logging.info(f"成功保存 {self.saved_mp3_count} 个 mp3 文件")  # 所有MP3文件都保存完毕后，记录一条总结性的日志
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
            logging.error(f"Error while processing news link {link}: {str(e).splitlines()[0]}")  # 只记录错误消息的第一行
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
                self.saved_mp3_count += 1  # 每成功保存一个MP3文件，就将计数加1
            else:
                logging.error(f"Error downloading audio file: Invalid response status code {response.status_code}")
            
        except Exception as e:
            logging.error(f"Error occurred while saving news details: {e}")

    def save_to_json(self):
        try:
            logging.debug("save_to_json method started")
            
            # 将新闻按月份分类
            monthly_news = {}
            for news in self.news_data:
                month_key = news['formatted_date'][:6]  # 获取年月，例如202308
                if month_key not in monthly_news:
                    monthly_news[month_key] = []
                monthly_news[month_key].append(news)

            # 为每个月份的新闻保存一个文件
            for month, news_list in monthly_news.items():
                json_file_path = os.path.join(self.news_dir, f'{month}.json')
                
                # 如果文件已存在，读取内容并检查新闻是否已经存在
                existing_news = []
                if os.path.exists(json_file_path):
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                        existing_news = json.load(f)
                
                # 检查新闻是否已经存在，如果不存在，添加到列表中
                for news in news_list:
                    if news not in existing_news:
                        existing_news.append(news)
                    else:
                        logging.info(f"跳过并未保存到json文件的新闻日期: {news['date']}")

                # 保存新闻到文件
                with open(json_file_path, 'w', encoding='utf-8') as f:
                    json.dump(existing_news, f, ensure_ascii=False, indent=4)

                logging.info(f"已成功写入 {len(news_list)} 条新闻，文件名为 {json_file_path}")
            
            logging.debug("save_to_json method finished successfully")
            self.status['save_to_json'] = True
        except Exception as e:
            logging.error(f"Error while saving news data to JSON: {e}")

if __name__ == "__main__":
    try:
        # 加载配置
        config_loader = ConfigLoader()
        configurations = config_loader.load_configurations()

        # 从配置中获取默认的新闻数量
        default_news_count = int(configurations['NEWS_COUNT_DEFAULT'])
        parser = argparse.ArgumentParser(description='NPR News Scraper')
        parser.add_argument('--news_count', type=int, default=default_news_count, help='Number of news to download')
        parser.add_argument('--debug', action='store_true', help='Enable debug mode')
        args = parser.parse_args()

        scraper = NPRScraper(configurations, news_count=args.news_count, debug=args.debug)
        scraper.get_news_links()
        scraper.scrape_news_data()
        scraper.save_to_json()
        print("Application Status:", scraper.status)

    except Exception as e:
        print(f"Error: {e}")