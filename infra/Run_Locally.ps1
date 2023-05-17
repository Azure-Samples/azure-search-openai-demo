# To deploy this main.bicep manually:
# az login
# az account set --subscription <subscriptionId>

# Deploy the main bicep file
az deployment sub create -n main-deploy-20230516T235241Z --location eastus --template-file infra/main.bicep --parameters environmentName=qa location=eastus principalId=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx resourceGroupName=rg_xxx_openai_qa appSuffix=xxxopenaiqa backendServiceName=xxx-openai-qa deployOpenAIResources=false deployFormsRecognizerResources=false deployOpenAIUserRoles=false deployOpenAIAppRoles=false

# Deploy just the roles
az deployment sub create -n roles-deploy-20230517T1358Z --location eastus --template-file infra/core/security/createUserRoles.bicep --parameters principalId=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx principalType=ServicePrincipal

