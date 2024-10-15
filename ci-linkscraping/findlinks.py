# Find Online Links
#
# Purpose:
# Pull links from a webpage. Best used on the main page of a site.
#
# Outputs to screen and to a text file.
#
# Created by Richie Atkinson, Callaghan Innovation, 2024
# v0.1
#
# Free to a good home.

## Import libraries
import requests
from bs4 import BeautifulSoup
import os
import re

## Variables to set
# URL we want to find links from - we don't need the trailing /
url_to_scrape = "https://www.callaghaninnovation.govt.nz"
# Pick the data directory to store the file in
data_dir = "/home/user/listsoflinks"


# Function to extract html document from given url
def getHTMLdocument(url):
    # Request for HTML document of given url
    response = requests.get(url)
    # Response will be provided as text
    return response.text


def sanitize_filename(url):
    # Remove 'http://' or 'https://'
    filename = re.sub(r"^https?://", "", url)
    # Remove any characters not allowed in filenames
    filename = re.sub(r"[^\w\-_\.]", "_", filename)
    return filename


# Check the folder to store stuff exists, and if not, make it
os.makedirs(data_dir, exist_ok=True)

# Create a HTML document to parse through
html_document = getHTMLdocument(url_to_scrape)

# Create soup object with HTML doc
soup = BeautifulSoup(html_document, "html.parser")

# Find all the anchor (a) tags with "href"
for link in soup.find_all(
    "a",
    # Uncomment below to add the base URL to the search - this is useful if the page is using anchor (a) tags for stuff that you won't want to capture
    # attrs={'href': re.compile("^https://www.callaghaninnovation.govt.nz")}
):
    ## Compile the output
    output = link.get("href")
    # Strip the trailing / -- the other script doesn't like trailing slashes
    outputstrip = output.rstrip("/")
    # Print the actual URL encapsulated with "",
    output = f'"{url_to_scrape}{outputstrip}",'
    print(output)

    # Use the URL to create a filename and save it to the desired directory
    filename = sanitize_filename(url_to_scrape)
    file_path = os.path.join(data_dir, f"{filename}.txt")

    # Write to file
    with open(file_path, "a") as file:
        file.write(output + "\n")
