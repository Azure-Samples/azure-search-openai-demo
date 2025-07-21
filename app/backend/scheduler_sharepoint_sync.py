#!/usr/bin/env python3
"""
Scheduler Automático para Sincronización SharePoint → Azure Search
================================================================

Sistema de automatización que ejecuta la sincronización de documentos
de SharePoint con Azure Search usando Document Intelligence de forma programada.

Características:
- Ejecución automática cada X horas
- Logging detallado con rotación
- Manejo robusto de errores
- Notificaciones de estado
- Control de concurrencia

Autor: Azure Search OpenAI Demo
Fecha: 2025-07-21
"""

import asyncio
import os
import sys
import time
import logging
import signal
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path
import json
import threading
from logging.handlers import RotatingFileHandler

# Importar nuestro sincronizador avanzado
from sync_sharepoint_simple_advanced import SharePointAdvancedSync, load_azd_env

class SharePointScheduler:
    """
    Scheduler automático para sincronización SharePoint
    """
    
    def __init__(self, sync_interval_hours: int = 6, max_files_per_sync: Optional[int] = None):
        self.sync_interval_hours = sync_interval_hours
        self.max_files_per_sync = max_files_per_sync
        self.is_running = False
        self.sync_in_progress = False
        self.last_sync_time = None
        self.sync_stats_history = []
        self.max_history = 10  # Mantener últimas 10 sincronizaciones
        
        # Configurar logging con rotación
        self.setup_logging()
        self.logger = logging.getLogger('sharepoint_scheduler')
        
        # Configurar manejador de señales
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def setup_logging(self):
        """Configurar sistema de logging con rotación"""
        log_dir = Path("/workspaces/azure-search-openai-demo/logs")
        log_dir.mkdir(exist_ok=True)
        
        # Logger principal
        logger = logging.getLogger('sharepoint_scheduler')
        logger.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Handler con rotación (10MB máximo, 5 archivos)
        log_file = log_dir / 'sharepoint_scheduler.log'
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        
        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Evitar duplicados
        logger.propagate = False
        
    def signal_handler(self, signum, frame):
        """Manejador para señales de terminación"""
        self.logger.info(f"📡 Señal {signum} recibida. Deteniendo scheduler...")
        self.is_running = False
        
    def save_sync_stats(self, stats: Dict):
        """Guardar estadísticas de sincronización"""
        try:
            stats_file = Path("/workspaces/azure-search-openai-demo/logs/sync_stats.json")
            
            # Agregar timestamp
            stats['timestamp'] = datetime.now().isoformat()
            stats['sync_interval_hours'] = self.sync_interval_hours
            
            # Agregar a historial
            self.sync_stats_history.append(stats)
            
            # Mantener solo las últimas N sincronizaciones
            if len(self.sync_stats_history) > self.max_history:
                self.sync_stats_history = self.sync_stats_history[-self.max_history:]
            
            # Guardar a archivo
            with open(stats_file, 'w') as f:
                json.dump({
                    'last_sync': stats,
                    'history': self.sync_stats_history,
                    'scheduler_config': {
                        'interval_hours': self.sync_interval_hours,
                        'max_files_per_sync': self.max_files_per_sync
                    }
                }, f, indent=2)
                
            self.logger.info(f"📊 Estadísticas guardadas en {stats_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando estadísticas: {e}")
    
    def get_next_sync_time(self) -> datetime:
        """Calcular próxima hora de sincronización"""
        if self.last_sync_time:
            return self.last_sync_time + timedelta(hours=self.sync_interval_hours)
        else:
            return datetime.now() + timedelta(minutes=1)  # Primera ejecución en 1 minuto
    
    def should_sync_now(self) -> bool:
        """Determinar si es hora de sincronizar"""
        if self.sync_in_progress:
            return False
            
        next_sync = self.get_next_sync_time()
        return datetime.now() >= next_sync
    
    async def perform_sync(self) -> Dict:
        """Ejecutar sincronización completa"""
        if self.sync_in_progress:
            self.logger.warning("⚠️ Sincronización ya en progreso, omitiendo...")
            return {"status": "skipped", "reason": "sync_in_progress"}
        
        self.sync_in_progress = True
        sync_start_time = datetime.now()
        
        try:
            self.logger.info("🚀 Iniciando sincronización automática SharePoint → Azure Search")
            self.logger.info(f"📅 Hora: {sync_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Crear sincronizador
            sync = SharePointAdvancedSync()
            sync.initialize()
            
            # Ejecutar sincronización
            stats = await sync.sync_documents(
                limit=self.max_files_per_sync,
                dry_run=False
            )
            
            if stats:
                sync_duration = (datetime.now() - sync_start_time).total_seconds()
                
                result = {
                    "status": "success",
                    "start_time": sync_start_time.isoformat(),
                    "duration_seconds": sync_duration,
                    "files_processed": stats.get('processed', 0),
                    "files_total": stats.get('total_files', 0),
                    "errors": stats.get('errors', 0)
                }
                
                self.logger.info(f"✅ Sincronización completada exitosamente")
                self.logger.info(f"📊 Procesados: {result['files_processed']}/{result['files_total']} archivos")
                self.logger.info(f"⏱️ Duración: {sync_duration:.1f} segundos")
                self.logger.info(f"❌ Errores: {result['errors']}")
                
                # Actualizar tiempo de última sincronización
                self.last_sync_time = sync_start_time
                
                return result
            else:
                return {
                    "status": "no_files", 
                    "start_time": sync_start_time.isoformat(),
                    "duration_seconds": (datetime.now() - sync_start_time).total_seconds()
                }
                
        except Exception as e:
            sync_duration = (datetime.now() - sync_start_time).total_seconds()
            error_result = {
                "status": "error",
                "start_time": sync_start_time.isoformat(),
                "duration_seconds": sync_duration,
                "error_message": str(e)
            }
            
            self.logger.error(f"❌ Error en sincronización automática: {e}")
            return error_result
            
        finally:
            self.sync_in_progress = False
    
    def print_status(self):
        """Mostrar estado actual del scheduler"""
        now = datetime.now()
        next_sync = self.get_next_sync_time()
        
        self.logger.info(f"📊 Estado del Scheduler:")
        self.logger.info(f"   • Ejecutándose: {'Sí' if self.is_running else 'No'}")
        self.logger.info(f"   • Sincronizando: {'Sí' if self.sync_in_progress else 'No'}")
        self.logger.info(f"   • Intervalo: cada {self.sync_interval_hours} horas")
        self.logger.info(f"   • Límite archivos: {self.max_files_per_sync or 'Sin límite'}")
        
        if self.last_sync_time:
            self.logger.info(f"   • Última sincronización: {self.last_sync_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.logger.info(f"   • Última sincronización: Nunca")
            
        self.logger.info(f"   • Próxima sincronización: {next_sync.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.sync_stats_history:
            last_stats = self.sync_stats_history[-1]
            self.logger.info(f"   • Último resultado: {last_stats.get('files_processed', 0)} archivos procesados")
    
    async def run(self):
        """Ejecutar scheduler principal"""
        self.is_running = True
        self.logger.info("🤖 Iniciando SharePoint Scheduler...")
        self.logger.info(f"⏰ Sincronización automática cada {self.sync_interval_hours} horas")
        
        if self.max_files_per_sync:
            self.logger.info(f"📄 Límite: {self.max_files_per_sync} archivos por sincronización")
        
        # Mostrar estado inicial
        self.print_status()
        
        while self.is_running:
            try:
                if self.should_sync_now():
                    # Ejecutar sincronización
                    stats = await self.perform_sync()
                    
                    # Guardar estadísticas
                    self.save_sync_stats(stats)
                    
                    # Mostrar próxima ejecución
                    next_sync = self.get_next_sync_time()
                    self.logger.info(f"⏰ Próxima sincronización: {next_sync.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Esperar 1 minuto antes de verificar nuevamente
                await asyncio.sleep(60)
                
                # Mostrar estado cada 30 minutos si no hay actividad
                if datetime.now().minute % 30 == 0:
                    self.print_status()
                    
            except KeyboardInterrupt:
                self.logger.info("🛑 Deteniendo por interrupción de teclado...")
                break
            except Exception as e:
                self.logger.error(f"❌ Error inesperado en scheduler: {e}")
                await asyncio.sleep(300)  # Esperar 5 minutos antes de reintentar
        
        self.logger.info("🛑 SharePoint Scheduler detenido")

async def main():
    """Función principal del scheduler"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scheduler Automático SharePoint → Azure Search')
    parser.add_argument('--interval', type=int, default=6, 
                       help='Intervalo en horas entre sincronizaciones (default: 6)')
    parser.add_argument('--max-files', type=int, 
                       help='Máximo número de archivos por sincronización')
    parser.add_argument('--test-sync', action='store_true',
                       help='Ejecutar una sincronización de prueba inmediata')
    
    args = parser.parse_args()
    
    try:
        # Verificar variables de entorno
        if not load_azd_env():
            print("❌ Error: No se pudieron cargar las variables de entorno")
            sys.exit(1)
        
        scheduler = SharePointScheduler(
            sync_interval_hours=args.interval,
            max_files_per_sync=args.max_files
        )
        
        if args.test_sync:
            # Ejecutar sincronización de prueba
            print("🧪 Ejecutando sincronización de prueba...")
            stats = await scheduler.perform_sync()
            scheduler.save_sync_stats(stats)
            print(f"✅ Prueba completada: {stats}")
        else:
            # Ejecutar scheduler
            await scheduler.run()
            
    except KeyboardInterrupt:
        print("\n🛑 Scheduler detenido por usuario")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
