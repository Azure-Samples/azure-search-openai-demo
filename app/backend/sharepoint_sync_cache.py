#!/usr/bin/env python3
"""
Sistema de Cache para SharePoint Sync
====================================

Maneja el cache de archivos procesados para evitar re-procesamiento innecesario.
Utiliza fechas de modificación y hashes para detectar cambios.

Autor: Azure Search OpenAI Demo
Fecha: 2025-07-21
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path

class SharePointSyncCache:
    """
    Sistema de cache para evitar re-procesamiento de archivos
    """
    
    def __init__(self, cache_file: str = None):
        if cache_file is None:
            cache_file = "/workspaces/azure-search-openai-demo/logs/sharepoint_sync_cache.json"
        
        self.cache_file = Path(cache_file)
        self.cache_data = self._load_cache()
        
    def _load_cache(self) -> Dict:
        """Cargar cache desde archivo"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            'processed_files': {},
            'last_sync': None,
            'stats': {
                'total_processed': 0,
                'cache_hits': 0,
                'new_files': 0,
                'updated_files': 0
            }
        }
    
    def _save_cache(self):
        """Guardar cache a archivo"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando cache: {e}")
    
    def _get_file_key(self, file_info: Dict) -> str:
        """Generar clave única para archivo"""
        return f"{file_info['id']}_{file_info['name']}"
    
    def _get_file_hash(self, file_info: Dict) -> str:
        """Generar hash para archivo basado en metadatos"""
        content = f"{file_info['name']}_{file_info['size']}_{file_info['last_modified']}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def needs_processing(self, file_info: Dict) -> bool:
        """
        Determinar si un archivo necesita ser procesado
        
        Returns:
            True si el archivo necesita procesamiento (nuevo o modificado)
            False si ya está en cache y no ha cambiado
        """
        file_key = self._get_file_key(file_info)
        file_hash = self._get_file_hash(file_info)
        
        processed_files = self.cache_data['processed_files']
        
        # Archivo no existe en cache
        if file_key not in processed_files:
            return True
            
        cached_info = processed_files[file_key]
        
        # Verificar si ha cambiado
        if cached_info.get('file_hash') != file_hash:
            return True
            
        # Verificar fecha de modificación como respaldo
        cached_modified = cached_info.get('last_modified')
        current_modified = file_info['last_modified']
        
        if cached_modified != current_modified:
            return True
            
        return False
    
    def mark_as_processed(self, file_info: Dict, processing_stats: Dict = None):
        """Marcar archivo como procesado y guardar en cache"""
        file_key = self._get_file_key(file_info)
        file_hash = self._get_file_hash(file_info)
        
        cache_entry = {
            'file_id': file_info['id'],
            'file_name': file_info['name'],
            'file_size': file_info['size'],
            'last_modified': file_info['last_modified'],
            'file_hash': file_hash,
            'processed_at': datetime.now().isoformat(),
            'processing_stats': processing_stats or {}
        }
        
        self.cache_data['processed_files'][file_key] = cache_entry
        self.cache_data['last_sync'] = datetime.now().isoformat()
        
        # Actualizar estadísticas
        stats = self.cache_data['stats']
        stats['total_processed'] = stats.get('total_processed', 0) + 1
        
        self._save_cache()
    
    def filter_files_for_processing(self, files: List[Dict]) -> Dict:
        """
        Filtrar archivos para determinar cuáles necesitan procesamiento
        
        Returns:
            Dict con 'to_process', 'skipped', y 'stats'
        """
        to_process = []
        skipped = []
        stats = {
            'total_files': len(files),
            'new_files': 0,
            'updated_files': 0,
            'cache_hits': 0
        }
        
        for file_info in files:
            file_key = self._get_file_key(file_info)
            
            if self.needs_processing(file_info):
                to_process.append(file_info)
                
                # Determinar si es nuevo o actualizado
                if file_key in self.cache_data['processed_files']:
                    stats['updated_files'] += 1
                else:
                    stats['new_files'] += 1
            else:
                skipped.append(file_info)
                stats['cache_hits'] += 1
        
        return {
            'to_process': to_process,
            'skipped': skipped,
            'stats': stats
        }
    
    def get_cache_stats(self) -> Dict:
        """Obtener estadísticas del cache"""
        processed_files = self.cache_data['processed_files']
        
        return {
            'cache_file': str(self.cache_file),
            'total_processed_files': len(processed_files),
            'last_sync': self.cache_data.get('last_sync'),
            'cache_size_kb': self.cache_file.stat().st_size / 1024 if self.cache_file.exists() else 0,
            'overall_stats': self.cache_data['stats']
        }
    
    def clear_cache(self):
        """Limpiar todo el cache"""
        self.cache_data = {
            'processed_files': {},
            'last_sync': None,
            'stats': {
                'total_processed': 0,
                'cache_hits': 0,
                'new_files': 0,
                'updated_files': 0
            }
        }
        self._save_cache()
    
    def remove_file_from_cache(self, file_info: Dict):
        """Remover archivo específico del cache"""
        file_key = self._get_file_key(file_info)
        if file_key in self.cache_data['processed_files']:
            del self.cache_data['processed_files'][file_key]
            self._save_cache()
    
    def cleanup_orphaned_entries(self, current_files: List[Dict]):
        """Limpiar entradas del cache que ya no existen en SharePoint"""
        current_file_keys = {self._get_file_key(f) for f in current_files}
        cached_file_keys = set(self.cache_data['processed_files'].keys())
        
        orphaned_keys = cached_file_keys - current_file_keys
        
        if orphaned_keys:
            for key in orphaned_keys:
                del self.cache_data['processed_files'][key]
            
            self._save_cache()
            return len(orphaned_keys)
        
        return 0

def test_cache_system():
    """Función de prueba para el sistema de cache"""
    print("🧪 Probando sistema de cache...")
    
    cache = SharePointSyncCache("/tmp/test_cache.json")
    
    # Archivo de prueba
    test_file = {
        'id': 'test123',
        'name': 'documento_prueba.pdf',
        'size': 1024,
        'last_modified': '2025-07-21T10:00:00Z'
    }
    
    # Primera verificación - debería necesitar procesamiento
    print(f"¿Necesita procesamiento? {cache.needs_processing(test_file)}")
    
    # Marcar como procesado
    cache.mark_as_processed(test_file, {'characters': 1500})
    
    # Segunda verificación - no debería necesitar procesamiento
    print(f"¿Necesita procesamiento después de cache? {cache.needs_processing(test_file)}")
    
    # Modificar archivo
    test_file['last_modified'] = '2025-07-21T11:00:00Z'
    print(f"¿Necesita procesamiento después de modificación? {cache.needs_processing(test_file)}")
    
    # Estadísticas
    stats = cache.get_cache_stats()
    print(f"Estadísticas del cache: {stats}")
    
    print("✅ Prueba del cache completada")

if __name__ == "__main__":
    test_cache_system()
