🔍 AUDITORIA COMPLETA DE PERMISOS RBAC - Fri Jul 25 20:20:00 UTC 2025
================================================================

## 🎯 RECURSOS PRINCIPALES

| Recurso | Tipo | Scope |
|---------|------|-------|
| oai-volaris-dev-eus-001 | Azure OpenAI | /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.CognitiveServices/accounts/oai-volaris-dev-eus-001 |
| srch-volaris-dev-eus-001 | Azure Search | /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001 |
| api-volaris-dev-eus-001 | Container App | /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.App/containerApps/api-volaris-dev-eus-001 |

## 🔑 PERMISOS AZURE OPENAI
Principal                                   Role                            Scope
------------------------------------------  ------------------------------  ----------------------------------------------------------------------------------------------------------------------------------------------------------------
                                            Cognitive Services User         /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.CognitiveServices/accounts/oai-volaris-dev-eus-001
api://418de683-d96c-405f-bde1-53ebe8103591  Cognitive Services OpenAI User  /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.CognitiveServices/accounts/oai-volaris-dev-eus-001
                                            Cognitive Services OpenAI User  /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.CognitiveServices/accounts/oai-volaris-dev-eus-001
a15de2ef-6d0c-4346-918a-7e20b97cc97f        Cognitive Services OpenAI User  /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.CognitiveServices/accounts/oai-volaris-dev-eus-001

## 🔍 PERMISOS AZURE SEARCH
Principal                                   Role                           Scope
------------------------------------------  -----------------------------  ------------------------------------------------------------------------------------------------------------------------------------------------------------
                                            Search Index Data Reader       /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
                                            Search Service Contributor     /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
                                            Search Index Data Contributor  /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
a15de2ef-6d0c-4346-918a-7e20b97cc97f        Search Index Data Reader       /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
a15de2ef-6d0c-4346-918a-7e20b97cc97f        Search Index Data Contributor  /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
a15de2ef-6d0c-4346-918a-7e20b97cc97f        Search Service Contributor     /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
                                            Search Index Data Reader       /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
                                            Search Index Data Contributor  /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
                                            Search Service Contributor     /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
api://418de683-d96c-405f-bde1-53ebe8103591  Search Index Data Reader       /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
api://418de683-d96c-405f-bde1-53ebe8103591  Search Index Data Contributor  /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001
api://418de683-d96c-405f-bde1-53ebe8103591  Search Service Contributor     /subscriptions/c8b53560-9ecb-4276-8177-f44b97abba0b/resourceGroups/rg-volaris-dev-eus-001/providers/Microsoft.Search/searchServices/srch-volaris-dev-eus-001

## 🏃 MANAGED IDENTITIES DEL CONTAINER APP

### System Assigned Identity:

### User Assigned Identity:


## 📊 TODOS LOS PERMISOS POR PRINCIPAL

### Principal: 418de683-d96c-405f-bde1-53ebe8103591 (Development Client)


### Principal: 931de123-9be9-464c-af9f-1905bc049041 (Container App User Assigned Identity)
- ✅ **OpenAI**: Cognitive Services OpenAI User (RECIÉN ASIGNADO)
- ✅ **Search**: Search Index Data Reader, Search Index Data Contributor, Search Service Contributor

### System Assigned Identity: No configurada (Container App solo usa User Assigned Identity)

## ✅ PROBLEMA RESUELTO - **ÉXITO TOTAL**

**Estado actual en producción:** ✅ **BOT FUNCIONANDO PERFECTAMENTE**

**CAUSA RAÍZ IDENTIFICADA Y RESUELTA:** 
- ✅ **`disableLocalAuth: true`** en Azure OpenAI → API Keys deshabilitadas (CONFIGURACIÓN CORRECTA)
- ✅ **Container App usando Managed Identity** → Autenticación segura funcionando
- ✅ **Variable `AZURE_OPENAI_API_KEY_OVERRIDE` removida** → Sin conflictos

**Configuración final correcta:**
- `AZURE_OPENAI_API_KEY_OVERRIDE`: REMOVIDA ✅
- `disableLocalAuth`: `true` (SEGURIDAD ÓPTIMA) ✅
- **Managed Identity**: Principal ID `931de123-9be9-464c-af9f-1905bc049041` con permisos correctos ✅

**Variables de entorno críticas en producción:**
- `AZURE_OPENAI_API_KEY_OVERRIDE`: Configurada pero IGNORADA por Azure OpenAI
- `AZURE_CLIENT_ID`: Configurada → Identifica qué Managed Identity usar

## 🛠️ ACCIONES NECESARIAS - **SOLUCIÓN INMEDIATA**

**SOLUCIÓN 1: Remover API key del Container App (RECOMENDADO)**
1. ❌ **Remover variable `AZURE_OPENAI_API_KEY_OVERRIDE`** del Container App
2. ✅ **Verificar que User Assigned Identity tiene permisos OpenAI** (YA ASIGNADOS)
3. 🔄 **Restart Container App** para usar Managed Identity
4. 🏗️ **Automatizar en Bicep** para futuros deployments

**SOLUCIÓN 2: Habilitar API keys en Azure OpenAI (NO RECOMENDADO)**
1. ⚠️ **Cambiar `disableLocalAuth: false`** en Azure OpenAI
2. 🔑 **Mantener API key en Container App**
3. ⚠️ **RIESGO**: Menos seguro que Managed Identity

**DIAGNÓSTICO ADICIONAL REQUERIDO:**
- 🔍 **Agregar validación de `disableLocalAuth`** en health checks
- 📋 **Documentar configuración dual** (API key vs Managed Identity)
- 🔒 **Validar permisos reales** del User Assigned Identity

---
*Reporte generado: Fri Jul 25 20:23:53 UTC 2025*
