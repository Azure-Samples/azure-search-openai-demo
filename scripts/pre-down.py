import argparse

from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

# Set up argument parsing
parser = argparse.ArgumentParser(description="Delete an Azure OpenAI deployment.")
parser.add_argument("--resource-name", required=True, help="The name of the Azure OpenAI resource.")
parser.add_argument("--resource-group", required=True, help="The name of the Azure resource group.")
parser.add_argument("--subscription-id", required=True, help="The Azure subscription ID.")

args = parser.parse_args()

# Authenticate using DefaultAzureCredential
credential = DefaultAzureCredential()

# Initialize the Cognitive Services client
client = CognitiveServicesManagementClient(credential, subscription_id=args.subscription_id)

# List all deployments
deployments = client.deployments.list(resource_group_name=args.resource_group, account_name=args.resource_name)

# Delete each deployment and wait for the operation to complete
for deployment in deployments:
    deployment_name = deployment.name
    if not deployment_name:
        continue
    poller = client.deployments.begin_delete(
        resource_group_name=args.resource_group, account_name=args.resource_name, deployment_name=deployment_name
    )
    poller.result()
    print(f"Deployment {deployment_name} deleted successfully.")
