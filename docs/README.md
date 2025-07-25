# 📚 Documentación Master - Azure Search OpenAI Demo

> **Índice consolidado de toda la documentación del proyecto**

## 🏗️ Arquitectura y Configuración

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [**ARCHITECTURE_AND_AUTH.md**](./ARCHITECTURE_AND_AUTH.md) | 🔐 Arquitectura de autenticación dual (Local vs Azure) | ✅ Actualizado |
| [azd.md](./azd.md) | 🚀 Deployment con Azure Developer CLI | ✅ |
| [azure_app_service.md](./azure_app_service.md) | 📱 Deployment en Azure App Service | ✅ |
| [azure_container_apps.md](./azure_container_apps.md) | 🐳 Deployment en Azure Container Apps | ✅ |

## 🔧 Desarrollo y Configuración

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [localdev.md](./localdev.md) | 💻 Desarrollo local | ✅ |
| [customization.md](./customization.md) | 🎨 Personalización del bot | ✅ |
| [data_ingestion.md](./data_ingestion.md) | 📥 Ingesta de datos | ✅ |

## 🔍 SharePoint Integration

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [sharepoint_deployment_guide.md](./sharepoint_deployment_guide.md) | 📂 Guía de integración SharePoint | ✅ |
| [../SHAREPOINT_INTEGRATION.md](../SHAREPOINT_INTEGRATION.md) | 🔗 Configuración SharePoint básica | ⚠️ Consolidar |
| [../SHAREPOINT_TECHNICAL_DETAILS.md](../SHAREPOINT_TECHNICAL_DETAILS.md) | 🔧 Detalles técnicos SharePoint | ⚠️ Consolidar |

## 🚀 Deployment y Troubleshooting

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [deploy_troubleshooting.md](./deploy_troubleshooting.md) | 🛠️ Solución de problemas de deployment | ✅ |
| [deploy_lowcost.md](./deploy_lowcost.md) | 💰 Deployment económico | ✅ |
| [monitoring.md](./monitoring.md) | 📊 Monitoreo y observabilidad | ✅ |

## 📊 Evaluación y Testing

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [evaluation.md](./evaluation.md) | 🧪 Evaluación de modelos | ✅ |
| [safety_evaluation.md](./safety_evaluation.md) | 🛡️ Evaluación de seguridad | ✅ |

## 🎯 Funcionalidades Avanzadas

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [agentic_retrieval.md](./agentic_retrieval.md) | 🤖 Retrieval inteligente | ✅ |
| [gpt4v.md](./gpt4v.md) | 👁️ Procesamiento de imágenes | ✅ |
| [reasoning.md](./reasoning.md) | 🧠 Modelos de razonamiento | ✅ |

## 📋 Documentos de Estado (A Consolidar)

> **⚠️ Estos documentos necesitan ser revisados y consolidados**

### Status Reports (Archivar o Consolidar)
- [../ESTADO_ACTUAL_DEPLOYMENT.md](../ESTADO_ACTUAL_DEPLOYMENT.md) - Estado del deployment (Jul 24)
- [../SESSION_STATUS_JULY22.md](../SESSION_STATUS_JULY22.md) - Estado de sesión Jul 22
- [../TECHNICAL_STATUS.md](../TECHNICAL_STATUS.md) - Estado técnico general
- [../PROGRESO_CITAS_SHAREPOINT.md](../PROGRESO_CITAS_SHAREPOINT.md) - Progreso SharePoint

### Guías Temporales (Consolidar)
- [../DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) → Mover a `docs/`
- [../POST_DEPLOYMENT_CONFIG.md](../POST_DEPLOYMENT_CONFIG.md) → Consolidar con troubleshooting
- [../SESSION_RECOVERY_GUIDE.md](../SESSION_RECOVERY_GUIDE.md) → Consolidar con troubleshooting

### Configuraciones Específicas (Mover a docs/)
- [../CONFIGURACION_AIBOT_SITE.md](../CONFIGURACION_AIBOT_SITE.md) → `docs/sharepoint_configuration.md`
- [../FRONTEND_PILOT_UPDATES.md](../FRONTEND_PILOT_UPDATES.md) → `docs/frontend_updates.md`

## 🔗 Quick Links

### 🚀 Para Desarrolladores
1. [Desarrollo Local](./localdev.md) - Configurar ambiente local
2. [Arquitectura de Auth](./ARCHITECTURE_AND_AUTH.md) - Entender autenticación
3. [Troubleshooting](./deploy_troubleshooting.md) - Resolver problemas

### 🏢 Para Deployment
1. [Azure Container Apps](./azure_container_apps.md) - Deployment recomendado
2. [AZD Guide](./azd.md) - Deployment automatizado
3. [SharePoint Setup](./sharepoint_deployment_guide.md) - Configurar SharePoint

### 🔧 Para Administradores
1. [Monitoring](./monitoring.md) - Configurar observabilidad
2. [Auth Architecture](./ARCHITECTURE_AND_AUTH.md) - Gestionar permisos RBAC
3. [Customization](./customization.md) - Personalizar comportamiento

---

> **📍 Último update**: Julio 25, 2025  
> **👤 Mantenido por**: Equipo de desarrollo  
> **🔄 Próxima revisión**: Consolidar documentos marcados con ⚠️

---

## 📝 Documentación Original (Referencia)

Consulta el [README principal](../README.md) para información general del proyecto.

### Temas Avanzados
- [Troubleshooting deployment](deploy_troubleshooting.md)
- [Debugging the app on App Service](appservice.md)
- [Deploying with existing Azure resources](deploy_existing.md)
- [Enabling optional features](deploy_features.md)
- [Login and access control](login_and_acl.md)
- [Private endpoints](deploy_private.md)
- [Sharing deployment environments](sharing_environments.md)
- [HTTP Protocol](http_protocol.md)
- [Productionizing](productionizing.md)
- [Alternative RAG chat samples](other_samples.md)
