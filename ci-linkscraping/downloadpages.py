# Download Pages
#
# Purpose:
# Scrape pages from a list of URLs.
# Takes a list of urls and reads the site, then saves the site as an HTML file.
#
# Created by Richie Atkinson, Callaghan Innovation, 2024
# v0.1
#
# Free to a good home.

# Import libraries
import os
import requests
import time
from bs4 import BeautifulSoup

## Variables to set
# Pick a folder to write the files to
data_dir = "html"

# List of URLs to download for indexing. We're manually pasting here to make sure there's some human oversight.
# For a production environment we probably wouldn't use this method, or we'd have a more robust way of managing the list.
# URLs should be complete, and each line must start with " and end with ",
urls = [
    "https://www.callaghaninnovation.govt.nz",
    "https://www.callaghaninnovation.govt.nz/products",
]

# Check the folder to store stuff exists, and if not, make it
os.makedirs(data_dir, exist_ok=True)

# Loop through each URL in the list
for i in range(len(urls)):
    response = requests.get(urls[i])

    # Check if the request was successful then parse the HTML content
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        # Clean it up in case of messy, confusing, or inconsistent formatting
        text = soup.prettify()
        # Create a file path for saving the HTML content, then write the content out to a file
        text_file = os.path.join(data_dir, urls[i].split("/")[-1] + ".html")
        with open(text_file, "w") as file:
            file.write(text)
        # Sleep for 30 seconds to avoid overwhelming the server
        time.sleep(30)
    else:
        # Print an error message if the request failed
        print(f"Failed to retrieve {urls[i]}. Status code: {response.status_code}")
