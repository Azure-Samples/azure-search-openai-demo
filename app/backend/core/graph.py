import requests
import os
import logging
from typing import List, Dict, Optional
import json
import sys

# Configurar logging más detallado para debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Importar configuración de SharePoint
try:
    from sharepoint_config.sharepoint_config import sharepoint_config
except ImportError:
    # Fallback si no se puede importar la configuración
    class FallbackConfig:
        def get_search_folders(self): return ["Pilotos"]
        def get_site_keywords(self): return ["company", "general", "operativ", "pilot"]
        def get_search_queries(self): return ["pilotos"]
        def get_max_sites(self): return 15
        def get_search_depth(self): return 5
        def is_content_fallback_enabled(self): return True
    
    sharepoint_config = FallbackConfig()
    logger.warning("Usando configuración fallback para SharePoint")

class GraphClient:
    """Cliente para interactuar con Microsoft Graph API y SharePoint"""
    
    def __init__(self):
        self.tenant_id = os.getenv('AZURE_AUTH_TENANT_ID') or os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_APP_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_APP_SECRET')
        # Usar Site ID y Drive ID específicos si están configurados
        self.specific_site_id = os.getenv('SITE_ID')
        self.specific_drive_id = os.getenv('DRIVE_ID')
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
        """Obtiene lista de sitios de SharePoint incluyendo sitios de Teams/Groups"""
        try:
            sites = []
            
            # Obtener sitios estándar de SharePoint
            url = f"{self.base_url}/sites"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            standard_sites = response.json().get("value", [])
            sites.extend(standard_sites)
            
            # Obtener sitios de Teams/Groups
            try:
                groups_url = f"{self.base_url}/groups?$filter=resourceProvisioningOptions/any(x:x eq 'Team')"
                groups_response = requests.get(groups_url, headers=headers)
                groups_response.raise_for_status()
                
                groups = groups_response.json().get("value", [])
                
                for group in groups:
                    # Para cada grupo de Teams, obtener su sitio de SharePoint
                    try:
                        group_id = group["id"]
                        site_url = f"{self.base_url}/groups/{group_id}/sites/root"
                        site_response = requests.get(site_url, headers=headers)
                        site_response.raise_for_status()
                        
                        team_site = site_response.json()
                        # Marcar que es un sitio de Teams
                        team_site["isTeamSite"] = True
                        team_site["teamDisplayName"] = group.get("displayName", "")
                        sites.append(team_site)
                        
                    except Exception as e:
                        logger.warning(f"Error obteniendo sitio para grupo {group.get('displayName', '')}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Error obteniendo sitios de Teams: {e}")
            
            logger.info(f"Encontrados {len(sites)} sitios en total (estándar + Teams)")
            return sites
            
        except Exception as e:
            logger.error(f"Error obteniendo sitios de SharePoint: {e}")
            return []

    def find_site_by_name(self, site_name: str) -> Optional[Dict]:
        """Busca un sitio de SharePoint por nombre (incluyendo sitios de Teams)"""
        sites = self.get_sharepoint_sites()
        site_name_lower = site_name.lower()
        
        # Primero buscar coincidencia exacta
        for site in sites:
            display_name = site.get("displayName", "").lower()
            team_name = site.get("teamDisplayName", "").lower()
            
            if (site_name_lower == display_name or 
                site_name_lower == team_name or
                site_name_lower in display_name or 
                site_name_lower in team_name):
                logger.info(f"Sitio encontrado: {site.get('displayName', '')} (Teams: {site.get('isTeamSite', False)})")
                return site
        
        # Si no se encuentra, buscar por partes del nombre
        for site in sites:
            display_name = site.get("displayName", "").lower()
            team_name = site.get("teamDisplayName", "").lower()
            web_url = site.get("webUrl", "").lower()
            
            # Buscar en la URL también
            if (any(word in display_name for word in site_name_lower.split()) or
                any(word in team_name for word in site_name_lower.split()) or
                site_name_lower.replace(" ", "").replace("-", "") in web_url.replace("-", "")):
                logger.info(f"Sitio encontrado por coincidencia parcial: {site.get('displayName', '')} (Teams: {site.get('isTeamSite', False)})")
                return site
        
        return None
    
    def find_site_by_url(self, site_url: str) -> Optional[Dict]:
        """Busca un sitio de SharePoint por su URL"""
        try:
            # Extraer el path del sitio de la URL
            # Por ejemplo: https://lumston.sharepoint.com/sites/Softwareengineering/ -> Softwareengineering
            if "/sites/" in site_url:
                site_path = site_url.split("/sites/")[1].rstrip("/")
                
                # Buscar usando Graph API directamente por hostname y path
                url = f"{self.base_url}/sites/lumston.sharepoint.com:/sites/{site_path}:"
                headers = self._get_headers()
                
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                site = response.json()
                logger.info(f"Sitio encontrado por URL: {site.get('displayName', '')}")
                return site
                
        except Exception as e:
            logger.warning(f"Error buscando sitio por URL {site_url}: {e}")
            
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
    
    def find_configured_folder_recursive(self, site_id: str, folder_name: str, current_path: str = "", depth: int = 0) -> Optional[str]:
        """Busca recursivamente una carpeta configurada en toda la estructura de SharePoint"""
        max_depth = sharepoint_config.get_search_depth()
        
        if depth > max_depth:
            logger.warning(f"Máxima profundidad alcanzada ({max_depth}) en búsqueda recursiva")
            return None
        
        try:
            logger.debug(f"Buscando carpeta '{folder_name}' en ruta: '{current_path}' (profundidad: {depth})")
            items = self.get_drive_items(site_id, folder_path=current_path)
            
            for item in items:
                item_name = item.get("name", "").lower()
                folder_name_lower = folder_name.lower()
                
                # Si encontramos la carpeta específica
                if item_name == folder_name_lower and "folder" in item:
                    found_path = f"{current_path}/{item['name']}" if current_path else item['name']
                    logger.info(f"¡Carpeta {folder_name} encontrada en: {found_path}")
                    return found_path
                
                # Si es una carpeta que podría contener documentos relevantes, buscar dentro
                if ("folder" in item and 
                    any(keyword in item_name for keyword in ["documentos", "compartidos", "documents", "shared", "files", "archivos"])):
                    
                    nested_path = f"{current_path}/{item['name']}" if current_path else item['name']
                    logger.debug(f"  Buscando recursivamente en carpeta: '{nested_path}'")
                    
                    result = self.find_configured_folder_recursive(site_id, folder_name, nested_path, depth + 1)
                    if result:
                        return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error en búsqueda recursiva de '{folder_name}' en '{current_path}': {e}")
            return None

    def find_configured_folder_in_document_library(self, site_id: str, folder_name: str) -> Optional[str]:
        """Busca una carpeta configurada específicamente en la biblioteca de documentos"""
        try:
            logger.info(f"Buscando carpeta '{folder_name}' en la biblioteca de documentos...")
            
            # Obtener elementos de la biblioteca de documentos
            library_items = self.get_document_library_items(site_id)
            
            for item in library_items:
                fields = item.get("fields", {})
                content_type = fields.get("ContentType", "")
                file_leaf_ref = fields.get("FileLeafRef", "")
                file_ref = fields.get("FileRef", "")
                
                # Buscar carpetas que coincidan con el nombre configurado
                if ("folder" in content_type.lower() and 
                    folder_name.lower() in file_leaf_ref.lower()):
                    logger.info(f"¡Carpeta {folder_name} encontrada en biblioteca: {file_ref}")
                    return file_ref
            
            # Si no se encuentra directamente, buscar en subcarpetas relevantes
            logger.debug(f"No se encontró {folder_name} en el nivel raíz, buscando en subcarpetas...")
            
            for item in library_items:
                fields = item.get("fields", {})
                content_type = fields.get("ContentType", "")
                file_leaf_ref = fields.get("FileLeafRef", "")
                file_ref = fields.get("FileRef", "")
                
                if ("folder" in content_type.lower() and 
                    any(keyword in file_leaf_ref.lower() for keyword in ["documentos", "compartidos", "documents", "shared"])):
                    
                    logger.debug(f"Explorando subcarpeta relacionada: {file_leaf_ref}")
                    # Buscar recursivamente en esta carpeta
                    subfolder_path = file_ref.split("/")[-1]  # Obtener solo el nombre de la carpeta
                    result = self.find_configured_folder_recursive(site_id, folder_name, subfolder_path)
                    if result:
                        return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error buscando '{folder_name}' en biblioteca de documentos: {e}")
            return None

    def search_files_in_configured_folders(self, site_id: str = None, site_name: str = None) -> List[Dict]:
        """Busca archivos en las carpetas configuradas dinámicamente"""
        try:
            # PRIORIDAD 1: Usar SITE_ID específico del .env si está configurado
            if not site_id and self.specific_site_id:
                logger.info(f"Usando SITE_ID específico del .env: {self.specific_site_id}")
                return self._search_files_in_single_site(self.specific_site_id, "AIBotProjectAutomation (Específico)")
            
            # PRIORIDAD 2: Si no se proporciona site_id, buscar dinámicamente en sitios de Teams
            if not site_id:
                logger.info("No se proporcionó site_id, buscando en sitios de Teams disponibles...")
                
                # Obtener todos los sitios de SharePoint
                all_sites = self.get_sharepoint_sites()
                
                # Obtener keywords de configuración
                site_keywords = sharepoint_config.get_site_keywords()
                
                # Filtrar sitios de Teams y sitios que podrían contener documentos operativos
                candidate_sites = []
                for site in all_sites:
                    site_name_lower = site.get("displayName", "").lower()
                    is_team_site = site.get("isTeamSite", False)
                    
                    # Priorizar sitios de Teams y sitios con nombres que sugieren contenido operativo
                    if (is_team_site or 
                        any(keyword in site_name_lower for keyword in site_keywords)):
                        candidate_sites.append(site)
                        logger.info(f"Sitio candidato: {site.get('displayName', 'Unknown')} (Teams: {is_team_site})")
                
                # Si no encontramos sitios específicos, usar todos los sitios de Teams como fallback
                if not candidate_sites:
                    candidate_sites = [site for site in all_sites if site.get("isTeamSite", False)]
                    logger.info(f"Fallback: usando todos los sitios de Teams ({len(candidate_sites)} sitios)")
                
                # Buscar en múltiples sitios candidatos (límite configurable)
                max_sites = sharepoint_config.get_max_sites()
                all_files = []
                for site in candidate_sites[:max_sites]:
                    try:
                        site_id = site["id"]
                        site_display_name = site.get("displayName", "Unknown")
                        logger.info(f"Buscando en: {site_display_name}")
                        
                        # Buscar archivos en este sitio específico
                        site_files = self._search_files_in_single_site(site_id, site_display_name)
                        if site_files:
                            logger.info(f"Encontrados {len(site_files)} archivos en {site_display_name}")
                            all_files.extend(site_files)
                        
                    except Exception as e:
                        logger.warning(f"Error buscando en {site_display_name}: {e}")
                        continue
                
                return all_files
            
            # Si se proporciona site_id específico, usar el método auxiliar
            return self._search_files_in_single_site(site_id, site_name or "Sitio específico")
            
        except Exception as e:
            logger.error(f"Error buscando archivos en carpetas configuradas: {e}")
            return []
    
    def _search_files_in_single_site(self, site_id: str, site_name: str) -> List[Dict]:
        """Método auxiliar para buscar archivos en las carpetas configuradas de un sitio específico"""
        try:
            logger.info(f"Buscando en sitio específico: {site_name}")
            
            # Obtener carpetas configuradas para buscar
            search_folders = sharepoint_config.get_search_folders()
            logger.info(f"Buscando en carpetas configuradas: {search_folders}")
            
            # Intentar buscar en cada carpeta configurada
            for folder_name in search_folders:
                logger.info(f"Intentando buscar carpeta: {folder_name}")
                
                # Buscar primero en la biblioteca de documentos
                folder_path = self.find_configured_folder_in_document_library(site_id, folder_name)
                
                if not folder_path:
                    # Si no se encuentra en la biblioteca, intentar búsqueda recursiva
                    logger.debug(f"No se encontró {folder_name} en biblioteca, intentando búsqueda recursiva...")
                    folder_path = self.find_configured_folder_recursive(site_id, folder_name)
                
                if folder_path:
                    logger.info(f"Carpeta {folder_name} encontrada en {site_name}: {folder_path}")
                    
                    # Obtener archivos de la carpeta encontrada
                    folder_files = self.get_drive_items(site_id, folder_path=folder_path)
                    
                    # Filtrar solo archivos (no carpetas)
                    files = []
                    for item in folder_files:
                        if "file" in item:  # Es un archivo, no una carpeta
                            files.append({
                                "id": item["id"],
                                "name": item["name"],
                                "webUrl": item["webUrl"],
                                "downloadUrl": item.get("@microsoft.graph.downloadUrl", ""),
                                "size": item.get("size", 0),
                                "lastModified": item.get("lastModifiedDateTime", ""),
                                "createdBy": item.get("createdBy", {}).get("user", {}).get("displayName", ""),
                                "mimeType": item.get("file", {}).get("mimeType", ""),
                                "site_id": site_id,
                                "site_name": site_name,
                                "folder_found": folder_name
                            })
                    
                    if files:
                        logger.info(f"Encontrados {len(files)} archivos en carpeta {folder_name} de {site_name}")
                        return files
            
            # Si no se encontró ninguna carpeta específica y está habilitado el fallback
            if sharepoint_config.is_content_fallback_enabled():
                logger.debug("No se encontraron carpetas específicas, usando búsqueda de contenido...")
                
                # Usar queries configuradas para búsqueda de contenido
                search_queries = sharepoint_config.get_search_queries()
                for query in search_queries:
                    files = self.search_all_files_in_site(site_id, query)
                    if files:
                        logger.info(f"Encontrados {len(files)} archivos por búsqueda de contenido '{query}' en {site_name}")
                        # Agregar información del sitio a cada archivo
                        for file in files:
                            file["site_name"] = site_name
                            file["found_by_content_search"] = True
                            file["search_query"] = query
                        return files
            
            return []
            
        except Exception as e:
            logger.warning(f"Error buscando en sitio {site_name}: {e}")
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
    
    def get_document_library_items(self, site_id: str, library_name: str = "Documentos compartidos") -> List[Dict]:
        """Obtiene elementos de una biblioteca específica de SharePoint"""
        try:
            # Usar la API específica para bibliotecas de documentos
            url = f"{self.base_url}/sites/{site_id}/lists"
            headers = self._get_headers()
            
            # Primero obtener todas las listas para encontrar la biblioteca de documentos
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            lists = response.json().get("value", [])
            document_library = None
            
            # Buscar la biblioteca de documentos
            for lst in lists:
                list_name = lst.get("displayName", "").lower()
                list_template = lst.get("baseTemplate", 0)
                
                # Las bibliotecas de documentos tienen baseTemplate = 101
                if (list_template == 101 and 
                    (library_name.lower() in list_name or 
                     "document" in list_name or 
                     "compartidos" in list_name)):
                    document_library = lst
                    break
            
            if not document_library:
                logger.warning(f"No se encontró la biblioteca de documentos: {library_name}")
                return []
            
            # Obtener elementos de la biblioteca de documentos
            library_id = document_library["id"]
            items_url = f"{self.base_url}/sites/{site_id}/lists/{library_id}/items?expand=fields"
            
            items_response = requests.get(items_url, headers=headers)
            items_response.raise_for_status()
            
            items = items_response.json().get("value", [])
            logger.info(f"Encontrados {len(items)} elementos en la biblioteca de documentos")
            
            return items
            
        except Exception as e:
            logger.error(f"Error obteniendo elementos de la biblioteca de documentos: {e}")
            return []

    def find_pilotos_in_document_library(self, site_id: str) -> Optional[str]:
        """Método legacy - busca la carpeta Pilotos (mantener para compatibilidad)"""
        return self.find_configured_folder_in_document_library(site_id, "Pilotos")

    def search_all_files_in_site(self, site_id: str, search_query: str = "pilotos") -> List[Dict]:
        """Busca archivos en todo el sitio usando la API de búsqueda de Microsoft Graph"""
        try:
            # Usar la API de búsqueda de Microsoft Graph
            url = f"{self.base_url}/sites/{site_id}/drive/search(q='{search_query}')"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            results = response.json().get("value", [])
            logger.info(f"Búsqueda '{search_query}' encontró {len(results)} resultados")
            
            # Formatear resultados
            files = []
            for item in results:
                if "file" in item:  # Solo archivos, no carpetas
                    files.append({
                        "id": item["id"],
                        "name": item["name"],
                        "webUrl": item["webUrl"],
                        "downloadUrl": item.get("@microsoft.graph.downloadUrl", ""),
                        "size": item.get("size", 0),
                        "lastModified": item.get("lastModifiedDateTime", ""),
                        "parentPath": item.get("parentReference", {}).get("path", ""),
                        "mimeType": item.get("file", {}).get("mimeType", ""),
                        "site_id": site_id  # Agregar site_id para poder usarlo después
                    })
            
            return files
            
        except Exception as e:
            logger.error(f"Error buscando archivos en sitio con query '{search_query}': {e}")
            return []

    def get_all_drives_in_site(self, site_id: str) -> List[Dict]:
        """Obtiene todas las unidades (drives) en un sitio de SharePoint"""
        try:
            url = f"{self.base_url}/sites/{site_id}/drives"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            drives = response.json().get("value", [])
            logger.info(f"Encontradas {len(drives)} unidades en el sitio")
            
            return drives
            
        except Exception as e:
            logger.error(f"Error obteniendo drives del sitio: {e}")
            return []
        

# Instancia global del cliente
graph_client = GraphClient()


# Funciones de conveniencia para usar en la aplicación
def get_configured_files(site_name: str = None) -> List[Dict]:
    """Función de conveniencia para obtener archivos de las carpetas configuradas"""
    return graph_client.search_files_in_configured_folders(site_name=site_name)


def get_pilotos_files(site_name: str = None) -> List[Dict]:
    """Función legacy - mantener para compatibilidad"""
    return graph_client.search_files_in_configured_folders(site_name=site_name)


def get_sharepoint_config_summary() -> Dict:
    """Función para obtener resumen de la configuración actual"""
    return sharepoint_config.get_config_summary()


def search_sharepoint_files(query: str, site_name: str = "DevOps") -> List[Dict]:
    """Función de conveniencia para buscar archivos en SharePoint"""
    site = graph_client.find_site_by_name(site_name)
    if not site:
        return []
    
    return graph_client.search_files_by_query(query, site["id"])


def download_sharepoint_file(download_url: str) -> bytes:
    """Función de conveniencia para descargar archivos de SharePoint"""
    return graph_client.download_file(download_url)
