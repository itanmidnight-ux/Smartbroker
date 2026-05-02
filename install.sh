#!/bin/bash
# ============================================================================
# Trading Bot ML v2.0 - Instalador Automático para Linux
# Basado en XAU_USD_MultiTrader_Pro v7.5 STABLE
# Compatible con sistemas con y sin root
# ============================================================================

set -e  # Detener en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables globales
INSTALL_DIR="/workspace"
PYTHON_CMD=""
HAS_ROOT=false
LOG_FILE="install_$(date +%Y%m%d_%H%M%S).log"

# ============================================================================
# Funciones de logging
# ============================================================================

log() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[⚠]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$LOG_FILE"
}

# ============================================================================
# Detección de sistema y permisos
# ============================================================================

detect_system() {
    log "Detectando sistema operativo..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        log "Sistema detectado: $OS $VER"
    else
        OS=$(uname -s)
        log "Sistema detectado: $OS"
    fi
    
    # Verificar si tenemos root
    if [ "$EUID" -eq 0 ]; then
        HAS_ROOT=true
        log "Ejecutando como ROOT"
    else
        HAS_ROOT=false
        log "Ejecutando como usuario normal (sin root)"
    fi
}

# ============================================================================
# Verificación de Python
# ============================================================================

check_python() {
    log "Verificando Python..."
    
    # Intentar diferentes comandos de Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        success "Python3 encontrado: $(python3 --version)"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        success "Python encontrado: $(python --version)"
    else
        error "Python no encontrado"
        
        if [ "$HAS_ROOT" = true ]; then
            log "Intentando instalar Python..."
            
            if command -v apt-get &> /dev/null; then
                apt-get update && apt-get install -y python3 python3-pip python3-venv
                PYTHON_CMD="python3"
                success "Python instalado correctamente"
            elif command -v yum &> /dev/null; then
                yum install -y python3 python3-pip
                PYTHON_CMD="python3"
                success "Python instalado correctamente"
            elif command -v dnf &> /dev/null; then
                dnf install -y python3 python3-pip
                PYTHON_CMD="python3"
                success "Python instalado correctamente"
            else
                error "No se pudo instalar Python automáticamente"
                exit 1
            fi
        else
            error "Instala Python 3.8+ manualmente o ejecuta este script como root"
            exit 1
        fi
    fi
    
    # Verificar versión mínima (3.8)
    PYVER=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$(echo $PYVER | cut -d. -f1)
    MINOR=$(echo $PYVER | cut -d. -f2)
    
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
        error "Python 3.8+ requerido, encontrado: $PYVER"
        exit 1
    fi
    
    success "Versión de Python válida: $PYVER"
}

# ============================================================================
# Verificación e instalación de dependencias del sistema
# ============================================================================

