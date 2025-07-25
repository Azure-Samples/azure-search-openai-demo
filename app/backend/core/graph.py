import requests
import os

GRAPH_API = "https://graph.microsoft.com/v1.0"

def get_access_token():
    """Obtener token de acceso usando client credentials"""
    url = f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}/oauth2/v2.0/token"
    data = {
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def get_drive_id(site_id, access_token):
    """Obtener el ID del drive de Documentos del sitio"""
    url = f"{GRAPH_API}/sites/{site_id}/drives"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    drives = response.json()["value"]
    for drive in drives:
        if drive["name"].lower().startswith("documentos"):
            return drive["id"]
    raise Exception("Drive 'Documentos' no encontrado.")

def list_pilotos_files(drive_id, access_token):
    """Listar archivos en la carpeta específica PILOTOS"""
    path = "Documentos Flightbot/PILOTOS"
    url = f"{GRAPH_API}/drives/{drive_id}/root:/{path}:/children"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["value"]

def get_file_content(drive_id, file_id, access_token):
    """Descargar y procesar el contenido de un archivo específico"""
    import tempfile
    from azure.identity import DefaultAzureCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
    
    url = f"{GRAPH_API}/drives/{drive_id}/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Verificar si es un archivo PDF o binario
    content_type = response.headers.get('content-type', '').lower()
    
    if 'pdf' in content_type or response.content[:4] == b'%PDF':
        try:
            # Procesar PDF con Document Intelligence
            doc_intelligence_service = os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE")
            if not doc_intelligence_service:
                return f"Documento PDF disponible en SharePoint (Document Intelligence no configurado)"
            
            credential = DefaultAzureCredential()
            doc_client = DocumentIntelligenceClient(
                endpoint=f"https://{doc_intelligence_service}.cognitiveservices.azure.com/",
                credential=credential
            )
            
            # Crear archivo temporal con el PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_file.flush()
                
                # Analizar documento
                with open(tmp_file.name, "rb") as f:
                    poller = doc_client.begin_analyze_document(
                        "prebuilt-read", 
                        analyze_request=AnalyzeDocumentRequest(bytes_source=f.read()),
                        content_type="application/octet-stream"
                    )
                    result = poller.result()
                    
                    # Extraer texto
                    if result.content:
                        return result.content
                    else:
                        return f"Documento PDF procesado pero sin contenido de texto extraído"
                        
        except Exception as e:
            print(f"Error procesando PDF con Document Intelligence: {e}")
            
            # Fallback: obtener información del archivo y generar contenido descriptivo
            try:
                file_info_url = f"{GRAPH_API}/drives/{drive_id}/items/{file_id}"
                file_response = requests.get(file_info_url, headers=headers)
                file_info = file_response.json()
                filename = file_info.get('name', 'documento.pdf')
                
                return f"Documento PDF: {filename}. Contenido no procesable con Document Intelligence, requiere revisión manual. Error: {str(e)}"
            except:
                return f"Documento PDF disponible en SharePoint (error en procesamiento: {str(e)})"
        finally:
            # Limpiar archivo temporal
            import os as temp_os
            try:
                temp_os.unlink(tmp_file.name)
            except:
                pass
    else:
        # Para archivos de texto, devolver el contenido
        return response.text

def get_sharepoint_config_summary():
    """Obtener resumen de configuración de SharePoint - Updated"""
    try:
        access_token = get_access_token()
        
        # Usar el SITE_ID hardcodeado
        site_id = os.getenv("SITE_ID", "lumston.sharepoint.com,eb1c1d06-9351-4a7d-ba09-9e1f54a3266d,634751fa-b01f-4197-971b-80c1cf5d18db")
        drive_id = os.getenv("DRIVE_ID", "b!Bh0c61GTfUq6CZ4fVKMmbfpRR2MfsJdBlxuAwc9dGNuwQn6ELM4KSYbgTdG2Ctzo")
        
        # Listar archivos en el drive
        files = list_pilotos_files(drive_id, access_token)
        
        return {
            "site_id": site_id,
            "drive_id": drive_id,
            "files_found": len(files),
            "sample_files": [f.get("name", "Sin nombre") for f in files[:5]],
            "authentication": "success"
        }
    except Exception as e:
        return {
            "error": str(e),
            "authentication": "failed"
        }
