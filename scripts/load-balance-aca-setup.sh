 #!/bin/sh

# To set up AZD environment variabless 
# for use with ACA load balancer https://github.com/Azure-Samples/openai-aca-lb
#
# Prereq: az login --use-device-code
# Example usage: bash load-balance-aca-setup.sh <ACA-LB-RESOURCE-GROUP-NAME> <ACA-LB-CONTAINER-APP-URI>

resourceGroupName="your-resource-group-name"
containerAppName="your-container-app-name"

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

fqdn=$(az container show --name $containerAppName --resource-group $resourceGroupName --query ipAddress.fqdn --output tsv)

# Check if fqdn is empty
if [ -z "$fqdn" ]; then
    echo "Error: fqdn is empty"
    exit 1
fi

azd env set OPENAI_HOST azure_custom
azd env set AZURE_OPENAI_CUSTOM_URL $fqdn

