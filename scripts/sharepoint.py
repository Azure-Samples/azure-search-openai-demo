"""
Demonstrates how to download a file from SharePoint site
"""
import os
import tempfile
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext



ctx = ClientContext("https://yh2cap.sharepoint.com").with_credentials(UserCredential("{username}", "{password}"))
file_url = '/YH2Investments/ET1vDFwzmXFCh0V-6cOYZOUBDcbn-D1fPu0hNqSXEaRnWg'
# file_url = "Shared Documents/!2022/Financial Sample.xlsx"
download_path = os.path.join(tempfile.mkdtemp(), os.path.basename(file_url))
with open(download_path, "wb") as local_file:
    file = ctx.web.get_file_by_server_relative_url(file_url).download(local_file).execute_query()
print("[Ok] file has been downloaded into: {0}".format(download_path))