# Azure Key Vault Setup Guide

This guide explains how to set up Azure Key Vault for secret management in the AI Master Engineer application.

## Overview

Azure Key Vault provides secure storage for application secrets such as:
- Bot Framework credentials (`MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`)
- Azure service keys (`AZURE_SEARCH_KEY`, `AZURE_OPENAI_API_KEY`)
- Web search API keys (`SERPER_API_KEY`, `FIRECRAWL_API_KEY`, etc.)

## Prerequisites

- Azure subscription with appropriate permissions
- Azure CLI or Azure Portal access
- Application deployed (or ready to deploy)

## Setup Steps

### 1. Enable Key Vault in Bicep Deployment

Update `infra/main.parameters.json` or pass parameter during deployment:

```json
{
  "enableKeyVault": {
    "value": true
  },
  "keyVaultName": {
    "value": ""  // Optional: will be auto-generated if empty
  }
}
```

Or use `azd` command:

```bash
azd up --parameter enableKeyVault=true
```

### 2. Deploy Infrastructure

The Key Vault will be created automatically with the deployment:

```bash
azd up
```

### 3. Grant Access to App Services

After deployment, you need to grant the App Service Managed Identities access to Key Vault.

#### Option A: Using Azure Portal

1. Navigate to your Key Vault in Azure Portal
2. Go to **Access policies** → **Add access policy**
3. For each App Service (backend and agents):
   - **Select principal**: Search for the App Service name
   - **Secret permissions**: Select `Get` and `List`
   - Click **Add**
4. Click **Save**

#### Option B: Using Azure CLI

```bash
# Get Key Vault name
KEY_VAULT_NAME=$(az keyvault list --query "[?contains(name, 'kv-')].name" -o tsv | head -n 1)

# Get App Service principal IDs
BACKEND_PRINCIPAL_ID=$(az webapp identity show --name <backend-app-name> --resource-group <rg-name> --query principalId -o tsv)
AGENTS_PRINCIPAL_ID=$(az webapp identity show --name <agents-app-name> --resource-group <rg-name> --query principalId -o tsv)

# Grant access
az keyvault set-policy \
  --name $KEY_VAULT_NAME \
  --object-id $BACKEND_PRINCIPAL_ID \
  --secret-permissions get list

az keyvault set-policy \
  --name $KEY_VAULT_NAME \
  --object-id $AGENTS_PRINCIPAL_ID \
  --secret-permissions get list
```

#### Option C: Using PowerShell Script

```powershell
# Get Key Vault name
$keyVaultName = (Get-AzKeyVault -ResourceGroupName "<rg-name>").VaultName

# Get App Service principal IDs
$backendPrincipalId = (Get-AzWebApp -ResourceGroupName "<rg-name>" -Name "<backend-app-name>").Identity.PrincipalId
$agentsPrincipalId = (Get-AzWebApp -ResourceGroupName "<rg-name>" -Name "<agents-app-name>").Identity.PrincipalId

# Grant access
Set-AzKeyVaultAccessPolicy `
  -VaultName $keyVaultName `
  -ObjectId $backendPrincipalId `
  -PermissionsToSecrets Get,List

Set-AzKeyVaultAccessPolicy `
  -VaultName $keyVaultName `
  -ObjectId $agentsPrincipalId `
  -PermissionsToSecrets Get,List
```

### 4. Store Secrets in Key Vault

#### Using Azure Portal

1. Navigate to Key Vault → **Secrets** → **Generate/Import**
2. Create secrets with these names:
   - `MICROSOFT-APP-ID`
   - `MICROSOFT-APP-PASSWORD`
   - `AZURE-SEARCH-KEY`
   - `AZURE-OPENAI-API-KEY`
   - `AZURE-CLIENT-SECRET`
   - `SERPER-API-KEY` (optional)
   - `FIRECRAWL-API-KEY` (optional)
   - `COHERE-API-KEY` (optional)
   - `DEEPSEEK-API-KEY` (optional)

#### Using Azure CLI

```bash
KEY_VAULT_NAME="<your-keyvault-name>"

az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name "MICROSOFT-APP-ID" \
  --value "<your-app-id>"

az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name "MICROSOFT-APP-PASSWORD" \
  --value "<your-app-password>"

az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name "AZURE-SEARCH-KEY" \
  --value "<your-search-key>"

# ... repeat for other secrets
```

#### Using PowerShell

```powershell
$keyVaultName = "<your-keyvault-name>"

Set-AzKeyVaultSecret `
  -VaultName $keyVaultName `
  -Name "MICROSOFT-APP-ID" `
  -SecretValue (ConvertTo-SecureString "<your-app-id>" -AsPlainText -Force)

Set-AzKeyVaultSecret `
  -VaultName $keyVaultName `
  -Name "MICROSOFT-APP-PASSWORD" `
  -SecretValue (ConvertTo-SecureString "<your-app-password>" -AsPlainText -Force)

# ... repeat for other secrets
```

### 5. Update Application Code

The application code already supports Key Vault. It will automatically:
1. Try to read from Key Vault using Managed Identity
2. Fall back to environment variables if Key Vault is not available

The Key Vault URL is automatically set in App Service configuration as `AZURE_KEY_VAULT_ENDPOINT`.

### 6. Verify Secret Access

#### Test from App Service Logs

Check Application Insights or App Service logs for:
- "Key Vault client initialized" (success)
- "Failed to initialize Key Vault client" (fallback to env vars)

#### Test via API

```bash
# Check backend health (should show healthy status)
curl https://<backend-app>.azurewebsites.net/health

# Check agents health (should show healthy status)
curl https://<agents-app>.azurewebsites.net/api/health
```

## Secret Naming Convention

Key Vault secrets use **hyphens** (`-`) instead of underscores (`_`):
- Environment variable: `MICROSOFT_APP_ID`
- Key Vault secret: `MICROSOFT-APP-ID`

The code automatically converts between these formats.

## Troubleshooting

### Secrets not found

1. **Check access policies**: Ensure App Service Managed Identity has `Get` and `List` permissions
2. **Check secret names**: Use hyphens, not underscores
3. **Check Key Vault URL**: Verify `AZURE_KEY_VAULT_ENDPOINT` is set in App Service configuration
4. **Check logs**: Application will log warnings if Key Vault access fails

### Access denied

1. **Verify Managed Identity**: Ensure App Service has System Assigned Managed Identity enabled
2. **Verify permissions**: Check Key Vault access policies include the App Service principal ID
3. **Wait for propagation**: Access policy changes may take a few minutes to propagate

### Fallback to environment variables

If Key Vault is not configured or unavailable, the application will automatically fall back to environment variables. This is expected behavior for:
- Local development
- When Key Vault is disabled
- When Key Vault is temporarily unavailable

## Best Practices

1. **Enable soft delete**: Already enabled by default (7 days retention)
2. **Enable purge protection**: For production (currently disabled by default)
3. **Rotate secrets regularly**: Update secrets in Key Vault, no code changes needed
4. **Monitor access**: Use Key Vault access logs to track secret access
5. **Use separate Key Vaults**: Consider separate Key Vaults for dev/staging/production

## Security Considerations

- **Network access**: Key Vault allows Azure services by default
- **Private endpoints**: Can be configured for private network access
- **Access policies**: Use least privilege (only `Get` and `List` for secrets)
- **Audit logging**: Enable diagnostic logs for Key Vault access

## Next Steps

After Key Vault is set up:
1. Remove secrets from App Service configuration (optional, but recommended)
2. Test application functionality
3. Monitor Key Vault access logs
4. Set up secret rotation policies (if applicable)





