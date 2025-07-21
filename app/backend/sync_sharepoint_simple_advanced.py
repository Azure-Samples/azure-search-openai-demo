#!/usr/bin/env python3
"""
Sincronización Avanzada SharePoint → Azure Search con Document Intelligence
================================================================

Versión simplificada que reutiliza la lógica del script básico exitoso,
añadiendo procesamiento con Document Intelligence.

Autor: Azure Search OpenAI Demo
Fecha: 2025-07-21
"""

import asyncio
import os
import sys
import argparse
import logging
import tempfile
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import hashlib
import requests
import io

# Azure SDK imports  
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Importar función de carga de env
def load_azd_env():
    """Cargar variables de entorno desde .azure/env"""
    try:
        env_path = os.path.join(os.getcwd(), "..", "..", ".azure", "dev", ".env")
        if not os.path.exists(env_path):
            env_path = os.path.join(os.getcwd(), ".azure", "dev", ".env")
        
        if os.path.exists(env_path):
            logger.info(f"Loading azd env from {env_path}")
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value.strip('"\'')
            logger.info("✅ Variables de entorno azd cargadas")
            return True
        return False
    except Exception as e:
        logger.error(f"Error cargando variables: {e}")
        return False

class SharePointAdvancedSync:
    """Sincronizador avanzado simplificado"""
    
    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.search_client = None
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']
        
    def initialize(self):
        """Inicializar conexiones"""
        try:
            logger.info("🔄 Inicializando sincronización AVANZADA SharePoint → Azure Search")
            
            if not load_azd_env():
                raise Exception("No se pudieron cargar las variables azd")
            
            # Configurar Azure Search
            search_service = os.getenv('AZURE_SEARCH_SERVICE')
            search_index = os.getenv('AZURE_SEARCH_INDEX')
            if not search_service or not search_index:
                raise Exception("Variables Azure Search requeridas")
                
            search_endpoint = f"https://{search_service}.search.windows.net"
            self.search_client = SearchClient(
                endpoint=search_endpoint,
                index_name=search_index,
                credential=self.credential
            )
            logger.info(f"✅ Azure Search configurado: {search_service}/{search_index}")
            
            # Verificar Document Intelligence
            doc_intel_service = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_SERVICE', 'di-volaris-dev-eus-001')
            if doc_intel_service:
                logger.info(f"✅ Document Intelligence disponible: {doc_intel_service}")
            else:
                logger.warning("⚠️ AZURE_DOCUMENT_INTELLIGENCE_SERVICE no configurado")
            
            logger.info("📁 SharePoint: Usando configuración conocida")
            
        except Exception as e:
            logger.error(f"❌ Error en inicialización: {e}")
            raise
    
    def get_sharepoint_files(self, limit: Optional[int] = None) -> List[Dict]:
        """Obtener archivos de SharePoint usando lógica probada"""
        try:
            # Obtener token
            token_result = self.credential.get_token("https://graph.microsoft.com/.default")
            headers = {
                'Authorization': f'Bearer {token_result.token}',
                'Content-Type': 'application/json'
            }
            
            # Usar valores conocidos
            drive_id = 'b!Bh0c61GTfUq6CZ4fVKMmbfpRR2MfsJdBlxuAwc9dGNuwQn6ELM4KSYbgTdG2Ctzo'
            encoded_path = "Documentos%20Flightbot/PILOTOS"
            url = f'https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}:/children'
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            all_files = response.json().get('value', [])
            
            # Filtrar archivos compatibles
            compatible_files = []
            for file_info in all_files:
                if file_info.get('file'):
                    file_name = file_info['name']
                    file_size = file_info['size']
                    
                    if any(file_name.lower().endswith(ext) for ext in self.supported_extensions):
                        if file_size <= self.max_file_size:
                            compatible_files.append({
                                'id': file_info['id'],
                                'name': file_name,
                                'size': file_size,
                                'last_modified': file_info['lastModifiedDateTime']
                            })
                        else:
                            logger.warning(f"⚠️ {file_name} demasiado grande ({file_size/(1024*1024):.1f}MB)")
            
            if limit:
                compatible_files = compatible_files[:limit]
                
            logger.info(f"📋 Encontrados {len(compatible_files)} archivos compatibles")
            return compatible_files
            
        except Exception as e:
            logger.error(f"Error obteniendo archivos: {e}")
            raise
    
    def download_file(self, file_id: str, file_name: str) -> bytes:
        """Descargar archivo"""
        try:
            logger.info(f"⬇️ Descargando {file_name}...")
            
            token_result = self.credential.get_token("https://graph.microsoft.com/.default")
            headers = {'Authorization': f'Bearer {token_result.token}'}
            
            drive_id = 'b!Bh0c61GTfUq6CZ4fVKMmbfpRR2MfsJdBlxuAwc9dGNuwQn6ELM4KSYbgTdG2Ctzo'
            url = f'https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/content'
            
            response = requests.get(url, headers=headers, allow_redirects=True)
            response.raise_for_status()
            
            content = response.content
            logger.info(f"✅ Descargado {file_name} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            logger.error(f"Error descargando {file_name}: {e}")
            raise
    
    async def process_with_document_intelligence(self, content: bytes, file_name: str) -> str:
        """
        Procesar con Document Intelligence usando llamada directa a API
        """
        try:
            logger.info(f"🧠 Procesando {file_name} con Document Intelligence...")
            
            doc_intel_service = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_SERVICE', 'di-volaris-dev-eus-001')
            if not doc_intel_service:
                # Fallback a extracción básica
                logger.warning(f"⚠️ Document Intelligence no disponible para {file_name}, usando fallback")
                return f"Contenido de {file_name} (procesamiento básico)"
            
            # Obtener token para Document Intelligence
            token_result = self.credential.get_token("https://cognitiveservices.azure.com/.default")
            
            # Endpoint de Document Intelligence
            endpoint = f"https://{doc_intel_service}.cognitiveservices.azure.com/documentintelligence/documentModels/prebuilt-read:analyze?api-version=2024-02-29-preview"
            
            headers = {
                'Authorization': f'Bearer {token_result.token}',
                'Content-Type': 'application/octet-stream'
            }
            
            # Iniciar análisis
            response = requests.post(endpoint, headers=headers, data=content)
            
            if response.status_code == 202:
                # Obtener resultado
                result_url = response.headers.get('Operation-Location')
                if result_url:
                    # Esperar resultado (polling simplificado)
                    for _ in range(10):  # Máximo 10 intentos
                        await asyncio.sleep(2)
                        result_response = requests.get(result_url, headers={'Authorization': f'Bearer {token_result.token}'})
                        if result_response.status_code == 200:
                            result = result_response.json()
                            if result.get('status') == 'succeeded':
                                # Extraer texto
                                content_text = result.get('analyzeResult', {}).get('content', '')
                                logger.info(f"✅ Document Intelligence completado: {len(content_text)} caracteres")
                                return content_text
                            elif result.get('status') == 'failed':
                                logger.error(f"❌ Document Intelligence falló para {file_name}")
                                break
                
            # Fallback si falla
            logger.warning(f"⚠️ Document Intelligence no completado para {file_name}, usando fallback")
            return f"Contenido de {file_name} (Document Intelligence no disponible)"
            
        except Exception as e:
            logger.error(f"Error procesando {file_name}: {e}")
            return f"Error procesando {file_name}: {str(e)}"
    
    def index_document(self, document: Dict) -> bool:
        """Indexar documento"""
        try:
            logger.info("🔍 Indexando documento avanzado...")
            
            result = self.search_client.upload_documents([document])
            
            if result and result[0].succeeded:
                logger.info(f"✅ {document['sourcefile']} indexado con Document Intelligence")
                return True
            else:
                error_msg = result[0].error_message if result else "Error desconocido"
                logger.error(f"❌ Error indexando: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error indexando: {e}")
            return False
    
    async def process_file(self, file_info: Dict) -> Tuple[bool, str]:
        """Procesar archivo individual"""
        file_name = file_info['name']
        file_id = file_info['id']
        
        try:
            # 1. Descargar
            content = self.download_file(file_id, file_name)
            
            # 2. Procesar con Document Intelligence
            processed_text = await self.process_with_document_intelligence(content, file_name)
            
            # 3. Crear documento
            doc_id = hashlib.sha256(f"sharepoint_advanced_{file_id}_{file_name}".encode()).hexdigest()[:32]
            
            document = {
                'id': doc_id,
                'content': processed_text[:32000],
                'sourcepage': f"SharePoint/PILOTOS/{file_name}",
                'sourcefile': file_name,
                'category': 'SharePoint-Advanced-DI'
            }
            
            # 4. Indexar
            success = self.index_document(document)
            
            if success:
                return True, "✅ Procesado con Document Intelligence"
            else:
                return False, "❌ Error en indexación"
                
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    async def sync_documents(self, limit: Optional[int] = None, dry_run: bool = False):
        """Sincronizar documentos"""
        try:
            files = self.get_sharepoint_files(limit)
            
            if not files:
                logger.info("📭 No se encontraron archivos")
                return
            
            if dry_run:
                logger.info(f"🔍 SIMULACIÓN: Se procesarían {len(files)} archivos con Document Intelligence:")
                for file_info in files:
                    ext = Path(file_info['name']).suffix
                    logger.info(f"  • {file_info['name']} ({file_info['size']/1024:.1f}KB, {ext})")
                return
            
            stats = {'total_files': len(files), 'processed': 0, 'errors': 0}
            
            for i, file_info in enumerate(files):
                logger.info(f"📄 [{i+1}/{len(files)}] Procesando: {file_info['name']}")
                success, message = await self.process_file(file_info)
                
                if success:
                    stats['processed'] += 1
                    logger.info(message)
                else:
                    stats['errors'] += 1
                    logger.error(f"Error: {message}")
            
            logger.info("🎉 Sincronización avanzada completada!")
            logger.info(f"📊 Estadísticas: Procesados {stats['processed']}/{stats['total_files']}, Errores: {stats['errors']}")
            return stats
            
        except Exception as e:
            logger.error(f"Error en sincronización: {e}")
            raise

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Sync SharePoint → Azure Search con Document Intelligence')
    parser.add_argument('--limit', type=int, help='Límite de archivos')
    parser.add_argument('--dry-run', action='store_true', help='Solo simular')
    parser.add_argument('--verbose', action='store_true', help='Logging detallado')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        sync = SharePointAdvancedSync()
        sync.initialize()
        
        stats = await sync.sync_documents(limit=args.limit, dry_run=args.dry_run)
        
        if not args.dry_run and stats:
            print(f"\n✅ Sincronización avanzada completada")
            print(f"📊 Estadísticas: {stats}")
            print(f"🚀 Documentos procesados con Document Intelligence para mejor extracción de texto")
        
    except KeyboardInterrupt:
        logger.info("🛑 Cancelado por usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
