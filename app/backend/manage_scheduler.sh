#!/bin/bash
"""
Script de Management para SharePoint Scheduler
==============================================

Facilita el control del scheduler automático con comandos simples.

Uso:
  ./manage_scheduler.sh start [interval] [max_files]
  ./manage_scheduler.sh stop
  ./manage_scheduler.sh status
  ./manage_scheduler.sh test
  ./manage_scheduler.sh logs
"""

SCHEDULER_SCRIPT="scheduler_sharepoint_sync.py"
PID_FILE="/tmp/sharepoint_scheduler.pid"
LOG_DIR="/workspaces/azure-search-openai-demo/logs"

function show_usage() {
    echo "📋 Uso del SharePoint Scheduler:"
    echo ""
    echo "  🚀 Comandos principales:"
    echo "    start [interval] [max_files]  - Iniciar scheduler"
    echo "    stop                          - Detener scheduler"
    echo "    restart                       - Reiniciar scheduler"
    echo "    status                        - Ver estado"
    echo "    test                          - Ejecutar prueba"
    echo "    logs                          - Ver logs"
    echo ""
    echo "  ⚙️ Parámetros opcionales:"
    echo "    interval    - Horas entre sincronizaciones (default: 6)"
    echo "    max_files   - Máximo archivos por sync (default: sin límite)"
    echo ""
    echo "  📁 Ejemplos:"
    echo "    ./manage_scheduler.sh start              # Cada 6 horas, todos los archivos"
    echo "    ./manage_scheduler.sh start 4           # Cada 4 horas, todos los archivos"
    echo "    ./manage_scheduler.sh start 2 10        # Cada 2 horas, máximo 10 archivos"
    echo ""
}

function start_scheduler() {
    local interval=${1:-6}
    local max_files=$2
    
    if is_running; then
        echo "⚠️ El scheduler ya está ejecutándose (PID: $(cat $PID_FILE))"
        return 1
    fi
    
    echo "🚀 Iniciando SharePoint Scheduler..."
    echo "   • Intervalo: cada $interval horas"
    
    if [ -n "$max_files" ]; then
        echo "   • Límite: $max_files archivos por sincronización"
    else
        echo "   • Límite: Sin límite de archivos"
    fi
    
    mkdir -p "$LOG_DIR"
    
    # Construir comando
    local cmd="python3 $SCHEDULER_SCRIPT --interval $interval"
    if [ -n "$max_files" ]; then
        cmd="$cmd --max-files $max_files"
    fi
    
    # Ejecutar en background
    nohup $cmd > "$LOG_DIR/scheduler_console.log" 2>&1 &
    local pid=$!
    
    echo $pid > "$PID_FILE"
    sleep 2
    
    if is_running; then
        echo "✅ Scheduler iniciado correctamente (PID: $pid)"
        echo "📁 Logs en: $LOG_DIR/"
    else
        echo "❌ Error iniciando scheduler"
        rm -f "$PID_FILE"
        return 1
    fi
}

function stop_scheduler() {
    if ! is_running; then
        echo "ℹ️ El scheduler no está ejecutándose"
        return 0
    fi
    
    local pid=$(cat "$PID_FILE")
    echo "🛑 Deteniendo scheduler (PID: $pid)..."
    
    kill -TERM $pid 2>/dev/null
    sleep 3
    
    if is_running; then
        echo "⚠️ Scheduler no respondió, forzando terminación..."
        kill -KILL $pid 2>/dev/null
        sleep 1
    fi
    
    if ! is_running; then
        echo "✅ Scheduler detenido correctamente"
        rm -f "$PID_FILE"
    else
        echo "❌ Error deteniendo scheduler"
        return 1
    fi
}

function is_running() {
    [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null
}

function show_status() {
    echo "📊 Estado del SharePoint Scheduler:"
    echo ""
    
    if is_running; then
        local pid=$(cat "$PID_FILE")
        echo "   ✅ Estado: EJECUTÁNDOSE"
        echo "   🆔 PID: $pid"
        
        # Mostrar tiempo de ejecución
        local start_time=$(ps -o lstart= -p $pid 2>/dev/null)
        if [ -n "$start_time" ]; then
            echo "   ⏰ Iniciado: $start_time"
        fi
        
        # Mostrar uso de recursos
        local cpu_mem=$(ps -o %cpu,%mem --no-headers -p $pid 2>/dev/null)
        if [ -n "$cpu_mem" ]; then
            echo "   💻 CPU/MEM: $cpu_mem"
        fi
    else
        echo "   ❌ Estado: DETENIDO"
        if [ -f "$PID_FILE" ]; then
            echo "   ⚠️ Archivo PID encontrado pero proceso no activo"
            rm -f "$PID_FILE"
        fi
    fi
    
    echo ""
    
    # Mostrar información de logs
    if [ -d "$LOG_DIR" ]; then
        echo "📁 Archivos de log:"
        ls -la "$LOG_DIR"/ 2>/dev/null | grep -E "(scheduler|sync)" || echo "   (no hay logs disponibles)"
        echo ""
    fi
    
    # Mostrar últimas estadísticas si existen
    local stats_file="$LOG_DIR/sync_stats.json"
    if [ -f "$stats_file" ]; then
        echo "📈 Última sincronización:"
        python3 -c "
import json
try:
    with open('$stats_file', 'r') as f:
        data = json.load(f)
        last = data.get('last_sync', {})
        print(f\"   • Fecha: {last.get('timestamp', 'N/A')}\")
        print(f\"   • Estado: {last.get('status', 'N/A')}\")
        print(f\"   • Archivos: {last.get('files_processed', 0)}/{last.get('files_total', 0)}\")
        print(f\"   • Duración: {last.get('duration_seconds', 0):.1f}s\")
        print(f\"   • Errores: {last.get('errors', 0)}\")
except:
    print('   (no hay datos disponibles)')
"
    fi
}

function test_sync() {
    echo "🧪 Ejecutando sincronización de prueba..."
    python3 "$SCHEDULER_SCRIPT" --test-sync
}

function show_logs() {
    echo "📄 Logs del SharePoint Scheduler:"
    echo ""
    
    if [ -f "$LOG_DIR/sharepoint_scheduler.log" ]; then
        echo "--- Últimas 20 líneas del log principal ---"
        tail -n 20 "$LOG_DIR/sharepoint_scheduler.log"
        echo ""
    fi
    
    if [ -f "$LOG_DIR/scheduler_console.log" ]; then
        echo "--- Últimas 10 líneas del log de consola ---"
        tail -n 10 "$LOG_DIR/scheduler_console.log"
        echo ""
    fi
    
    echo "💡 Para seguir los logs en tiempo real:"
    echo "   tail -f $LOG_DIR/sharepoint_scheduler.log"
}

function restart_scheduler() {
    echo "🔄 Reiniciando scheduler..."
    stop_scheduler
    sleep 2
    start_scheduler "$@"
}

# Función principal
case "${1:-}" in
    "start")
        start_scheduler "$2" "$3"
        ;;
    "stop")
        stop_scheduler
        ;;
    "restart")
        restart_scheduler "$2" "$3"
        ;;
    "status")
        show_status
        ;;
    "test")
        test_sync
        ;;
    "logs")
        show_logs
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
