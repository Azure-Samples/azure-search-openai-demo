# Integración SharePoint + Document Intelligence

## Flujo de integración propuesto:

### 1. **Ingesta automática desde SharePoint**
```python
# Nuevo script: sync_sharepoint_to_index.py

async def sync_sharepoint_documents():
    """Sincroniza documentos de SharePoint usando Document Intelligence"""
    
    # 1. Listar archivos de SharePoint/PILOTOS
    files = list_pilotos_files(drive_id, token)
    
    # 2. Para cada archivo PDF/imagen:
    for file in files:
        if file['name'].endswith(('.pdf', '.png', '.jpg', '.jpeg')):
            # 3. Descargar archivo temporalmente
            content = get_file_content(drive_id, file['id'], token)
            
            # 4. Procesar con Document Intelligence
            processed_text = await process_with_document_intelligence(content)
            
            # 5. Indexar en Azure Search con metadata de SharePoint
            await index_document({
                'id': f"sharepoint_{file['id']}",
                'content': processed_text,
                'source': 'SharePoint/PILOTOS',
                'filename': file['name'],
                'sharepoint_id': file['id'],
                'last_modified': file['lastModifiedDateTime']
            })
```

### 2. **Búsqueda unificada**
```python
async def unified_search(query: str, top: int = 15):
    """Búsqueda que combina Azure Search indexado + SharePoint en tiempo real"""
    
    # 1. Búsqueda en Azure Search (incluye documentos ya procesados de SharePoint)
    search_results = await search_client.search(query, top=top)
    
    # 2. Si no hay suficientes resultados, buscar en SharePoint en tiempo real
    if len(search_results) < top // 2:
        sharepoint_results = await search_sharepoint_files(query, top=10)
        
        # Procesar archivos de SharePoint con Document Intelligence si es necesario
        for result in sharepoint_results:
            if result['name'].endswith('.pdf') and 'processed_content' not in result:
                content = get_file_content(drive_id, result['id'], token)
                result['processed_content'] = await process_with_document_intelligence(content)
    
    return merge_results(search_results, sharepoint_results)
```

### 3. **Ventajas de la integración:**

#### ✅ **Procesamiento mejorado de PDFs escaneados**
- Document Intelligence puede extraer texto de PDFs escaneados en SharePoint
- OCR avanzado para documentos de calidad variable
- Reconocimiento de estructuras (tablas, formularios)

#### ✅ **Índice enriquecido**
- Contenido de SharePoint indexado y buscable
- Metadata preservada (autor, fecha modificación)
- Búsqueda semántica mejorada

#### ✅ **Sincronización automática**
- Scheduler que revisa cambios en SharePoint
- Reindexación solo de documentos modificados
- Notificaciones de nuevos documentos

#### ✅ **Fallback inteligente**
- Si un documento no está indexado, se procesa en tiempo real
- Combina resultados indexados + tiempo real
- Mejor cobertura de contenido

### 4. **Configuración requerida:**

#### Variables de entorno adicionales:
```env
# Sincronización SharePoint
SHAREPOINT_SYNC_ENABLED=true
SHAREPOINT_SYNC_INTERVAL_HOURS=4
SHAREPOINT_AUTO_PROCESS_PDFS=true

# Document Intelligence para SharePoint
SHAREPOINT_USE_DOCUMENT_INTELLIGENCE=true
SHAREPOINT_PROCESS_SCANNED_PDFS=true
```

#### Nuevo scheduler:
```python
# scheduler.py
@scheduler.scheduled_job('interval', hours=int(os.getenv('SHAREPOINT_SYNC_INTERVAL_HOURS', 4)))
async def sync_sharepoint_job():
    """Job automático de sincronización"""
    await sync_sharepoint_documents()
    logger.info("SharePoint sync completed")
```

## 5. **Implementación paso a paso:**

### Fase 1: Sincronización básica ✅ COMPLETADA
- [x] Crear script de sincronización manual ✅ sync_sharepoint_basic.py
- [x] Probar indexación de documentos de SharePoint ✅ 2 PDFs indexados exitosamente
- [x] Validar búsqueda unificada ✅ Documentos disponibles en Azure Search

### Fase 2: Document Intelligence ✅ COMPLETADA
- [x] Integrar procesamiento automático de PDFs ✅ sync_sharepoint_simple_advanced.py
- [x] Manejar diferentes tipos de documentos ✅ PDFs escaneados procesados exitosamente
- [x] Optimizar rendimiento ✅ Procesamiento secuencial funcional

### Fase 3: Automatización 🚀 SIGUIENTE
- [ ] Implementar scheduler automático
- [ ] Monitoring y logging
- [ ] Manejo de errores robusto

## 6. **Beneficios esperados:**

🎯 **Para PDFs escaneados:** Mejor extracción de texto que mejora significativamente la búsqueda
🎯 **Para documentos complejos:** Reconocimiento de tablas, formularios, estructuras
🎯 **Para contenido dinámico:** Sincronización automática mantiene el índice actualizado
🎯 **Para usuarios finales:** Una sola búsqueda accede a todo el contenido disponible
