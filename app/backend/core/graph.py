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
    """Descargar el contenido de un archivo específico"""
    url = f"{GRAPH_API}/drives/{drive_id}/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text
