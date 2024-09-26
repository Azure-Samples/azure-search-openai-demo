$roles = @(
    "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd",
    "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1",
    "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
    "1407120a-92aa-4202-b7e9-c0e197c71c8f",
    "8ebe5a00-799e-43f5-93ac-243d3dce84a7"
)

AZURE_RESOURCE_GROUP = $(azd env get-value AZURE_RESOURCE_GROUP)

if ([string]::IsNullOrEmpty($AZURE_RESOURCE_GROUP)) {
    AZURE_ENV_NAME=$(azd env get-value AZURE_ENV_NAME)
    AZURE_RESOURCE_GROUP = "rg-$AZURE_ENV_NAME"
    azd env set AZURE_RESOURCE_GROUP $env:AZURE_RESOURCE_GROUP
}

AZURE_PRINCIPAL_ID = $(azd env get-value AZURE_PRINCIPAL_ID)
AZURE_SUBSCRIPTION_ID = $(azd env get-value AZURE_SUBSCRIPTION_ID)
foreach ($role in $roles) {
    az role assignment create `
        --role $role `
        --assignee-object-id $AZURE_PRINCIPAL_ID `
        --scope /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP `
        --assignee-principal-type User
}
