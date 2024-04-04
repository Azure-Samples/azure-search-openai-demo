import argparse
import asyncio
import json
import logging
import os
from typing import Any, Optional

import aiohttp
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential
from azure.storage.filedatalake.aio import (
    DataLakeDirectoryClient,
    DataLakeServiceClient,
)


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
            When creating groups in Azure AD, whether or not to make them security enabled
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

    async def run(self):
        async with self.create_service_client() as service_client:
            logging.info(f"Ensuring {self.filesystem_name} exists...")
            async with service_client.get_file_system_client(self.filesystem_name) as filesystem_client:
                if not await filesystem_client.exists():
                    await filesystem_client.create_file_system()

                logging.info("Creating groups...")
                groups: dict[str, str] = {}
                for group in self.data_access_control_format["groups"]:
                    group_id = await self.create_or_get_group(group)
                    groups[group] = group_id

                logging.info("Ensuring directories exist...")
                directories: dict[str, DataLakeDirectoryClient] = {}
                try:
                    for directory in self.data_access_control_format["directories"].keys():
                        directory_client = (
                            await filesystem_client.create_directory(directory)
                            if directory != "/"
                            else filesystem_client._get_root_directory_client()
                        )
                        directories[directory] = directory_client

                    logging.info("Uploading files...")
                    for file, file_info in self.data_access_control_format["files"].items():
                        directory = file_info["directory"]
                        if directory not in directories:
                            logging.error(f"File {file} has unknown directory {directory}, exiting...")
                            return
                        await self.upload_file(
                            directory_client=directories[directory], file_path=os.path.join(self.data_directory, file)
                        )

                    logging.info("Setting access control...")
                    for directory, access_control in self.data_access_control_format["directories"].items():
                        directory_client = directories[directory]
                        if "groups" in access_control:
                            for group_name in access_control["groups"]:
                                if group_name not in groups:
                                    logging.error(
                                        f"Directory {directory} has unknown group {group_name} in access control list, exiting"
                                    )
                                    return
                                await directory_client.update_access_control_recursive(
                                    acl=f"group:{groups[group_name]}:r-x"
                                )
                finally:
                    for directory_client in directories.values():
                        await directory_client.close()

    def create_service_client(self):
        return DataLakeServiceClient(
            account_url=f"https://{self.storage_account_name}.dfs.core.windows.net", credential=self.credentials
        )

    async def upload_file(self, directory_client: DataLakeDirectoryClient, file_path: str):
        with open(file=file_path, mode="rb") as f:
            file_client = directory_client.get_file_client(file=os.path.basename(file_path))
            await file_client.upload_data(f, overwrite=True)

    async def create_or_get_group(self, group_name: str):
        group_id = None
        if not self.graph_headers:
            token_result = await self.credentials.get_token("https://graph.microsoft.com/.default")
            self.graph_headers = {"Authorization": f"Bearer {token_result.token}"}
        async with aiohttp.ClientSession(headers=self.graph_headers) as session:
            logging.info(f"Searching for group {group_name}...")
            async with session.get(
                f"https://graph.microsoft.com/v1.0/groups?$select=id&$top=1&$filter=displayName eq '{group_name}'"
            ) as response:
                content = await response.json()
                if response.status != 200:
                    raise Exception(content)
                if len(content["value"]) == 1:
                    group_id = content["value"][0]["id"]
            if not group_id:
                logging.info(f"Could not find group {group_name}, creating...")
                group = {
                    "displayName": group_name,
                    "groupTypes": ["Unified"],
                    "securityEnabled": self.security_enabled_groups,
                }
                async with session.post("https://graph.microsoft.com/v1.0/groups", json=group) as response:
                    content = await response.json()
                    if response.status != 201:
                        raise Exception(content)
                    group_id = content["id"]
        logging.info(f"Group {group_name} ID {group_id}")
        return group_id


async def main(args: Any):
    async with AzureDeveloperCliCredential() as credentials:
        with open(args.data_access_control) as f:
            data_access_control_format = json.load(f)
        command = AdlsGen2Setup(
            data_directory=args.data_directory,
            storage_account_name=args.storage_account,
            filesystem_name="gptkbcontainer",
            security_enabled_groups=args.create_security_enabled_groups,
            credentials=credentials,
            data_access_control_format=data_access_control_format,
        )
        await command.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upload sample data to a Data Lake Storage Gen2 account and associate sample access control lists with it using sample groups",
        epilog="Example: ./scripts/adlsgen2setup.py ./data --data-access-control ./scripts/sampleacls.json --storage-account <name of storage account> --create-security-enabled-groups <true|false>",
    )
    parser.add_argument("data_directory", help="Data directory that contains sample PDFs")
    parser.add_argument(
        "--storage-account",
        required=True,
        help="Name of the Data Lake Storage Gen2 account to upload the sample data to",
    )
    parser.add_argument(
        "--create-security-enabled-groups",
        required=False,
        action="store_true",
        help="Whether or not the sample groups created are security enabled in Azure AD",
    )
    parser.add_argument(
        "--data-access-control", required=True, help="JSON file describing access control for the sample data"
    )
    parser.add_argument("--verbose", "-v", required=False, action="store_true", help="Verbose output")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig()
        logging.getLogger().setLevel(logging.INFO)

    asyncio.run(main(args))
