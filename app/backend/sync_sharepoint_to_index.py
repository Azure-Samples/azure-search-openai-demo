#!/usr/bin/env python3
"""
Script de sincronización SharePoint + Document Intelligence
Sincroniza documentos de la carpeta PILOTOS de SharePoint al índice de Azure Search
"""

import asyncio
import logging
import os
import tempfile
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

# Importaciones de Azure
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.identity import DefaultAzureCredential

# Importaciones locales
from core.graph import get_access_token, get_drive_id, list_pilotos_files, get_file_content
from prepdocslib.textsplitter import SentenceTextSplitter

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SharePointDocumentSyncer:
    def __init__(self):
        """Inicializar el sincronizador con las configuraciones necesarias"""
        
        # Cargar variables de entorno de azd
        try:
            import sys
            sys.path.append('../..')
            from scripts.load_azd_env import load_azd_env
            load_azd_env()
            logger.info("✅ Variables de entorno azd cargadas")
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron cargar variables azd: {e}")
        
        # Configuración de Azure Search
        self.search_service = os.getenv("AZURE_SEARCH_SERVICE")
        self.search_index = os.getenv("AZURE_SEARCH_INDEX") 
        self.search_key = os.getenv("SEARCH_KEY")  # Para desarrollo, usar key si está disponible
        
        # Configuración de Document Intelligence
        self.doc_intelligence_service = os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE")
        
        # Configuración de SharePoint
        self.site_id = os.getenv("SHAREPOINT_SITE_ID")
        
        # Configuración de autenticación
        self.credential = DefaultAzureCredential()
        
        # Inicializar clientes
        self.search_client = None
        self.doc_intelligence_client = None
        
        # Text splitter para dividir contenido
        self.text_splitter = SentenceTextSplitter()
        
    async def initialize_clients(self):
        """Inicializar clientes de Azure"""
        try:
            # Cliente de Azure Search
            if self.search_key:
                search_credential = AzureKeyCredential(self.search_key)
            else:
                search_credential = self.credential
                
            self.search_client = SearchClient(
                endpoint=f"https://{self.search_service}.search.windows.net",
                index_name=self.search_index,
                credential=search_credential
            )
            
            # Cliente de Document Intelligence
            if self.doc_intelligence_service:
                self.doc_intelligence_client = DocumentIntelligenceClient(
                    endpoint=f"https://{self.doc_intelligence_service}.cognitiveservices.azure.com/",
                    credential=self.credential
                )
                logger.info("✅ Document Intelligence client initialized")
            else:
                logger.warning("⚠️ Document Intelligence not configured")
                
            logger.info("✅ Azure clients initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Error initializing clients: {e}")
            raise
    
    async def process_document_with_intelligence(self, file_content: bytes, filename: str) -> Optional[str]:
        """Procesar documento usando Document Intelligence"""
        if not self.doc_intelligence_client:
            logger.warning(f"Document Intelligence not available for {filename}")
            return None
            
        try:
            logger.info(f"🔍 Processing {filename} with Document Intelligence...")
            
            # Analizar documento
            poller = await self.doc_intelligence_client.begin_analyze_document(
                "prebuilt-read",  # Modelo prebuilt para lectura general
                analyze_request=AnalyzeDocumentRequest(bytes_source=file_content),
            )
            
            result = await poller.result()
            
            # Extraer texto
            content_parts = []
            if result.content:
                content_parts.append(result.content)
                
            # Extraer texto de tablas si existen
            if result.tables:
                for table in result.tables:
                    table_text = f"\n--- Tabla {table.row_count}x{table.column_count} ---\n"
                    for cell in table.cells:
                        if cell.content:
                            table_text += f"{cell.content} "
                    content_parts.append(table_text)
            
            full_content = "\n\n".join(content_parts)
            logger.info(f"✅ Extracted {len(full_content)} characters from {filename}")
            
            return full_content
            
        except Exception as e:
            logger.error(f"❌ Error processing {filename} with Document Intelligence: {e}")
            return None
    
    def create_document_id(self, sharepoint_file_id: str) -> str:
        """Crear ID único para el documento en Azure Search"""
        return f"sharepoint_{sharepoint_file_id}"
    
    def should_process_file(self, filename: str) -> bool:
        """Determinar si un archivo debe procesarse"""
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
        return any(filename.lower().endswith(ext) for ext in supported_extensions)
    
    async def index_document(self, document: Dict[str, Any]) -> bool:
        """Indexar documento en Azure Search"""
        try:
            # Preparar documento para indexación
            search_document = {
                "id": document["id"],
                "content": document["content"],
                "category": document.get("category", "SharePoint-PILOTOS"),
                "sourcepage": document["filename"],
                "sourcefile": document["filename"],
                "source": document.get("source", "SharePoint/PILOTOS"),
                "metadata": {
                    "sharepoint_id": document.get("sharepoint_id"),
                    "last_modified": document.get("last_modified"),
                    "sync_timestamp": datetime.now().isoformat()
                }
            }
            
            # Indexar
            await self.search_client.upload_documents([search_document])
            logger.info(f"✅ Indexed document: {document['filename']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error indexing {document['filename']}: {e}")
            return False
    
    async def sync_sharepoint_documents(self) -> Dict[str, int]:
        """Sincronizar documentos de SharePoint"""
        stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0
        }
        
        try:
            logger.info("🔄 Starting SharePoint synchronization...")
            
            # 1. Obtener token de acceso a SharePoint
            token = get_access_token()
            logger.info("✅ SharePoint access token obtained")
            
            # 2. Obtener drive ID
            drive_id = get_drive_id(self.site_id, token)
            logger.info(f"✅ Drive ID obtained: {drive_id}")
            
            # 3. Listar archivos en carpeta PILOTOS
            files = list_pilotos_files(drive_id, token)
            stats["total_files"] = len(files)
            logger.info(f"📁 Found {len(files)} files in SharePoint/PILOTOS")
            
            # 4. Procesar cada archivo
            for file_info in files:
                filename = file_info.get('name', 'Unknown')
                file_id = file_info.get('id', '')
                
                try:
                    # Verificar si debe procesarse
                    if not self.should_process_file(filename):
                        logger.info(f"⏭️ Skipping {filename} (unsupported format)")
                        stats["skipped"] += 1
                        continue
                    
                    logger.info(f"📥 Processing {filename}...")
                    
                    # 5. Descargar contenido del archivo
                    file_content = get_file_content(drive_id, file_id, token)
                    if not file_content:
                        logger.warning(f"⚠️ Could not download {filename}")
                        stats["errors"] += 1
                        continue
                    
                    # 6. Procesar con Document Intelligence
                    processed_text = await self.process_document_with_intelligence(
                        file_content, filename
                    )
                    
                    if not processed_text:
                        logger.warning(f"⚠️ Could not extract text from {filename}")
                        stats["errors"] += 1
                        continue
                    
                    # 7. Preparar documento para indexación
                    document = {
                        "id": self.create_document_id(file_id),
                        "content": processed_text,
                        "filename": filename,
                        "source": "SharePoint/PILOTOS",
                        "sharepoint_id": file_id,
                        "last_modified": file_info.get('lastModifiedDateTime'),
                        "category": "SharePoint-PILOTOS"
                    }
                    
                    # 8. Indexar documento
                    if await self.index_document(document):
                        stats["processed"] += 1
                    else:
                        stats["errors"] += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error processing {filename}: {e}")
                    stats["errors"] += 1
            
            logger.info(f"🎯 Synchronization completed!")
            logger.info(f"📊 Stats: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Critical error during synchronization: {e}")
            raise
    
    async def close(self):
        """Cerrar conexiones"""
        if self.search_client:
            await self.search_client.close()
        if self.doc_intelligence_client:
            await self.doc_intelligence_client.close()

async def main():
    """Función principal"""
    syncer = SharePointDocumentSyncer()
    
    try:
        # Inicializar clientes
        await syncer.initialize_clients()
        
        # Ejecutar sincronización
        stats = await syncer.sync_sharepoint_documents()
        
        print("\n" + "="*50)
        print("📊 SHAREPOINT SYNC RESULTS")
        print("="*50)
        print(f"Total files found: {stats['total_files']}")
        print(f"Successfully processed: {stats['processed']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print("="*50)
        
        return stats["errors"] == 0  # Return True if no errors
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return False
        
    finally:
        await syncer.close()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