check_system_deps() {
    log "Verificando dependencias del sistema..."
    
    DEPS_NEEDED=()
    
    # Verificar gcc/g++ para compilación de paquetes
    if ! command -v gcc &> /dev/null; then
        DEPS_NEEDED+=("gcc")
    fi
    
    if ! command -v g++ &> /dev/null; then
        DEPS_NEEDED+=("g++")
    fi
    
    # Verificar make
    if ! command -v make &> /dev/null; then
        DEPS_NEEDED+=("make")
    fi
    
    # Verificar libffi-dev para cryptography
    if ! dpkg -l | grep -q libffi-dev && [ -f /etc/debian_version ]; then
        DEPS_NEEDED+=("libffi-dev")
    fi
    
    # Verificar python3-dev
    if ! dpkg -l | grep -q python3-dev && [ -f /etc/debian_version ]; then
        DEPS_NEEDED+=("python3-dev")
    fi
    
    if [ ${#DEPS_NEEDED[@]} -gt 0 ]; then
        warning "Dependencias faltantes: ${DEPS_NEEDED[*]}"
        
        if [ "$HAS_ROOT" = true ]; then
            log "Instalando dependencias del sistema..."
            
            if command -v apt-get &> /dev/null; then
                apt-get update
                apt-get install -y "${DEPS_NEEDED[@]}"
            elif command -v yum &> /dev/null; then
                yum install -y "${DEPS_NEEDED[@]}"
            elif command -v dnf &> /dev/null; then
                dnf install -y "${DEPS_NEEDED[@]}"
            fi
            
            success "Dependencias instaladas"
        else
            warning "No se pueden instalar dependencias sin root"
            warning "Por favor instala: ${DEPS_NEEDED[*]}"
            warning "Continuando de todos modos..."
        fi
    else
        success "Todas las dependencias del sistema están presentes"
    fi
}

# ============================================================================
# Configuración del entorno virtual
# ============================================================================

setup_venv() {
    log "Configurando entorno virtual..."
    
    VENV_DIR="$INSTALL_DIR/venv"
    
    if [ -d "$VENV_DIR" ]; then
        warning "Entorno virtual ya existe"
        read -p "¿Recrear el entorno virtual? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
            log "Entorno virtual eliminado"
        else
            success "Usando entorno virtual existente"
        fi
    fi
    
    if [ ! -d "$VENV_DIR" ]; then
        log "Creando entorno virtual..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        success "Entorno virtual creado en $VENV_DIR"
    fi
    
    # Activar entorno virtual
    source "$VENV_DIR/bin/activate"
    success "Entorno virtual activado"
    
    # Actualizar pip
    log "Actualizando pip..."
    pip install --upgrade pip wheel setuptools
}

# ============================================================================
# Instalación de dependencias Python
# ============================================================================

install_python_deps() {
    log "Instalando dependencias de Python..."
    
    REQUIREMENTS_FILE="$INSTALL_DIR/requirements.txt"
    
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        error "requirements.txt no encontrado"
        exit 1
    fi
    
    log "Instalando paquetes desde requirements.txt..."
    pip install -r "$REQUIREMENTS_FILE"
    
    success "Dependencias de Python instaladas"
}

# ============================================================================
# Verificación de instalación
# ============================================================================

verify_installation() {
    log "Verificando instalación..."
    
    ERRORS=0
    
    # Verificar imports principales
    log "Verificando módulos Python..."
    
    if ! $PYTHON_CMD -c "import pandas" 2>/dev/null; then
        error "pandas no instalado correctamente"
        ERRORS=$((ERRORS + 1))
    fi
    
    if ! $PYTHON_CMD -c "import numpy" 2>/dev/null; then
        error "numpy no instalado correctamente"
        ERRORS=$((ERRORS + 1))
    fi
    
    if ! $PYTHON_CMD -c "import sklearn" 2>/dev/null; then
        error "scikit-learn no instalado correctamente"
        ERRORS=$((ERRORS + 1))
    fi
    
    if ! $PYTHON_CMD -c "import flask" 2>/dev/null; then
        error "flask no instalado correctamente"
        ERRORS=$((ERRORS + 1))
    fi
    
    if ! $PYTHON_CMD -c "import yfinance" 2>/dev/null; then
        error "yfinance no instalado correctamente"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Verificar estructura de directorios
    log "Verificando estructura de directorios..."
    
    REQUIRED_DIRS=(
        "trading_bot"
        "trading_bot/config"
        "trading_bot/data"
        "trading_bot/ml"
        "trading_bot/core"
        "trading_bot/simulation"
        "templates"
        "static"
    )
    
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ ! -d "$INSTALL_DIR/$dir" ]; then
            error "Directorio faltante: $dir"
            ERRORS=$((ERRORS + 1))
        fi
    done
    
    # Verificar archivos principales
    REQUIRED_FILES=(
        "main.py"
        "run.sh"
        "requirements.txt"
    )
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$INSTALL_DIR/$file" ]; then
            error "Archivo faltante: $file"
            ERRORS=$((ERRORS + 1))
        fi
    done
    
    if [ $ERRORS -eq 0 ]; then
        success "✅ Instalación verificada correctamente"
        return 0
    else
        error "❌ Se encontraron $ERRORS errores en la verificación"
        return 1
    fi
}

# ============================================================================
# Crear archivo de configuración
# ============================================================================

create_config() {
    log "Creando archivo de configuración..."
    
    CONFIG_FILE="$INSTALL_DIR/bot_config.json"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        cat > "$CONFIG_FILE" << 'EOF'
{
    "symbol": "GC=F",
    "timeframe": "15m",
    "mode": "normal",
    "initial_capital": 1000.0,
    "auto_adjust": true,
    "port": 9000,
    "debug": false
}
EOF
        success "Archivo de configuración creado"
    else
        warning "Archivo de configuración ya existe"
    fi
}

# ============================================================================
# Mensaje final
# ============================================================================

show_final_message() {
    echo ""
    echo "============================================================================"
    success "🎉 INSTALACIÓN COMPLETADA EXITOSAMENTE"
    echo "============================================================================"
    echo ""
    echo "El Trading Bot ML v2.0 ha sido instalado correctamente."
    echo ""
    echo "Para iniciar el bot, ejecuta:"
    echo "  ${GREEN}./run.sh${NC}"
    echo ""
    echo "O directamente:"
    echo "  ${GREEN}source venv/bin/activate && python main.py${NC}"
    echo ""
    echo "Una vez iniciado, accede a la interfaz web en:"
    echo "  ${BLUE}http://localhost:9000${NC}"
    echo ""
    echo "Características incluidas:"
    echo "  ✓ Machine Learning con ensemble de modelos"
    echo "  ✓ Supervisor LLM para ajustes automáticos"
    echo "  ✓ Gestión de riesgo profesional (estilo MQL5 v7.5)"
    echo "  ✓ Simulador de trading con datos reales"
    echo "  ✓ Timeframes: 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h"
    echo "  ✓ Modos: Safe, Normal, Aggressive, Very Active"
    echo "  ✓ Logging completo en CSV"
    echo "  ✓ Interfaz web avanzada con gráficos en tiempo real"
    echo ""
    echo "Log de instalación: $LOG_FILE"
    echo "============================================================================"
}

# ============================================================================
# Ejecución principal
# ============================================================================

main() {
    echo ""
    echo "============================================================================"
    echo "  Trading Bot ML v2.0 - Instalador Automático"
    echo "  Basado en XAU_USD_MultiTrader_Pro v7.5 STABLE"
    echo "============================================================================"
    echo ""
    
    # Cambiar al directorio de instalación
    cd "$INSTALL_DIR"
    
    # Ejecutar pasos de instalación
    detect_system
    check_python
    check_system_deps
    setup_venv
    install_python_deps
    create_config
    verify_installation
    
    # Mostrar mensaje final
    show_final_message
}

# Ejecutar main
main "$@"
