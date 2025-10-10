import argparse
import asyncio
from datetime import datetime
import json
import logging
import os
import hashlib
from typing import Any, Optional

import aiohttp
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential
from azure.storage.filedatalake.aio import (
    DataLakeDirectoryClient,
    DataLakeServiceClient,
)

from load_azd_env import load_azd_env

logger = logging.getLogger("scripts")
# Set the logging level for the azure package to DEBUG
logging.getLogger("azure").setLevel(logging.DEBUG)
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.DEBUG)

class AdlsGen2Setup:
    """
    Sets up a Data Lake Storage Gen 2 account with sample data and access control
    """

    def __init__(
        self,
        data_directory: str,
        storage_account_name: str,
        filesystem_name: str,
        security_enabled_groups: bool,
        data_access_control_format: dict[str, Any],
        credentials: AsyncTokenCredential,
    ):
        """
        Initializes the command

        Parameters
        ----------
        data_directory
            Directory where sample files are located
        storage_account_name
            Name of the Data Lake Storage Gen 2 account to use
        filesystem_name
            Name of the container / filesystem in the Data Lake Storage Gen 2 account to use
        security_enabled_groups
            When creating groups in Microsoft Entra, whether or not to make them security enabled
        data_access_control_format
            File describing how to create groups, upload files with access control. See the sampleacls.json for the format of this file
        """
        self.data_directory = data_directory
        self.storage_account_name = storage_account_name
        self.filesystem_name = filesystem_name
        self.credentials = credentials
        self.security_enabled_groups = security_enabled_groups
        self.data_access_control_format = data_access_control_format
        self.graph_headers: Optional[dict[str, str]] = None

    async def run(self, scandirs: bool = False):
        async with self.create_service_client() as service_client:
            logger.info(f"Ensuring {self.filesystem_name} exists...")
            async with service_client.get_file_system_client(self.filesystem_name) as filesystem_client:
                if not await filesystem_client.exists():
                    await filesystem_client.create_file_system()

                logger.info("Creating groups...")
                groups: dict[str, str] = {}
                for group in self.data_access_control_format["groups"]:
                    group_id = await self.create_or_get_group(group)
                    groups[group] = group_id

                logger.info("Ensuring directories exist...")
                directories: dict[str, DataLakeDirectoryClient] = {}
                try:
                    for directory in self.data_access_control_format["directories"].keys():
                        directory_client = (
                            await filesystem_client.create_directory(directory)
                            if directory != "/"
                            else filesystem_client._get_root_directory_client()
                        )
                        directories[directory] = directory_client

                    logger.info("Uploading scanned files...")
                    if scandirs:
                        await self.scan_and_upload_directories(directories, filesystem_client)

                    logger.info("Uploading files...")
                    for file, file_info in self.data_access_control_format["files"].items():
                        directory = file_info["directory"]
                        if directory not in directories:
                            logger.error(f"File {file} has unknown directory {directory}, exiting...")
                            return
                        await self.upload_file(directory_client=directories[directory], file_path=os.path.join(self.data_directory, file))

                    logger.info("Setting access control...")
                    for directory, access_control in self.data_access_control_format["directories"].items():
                        directory_client = directories[directory]
                        if "groups" in access_control:
                            for group_name in access_control["groups"]:
                                if group_name not in groups:
                                    logger.error(
                                        f"Directory {directory} has unknown group {group_name} in access control list, exiting"
                                    )
                                    return
                                await directory_client.update_access_control_recursive(acl=f"group:{groups[group_name]}:r-x"
                                )
                        if "oids" in access_control:
                            for oid in access_control["oids"]:
                                await directory_client.update_access_control_recursive(acl=f"user:{oid}:r-x")
                finally:
                    for directory_client in directories.values():
                        await directory_client.close()

    async def walk_files(self, src_filepath = "."):
        filepath_list = []
    
        #This for loop uses the os.walk() function to walk through the files and directories
        #and records the filepaths of the files to a list
        for root, dirs, files in os.walk(src_filepath):
            
            #iterate through the files currently obtained by os.walk() and
            #create the filepath string for that file and add it to the filepath_list list
            root_found: bool = False
            for file in files:
                #Checks to see if the root is '.' and changes it to the correct current
                #working directory by calling os.getcwd(). Otherwise root_path will just be the root variable value.                
                
                if not root_found and root == '.':
                    filepath =os.path.join(os.getcwd() + "/", file)
                    root_found = True
                else:
                    filepath = os.path.join(root, file)
               
                #Appends filepath to filepath_list if filepath does not currently exist in filepath_list
                if filepath not in filepath_list:
                    filepath_list.append(filepath)               
                    
        #Return filepath_list        
        return filepath_list

    async def scan_and_upload_directories(self, directories: dict[str, DataLakeDirectoryClient], filesystem_client):
        logger.info("Scanning and uploading files from directories recursively...")
        
        for directory, directory_client in directories.items():
            directory_path = os.path.join(self.data_directory, directory)
            if directory == "/":
                continue
            
             # Check if 'scandir' exists and is set to False
            if not self.data_access_control_format["directories"][directory].get("scandir", True):
                logger.info(f"Skipping directory {directory} as 'scandir' is set to False")
                continue
            
            # Check if the directory exists before walking it
            if not os.path.exists(directory_path):
                logger.warning(f"Directory does not exist: {directory_path}")
                continue
            
            # Get all file paths using the walk_files function
            file_paths = await self.walk_files(directory_path)

            # Upload each file collected
            count =0
            num = len(file_paths)
            for file_path in file_paths:
                await self.upload_file(directory_client, file_path, directory)
                count=+1
                logger.info(f"Uploaded [{count}/{num}] {directory}/{file_path}")

    def create_service_client(self):
        return DataLakeServiceClient(
            account_url=f"https://{self.storage_account_name}.dfs.core.windows.net", credential=self.credentials
        )

    async def calc_md5(self, path: str) -> str:
        hash_md5 = hashlib.md5()
        with open(path, "rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    async def get_blob_md5(self, directory_client: DataLakeDirectoryClient, filename: str) -> Optional[str]:
        """
        Retrieves the MD5 checksum from the metadata of the specified blob.
        """
        file_client = directory_client.get_file_client(filename)
        try:
            properties = await file_client.get_file_properties()
            return properties.metadata.get('md5')
        except Exception as e:
            logger.error(f"Error getting blob properties for {filename}: {e}")
            return None
    
    async def upload_file(self, directory_client: DataLakeDirectoryClient, file_path: str, category: str = ""):
        # Calculate MD5 hash once
        md5_hash = await self.calc_md5(file_path)

        # Get the filename
        filename = os.path.basename(file_path)

        # Get the MD5 checksum from the blob metadata
        blob_md5 = await self.get_blob_md5(directory_client, filename)

        # Upload the file if it does not exist or the checksum differs
        if blob_md5 is None or md5_hash != blob_md5:
            with open(file_path, "rb") as f:
                file_client = directory_client.get_file_client(filename)
                tmtime = os.path.getmtime(file_path)
                last_modified = datetime.fromtimestamp(tmtime).isoformat()
                title = os.path.splitext(filename)[0]
                metadata = {
                    "md5": md5_hash,
                    "category": category,
                    "updated": last_modified,
                    "title": title
                }
                await file_client.upload_data(f, overwrite=True)
                await file_client.set_metadata(metadata)
                logger.info(f"Uploaded and updated metadata for {filename}")
        else:
            logger.info(f"No upload needed for {filename}, checksums match")

    async def create_or_get_group(self, group_name: str):
        group_id = None
        if not self.graph_headers:
            token_result = await self.credentials.get_token("https://graph.microsoft.com/.default")
            self.graph_headers = {"Authorization": f"Bearer {token_result.token}"}
        async with aiohttp.ClientSession(headers=self.graph_headers) as session:
            logger.info(f"Searching for group {group_name}...")
            async with session.get(
                f"https://graph.microsoft.com/v1.0/groups?$select=id&$top=1&$filter=displayName eq '{group_name}'"
            ) as response:
                content = await response.json()
                if response.status != 200:
                    raise Exception(content)
                if len(content["value"]) == 1:
                    group_id = content["value"][0]["id"]
            if not group_id:
                logger.info(f"Could not find group {group_name}, creating...")
                group = {
                    "displayName": group_name,
                    "securityEnabled": self.security_enabled_groups,
                    "groupTypes": ["Unified"],
                    # If Unified does not work for you, then you may need the following settings instead:
                    # "mailEnabled": False,
                    # "mailNickname": group_name,

                }
                async with session.post("https://graph.microsoft.com/v1.0/groups", json=group) as response:
                    content = await response.json()
                    if response.status != 201:
                        raise Exception(content)
                    group_id = content["id"]
        logger.info(f"Group {group_name} ID {group_id}")
        return group_id


async def main(args: Any):
    load_azd_env()

    if not os.getenv("AZURE_ADLS_GEN2_STORAGE_ACCOUNT"):
        raise Exception("AZURE_ADLS_GEN2_STORAGE_ACCOUNT must be set to continue")

    async with AzureDeveloperCliCredential() as credentials:
        with open(args.data_access_control) as f:
            data_access_control_format = json.load(f)
        command = AdlsGen2Setup(
            data_directory=args.data_directory,
            storage_account_name=os.environ["AZURE_ADLS_GEN2_STORAGE_ACCOUNT"],            
            filesystem_name=os.environ["AZURE_ADLS_GEN2_FILESYSTEM"],
            security_enabled_groups=args.create_security_enabled_groups,
            credentials=credentials,
            data_access_control_format=data_access_control_format,
        )
        await command.run(args.scandirs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upload data to a Data Lake Storage Gen2 account and associate access control lists with it using sample groups",
        epilog="Example: ./scripts/adlsgen2setup.py ./data --data-access-control .azure/${AZURE_ENV_NAME}/docs_acls.json --create-security-enabled-groups <true|false> --scandirs",
    )
    parser.add_argument("data_directory", help="Data directory that contains sample PDFs")
    parser.add_argument(
        "--create-security-enabled-groups",
        required=False,
        action="store_true",
        help="Whether or not the sample groups created are security enabled in Microsoft Entra",
    )
    parser.add_argument(
        "--data-access-control", required=True, help="JSON file describing access control for the sample data"
    )
    parser.add_argument("--verbose", "-v", required=False, action="store_true", help="Verbose output")
    parser.add_argument("--scandirs", required=False, action="store_true", help="Scan and upload all files from directories recursively")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig()
        logging.getLogger().setLevel(logging.INFO)        

    asyncio.run(main(args))
