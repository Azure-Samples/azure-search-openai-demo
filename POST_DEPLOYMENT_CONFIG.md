# Post-Deployment Configuration Guide

**Created**: 17 de Julio de 2025  
**For**: Azure Container Apps deployment  
**Purpose**: Configuration reference for production environment

---

## 🔧 **REQUIRED ENVIRONMENT VARIABLES**

### **Critical SharePoint Variables**
Estas variables deben estar configuradas en el Container Apps environment:

```bash
# Azure AD Authentication
AZURE_CLIENT_APP_ID=418de683-d96c-405f-bde1-53ebe8103591
AZURE_CLIENT_APP_SECRET=<secret-value-configured-in-env>
AZURE_TENANT_ID=cee3a5ad-5671-483b-b551-7215dea20158

# SharePoint Configuration (hardcoded in graph.py)
# SITE_ID=lumston.sharepoint.com,eb1c1d06-9351-4a7d-ba09-9e1f54a3266d,634751fa-b01f-4197-971b-80c1cf5d18db
# DRIVE_ID=b!Bh0c61GTfUq6CZ4fVKMmbfpRR2MfsJdBlxuAwc9dGNuwQn6ELM4KSYbgTdG2Ctzo
```

### **Azure Services Configuration**
```bash
# AI Search
AZURE_SEARCH_SERVICE=search-volaris-dev-eus-001
AZURE_SEARCH_INDEX=gptkbindex

# OpenAI
AZURE_OPENAI_SERVICE=aoai-volaris-dev-eus-001
AZURE_OPENAI_CHATGPT_DEPLOYMENT=chat
AZURE_OPENAI_EMB_DEPLOYMENT=embedding

# Storage
AZURE_STORAGE_ACCOUNT=stgvolarisdeveus001
AZURE_STORAGE_CONTAINER=content
```

---

## 🏥 **HEALTH CHECK ENDPOINTS**

### **SharePoint Integration Validation**
```bash
# Verify SharePoint connection
GET /debug/sharepoint/config
Expected Response: 
{
  "status": "success",
  "files_found": 64,
  "site_name": "AIBotProjectAutomation"
}

# Test pilot query detection
POST /debug/pilot-query
Body: {"query": "documentos sobre pilotos"}
Expected Response:
{
  "is_pilot_related": true,
  "sharepoint_results_count": 3+
}
```

### **General Health Checks**
```bash
# Application health
GET /
Expected: Returns frontend application

# Backend configuration
GET /config
Expected: Returns application configuration object

# Authentication setup
GET /auth_setup
Expected: Returns MSAL configuration
```

---

## 🔍 **TROUBLESHOOTING GUIDE**

### **SharePoint Access Issues**
1. **Error**: "No documents found"
   - Check AZURE_CLIENT_APP_ID and secret are correctly set
   - Verify tenant_id matches Azure AD tenant
   - Test Graph API access manually

2. **Error**: "Authentication failed"
   - Validate App Registration permissions:
     - Sites.Read.All ✅
     - Files.Read.All ✅
     - Directory.Read.All ✅
   - Check secret hasn't expired

3. **Error**: "Site not found"
   - Verify SITE_ID in graph.py matches actual site
   - Check site permissions allow app access

### **Container Apps Specific Issues**
1. **Environment variables not loading**
   - Check azd deployment included all .env variables
   - Verify Container Apps environment variables section
   - Restart container app if needed

2. **Outbound connectivity issues**
   - Ensure Container Apps can reach graph.microsoft.com
   - Check no network security groups blocking HTTPS
   - Verify Container Apps environment network config

### **Performance Issues**
1. **Slow SharePoint responses**
   - Normal: First request may be slow (token acquisition)
   - Monitor: Subsequent requests should be faster
   - Cache: Graph client caches tokens for 1 hour

2. **Memory issues**
   - Monitor container memory usage
   - SharePoint responses can be large (64+ files)
   - Consider pagination for large document sets

---

## 📊 **MONITORING & LOGS**

### **Key Log Messages to Monitor**
```bash
# Successful SharePoint connection
"✅ Encontrados 64 archivos de pilotos"

# Authentication success
"Microsoft Graph client initialized successfully"

# Query detection working
"Pilot-related query detected: true"

# Error patterns to watch
"Error en debug_sharepoint:"
"Authentication failed to Graph API"
"Site not found or access denied"
```

### **Application Insights Queries**
```kusto
// SharePoint integration performance
requests
| where name contains "sharepoint"
| summarize avg(duration), count() by name
| order by avg_duration desc

// Pilot query detection frequency
traces
| where message contains "Pilot-related query detected"
| summarize count() by bin(timestamp, 1h)

// SharePoint errors
exceptions
| where outerMessage contains "sharepoint" or outerMessage contains "graph"
| order by timestamp desc
```

---

## 🔄 **UPDATING SHAREPOINT CONFIGURATION**

### **To Change Target Site**
1. Update hardcoded values in `app/backend/core/graph.py`:
   ```python
   self.specific_site_id = "new-site-id-here"
   self.specific_drive_id = "new-drive-id-here"
   ```

2. Redeploy with `azd up`

### **To Add New Document Sources**
1. Update folder search configuration in graph.py
2. Modify search keywords in chatreadretrieveread.py
3. Test with debug endpoints before deployment

### **To Update Authentication**
1. Generate new client secret in Azure AD
2. Update AZURE_CLIENT_APP_SECRET in .env
3. Redeploy application

---

## ✅ **DEPLOYMENT VALIDATION CHECKLIST**

Post-deployment, verify these items:

- [ ] GET /debug/sharepoint/config returns 64+ files
- [ ] POST /debug/pilot-query detects pilot queries correctly
- [ ] Chat queries about "pilotos" return SharePoint results
- [ ] No authentication errors in Application Insights
- [ ] Response times for pilot queries < 10 seconds
- [ ] Container Apps shows "Running" status
- [ ] No memory or CPU issues in container metrics

---

## 📞 **SUPPORT INFORMATION**

### **Technical Contacts**
- Development Team: GitHub repository issues
- Azure Support: For infrastructure issues
- Microsoft Graph Support: For API-related issues

### **Key Documentation**
- Microsoft Graph API: https://docs.microsoft.com/en-us/graph/
- Azure Container Apps: https://docs.microsoft.com/en-us/azure/container-apps/
- SharePoint API: https://docs.microsoft.com/en-us/sharepoint/dev/apis/

---

**Last Updated**: 17 de Julio de 2025  
**Next Review**: Post first production deployment
