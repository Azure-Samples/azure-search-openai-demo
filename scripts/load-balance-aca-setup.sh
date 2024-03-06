 #!/bin/sh

# To set up AZD environment variabless
# for use with ACA load balancer https://github.com/Azure-Samples/openai-aca-lb

# Fill in your resource group name and container app name:
resourceGroupName="your-resource-group-name"
containerAppName="your-container-app-name"

if [ -z "$(az account show)" ]; then
    echo "You are not logged in. Please run 'az login' or 'az login --use-device-code' first."
    exit 1
fi

echo "Running provisioning using this subscription:"
az account show --query "{subscriptionId:id, name:name}"
echo "If that is not the correct subscription, please run 'az account set --subscription \"<SUBSCRIPTION-NAME>\"'"

# Check if resourceGroupName is empty
if [ -z "$resourceGroupName" ]; then
    echo "Error: resourceGroupName is empty"
    exit 1
fi

# Check if containerAppName is empty
if [ -z "$containerAppName" ]; then
    echo "Error: containerAppName is empty"
    exit 1
fi

fqdn=$(az containerapp show --name $containerAppName --resource-group $resourceGroupName --query properties.configuration.ingress.fqdn --output tsv)
fqdn="https://$fqdn"

# Check if fqdn is empty
if [ -z "$fqdn" ]; then
    echo "Error: fqdn is empty"
    exit 1
fi

azd env set OPENAI_HOST azure_custom
azd env set AZURE_OPENAI_CUSTOM_URL $fqdn
echo "Successfully set OPENAI_HOST to azure_custom and AZURE_OPENAI_CUSTOM_URL to $fqdn"
