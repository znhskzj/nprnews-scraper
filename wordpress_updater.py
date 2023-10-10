# Version: wordpress_updater.py v1.2.0
# Description: Main script to backup the current website content, scrape new news data, and update the WordPress page with the latest news.

import json
import os
import shutil
import logging
from wordpress_utils import get_existing_news_dates, news_exists_for_date, add_news_to_page
from config_loader import ConfigLoader

# Set up logging
logging.basicConfig(level=logging.INFO)

def backup_website_content(subdir="english"):
    """Backup the website content."""
    current_dir = os.getcwd()
    backup_dir = os.path.join(current_dir, f"{subdir}_backup")
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    for item in os.listdir(subdir):
        s = os.path.join(current_dir, subdir, item)
        d = os.path.join(backup_dir, item)
        shutil.copy2(s, d)

    logging.info("Website content backed up successfully.")

def main(test_mode=True):
    # Load environment configurations
    config_loader = ConfigLoader()
    configurations = config_loader.load_configurations()

    # Load the pre-generated news data from the file
    with open(configurations["TRANSLATED_DATA_FILE"], 'r', encoding='utf-8') as f:
        news_data = json.load(f)

    existing_dates = get_existing_news_dates()  # Get the existing news dates once

    # Backup website content only if not in test_mode
    if not test_mode:
        backup_website_content()

    # Iterate through the news data and update the website accordingly
    for news_item in news_data:
        news_date = news_item["date"]
        if not news_exists_for_date(news_date, existing_dates):
            add_news_to_page(news_item)

    logging.info("Website update completed.")


if __name__ == "__main__":
    main()
