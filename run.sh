#!/bin/bash
# ============================================================================
# Trading Bot ML v2.0 - Ejecutor Principal
# Inicia todos los módulos del sistema con logging detallado
# Basado en XAU_USD_MultiTrader_Pro v7.5 STABLE
# ============================================================================

set -e  # Detener en caso de error crítico

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Variables
INSTALL_DIR="/workspace"
LOG_DIR="$INSTALL_DIR/logs"
LOG_FILE="$LOG_DIR/startup_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="$INSTALL_DIR/bot.pid"

# ============================================================================
# Funciones de logging
# ============================================================================

log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[$timestamp]${NC} $1" | tee -a "$LOG_FILE"
}

module_log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${CYAN}[$timestamp]${NC} ${MAGENTA}[MODULE]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[$timestamp] ✓${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[$timestamp] ⚠${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[$timestamp] ✗${NC} $1" | tee -a "$LOG_FILE"
}

# ============================================================================
# Verificaciones previas
# ============================================================================

check_prerequisites() {
    log "Verificando prerrequisitos..."
    
    # Verificar directorio de instalación
    if [ ! -d "$INSTALL_DIR" ]; then
        error "Directorio de instalación no encontrado: $INSTALL_DIR"
        exit 1
    fi
    
    # Verificar Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        error "Python no encontrado"
        exit 1
    fi
    
    success "Python encontrado: $($PYTHON_CMD --version)"
    
    # Verificar entorno virtual
    VENV_DIR="$INSTALL_DIR/venv"
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        success "Entorno virtual activado"
    else
        warning "Entorno virtual no encontrado, usando Python del sistema"
    fi
    
    # Verificar archivo main.py
    if [ ! -f "$INSTALL_DIR/main.py" ]; then
        error "main.py no encontrado"
        exit 1
    fi
    
    success "Archivos principales verificados"
}

# ============================================================================
# Preparar directorios
# ============================================================================

prepare_directories() {
    log "Preparando directorios..."
    
    # Crear directorio de logs
    mkdir -p "$LOG_DIR"
    success "Directorio de logs creado: $LOG_DIR"
    
    # Crear otros directorios necesarios
    mkdir -p "$INSTALL_DIR/data_cache"
    mkdir -p "$INSTALL_DIR/models"
    mkdir -p "$INSTALL_DIR/trading_bot/ml/models"
    
    success "Directorios preparados"
}

# ============================================================================
# Iniciar módulos con logging
# ============================================================================

start_module() {
    local module_name=$1
    local module_status=$2
    
    if [ "$module_status" = "ok" ]; then
        success "Módulo iniciado: $module_name"
        module_log "$module_name -> INICIALIZADO CORRECTAMENTE"
    else
        error "Módulo falló: $module_name"
        module_log "$module_name -> ERROR EN INICIALIZACIÓN"
        return 1
    fi
}

init_modules() {
    log "Iniciando módulos del sistema..."
    echo ""
    
    # Módulo 1: Configuración
    module_log "Inicializando módulo de CONFIGURACIÓN..."
    if $PYTHON_CMD -c "from trading_bot.config.settings import *; print('Config OK')" >> "$LOG_FILE" 2>&1; then
        start_module "CONFIGURACIÓN" "ok"
    else
        start_module "CONFIGURACIÓN" "error"
    fi
    
    # Módulo 2: Data Fetcher
    module_log "Inicializando módulo de DATA FETCHER..."
    if $PYTHON_CMD -c "from trading_bot.data.data_fetcher import DataFetcher, TechnicalIndicators; print('DataFetcher OK')" >> "$LOG_FILE" 2>&1; then
        start_module "DATA FETCHER" "ok"
    else
        start_module "DATA FETCHER" "error"
    fi
    
    # Módulo 3: Machine Learning Engine
    module_log "Inicializando módulo de MACHINE LEARNING..."
    if $PYTHON_CMD -c "from trading_bot.ml.ml_engine import MLEngine, AdaptiveMLManager; print('MLEngine OK')" >> "$LOG_FILE" 2>&1; then
        start_module "MACHINE LEARNING" "ok"
    else
        start_module "MACHINE LEARNING" "error"
    fi
    
    # Módulo 4: Risk Management
    module_log "Inicializando módulo de RISK MANAGEMENT..."
    if $PYTHON_CMD -c "from trading_bot.risk.risk_manager import RiskManager, TradeValidator; print('RiskManager OK')" >> "$LOG_FILE" 2>&1; then
        start_module "RISK MANAGEMENT" "ok"
    else
        start_module "RISK MANAGEMENT" "error"
    fi
    
    # Módulo 5: Trading Simulator
    module_log "Inicializando módulo de TRADING SIMULATOR..."
    if $PYTHON_CMD -c "from trading_bot.simulation.trading_simulator import TradingSimulator; print('Simulator OK')" >> "$LOG_FILE" 2>&1; then
        start_module "TRADING SIMULATOR" "ok"
    else
        start_module "TRADING SIMULATOR" "error"
    fi
    
    # Módulo 6: LLM Supervisor
    module_log "Inicializando módulo de LLM SUPERVISOR..."
    if $PYTHON_CMD -c "from trading_bot.core.llm_supervisor import LLMSupervisor; print('LLMSupervisor OK')" >> "$LOG_FILE" 2>&1; then
        start_module "LLM SUPERVISOR" "ok"
    else
        start_module "LLM SUPERVISOR" "error"
    fi
    
    # Módulo 7: Trading Engine Core
    module_log "Inicializando módulo de TRADING ENGINE CORE..."
    if $PYTHON_CMD -c "from trading_bot.core.trading_engine import TradingEngine, get_trading_engine; print('TradingEngine OK')" >> "$LOG_FILE" 2>&1; then
        start_module "TRADING ENGINE CORE" "ok"
    else
        start_module "TRADING ENGINE CORE" "error"
    fi
    
    # Módulo 8: Web Server
    module_log "Inicializando módulo de WEB SERVER..."
    if $PYTHON_CMD -c "from trading_bot.core.web_server import WebServer; print('WebServer OK')" >> "$LOG_FILE" 2>&1; then
        start_module "WEB SERVER" "ok"
    else
        start_module "WEB SERVER" "error"
    fi
    
    echo ""
    success "Todos los módulos inicializados"
}

# ============================================================================
# Verificar puerto
# ============================================================================

check_port() {
    local PORT=9000
    log "Verificando puerto $PORT..."
    
    if command -v lsof &> /dev/null; then
        if lsof -i :$PORT &> /dev/null; then
            warning "El puerto $PORT ya está en uso"
            warning "Intentando liberar el puerto..."
            
            # Intentar matar el proceso que usa el puerto
            PID=$(lsof -t -i :$PORT)
            if [ ! -z "$PID" ]; then
                kill -9 $PID 2>/dev/null || true
                sleep 2
                success "Puerto $PORT liberado"
            fi
        else
            success "Puerto $PORT disponible"
        fi
    else
        warning "No se pudo verificar el puerto (lsof no disponible)"
    fi
}

# ============================================================================
# Iniciar aplicación principal
# ============================================================================

start_application() {
    log "Iniciando aplicación principal..."
    echo ""
    
    # Guardar PID
    echo $$ > "$PID_FILE"
    
    # Cambiar al directorio de instalación
    cd "$INSTALL_DIR"
    
    # Iniciar main.py
    log "Ejecutando main.py..."
    log "============================================================"
    
    # Ejecutar y capturar salida
    $PYTHON_CMD main.py 2>&1 | tee -a "$LOG_FILE"
    
    # Verificar código de salida
    EXIT_CODE=${PIPESTATUS[0]}
    
    if [ $EXIT_CODE -eq 0 ]; then
        success "Aplicación finalizada correctamente"
    else
        warning "Aplicación finalizó con código: $EXIT_CODE"
    fi
}

# ============================================================================
# Manejo de señales
# ============================================================================

cleanup() {
    log ""
    log "Recibida señal de terminación..."
    log "Limpiando recursos..."
    
    # Eliminar PID file
    rm -f "$PID_FILE"
    
    log "Recursos limpiados"
    log "============================================================"
    log "Trading Bot ML v2.0 - SESIÓN FINALIZADA"
    log "============================================================"
    
    exit 0
}

# Configurar manejo de señales
trap cleanup SIGINT SIGTERM

# ============================================================================
# Mensaje de inicio
# ============================================================================

show_header() {
    echo ""
    echo "============================================================================"
    echo "  Trading Bot ML v2.0 - Sistema de Trading Profesional"
    echo "  Basado en XAU_USD_MultiTrader_Pro v7.5 STABLE"
    echo "============================================================================"
    echo ""
    echo "  Módulos cargados:"
    echo "    ✓ Data Fetcher con validación Spread/ATR"
    echo "    ✓ Machine Learning Ensemble (RF, GB, MLP)"
    echo "    ✓ Risk Management profesional"
    echo "    ✓ LLM Supervisor para ajustes automáticos"
    echo "    ✓ Trading Simulator con datos reales"
    echo "    ✓ Web Server en puerto 9000"
    echo ""
    echo "  Timeframes soportados: 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h"
    echo "  Modos de operación: Safe, Normal, Aggressive, Very Active"
    echo ""
    echo "  Log de sesión: $LOG_FILE"
    echo "============================================================================"
    echo ""
}

# ============================================================================
# Ejecución principal
# ============================================================================

main() {
    show_header
    
    check_prerequisites
    prepare_directories
    init_modules
    check_port
    start_application
}

# Ejecutar main
main "$@"
