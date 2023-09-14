import argparse
import aiohttp
from azure.identity.aio import AzureDeveloperCliCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import ResourceExistsError
from azure.storage.filedatalake.aio import (
    DataLakeServiceClient,
    DataLakeDirectoryClient
)
import os
import asyncio

class AdlsGen2Setup:
    async def __aenter__(self):
        self.service_client = DataLakeServiceClient(account_url=f"https://{self.storage_account_name}.dfs.core.windows.net", credential=self.credentials)
        await self.service_client.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.service_client.__aexit__(*args, **kwargs)

    def __init__(self, data_directory: str, storage_account_name: str, filesystem_name: str, security_enabled_groups: bool, credentials: AsyncTokenCredential, verbose: bool = False):
        self.data_directory = data_directory
        self.storage_account_name = storage_account_name
        self.filesystem_name = filesystem_name
        self.credentials = credentials
        self.security_enabled_groups = security_enabled_groups
        self.verbose = verbose

    async def run(self):
        token_result = await self.credentials.get_token("https://graph.microsoft.com/.default")
        self.graph_headers = { "Authorization": f"Bearer {token_result.token}"}
        if self.verbose: print("Ensuring gptkbcontainer exists...")
        async with self.service_client.get_file_system_client("gptkbcontainer") as filesystem_client:
            if not await filesystem_client.exists():
                await filesystem_client.create_file_system()

            if self.verbose: print("Creating groups...")
            admin_id = await self.create_or_get_group("GPTKB_AdminTest")
            hr_id = await self.create_or_get_group("GPTKB_HRTest")
            employee_id = await self.create_or_get_group("GPTKB_EmployeeTest")

            if self.verbose: print("Ensuring benefitinfo and employeeinfo directories exist...")
            async with await filesystem_client.create_directory("benefitinfo") as benefit_info, await filesystem_client.create_directory("employeeinfo") as employee_info:
                if self.verbose: print("Uploading PDFs...")
                await self.upload_file(directory_client=benefit_info, file_path=os.path.join(self.data_directory, "Benefit_Options.pdf"))
                await self.upload_file(directory_client=benefit_info, file_path=os.path.join(self.data_directory, "Northwind_Health_Plus_Benefits_Details.pdf"))
                await self.upload_file(directory_client=benefit_info, file_path=os.path.join(self.data_directory, "Northwind_Standard_Benefits_Details.pdf"))
                await self.upload_file(directory_client=benefit_info, file_path=os.path.join(self.data_directory, "PerksPlus.pdf"))
                await self.upload_file(directory_client=employee_info, file_path=os.path.join(self.data_directory, "role_library.pdf"))
                await self.upload_file(directory_client=employee_info, file_path=os.path.join(self.data_directory, "employee_handbook.pdf"))

                if self.verbose: print("Setting access control...")
                await filesystem_client._get_root_directory_client().set_access_control(acl=f"group:{employee_id}:r-x,group:{hr_id}:r-x")
                await filesystem_client._get_root_directory_client().update_access_control_recursive(acl=f"group:{admin_id}:r-x")

                await benefit_info.update_access_control_recursive(acl=f"group:{employee_id}:r-x")

                await benefit_info.update_access_control_recursive(acl=f"group:{hr_id}:r-x")
                await employee_info.update_access_control_recursive(acl=f"group:{hr_id}:r-x")


    async def upload_file(self, directory_client: DataLakeDirectoryClient, file_path: str):
        with open(file=file_path, mode="rb") as f:
            file_client = directory_client.get_file_client(file=os.path.basename(file_path))
            await file_client.upload_data(f, overwrite=True)

    
    async def create_or_get_group(self, group_name: str):
        group_id = None
        async with aiohttp.ClientSession(headers=self.graph_headers) as session:
            if self.verbose: print(f"Searching for group {group_name}...")
            async with session.get(f"https://graph.microsoft.com/v1.0/groups?$select=id&$top=1&$filter=displayName eq '{group_name}'") as response:
                if response.status != 200:
                    raise Exception(await response.json())
                content = await response.json()
                if len(content["value"]) == 1:
                    group_id = content["value"][0]["id"]
            if not group_id:
                if self.verbose: print(f"Could not find group {group_name}, creating...")
                group = {
                    "displayName": group_name,
                    "groupTypes": [
                        "Unified"
                    ],
                    "securityEnabled": self.security_enabled_groups
                }
                async with session.post(f"https://graph.microsoft.com/v1.0/groups", json=group):
                    if response.status != 201:
                        raise Exception(await response.json())
                    group_id = response.json()["id"]
        
        if self.verbose: print(f"Group {group_name} ID {group_id}")
        return group_id


async def main(args: any):
    async with AzureDeveloperCliCredential() as credentials, AdlsGen2Setup(data_directory=args.data_directory, storage_account_name=args.storage_account, filesystem_name="gptkbcontainer", security_enabled_groups=args.create_security_enabled_groups, credentials=credentials, verbose=args.verbose) as command:
        await command.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upload sample data to a Data Lake Storage Gen2 account and associate sample access control lists with it using sample groups",
        epilog="Example: adlsgen2setup.py --storage-account <name of storage account> --create-security-enabled-groups <true|false>",
    )
    parser.add_argument("--data-directory", required=True, help="Data directory that contains sample PDFs")
    parser.add_argument("--storage-account", required=True, help="Name of the Data Lake Storage Gen2 account to upload the sample data to")
    parser.add_argument("--create-security-enabled-groups", required=False, action="store_true", help="Whether or not the sample groups created are security enabled in Azure AD")
    parser.add_argument("--verbose", "-v", required=False, action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    asyncio.run(main(args))
