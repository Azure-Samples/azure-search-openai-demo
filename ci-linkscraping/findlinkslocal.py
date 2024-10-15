# Find Local Links
#
# Purpose:
# Pull links from a locally saved HTML file.
# Specific use-case: Sites with complex JS that can't be scraped by usual methods.
# Best used on the main page of a site.
#
# You can parse multiple HTML files at once by saving them all to the input directory.
#
# Outputs to screen and to a text file.
#
# Created by Richie Atkinson, Callaghan Innovation, 2024
# v0.1
#
# Free to a good home.

## Import libraries
from bs4 import BeautifulSoup
import os

## Variables to set
# Set input directory you've saved your file(s) in
input_directory = "/home/user/unparsed"
# Base URL for links - this is usually required for sites which use relative links and a <link rel="canonical" href="https://www.callaghaninnovation.govt.nz/"/>-type meta tag
# This can be blank if the site uses absolute URLs. You won't need the trailing slash.
base_url = "https://www.callaghaninnovation.govt.nz"
# Set a folder to store the output to
data_dir = "/home/user/listsoflinks"

# Check the folder to store outputs exists, and if not, make it
os.makedirs(data_dir, exist_ok=True)

# Collect all the files present in the input directory:
for filename in os.listdir(input_directory):

    # Check files have HTML extension. Ignore if not.
    if filename.endswith(".html"):

        # Join filename and path to get explicit path
        fname = os.path.join(input_directory, filename)
        print("Current file name ..", os.path.abspath(fname))

        # Open the file to begin operations
        with open(fname, "r") as file:
            # Create soup object
            soup = BeautifulSoup(file.read(), "html.parser")

            # parse the html as you wish
            for link in soup.find_all(
                "a",
                # Uncomment below to add the base URL to the search - this is useful if the page is using anchor (a) tags for stuff that you won't want to capture
                # attrs={'href': re.compile("^https://www.callaghaninnovation.govt.nz")}
            ):
                ## Compile the output
                output = link.get("href")
                # Strip the trailing / -- the other script doesn't like trailing slashes
                outputstrip = output.rstrip("/")
                # Print the actual URL encapsultated with "",
                output = f'"{base_url}{outputstrip}",'
                print(output)
                # Create a filename for saving the output
                out_filename = filename.split(".")[0]
                # Create a file path for saving the output
                file_path = os.path.join(data_dir, f"{out_filename}.txt")
                # Write to file
                with open(file_path, "a") as file:
                    file.write(output + "\n")
