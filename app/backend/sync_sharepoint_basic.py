#!/usr/bin/env python3

"""
Integración Básica SharePoint + Azure Search (SIN Document Intelligence)
Script simplificado para probar la sincronización básica primero
"""

import asyncio
import os
import sys
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Agregar el directorio actual al path para importaciones
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def sync_basic_sharepoint_documents(dry_run: bool = False, limit: int = 10) -> Dict[str, int]:
    """
    Sincronización BÁSICA de SharePoint a Azure Search (sin Document Intelligence)
    Solo procesa archivos de texto simples para probar la integración
    """
    stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'total_files': 0
    }
    
    try:
        # Cargar variables de entorno de azd
        try:
            import sys
            sys.path.append('../..')
            from scripts.load_azd_env import load_azd_env
            load_azd_env()
            logger.info("✅ Variables de entorno azd cargadas")
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron cargar variables azd: {e}")
        
        # Importar dependencias necesarias
        from core.graph import get_access_token, get_drive_id, list_pilotos_files, get_file_content
        from azure.search.documents.aio import SearchClient
        from azure.identity import DefaultAzureCredential
        from prepdocslib.textsplitter import SentenceTextSplitter
        
        logger.info("🔄 Iniciando sincronización BÁSICA SharePoint → Azure Search")
        
        # 1. Configurar credenciales y clientes
        azure_credential = DefaultAzureCredential()
        
        # Cliente de Azure Search
        search_service = os.getenv("AZURE_SEARCH_SERVICE")
        search_index = os.getenv("AZURE_SEARCH_INDEX")
        
        if not search_service or not search_index:
            raise ValueError("AZURE_SEARCH_SERVICE y AZURE_SEARCH_INDEX deben estar configurados")
            
        search_client = SearchClient(
            endpoint=f"https://{search_service}.search.windows.net",
            index_name=search_index,
            credential=azure_credential
        )
        
        logger.info(f"✅ Azure Search configurado: {search_service}/{search_index}")
        
        # 2. Obtener archivos de SharePoint
        logger.info("📁 Conectando a SharePoint...")
        
        token = get_access_token()
        site_id = os.getenv("SHAREPOINT_SITE_ID")
        drive_id = get_drive_id(site_id, token)
        
        logger.info(f"🔗 Conectado a SharePoint: {site_id}")
        
        # 3. Listar archivos en PILOTOS (límite para pruebas)
        files = list_pilotos_files(drive_id, token)
        files = files[:limit]  # Limitar para pruebas
        stats['total_files'] = len(files)
        
        logger.info(f"📋 Procesando {len(files)} archivos de SharePoint/PILOTOS (limitado a {limit})")
        
        # 4. Procesar cada archivo (solo tipos básicos)
        text_splitter = SentenceTextSplitter()
        
        for i, file_info in enumerate(files, 1):
            file_name = file_info.get('name', 'Unknown')
            file_id = file_info.get('id', '')
            file_size = file_info.get('size', 0)
            last_modified = file_info.get('lastModifiedDateTime', '')
            
            logger.info(f"📄 [{i}/{len(files)}] Procesando: {file_name}")
            
            # Solo procesar archivos de texto simples por ahora
            is_text = file_name.lower().endswith(('.txt', '.md', '.json'))
            is_small_pdf = file_name.lower().endswith('.pdf') and file_size < 1000000  # PDFs < 1MB
            
            if not (is_text or is_small_pdf):
                logger.info(f"⏭️ Omitiendo {file_name} (tipo no soportado o demasiado grande)")
                stats['skipped'] += 1
                continue
            
            # Generar ID único para el documento
            doc_id = f"sharepoint_basic_{hashlib.md5(file_id.encode()).hexdigest()}"
            
            if dry_run:
                logger.info(f"🔍 [DRY RUN] Se procesaría: {file_name}")
                stats['processed'] += 1
                continue
            
            try:
                # 5. Descargar contenido del archivo
                logger.info(f"⬇️ Descargando {file_name}...")
                file_content = get_file_content(drive_id, file_id, token)
                
                if not file_content:
                    logger.warning(f"⚠️ No se pudo descargar {file_name}")
                    stats['errors'] += 1
                    continue
                
                # 6. Procesar contenido según el tipo
                processed_text = ""
                
                if is_text:
                    # Archivos de texto simples
                    try:
                        processed_text = file_content.decode('utf-8', errors='ignore')
                    except:
                        processed_text = str(file_content)[:2000]  # Fallback
                        
                elif is_small_pdf:
                    # Para PDFs pequeños, crear metadata sin procesar contenido
                    processed_text = f"""
                    Documento PDF: {file_name}
                    Tamaño: {file_size} bytes
                    Fecha modificación: {last_modified}
                    
                    Este documento está disponible en SharePoint/PILOTOS.
                    Para acceso completo al contenido, consulte el documento original.
                    
                    Palabras clave extraídas del nombre:
                    {file_name.replace('.pdf', '').replace('_', ' ').replace('-', ' ')}
                    """
                
                if not processed_text or len(processed_text.strip()) < 10:
                    logger.warning(f"⚠️ No se extrajo texto útil de {file_name}")
                    stats['errors'] += 1
                    continue
                
                # 7. Preparar documento para indexación
                document = {
                    'id': doc_id,
                    'content': processed_text[:32000],  # Azure Search limit
                    'sourcepage': f"SharePoint/PILOTOS/{file_name}",
                    'sourcefile': file_name,
                    'category': 'SharePoint-Basic'
                }
                
                # 8. Indexar en Azure Search
                logger.info(f"🔍 Indexando documento básico...")
                
                result = await search_client.upload_documents([document])
                
                if result[0].succeeded:
                    logger.info(f"✅ {file_name} indexado correctamente")
                    stats['processed'] += 1
                else:
                    logger.error(f"❌ Error indexando {file_name}: {result[0].error_message}")
                    stats['errors'] += 1
                
            except Exception as e:
                logger.error(f"❌ Error procesando {file_name}: {str(e)}")
                stats['errors'] += 1
                continue
        
        # 9. Resumen final
        logger.info("🎉 Sincronización básica completada!")
        logger.info(f"📊 Estadísticas:")
        logger.info(f"  • Total archivos: {stats['total_files']}")
        logger.info(f"  • Procesados: {stats['processed']}")
        logger.info(f"  • Omitidos: {stats['skipped']}")
        logger.info(f"  • Errores: {stats['errors']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error crítico en sincronización: {str(e)}")
        stats['errors'] += 1
        raise


async def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sincronización BÁSICA SharePoint con Azure Search")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar qué se procesaría sin hacerlo")
    parser.add_argument("--verbose", "-v", action="store_true", help="Logging verbose")
    parser.add_argument("--limit", type=int, default=5, help="Límite de archivos a procesar (default: 5)")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Ejecutar sincronización básica
        stats = await sync_basic_sharepoint_documents(
            dry_run=args.dry_run, 
            limit=args.limit
        )
        
        if args.dry_run:
            print("\n🔍 DRY RUN completado - No se hicieron cambios reales")
        else:
            print("\n✅ Sincronización básica completada exitosamente")
            
        print(f"📊 Estadísticas: {stats}")
        
        # Si la sincronización básica funciona, sugerir el siguiente paso
        if stats['processed'] > 0:
            print("\n🚀 ¡Éxito! La integración básica funciona.")
            print("   Siguiente paso: Implementar Document Intelligence para PDFs")
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
