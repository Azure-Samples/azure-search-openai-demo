import os
import json
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class SharePointConfig:
    """Clase para manejar la configuración de SharePoint de forma dinámica"""
    
    def __init__(self, config_file: str = None, env_file: str = None):
        """
        Inicializa la configuración de SharePoint
        
        Args:
            config_file: Ruta al archivo JSON de configuración
            env_file: Ruta al archivo .env de configuración específica
        """
        self.config_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Archivos de configuración por defecto
        self.default_config_file = os.path.join(self.config_dir, "sharepoint_config.json")
        self.default_env_file = os.path.join(self.config_dir, "sharepoint.env")
        
        # Usar archivos especificados o por defecto
        self.config_file = config_file or self.default_config_file
        self.env_file = env_file or self.default_env_file
        
        # Cargar configuración
        self._load_config()
    
    def _load_config(self):
        """Carga la configuración desde archivos y variables de entorno"""
        try:
            # Cargar configuración base desde JSON
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.base_config = json.load(f)
                logger.info(f"Configuración base cargada desde: {self.config_file}")
            else:
                logger.warning(f"Archivo de configuración no encontrado: {self.config_file}")
                self.base_config = self._get_default_config()
            
            # Cargar configuración específica del entorno
            if os.path.exists(self.env_file):
                load_dotenv(self.env_file)
                logger.info(f"Variables de entorno cargadas desde: {self.env_file}")
            
            # Configuración final (variables de entorno sobrescriben JSON)
            self._setup_final_config()
            
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            self.base_config = self._get_default_config()
            self._setup_final_config()
    
    def _get_default_config(self) -> Dict:
        """Retorna configuración por defecto en caso de error"""
        return {
            "search_folders": ["Pilotos", "Pilots", "Documents", "Documentos"],
            "site_keywords": ["company", "general", "operativ", "pilot", "flight", "vuelo", "aviaci"],
            "file_extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"],
            "max_sites_to_search": 15,
            "search_depth": 5,
            "fallback_to_content_search": True,
            "search_queries": ["pilotos", "pilots", "documentos", "documents"]
        }
    
    def _setup_final_config(self):
        """Configura los valores finales combinando JSON y variables de entorno"""
        # Carpetas de búsqueda
        env_folders = os.getenv('SHAREPOINT_SEARCH_FOLDERS', '')
        if env_folders:
            self.search_folders = [folder.strip() for folder in env_folders.split(',')]
        else:
            self.search_folders = self.base_config.get("search_folders", ["Pilotos"])
        
        # Keywords para sitios
        env_keywords = os.getenv('SHAREPOINT_SITE_KEYWORDS', '')
        if env_keywords:
            self.site_keywords = [keyword.strip() for keyword in env_keywords.split(',')]
        else:
            self.site_keywords = self.base_config.get("site_keywords", ["company", "general"])
        
        # Queries de búsqueda
        env_queries = os.getenv('SHAREPOINT_SEARCH_QUERIES', '')
        if env_queries:
            self.search_queries = [query.strip() for query in env_queries.split(',')]
        else:
            self.search_queries = self.base_config.get("search_queries", ["pilotos"])
        
        # Extensiones de archivo
        env_extensions = os.getenv('SHAREPOINT_FILE_EXTENSIONS', '')
        if env_extensions:
            self.file_extensions = [ext.strip() for ext in env_extensions.split(',')]
        else:
            self.file_extensions = self.base_config.get("file_extensions", [".pdf", ".doc", ".docx"])
        
        # Configuraciones numéricas
        self.max_sites_to_search = int(os.getenv('SHAREPOINT_MAX_SITES', 
                                                self.base_config.get("max_sites_to_search", 15)))
        
        self.search_depth = int(os.getenv('SHAREPOINT_SEARCH_DEPTH', 
                                         self.base_config.get("search_depth", 5)))
        
        # Configuraciones booleanas
        fallback_env = os.getenv('SHAREPOINT_ENABLE_CONTENT_FALLBACK', '').lower()
        if fallback_env in ['true', '1', 'yes', 'on']:
            self.fallback_to_content_search = True
        elif fallback_env in ['false', '0', 'no', 'off']:
            self.fallback_to_content_search = False
        else:
            self.fallback_to_content_search = self.base_config.get("fallback_to_content_search", True)
        
        logger.info(f"Configuración final - Carpetas: {self.search_folders}")
        logger.info(f"Configuración final - Keywords sitios: {self.site_keywords}")
        logger.info(f"Configuración final - Queries búsqueda: {self.search_queries}")
    
    def get_search_folders(self) -> List[str]:
        """Retorna lista de carpetas a buscar"""
        return self.search_folders
    
    def get_site_keywords(self) -> List[str]:
        """Retorna keywords para identificar sitios relevantes"""
        return self.site_keywords
    
    def get_search_queries(self) -> List[str]:
        """Retorna queries para búsqueda de contenido"""
        return self.search_queries
    
    def get_file_extensions(self) -> List[str]:
        """Retorna extensiones de archivo válidas"""
        return self.file_extensions
    
    def get_max_sites(self) -> int:
        """Retorna máximo número de sitios a buscar"""
        return self.max_sites_to_search
    
    def get_search_depth(self) -> int:
        """Retorna profundidad máxima de búsqueda"""
        return self.search_depth
    
    def is_content_fallback_enabled(self) -> bool:
        """Retorna si está habilitado el fallback a búsqueda de contenido"""
        return self.fallback_to_content_search
    
    def reload_config(self):
        """Recarga la configuración desde los archivos"""
        self._load_config()
    
    def get_config_summary(self) -> Dict:
        """Retorna un resumen de la configuración actual"""
        return {
            "search_folders": self.search_folders,
            "site_keywords": self.site_keywords,
            "search_queries": self.search_queries,
            "file_extensions": self.file_extensions,
            "max_sites_to_search": self.max_sites_to_search,
            "search_depth": self.search_depth,
            "fallback_to_content_search": self.fallback_to_content_search,
            "config_file": self.config_file,
            "env_file": self.env_file
        }


# Instancia global de configuración
sharepoint_config = SharePointConfig()
