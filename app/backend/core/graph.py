import requests
import os
import logging
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class GraphClient:
    """Cliente para interactuar con Microsoft Graph API y SharePoint"""
    
    def __init__(self):
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_APP_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_APP_SECRET')
        self.base_url = "https://graph.microsoft.com/v1.0"
        self._token = None
    
    def get_graph_token(self) -> str:
        """Obtiene token de acceso para Microsoft Graph API"""
        try:
            url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self._token = token_data["access_token"]
            return self._token
            
        except Exception as e:
            logger.error(f"Error obteniendo token de Graph API: {e}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """Obtiene headers con token de autorización"""
        if not self._token:
            self.get_graph_token()
        
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }
    
    def get_sharepoint_sites(self) -> List[Dict]:
        """Obtiene lista de sitios de SharePoint"""
        try:
            url = f"{self.base_url}/sites"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            return response.json().get("value", [])
            
        except Exception as e:
            logger.error(f"Error obteniendo sitios de SharePoint: {e}")
            return []
    
    def find_site_by_name(self, site_name: str) -> Optional[Dict]:
        """Busca un sitio de SharePoint por nombre"""
        sites = self.get_sharepoint_sites()
        for site in sites:
            if site_name.lower() in site.get("displayName", "").lower():
                return site
        return None
    
    def get_drive_items(self, site_id: str, drive_id: str = None, folder_path: str = "") -> List[Dict]:
        """Obtiene elementos de una unidad de SharePoint"""
        try:
            if drive_id:
                url = f"{self.base_url}/sites/{site_id}/drives/{drive_id}/root"
            else:
                url = f"{self.base_url}/sites/{site_id}/drive/root"
            
            if folder_path:
                url += f":/{folder_path}:"
            
            url += "/children"
            
            headers = self._get_headers()
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            return response.json().get("value", [])
            
        except Exception as e:
            logger.error(f"Error obteniendo elementos de la unidad: {e}")
            return []
    
    def search_files_in_pilotos_folder(self, site_id: str = None, site_name: str = "SharePoint") -> List[Dict]:
        """Busca archivos específicamente en la carpeta 'Pilotos'"""
        try:
            # Si no se proporciona site_id, buscar por nombre
            if not site_id:
                site = self.find_site_by_name(site_name)
                if not site:
                    logger.warning(f"No se encontró el sitio: {site_name}")
                    return []
                site_id = site["id"]
            
            # Buscar en la carpeta "Pilotos"
            pilotos_files = self.get_drive_items(site_id, folder_path="Pilotos")
            
            # Filtrar solo archivos (no carpetas)
            files = []
            for item in pilotos_files:
                if "file" in item:  # Es un archivo, no una carpeta
                    files.append({
                        "id": item["id"],
                        "name": item["name"],
                        "webUrl": item["webUrl"],
                        "downloadUrl": item.get("@microsoft.graph.downloadUrl", ""),
                        "size": item.get("size", 0),
                        "lastModified": item.get("lastModifiedDateTime", ""),
                        "createdBy": item.get("createdBy", {}).get("user", {}).get("displayName", ""),
                        "mimeType": item.get("file", {}).get("mimeType", "")
                    })
            
            logger.info(f"Encontrados {len(files)} archivos en la carpeta Pilotos")
            return files
            
        except Exception as e:
            logger.error(f"Error buscando archivos en carpeta Pilotos: {e}")
            return []
    
    def download_file(self, download_url: str) -> bytes:
        """Descarga un archivo desde SharePoint"""
        try:
            headers = self._get_headers()
            response = requests.get(download_url, headers=headers)
            response.raise_for_status()
            return response.content
            
        except Exception as e:
            logger.error(f"Error descargando archivo: {e}")
            return b""
    
    def search_files_by_query(self, query: str, site_id: str = None) -> List[Dict]:
        """Busca archivos en SharePoint usando una consulta"""
        try:
            if not site_id:
                # Usar el primer sitio disponible si no se especifica
                sites = self.get_sharepoint_sites()
                if not sites:
                    return []
                site_id = sites[0]["id"]
            
            url = f"{self.base_url}/sites/{site_id}/drive/search(q='{query}')"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            results = response.json().get("value", [])
            
            # Formatear resultados
            files = []
            for item in results:
                if "file" in item:
                    files.append({
                        "id": item["id"],
                        "name": item["name"],
                        "webUrl": item["webUrl"],
                        "downloadUrl": item.get("@microsoft.graph.downloadUrl", ""),
                        "size": item.get("size", 0),
                        "lastModified": item.get("lastModifiedDateTime", ""),
                        "parentPath": item.get("parentReference", {}).get("path", ""),
                        "mimeType": item.get("file", {}).get("mimeType", "")
                    })
            
            return files
            
        except Exception as e:
            logger.error(f"Error buscando archivos con query '{query}': {e}")
            return []
    
    def get_file_content(self, site_id: str, file_id: str) -> str:
        """Obtiene el contenido de un archivo de texto desde SharePoint"""
        try:
            url = f"{self.base_url}/sites/{site_id}/drive/items/{file_id}/content"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Intentar decodificar como texto
            try:
                return response.content.decode('utf-8')
            except UnicodeDecodeError:
                # Si falla UTF-8, intentar con latin-1
                return response.content.decode('latin-1', errors='ignore')
                
        except Exception as e:
            logger.error(f"Error obteniendo contenido del archivo {file_id}: {e}")
            return ""


# Instancia global del cliente
graph_client = GraphClient()


# Funciones de conveniencia para usar en la aplicación
def get_pilotos_files(site_name: str = "SharePoint") -> List[Dict]:
    """Función de conveniencia para obtener archivos de la carpeta Pilotos"""
    return graph_client.search_files_in_pilotos_folder(site_name=site_name)


def search_sharepoint_files(query: str, site_name: str = "SharePoint") -> List[Dict]:
    """Función de conveniencia para buscar archivos en SharePoint"""
    site = graph_client.find_site_by_name(site_name)
    if not site:
        return []
    
    return graph_client.search_files_by_query(query, site["id"])


def download_sharepoint_file(download_url: str) -> bytes:
    """Función de conveniencia para descargar archivos de SharePoint"""
    return graph_client.download_file(download_url)
