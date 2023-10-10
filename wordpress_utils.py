# Version: wordpress_utils.py v1.2.0
# Description: Utility functions for fetching existing news dates, checking news existence, and updating the WordPress page with new news data.

import requests
import logging
from config_loader import ConfigLoader

# Set up logging
logging.basicConfig(level=logging.INFO)

config_loader = ConfigLoader()
configurations = config_loader.load_configurations()

WP_API_URL = configurations['WP_API_URL']
WP_USERNAME = configurations['WP_USERNAME']
WP_APP_PASSWORD = configurations['WP_APP_PASSWORD']
PAGE_ID = configurations['PAGE_ID']

# Auth tuple
auth = (WP_USERNAME, WP_APP_PASSWORD)

def get_existing_news_dates():
    """Fetch the existing news dates from the WordPress page."""
    try:
        response = requests.get(f"{WP_API_URL}/pages/{PAGE_ID}", auth=auth)
        response.raise_for_status()
        
        content = response.json().get("content", {}).get("rendered", "")
        return [date.split('">')[1].split('</a')[0] for date in content.split('<li><a href=')]
    except requests.RequestException as e:
        logging.error(f"Error fetching page. Error: {e}")
        return []

def news_exists_for_date(date, existing_dates):
    """Check if news already exists for a given date."""
    formatted_date = f"{date[4:6]}-{date[6:8]}-{date[:4]}"
    return formatted_date in existing_dates

def add_news_to_page(news_data, test_mode=False):
    """Add the scraped news data to the WordPress page."""
    existing_dates = get_existing_news_dates()
    formatted_date = f"{news_data['date'][4:6]}-{news_data['date'][6:8]}-{news_data['date'][:4]}"
    
    if not news_exists_for_date(news_data["date"], existing_dates):
        try:
            if test_mode:
                print(f"[TEST MODE] News for date {news_data['date']} would be added!")
                news_item = f'<li><a href="https://www.zhurong.link/english/{formatted_date}-morning-news-brief-npr/">{formatted_date}</a></li>'
                print(news_item)
                return
            
            response = requests.get(f"{WP_API_URL}/pages/{PAGE_ID}", auth=auth)
            response.raise_for_status()
            
            page_content = response.json().get("content", {}).get("rendered", "")
            news_item = f'<li><a href="https://www.zhurong.link/english/{formatted_date}-morning-news-brief-npr/">{formatted_date}</a></li>'
            
            # Insert the news item into the existing content
            updated_content = page_content.replace('</ul>', f'{news_item}</ul>')
            
            response = requests.post(f"{WP_API_URL}/pages/{PAGE_ID}", auth=auth, json={"content": updated_content})
            response.raise_for_status()

            logging.info(f"News for date {news_data['date']} added successfully!")
        except requests.RequestException as e:
            logging.error(f"Failed to add news for date {news_data['date']}. Error: {e}")
