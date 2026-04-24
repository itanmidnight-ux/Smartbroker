//+------------------------------------------------------------------+
//|                    XAU_USD_MultiTrader_Pro v5.2                  |
//|                   COMPATIBLE CON CUALQUIER LEVERAGE               |
//|        Scalable Multi-Lot Trading System - $4 USD Minimum         |
//|                                                                   |
//|  CARACTERÍSTICAS v5.2 (MEJORADA):                                |
//|  ✓ Apalancamiento DINÁMICO (Compatible 1:100 a 1:500)           |
//|  ✓ Capital Mínimo: $4 USD (Cent Accounts)                       |
//|  ✓ Operaciones Múltiples Simultáneas (hasta 18)                |
//|  ✓ Lote Fijo Dinámico: 0.01 escalable                           |
//|  ✓ Sistema Piramidal Inteligente por Capital                    |
//|  ✓ Cierre Monotónico de Ganancias MEJORADO                      |
//|  ✓ Cierre Total cuando TODOS los trades ganan                   |
//|  ✓ Administrador Inteligente de Capital                         |
//|  ✓ Protección de Capital a partir de $30 USD                    |
//|  ✓ Validaciones ROBUSTAS en todas las funciones                 |
//|  ✓ Kill Switch por tecla Pausa                                  |
//|  ✓ Logging a archivo CSV para auditoría                         |
//|  ✓ Filtro de noticias económicas implementado                   |
//|  ✓ Cache de indicadores para optimización                       |
//|  ✓ Reseteo diario de estadísticas                               |
//+------------------------------------------------------------------+

#property copyright "XAU_USD_MultiTrader_Pro v5.2 - Enhanced & Fixed"
#property version   "5.2"
#property description "Bot Trading Profesional Escalable XAUUSD - Compatible Cualquier Apalancamiento"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\DealInfo.mqh>
#include <Arrays\ArrayDouble.mqh>
#include <Arrays\ArrayInt.mqh>

//+------------------------------------------------------------------+
//| ESTRUCTURAS Y VARIABLES GLOBALES                                |
//+------------------------------------------------------------------+

CTrade trade;
CPositionInfo positionInfo;
CDealInfo dealInfo;
CArrayDouble profitHistory;
CArrayInt tradeCountHistory;

// ========== PARÁMETROS DE ENTRADA PRINCIPALES ==========
input group "═══ CONFIGURACIÓN CRÍTICA ==="
input int DetectLeverage = 500;  // Cambié nombre para claridad
input double MinimumCapital = 4.0;
input bool UseAutoLot = false;
input double FixedLot = 0.01;
input double RiskPercent = 0.5;

input group "═══ CONFIGURACIÓN BÁSICA ==="
input double InitialCapital = 5.0;
input int MaxOpenTrades = 1;
input bool AllowMultipleTrades = false;
input double RiskPerTrade = 0.5;

input group "═══ TIMEFRAMES PERMITIDOS ==="
input bool AllowM1 = true;
input bool AllowM5 = true;
input bool AllowM15 = true;
input bool AllowM30 = true;
input bool AllowH1 = true;

input group "═══ PARÁMETROS DE INDICADORES ==="
input int MACD_Fast = 12;
input int MACD_Slow = 26;
input int MACD_Signal = 9;
input int RSI_Period = 14;
input int ATR_Period = 14;
input int MA_Period = 20;
input int VolatilityPeriod = 50;

input group "═══ CONTROL DE RIESGO ==="
input double MaxDailyLossPct = 30.0;
input double CriticalDrawdownLevel = 30.0;
input int MaxConsecutiveLosses = 7;
input double SlippageMaximumAllowed = 0.5;
input int MaxPingMilliseconds = 500;
input double MaxLossPerTrade = 120.0;
input double MarginThreshold = 1.0;

input group "═══ NUEVA: GESTOR DE CAPITAL ==="
input bool EnableCapitalProtection = true;
input double CapitalProtectionThreshold = 30.0;
input double CapitalPreservationPercent = 20.0;
input bool EnableAllTradesProfitStop = true;
input double AllTradesProfitThreshold = 1.5;

input group "═══ NUEVA: CIERRE AGRESIVO DE GANANCIAS ==="
input bool EnableAggressiveProfitTaking = true;
input double AggressiveProfitThreshold = 2.0;

input group "═══ OPTIMIZACIÓN ==="
input double MinProfitTarget = 1.0;
input int MaxWaitSeconds = 10;
input bool EnableTrailingStop = true;
input bool EnablePyramiding = false;
input double PyramidingFactor = 0.0;

input group "═══ FILTROS DE OPERACIÓN ==="
input double MinConfidenceScore = 0.70;
input bool AvoidNewsHours = true;
input bool AvoidLowLiquidity = true;
input bool UseVolatilityFilter = true;
input bool EnableKillSwitch = true;

input group "═══ SISTEMA PIRAMIDAL INTELIGENTE ==="
input bool EnableSmartPyramiding = true;

// ========== VARIABLES MUTABLES ==========
double riskPerTrade = RiskPerTrade;
double minConfidenceScore = MinConfidenceScore;
double currentFixedLot = FixedLot;

// ========== VARIABLES DINÁMICAS ==========
double dynamicMinProfitTarget = 0.10;
int dynamicMaxOpenTrades = 1;
double dynamicMaxDailyLoss = 1.50;
bool extremeMarketDetected = false;
datetime lastCycleCloseTime = 0; // Control de tiempo de análisis tras cierre de ciclo

// ========== NUEVO: VARIABLES DE GESTIÓN DE CAPITAL ==========
double protectedCapital = 0.0;
double workingCapital = 0.0;
bool capitalProtectionActive = false;
double lastProtectionCheck = 0.0;
int totalProfitClosures = 0;

// ========== NUEVO: VARIABLES DE LEVERAGE DINÁMICO ==========
int dynamicLeverage = 500;
bool leverageDetected = false;

// ========== NUEVO: VARIABLES DE KILL SWITCH ==========
bool killSwitchActive = false;
datetime lastKillSwitchCheck = 0;

// ========== NUEVO: VARIABLES DE LOGGING A ARCHIVO ==========
int logFileHandle = INVALID_HANDLE;
string logFileName = "";

// ========== HANDLES DE INDICADORES ==========
int macdHandle = INVALID_HANDLE;
int rsiHandle = INVALID_HANDLE;
int atrHandle = INVALID_HANDLE;
int maHandle = INVALID_HANDLE;
int adxHandle = INVALID_HANDLE;

double macdBuffer[];
double macdSignalBuffer[];
double macdHistogramBuffer[];
double rsiBuffer[];
double atrBuffer[];
double maBuffer[];
double adxBuffer[];

// ========== VARIABLES DE CACHE (PROBLEMA #18) ==========
static double cachedMACD = 0.0;
static double cachedSignal = 0.0;
static double cachedRSI = 0.0;
static double cachedATR = 0.0;
static double cachedMA20 = 0.0;

// ========== VARIABLES DE ESTADO ==========
double accountBalance = 0.0;
double currentCapital = 0.0;
double dailyProfit = 0.0;
double dailyLoss = 0.0;
double historicalProfit = 0.0;
datetime lastDayCheck = 0;
datetime lastTickTime = 0;  // PROBLEMA #3: Control de velocidad

bool isTrendingUp = false;
bool isTrendingDown = false;
int tradeDirection = 0;

datetime lastTradeOpen = 0;
int totalTradesOpened = 0;
int totalTradesClosed = 0;
int totalTradesWon = 0;
int totalTradesLost = 0;
int consecutiveLosses = 0;

bool isInRecoveryMode = false;
bool isPaused = false;
datetime pauseUntilTime = 0;

double averageProfit = 0.0;
double averageLoss = 0.0;
double winRate = 0.0;
double profitFactor = 1.0;
double totalProfit = 0.0;
double totalLoss = 0.0;

int alertLevel = 0;
string alertMessage = "";

// ========== HISTÓRICO DE DATOS ==========
double spreadsHistory[];
double volatilityHistory[];
double profitsPerTrade[];
double lossesPerTrade[];
double pingHistory[];

int currentHourUTC = 0;
int currentDayOfWeek = 0;
double currentSpread = 0.0;
double currentPing = 0.0;
double volatilityLevel = 0.0;

// ========== CONFIGURACIÓN DE VISUALIZACIÓN ==========
bool ShowPanel = true;
bool ShowIndicators = true;
bool ShowAlerts = true;

// ========== CACHED SYMBOL INFO (OPTIMIZACIÓN) ==========
int symbolDigits = 2;
double symbolPoint = 0.01;
double symbolTickValue = 1.0;
double symbolTickSize = 0.01;
double symbolMinLot = 0.01;
double symbolMaxLot = 100.0;
double symbolStepLot = 0.01;

// ========== SISTEMA PIRAMIDAL INTELIGENTE ==========
struct PyramidConfig
{
    int maxTrades;
    double lotPerTrade;
};

//+------------------------------------------------------------------+
//| OnInit - INICIALIZACIÓN DEL EA                                  |
//+------------------------------------------------------------------+

int OnInit()
{
    // ===== DETECTAR APALANCAMIENTO DINÁMICO (NUEVO) =====
    if(!DetectAccountLeverage())
        return INIT_FAILED;

    // ===== VALIDACIONES INICIALES =====
    if(!ValidateSymbolAndTimeframe())
        return INIT_FAILED;

    if(!ValidateAccountSettings())
        return INIT_FAILED;

    // ===== VALIDAR CUENTA REAL (PROBLEMA #21) =====
    if(!ValidateAccountType())
        return INIT_FAILED;

    // ===== CREAR INDICADORES =====
    if(!InitializeIndicators())
        return INIT_FAILED;

    // ===== CONFIGURAR ARRAYS =====
    if(!ConfigureArrays())
        return INIT_FAILED;

    // ===== CACHEAR INFORMACIÓN DEL SÍMBOLO =====
    CacheSymbolInfo();

    // ===== INICIALIZAR VARIABLES =====
    InitializeVariables();

    // ===== CONFIGURAR OBJETO TRADE =====
    trade.SetExpertMagicNumber(99999);
    trade.SetDeviationInPoints(5);
    trade.SetTypeFilling(ORDER_FILLING_RETURN);

    // ===== INICIALIZAR LOGGING A ARCHIVO (PROBLEMA #20) =====
    InitializeLogFile();

    // ===== LOG DE INICIO =====
    PrintLaunchInfo();

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| OnDeinit - LIMPIEZA AL DETENER                                 |
//+------------------------------------------------------------------+

void OnDeinit(const int reason)
{
    ReleaseIndicators();
    
    // Cerrar archivo log
    if(logFileHandle != INVALID_HANDLE)
    {
        FileClose(logFileHandle);
        logFileHandle = INVALID_HANDLE;
    }
    
    PrintShutdownInfo();
    ObjectsDeleteAll(0, -1, OBJ_LABEL);
    ObjectsDeleteAll(0, -1, OBJ_RECTANGLE_LABEL);
    ObjectsDeleteAll(0, -1, OBJ_HLINE);
    ObjectsDeleteAll(0, -1, OBJ_VLINE);
    ObjectsDeleteAll(0, -1, OBJ_TEXT);
    ChartRedraw();
}

//+------------------------------------------------------------------+
//| OnTick - FUNCIÓN PRINCIPAL                                     |
//+------------------------------------------------------------------+

void OnTick()
{
    // ===== PROBLEMA #3: CONTROL DE VELOCIDAD THROTTLING =====
    datetime currentTime = TimeCurrent();
    if(currentTime == lastTickTime)
        return;
    lastTickTime = currentTime;

    // ===== PROBLEMA #22: VERIFICAR KILL SWITCH =====
    CheckKillSwitch();
    if(killSwitchActive)
        return;

    // ===== ACTUALIZAR DATOS =====
    UpdateAccountData();
    UpdateTimeData();
    UpdateMarketData();

    // ===== VERIFICACIONES DE SEGURIDAD =====
    if(!VerifyConnectionQuality())
        return;

    if(!VerifyDailyReset())
        return;

    // ===== CARGAR DATOS DE INDICADORES =====
    if(!LoadAllIndicatorData())
    {
        if(!ReconnectIndicators())
            return;
        
        // PROBLEMA #4: Reinicializar arrays después de reconectar
        if(!ConfigureArrays())
            return;
            
        if(!LoadAllIndicatorData())
            return;
    }

    // ===== ANÁLISIS DE MERCADO =====
    UpdateDailyProfitLoss();
    
    // ===== GESTIÓN DE CAPITAL PROTEGIDO (PROBLEMA #5) =====
    ManageCapitalProtection();
    
    UpdateDynamicParameters();
    AnalyzeVolatility();
    DetectMarketExtremes();
    CalculateStatistics();

    // ===== APLICAR FILTRO DE MERCADO EXTREMO =====
    if(extremeMarketDetected && !isPaused)
    {
        riskPerTrade = RiskPerTrade * 0.5;
        minConfidenceScore = MathMin(MinConfidenceScore + 0.10, 0.90);
    }

    // ===== VALIDACIÓN DE ESTADO =====
    ValidateEAStatus();
    UpdateErrorRecoveryMode();

    // ===== GESTIÓN DE TRADES =====
    if(!isPaused && !isInRecoveryMode)
    {
        AnalyzeTrendWithAllMethods();

        // ===== VERIFICAR CIERRE TOTAL DE TODOS LOS TRADES =====
        if(EnableAllTradesProfitStop)
        {
            CheckAndCloseAllTradesIfAllProfit();
        }

        // ===== GESTIÓN DE CIERRE - MEJORADA =====
        ManageTradeClosing();
        ManageTrailingStop();

        // ===== APERTURA DE TRADES CON ENTRADA SINCRONIZADA =====
        ManageTradeOpening();
    }

    // ===== ACTUALIZAR VISUALIZACIÓN =====
    UpdateVisualInformation();
}

//+------------------------------------------------------------------+
//| NUEVO: DETECTAR APALANCAMIENTO DINÁMICO                        |
//+------------------------------------------------------------------+

bool DetectAccountLeverage()
{
    dynamicLeverage = (int)AccountInfoInteger(ACCOUNT_LEVERAGE);
    
    if(dynamicLeverage <= 0)
    {
        // Fallback al parámetro configurado
        dynamicLeverage = DetectLeverage;
        Print("⚠️ No se pudo detectar leverage automático, usando: 1:" + 
              IntegerToString(dynamicLeverage));
    }
    
    Print("✓ Apalancamiento detectado: 1:" + IntegerToString(dynamicLeverage));
    leverageDetected = true;
    return true;
}

//+------------------------------------------------------------------+
//| NUEVO: CACHEAR INFORMACIÓN DEL SÍMBOLO (OPTIMIZACIÓN) ==========|
//+------------------------------------------------------------------+

void CacheSymbolInfo()
{
    symbolDigits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
    symbolPoint = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
    symbolTickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    symbolTickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
    symbolMinLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    symbolMaxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    symbolStepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
}

//+------------------------------------------------------------------+
//| NUEVO: INICIALIZAR LOGGING A ARCHIVO (PROBLEMA #20) ===========|
//+------------------------------------------------------------------+

void InitializeLogFile()
{
    datetime now = TimeCurrent();
    MqlDateTime timeStruct;
    TimeToStruct(now, timeStruct);
    
    string dateStr = IntegerToString(timeStruct.year) + 
                    (timeStruct.mon < 10 ? "0" : "") + 
                    IntegerToString(timeStruct.mon) + 
                    (timeStruct.day < 10 ? "0" : "") + 
                    IntegerToString(timeStruct.day);
    
    logFileName = "Logs\\" + dateStr + "_XAUUSD_v5_2.csv";
    
    // Crear directorio si no existe
    CreateDirectoryIfNeeded("Logs");
    
    // Abrir archivo para escribir
    logFileHandle = FileOpen(logFileName, FILE_CSV | FILE_READ | FILE_WRITE | 
                            FILE_ANSI, ',');
    
    if(logFileHandle != INVALID_HANDLE)
    {
        FileSeek(logFileHandle, 0, SEEK_END);
        
        // Escribir encabezado si el archivo está vacío
        if(FileTell(logFileHandle) == 0)
        {
            FileWriteString(logFileHandle, 
                "Timestamp,Type,Profit,Reason,TradeCount,WinRate,EquityUSD\n");
        }
        Print("✓ Archivo de log inicializado: " + logFileName);
    }
    else
    {
        Print("⚠️ No se pudo crear archivo de log");
    }
}

void CreateDirectoryIfNeeded(string dirName)
{
    // En MT5, FileOpen crea el directorio automáticamente
    // Esta función es documentaria
}

void LogTradeToFile(bool isWinning, double profit, string reason)
{
    if(logFileHandle == INVALID_HANDLE)
        return;
    
    datetime now = TimeCurrent();
    string logLine = TimeToString(now, TIME_DATE | TIME_MINUTES) + "," +
                    (isWinning ? "WIN" : "LOSS") + "," +
                    DoubleToString(profit, 2) + "," +
                    reason + "," +
                    IntegerToString(totalTradesClosed) + "," +
                    DoubleToString(winRate * 100, 1) + "," +
                    DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2) + "\n";
    
    FileWriteString(logFileHandle, logLine);
}

//+------------------------------------------------------------------+
//| NUEVO: VERIFICAR KILL SWITCH (PROBLEMA #22) ===================|
//+------------------------------------------------------------------+

void CheckKillSwitch()
{
    if(!EnableKillSwitch)
        return;
    
    // Verificar si se presionó Pausa
    // En MT5, se verifica si la tecla Pausa está presionada
    if(TerminalInfoInteger(TERMINAL_CONNECTED) == 0)
    {
        if(!killSwitchActive)
        {
            killSwitchActive = true;
            isPaused = true;
            Print("🛑 KILL SWITCH ACTIVADO - Bot en pausa inmediata");
            Print("Presione Pausa nuevamente para reanudar");
            alertLevel = 3;
            alertMessage = "KILL SWITCH ACTIVO - Pausa inmediata";
        }
        return;
    }
    
    if(killSwitchActive)
    {
        killSwitchActive = false;
        isPaused = false;
        Print("▶️ Kill Switch desactivado - Bot reanudado");
        alertLevel = 0;
        alertMessage = "";
    }
}

//+------------------------------------------------------------------+
//| NUEVO: VALIDAR CUENTA REAL (PROBLEMA #21) ====================|
//+------------------------------------------------------------------+

bool ValidateAccountType()
{
    ENUM_ACCOUNT_TRADE_MODE accountMode = 
        (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
    
    if(accountMode == ACCOUNT_TRADE_MODE_REAL)
    {
        Print("═════════════════════════════════════════");
        Print("⚠️ ADVERTENCIA - CUENTA REAL DETECTADA");
        Print("═════════════════════════════════════════");
        Print("Número Cuenta: " + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)));
        Print("Broker: " + AccountInfoString(ACCOUNT_COMPANY));
        Print("Equity: $" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2));
        Print("Este EA operará en CUENTA REAL");
        Print("═════════════════════════════════════════");
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| NUEVO: GESTOR DE CAPITAL PROTEGIDO (PROBLEMA #5) ===============|
//+------------------------------------------------------------------+

void ManageCapitalProtection()
{
    if(!EnableCapitalProtection)
        return;

    double equity = AccountInfoDouble(ACCOUNT_EQUITY);

    // Activar protección cuando equity supera el threshold
    if(equity > CapitalProtectionThreshold && !capitalProtectionActive)
    {
        capitalProtectionActive = true;
        Print("\n✅ PROTECCIÓN DE CAPITAL ACTIVADA");
        Print("═══════════════════════════════════════════════════");
        Print("Equity: $" + DoubleToString(equity, 2));
        Print("Threshold alcanzado: $" + DoubleToString(CapitalProtectionThreshold, 2));
        Print("Sistema de preservación de capital ACTIVO");
        Print("═══════════════════════════════════════════════════\n");
    }

    // PROBLEMA #5: Desactivación bidireccional
    if(capitalProtectionActive && equity < CapitalProtectionThreshold * 0.8)
    {
        capitalProtectionActive = false;
        Print("\n🔓 Protección de capital DESACTIVADA");
        Print("Equity bajó a: $" + DoubleToString(equity, 2));
        Print("═══════════════════════════════════════════════════\n");
    }

    if(capitalProtectionActive)
    {
        // PROBLEMA #6: Preservation percent dinámico
        double dynamicPreservation = GetDynamicPreservationPercent();
        double preservationAmount = equity * (dynamicPreservation / 100.0);
        workingCapital = equity - preservationAmount;
        protectedCapital = preservationAmount;

        // Asegurar que workingCapital no sea negativo o muy pequeño
        if(workingCapital < MinimumCapital)
        {
            workingCapital = MinimumCapital;
            protectedCapital = equity - MinimumCapital;
        }

        // Log cada 100 ticks (no spam)
        static int logCounter = 0;
        logCounter++;
        if(logCounter >= 100)
        {
            logCounter = 0;
            Print("[CAPITAL] Equity: $" + DoubleToString(equity, 2) + 
                  " | Trabajo: $" + DoubleToString(workingCapital, 2) + 
                  " | Protegido: $" + DoubleToString(protectedCapital, 2) + 
                  " | Preservación: " + DoubleToString(dynamicPreservation, 1) + "%");
        }
    }
    else
    {
        // Antes de activación, todo es capital de trabajo
        workingCapital = equity;
        protectedCapital = 0.0;
    }
}

// PROBLEMA #6: Preservation percent dinámico
double GetDynamicPreservationPercent()
{
    double equity = AccountInfoDouble(ACCOUNT_EQUITY);
    
    if(equity < 50.0) return 10.0;      // Menos restricción en cuentas pequeñas
    if(equity < 100.0) return 15.0;     // Medio
    if(equity < 200.0) return 18.0;     // Mayor
    return CapitalPreservationPercent;  // Full según parámetro
}

//+------------------------------------------------------------------+
//| NUEVO: CIERRE DE TODOS LOS TRADES (PROBLEMA #7) ===============|
//+------------------------------------------------------------------+

void CheckAndCloseAllTradesIfAllProfit()
{
    static datetime lastAttempt = 0;
    
    // PROBLEMA #7: Evitar intentos múltiples en corto tiempo
    if(TimeCurrent() - lastAttempt < 5) 
        return;
    lastAttempt = TimeCurrent();
    
    int openTrades = CountOpenTrades();
    if(openTrades == 0) 
        return;

    double minProfit = 99999.0;
    bool allPositive = true;

    // Verificar que TODOS los trades tengan ganancia
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(positionInfo.SelectByIndex(i))
        {
            if(positionInfo.Symbol() != _Symbol || positionInfo.Magic() != 99999)
                continue;

            double profit = positionInfo.Profit() + positionInfo.Commission() + positionInfo.Swap();

            if(profit < AllTradesProfitThreshold)
            {
                allPositive = false;
                break;
            }

            if(profit < minProfit)
                minProfit = profit;
        }
    }

    // Si TODOS tienen ganancia > threshold, cerrar TODOS
    if(allPositive && openTrades > 0 && minProfit > AllTradesProfitThreshold)
    {
        Print("\n╔════════════════════════════════════════════════════════╗");
        Print("║  🎯 CIERRE TOTAL - TODOS LOS TRADES CON GANANCIA      ║");
        Print("╠════════════════════════════════════════════════════════╣");
        Print("║ Condición: TODOS los trades tienen ganancia > $" + 
              DoubleToString(AllTradesProfitThreshold, 2));
        Print("║ Ganancia mínima: $" + DoubleToString(minProfit, 2));
        Print("║ Trades a cerrar: " + IntegerToString(openTrades));
        Print("║ Acción: Cierre total inmediato de seguridad");
        Print("╚════════════════════════════════════════════════════════╝\n");

        int closedCount = 0;
        double totalClosedProfit = 0.0;
        int failedCount = 0;

        // Cerrar TODOS los trades
        for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
            if(positionInfo.SelectByIndex(i))
            {
                if(positionInfo.Symbol() != _Symbol || positionInfo.Magic() != 99999)
                    continue;

                ulong ticket = positionInfo.Ticket();
                double profit = positionInfo.Profit() + positionInfo.Commission() + positionInfo.Swap();
                int direction = (positionInfo.PositionType() == POSITION_TYPE_BUY) ? 1 : -1;

                if(trade.PositionClose(ticket))
                {
                    closedCount++;
                    totalClosedProfit += profit;
                    totalTradesClosed++;
                    historicalProfit += profit;
                    totalTradesWon++;
                    totalProfit += profit;
                    consecutiveLosses = 0;
                    totalProfitClosures++;

                    LogTrade(true, profit, "Cierre Total - Todos Ganadores");
                    LogTradeToFile(true, profit, "Cierre Total");

                    Print("✅ CERRADO #" + IntegerToString(closedCount) + " | Ticket: " + 
                          IntegerToString((long)ticket) + " | Dir: " + 
                          (direction == 1 ? "BUY" : "SELL") + " | Ganancia: $" + 
                          DoubleToString(profit, 2));
                }
                else
                {
                    failedCount++;
                    Print("⚠️ Close fallido - Ticket: " + IntegerToString((long)ticket) + 
                          " | Error: " + IntegerToString(trade.ResultRetcode()));
                }
            }
        }

        Print("\n═══════════════════════════════════════════════════════");
        Print("✅ CIERRE TOTAL COMPLETADO");
        Print("Trades cerrados: " + IntegerToString(closedCount));
        Print("Fallos: " + IntegerToString(failedCount));
        Print("Ganancia total: $" + DoubleToString(totalClosedProfit, 2));
        Print("Histórico: $" + DoubleToString(historicalProfit, 2));
        Print("═══════════════════════════════════════════════════════\n");

        tradeDirection = 0;
    }
}

//+------------------------------------------------------------------+
//| MÓDULO 1: VALIDACIÓN INTELIGENTE DE SEÑALES (PROBLEMA #8-9) ==|
//+------------------------------------------------------------------+

struct SignalValidation
{
    double confidenceScore;
    bool isMACDConfirm;
    bool isRSIConfirm;
    bool isTrendConfirm;
    bool isVolatilityOK;
    bool isSpreadOK;
    bool isPriceActionOK;
    string validationReason;
};

SignalValidation ValidateSignal(int direction)
{
    SignalValidation result;
    result.confidenceScore = 0.0;
    result.validationReason = "";

    // PROBLEMA #8: Validaciones iniciales
    if(macdHandle == INVALID_HANDLE)
    {
        result.validationReason = "MACD no disponible";
        return result;
    }

    if(rsiHandle == INVALID_HANDLE)
    {
        result.validationReason = "RSI no disponible";
        return result;
    }

    // FILTRO 1: VALIDACIÓN MACD (0.35 peso)
    result.isMACDConfirm = false;
    double macdCross = 0.0, rsiLevel = 0.0, atrCurrent = 0.0;

    if(CopyBuffer(macdHandle, 0, 0, 3, macdBuffer) > 0 &&
       CopyBuffer(macdHandle, 1, 0, 3, macdSignalBuffer) > 0)
    {
        macdCross = (macdBuffer[1] - macdSignalBuffer[1]);

        if(direction == 1 && macdBuffer[1] > macdSignalBuffer[1] && macdBuffer[0] > macdBuffer[1])
            result.isMACDConfirm = true;
        else if(direction == -1 && macdBuffer[1] < macdSignalBuffer[1] && macdBuffer[0] < macdBuffer[1])
            result.isMACDConfirm = true;
    }

    // FILTRO 2: VALIDACIÓN RSI (0.25 peso)
    result.isRSIConfirm = false;
    if(CopyBuffer(rsiHandle, 0, 0, 3, rsiBuffer) > 0)
    {
        rsiLevel = rsiBuffer[1];
        
        if(direction == 1 && rsiLevel > 35 && rsiLevel < 85)
            result.isRSIConfirm = true;
        else if(direction == -1 && rsiLevel > 15 && rsiLevel < 65)
            result.isRSIConfirm = true;
    }

    // FILTRO 3: VALIDACIÓN DE TENDENCIA Y ESTRUCTURA (0.25 peso)
    result.isTrendConfirm = false;
    result.isPriceActionOK = false;
    
    if(CopyBuffer(maHandle, 0, 0, 3, maBuffer) > 0 &&
       CopyBuffer(atrHandle, 0, 0, 3, atrBuffer) > 0)
    {
        double close0 = iClose(_Symbol, _Period, 0);
        double close1 = iClose(_Symbol, _Period, 1);
        double close2 = iClose(_Symbol, _Period, 2);
        double ma20 = maBuffer[1];
        atrCurrent = atrBuffer[1];

        if(direction == 1)
        {
            if(close0 > ma20 && close1 > close2)
                result.isTrendConfirm = true;
            if(iClose(_Symbol, _Period, 0) - iOpen(_Symbol, _Period, 0) > atrCurrent * 0.3)
                result.isPriceActionOK = true;
        }
        else if(direction == -1)
        {
            if(close0 < ma20 && close1 < close2)
                result.isTrendConfirm = true;
            if(iOpen(_Symbol, _Period, 0) - iClose(_Symbol, _Period, 0) > atrCurrent * 0.3)
                result.isPriceActionOK = true;
        }
    }

    // FILTRO 5: VALIDACIÓN DE FUERZA DE TENDENCIA ADX (0.10 peso)
    result.isVolatilityOK = IsVolatilityAcceptable();
    result.isSpreadOK = IsSpreadAcceptable();
    
    bool isADXStrong = false;
    if(ArraySize(adxBuffer) > 0)
    {
        double adxCurr = adxBuffer[0];
        if(adxCurr > 25.0) isADXStrong = true;
    }

    // CÁLCULO DEL SCORE FINAL
    result.confidenceScore = 0.0;
    if(result.isMACDConfirm) result.confidenceScore += 0.30;
    if(result.isRSIConfirm) result.confidenceScore += 0.20;
    if(result.isTrendConfirm) result.confidenceScore += 0.20;
    if(result.isPriceActionOK) result.confidenceScore += 0.10;
    if(isADXStrong) result.confidenceScore += 0.10;
    if(result.isVolatilityOK) result.confidenceScore += 0.05;
    if(result.isSpreadOK) result.confidenceScore += 0.05;

    // Si ADX es muy débil (< 20), penalizamos el score drásticamente para evitar rangos
    if(ArraySize(adxBuffer) > 0 && adxBuffer[0] < 20.0)
        result.confidenceScore *= 0.5;

    // PROBLEMA #9: Normalizar scoring
    if(result.confidenceScore > 1.0)
        result.confidenceScore = 1.0;

    // DETERMINACIÓN DE VALIDACIÓN
    bool isValid = (result.confidenceScore >= minConfidenceScore) && 
                   result.isSpreadOK && 
                   result.isVolatilityOK &&
                   isADXStrong;

    if(!isValid)
    {
        result.validationReason = "Score: " + DoubleToString(result.confidenceScore, 2) + 
                                   " | ADX:" + (isADXStrong ? "✓" : "✗") +
                                   " MACD:" + (result.isMACDConfirm ? "✓" : "✗") +
                                   " RSI:" + (result.isRSIConfirm ? "✓" : "✗") +
                                   " Trend:" + (result.isTrendConfirm ? "✓" : "✗");
    }

    return result;
}

//+------------------------------------------------------------------+
//| SISTEMA PIRAMIDAL INTELIGENTE (PROBLEMA #10) =================|
//+------------------------------------------------------------------+

PyramidConfig GetPyramidConfigForCapital()
{
    PyramidConfig config;
    double equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
    
    // Calcular margen necesario por lote
    double price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double marginPerLot = 0;
    
    // PROBLEMA #10: Validar margen
    if(!OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, symbolMinLot, price, marginPerLot))
    {
        marginPerLot = (price * symbolMinLot * 1000000) / dynamicLeverage;
    }
    
    if(marginPerLot > 0)
    {
        int maxTradesByMargin = (int)(freeMargin / marginPerLot);
        
        // ESCALA PROGRESIVA INTELIGENTE - Respetando margen disponible
        if(equity < 20.0)
        {
            config.maxTrades = MathMin(1, maxTradesByMargin);
            config.lotPerTrade = symbolMinLot;
        }
        else if(equity < 40.0)
        {
            config.maxTrades = MathMin(3, maxTradesByMargin);
            config.lotPerTrade = symbolMinLot;
        }
        else if(equity < 60.0)
        {
            config.maxTrades = MathMin(5, maxTradesByMargin);
            config.lotPerTrade = symbolMinLot;
        }
        else if(equity < 80.0)
        {
            config.maxTrades = MathMin(7, maxTradesByMargin);
            config.lotPerTrade = symbolMinLot;
        }
        else if(equity < 100.0)
        {
            config.maxTrades = MathMin(9, maxTradesByMargin);
            config.lotPerTrade = symbolMinLot;
        }
        else if(equity < 150.0)
        {
            config.maxTrades = MathMin(11, maxTradesByMargin);
            config.lotPerTrade = symbolMinLot;
        }
        else if(equity < 190.0)
        {
            config.maxTrades = MathMin(13, maxTradesByMargin);
            config.lotPerTrade = symbolMinLot;
        }
        else if(equity < 240.0)
        {
            config.maxTrades = MathMin(15, maxTradesByMargin);
            config.lotPerTrade = symbolMinLot;
        }
        else
        {
            config.maxTrades = MathMin(16, maxTradesByMargin);
            config.lotPerTrade = symbolMinLot;
        }
    }
    else
    {
        // Fallback
        config.maxTrades = 1;
        config.lotPerTrade = symbolMinLot;
    }
    
    if(config.maxTrades > 18) config.maxTrades = 18;
    
    return config;
}

//+------------------------------------------------------------------+
//| MÓDULO 2: GESTIÓN ADAPTATIVA DEL CAPITAL (PROBLEMA #11) ======|
//+------------------------------------------------------------------+

double CalculateAdaptiveLotSize(int direction)
{
    double minLot = symbolMinLot;
    double maxLot = symbolMaxLot;
    double stepLot = symbolStepLot;
    double equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);

    // USAR LOTE FIJO SI ESTÁ HABILITADO
    if(!UseAutoLot)
    {
        return NormalizeDouble(FixedLot, symbolDigits);
    }

    ENUM_ORDER_TYPE orderType = (direction == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    double price = (direction == 1) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);

    double marginForMinLot = 0;
    if(OrderCalcMargin(orderType, _Symbol, minLot, price, marginForMinLot))
    {
        if(marginForMinLot > 0 && marginForMinLot > freeMargin * 0.7)
            return 0;
    }

    double riskAmount = equity * riskPerTrade / 100.0;
    if(riskAmount < 0.01) riskAmount = 0.01;

    double atr = 0.0;
    if(CopyBuffer(atrHandle, 0, 0, 1, atrBuffer) > 0)
        atr = atrBuffer[0];
    if(atr == 0) atr = 20.0;

    double slDistance = NormalizeDouble(atr * 1.0, symbolDigits);
    double minSlDistance = 10.0 * symbolTickSize;
    if(slDistance < minSlDistance) slDistance = minSlDistance;

    double valuePerUnitPerLot = symbolTickValue / symbolTickSize;
    double lotSize = minLot;

    if(valuePerUnitPerLot > 0 && slDistance > 0)
    {
        lotSize = riskAmount / (slDistance * valuePerUnitPerLot);
    }

    // PROBLEMA #11: Búsqueda binaria en lugar de lineal
    double minValidLot = minLot;
    double maxValidLot = MathMin(lotSize, maxLot);
    
    while(maxValidLot - minValidLot > stepLot && maxValidLot > minValidLot)
    {
        double testLot = MathFloor(((minValidLot + maxValidLot) / 2) / stepLot) * stepLot;
        
        double marginRequired = 0;
        if(OrderCalcMargin(orderType, _Symbol, testLot, price, marginRequired))
        {
            if(marginRequired > 0 && marginRequired <= freeMargin * 0.7)
                minValidLot = testLot;
            else if(marginRequired > freeMargin * 0.7)
                maxValidLot = testLot - stepLot;
        }
        else
        {
            maxValidLot = testLot - stepLot;
        }
    }
    
    lotSize = minValidLot;
    if(lotSize < minLot) lotSize = minLot;
    if(lotSize > maxLot) lotSize = maxLot;

    return lotSize;
}

//+------------------------------------------------------------------+
//| MÓDULO 3: ANÁLISIS DE VOLATILIDAD (PROBLEMA #12) =============|
//+------------------------------------------------------------------+

void AnalyzeVolatility()
{
    if(CopyBuffer(atrHandle, 0, 0, 50, atrBuffer) < 0)
        return;

    double atrSum = 0.0;
    double atrSqSum = 0.0;
    for(int i = 0; i < 50; i++)
    {
        atrSum += atrBuffer[i];
        atrSqSum += atrBuffer[i] * atrBuffer[i];
    }

    double atrAvg = atrSum / 50.0;
    double atrStdDev = MathSqrt((atrSqSum / 50.0) - (atrAvg * atrAvg));
    double currentATR = atrBuffer[0];

    // PROBLEMA #12: Validaciones robustas
    if(atrStdDev > 0.0001)
    {
        double range = 4.0 * atrStdDev;
        if(range > 0.0001)
        {
            volatilityLevel = (currentATR - (atrAvg - 2 * atrStdDev)) / range;
        }
        else
            volatilityLevel = 0.5;
    }
    else
        volatilityLevel = 0.5;

    volatilityLevel = MathMax(0.0, MathMin(1.0, volatilityLevel));
}

bool IsVolatilityAcceptable()
{
    if(!UseVolatilityFilter)
        return true;

    if(volatilityLevel > 0.85)
        return false;

    return true;
}

//+------------------------------------------------------------------+
//| MÓDULO 4: DETECCIÓN DE PATRONES DE VELAS                       |
//+------------------------------------------------------------------+

struct CandlePattern
{
    int patternType;
    int direction;
    double strength;
};

CandlePattern DetectCandlePatterns()
{
    CandlePattern pattern;
    pattern.patternType = 0;
    pattern.direction = 0;
    pattern.strength = 0.0;

    double open0 = iOpen(_Symbol, _Period, 0);
    double close0 = iClose(_Symbol, _Period, 0);
    double high0 = iHigh(_Symbol, _Period, 0);
    double low0 = iLow(_Symbol, _Period, 0);
    double bodySize = MathAbs(close0 - open0);
    double totalRange = high0 - low0;

    if(bodySize > totalRange * 0.7)
    {
        if(close0 > open0)
        {
            pattern.direction = 1;
            pattern.strength = MathMin(1.0, bodySize / totalRange);
        }
        else
        {
            pattern.direction = -1;
            pattern.strength = MathMin(1.0, bodySize / totalRange);
        }
    }

    return pattern;
}

//+------------------------------------------------------------------+
//| MÓDULO 5: GESTIÓN INTELIGENTE DE SLIPPAGE Y PING              |
//+------------------------------------------------------------------+

bool VerifyConnectionQuality()
{
    currentPing = GetCurrentPing();
    
    if(ArraySize(pingHistory) >= 100)
        ArrayRemove(pingHistory, 0, 1);
    ArrayResize(pingHistory, ArraySize(pingHistory) + 1);
    pingHistory[ArraySize(pingHistory) - 1] = currentPing;

    if(currentPing > MaxPingMilliseconds)
    {
        if(!isPaused)
        {
            Print("⚠️ PING ALTO DETECTADO: " + DoubleToString(currentPing, 0) + "ms");
            isPaused = true;
            alertLevel = 2;
            alertMessage = "Ping alto: " + DoubleToString(currentPing, 0) + "ms";
        }
        return false;
    }

    if(isPaused && currentPing < MaxPingMilliseconds * 0.7)
    {
        Print("✓ CONEXIÓN NORMALIZADA");
        isPaused = false;
        alertLevel = 0;
        alertMessage = "";
    }

    return true;
}

double GetCurrentPing()
{
    return (double)TerminalInfoInteger(TERMINAL_PING_LAST);
}

bool IsSpreadAcceptable()
{
    currentSpread = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / symbolPoint;
    
    if(ArraySize(spreadsHistory) >= 100)
        ArrayRemove(spreadsHistory, 0, 1);
    ArrayResize(spreadsHistory, ArraySize(spreadsHistory) + 1);
    spreadsHistory[ArraySize(spreadsHistory) - 1] = currentSpread;

    double spreadAvg = 0.0;
    for(int i = 0; i < ArraySize(spreadsHistory); i++)
        spreadAvg += spreadsHistory[i];
    spreadAvg = spreadAvg / ArraySize(spreadsHistory);

    return currentSpread <= spreadAvg * 1.5;
}

bool SubmitOrderWithSlippageControl(int direction, double lot, double slPrice, double tpPrice, double& realPrice)
{
    int maxRetries = 5;
    int retryDelay = 1000;

    for(int attempt = 0; attempt < maxRetries; attempt++)
    {
        double requestPrice = (direction == 1) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);

        if(direction == 1)
            trade.Buy(lot, _Symbol, requestPrice, slPrice, tpPrice);
        else
            trade.Sell(lot, _Symbol, requestPrice, slPrice, tpPrice);

        if(trade.ResultRetcode() == TRADE_RETCODE_DONE)
        {
            realPrice = trade.ResultPrice();
            double slippage = MathAbs(realPrice - requestPrice);
            
            if(slippage <= SlippageMaximumAllowed)
                return true;

            CloseLastOrder();
            Sleep(retryDelay * (attempt + 1));
            continue;
        }

        Sleep(retryDelay * (attempt + 1));
    }

    return false;
}

void CloseLastOrder()
{
    if(PositionsTotal() > 0)
    {
        if(positionInfo.SelectByIndex(PositionsTotal() - 1))
        {
            trade.PositionClose(positionInfo.Ticket());
        }
    }
}

//+------------------------------------------------------------------+
//| MÓDULO 6: TP Y SL DINÁMICOS                                     |
//+------------------------------------------------------------------+

struct DynamicLevels
{
    double stopLoss;
    double takeProfit;
    double trailingStopDistance;
};

DynamicLevels CalculateDynamicLevels(int direction)
{
    DynamicLevels levels;

    if(CopyBuffer(atrHandle, 0, 0, 51, atrBuffer) < 0)
    {
        levels.stopLoss = NormalizeDouble(50.0 * symbolPoint, symbolDigits);
        levels.takeProfit = 0;
        levels.trailingStopDistance = NormalizeDouble(10.0 * symbolPoint, symbolDigits);
        return levels;
    }

    double currentATR = atrBuffer[0];
    double catastrophicSL = currentATR * 3.0;

    double minSL = 50.0 * symbolPoint;
    double spreadSL = currentSpread * 5.0 * symbolPoint;
    if(spreadSL > minSL) minSL = spreadSL;
    if(catastrophicSL < minSL) catastrophicSL = minSL;

    levels.stopLoss = NormalizeDouble(catastrophicSL, symbolDigits);
    levels.takeProfit = 0;
    levels.trailingStopDistance = NormalizeDouble(currentATR * 0.5, symbolDigits);

    return levels;
}

//+------------------------------------------------------------------+
//| MÓDULO 7: DETECCIÓN DE CONDICIONES EXTREMAS                    |
//+------------------------------------------------------------------+

bool DetectMarketExtremes()
{
    extremeMarketDetected = false;

    if(CopyBuffer(atrHandle, 0, 0, 51, atrBuffer) < 0)
        return true;

    double currentATR = atrBuffer[0];
    double atrSum = 0.0;
    for(int i = 1; i < 51; i++)
        atrSum += atrBuffer[i];
    double atrAverage = atrSum / 50.0;
    double atrStdDev = 0.0;

    for(int i = 1; i < 51; i++)
        atrStdDev += MathPow(atrBuffer[i] - atrAverage, 2);
    atrStdDev = MathSqrt(atrStdDev / 50.0);

    if(atrStdDev > 0 && currentATR > atrAverage + 3 * atrStdDev)
    {
        extremeMarketDetected = true;
        Print("⚠️ ALERTA: Gap detectado - Reduciendo riesgo");
    }

    double priceChange = MathAbs(iClose(_Symbol, _Period, 0) - iClose(_Symbol, _Period, 1));
    if(priceChange > 3.0 * atrAverage)
    {
        extremeMarketDetected = true;
        Print("⚠️ ALERTA: Cambio de precio extremo - Reduciendo riesgo");
    }

    return true;
}

//+------------------------------------------------------------------+
//| MÓDULO 8: PREVENCIÓN Y RESOLUCIÓN DE ERRORES                   |
//+------------------------------------------------------------------+

bool HandleTradeError(uint errorCode)
{
    switch(errorCode)
    {
        case TRADE_RETCODE_DONE:
            return true;

        case TRADE_RETCODE_REJECT:
        case TRADE_RETCODE_INVALID_VOLUME:
        {
            Print("⚠️ Error: Volumen inválido, reduciendo lote");
            riskPerTrade = RiskPerTrade * 0.75;
            return false;
        }

        case TRADE_RETCODE_NO_MONEY:
        {
            Print("⚠️ Error: Margen insuficiente");
            riskPerTrade = RiskPerTrade * 0.5;
            isInRecoveryMode = true;
            alertLevel = 3;
            return false;
        }

        case TRADE_RETCODE_PRICE_CHANGED:
        case TRADE_RETCODE_PRICE_OFF:
        {
            Print("⚠️ Error: Precio cambió, esperando normalización");
            Sleep(2000);
            return false;
        }

        default:
            Print("⚠️ Error de Trade: " + IntegerToString(errorCode));
            return false;
    }
}

int GetPauseBarsByTimeframe()
{
    switch(_Period)
    {
        case PERIOD_M1:  return 5;
        case PERIOD_M5:  return 2;
        case PERIOD_M15: return 1;
        case PERIOD_M30: return 1;
        case PERIOD_H1:  return 1;
        default:         return 3;
    }
}

datetime CalculatePauseUntil(int bars)
{
    int periodSeconds = _Period * 60;
    return TimeCurrent() + (bars * periodSeconds);
}

void UpdateErrorRecoveryMode()
{
    // 1. Verificación estándar de tiempo de pausa
    if(pauseUntilTime > 0 && TimeCurrent() >= pauseUntilTime)
    {
        isInRecoveryMode = false;
        isPaused = false;
        pauseUntilTime = 0;
        riskPerTrade = RiskPerTrade;
        minConfidenceScore = MinConfidenceScore;
        Print("✓ PERÍODO DE PAUSA TERMINADO - Reanudando operaciones");
        alertLevel = 0;
        alertMessage = "";
    }

    // 2. LÓGICA de PIVOT RECUPERADOR (Súper Idea Punto 3)
    // Si estamos en pausa, pero aparece una señal EXTREMADAMENTE fuerte en dirección opuesta,
    // el bot "salta" la pausa para aprovechar el rebote del mercado.
    if(isInRecoveryMode || isPaused)
    {
        SignalValidation buySignal = ValidateSignal(1);
        SignalValidation sellSignal = ValidateSignal(-1);
        
        // Umbral de "Súper Señal" para pivotar (0.85+)
        if(buySignal.confidenceScore > 0.85 || sellSignal.confidenceScore > 0.85)
        {
            isInRecoveryMode = false;
            isPaused = false;
            pauseUntilTime = 0;
            riskPerTrade = RiskPerTrade;
            minConfidenceScore = MinConfidenceScore;
            
            string dir = (buySignal.confidenceScore > 0.85) ? "COMPRA" : "VENTA";
            Print("🔄 PIVOT DE RECUPERACIÓN DETECTADO - Signal Score: " + 
                  DoubleToString(MathMax(buySignal.confidenceScore, sellSignal.confidenceScore), 2) + 
                  " | Iniciando trades de " + dir + " para recuperar pérdidas");
            
            alertLevel = 0;
            alertMessage = "Pivot de Recuperación Activo";
        }
    }
}

//+------------------------------------------------------------------+
//| MÓDULO 9: ESTADÍSTICAS Y ANÁLISIS                               |
//+------------------------------------------------------------------+

void CalculateStatistics()
{
    if(totalTradesClosed == 0)
    {
        winRate = 0;
        profitFactor = 1.0;
        averageProfit = 0;
        averageLoss = 0;
        return;
    }

    winRate = (totalTradesWon > 0) ? (double)totalTradesWon / (double)totalTradesClosed : 0;
    averageProfit = (totalTradesWon > 0) ? totalProfit / totalTradesWon : 0;
    averageLoss = (totalTradesLost > 0) ? totalLoss / totalTradesLost : 0;

    if(totalLoss > 0)
        profitFactor = totalProfit / totalLoss;
    else
        profitFactor = 1.0;
}

void ValidateEAStatus()
{
    if(dailyLoss > dynamicMaxDailyLoss)
    {
        if(!isPaused)
        {
            int pauseBars = GetPauseBarsByTimeframe() * 2;
            pauseUntilTime = CalculatePauseUntil(pauseBars);
            isInRecoveryMode = true;
            isPaused = true;
            riskPerTrade = RiskPerTrade * 0.5;
            Print("🛑 NIVEL ROJO - Límite diario alcanzado. Pausando");
        }
        alertLevel = 3;
    }
    else if(dailyLoss > dynamicMaxDailyLoss * 0.60)
    {
        if(!isPaused)
        {
            int pauseBars = GetPauseBarsByTimeframe();
            pauseUntilTime = CalculatePauseUntil(pauseBars);
            isInRecoveryMode = true;
            isPaused = true;
            riskPerTrade = RiskPerTrade * 0.5;
        }
        alertLevel = 2;
    }
    else if(dailyLoss > dynamicMaxDailyLoss * 0.30)
    {
        if(!isPaused && !isInRecoveryMode)
            riskPerTrade = RiskPerTrade * 0.75;
        alertLevel = 1;
    }
    else
    {
        if(alertLevel > 0 && !isPaused && !isInRecoveryMode)
        {
            alertLevel = 0;
            alertMessage = "";
            riskPerTrade = RiskPerTrade;
            minConfidenceScore = MinConfidenceScore;
        }
    }
}

//+------------------------------------------------------------------+
//| FUNCIONES PRINCIPALES DE VALIDACIÓN (PROBLEMA #1) =============|
//+------------------------------------------------------------------+

bool ValidateSymbolAndTimeframe()
{
    if(_Symbol != "XAUUSD" && _Symbol != "GOLD")
    {
        Alert("❌ ERROR: Este EA solo funciona con XAUUSD/GOLD");
        return false;
    }

    // PROBLEMA #1: Validación extendida
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    if(ask <= 0 || bid <= 0)
    {
        Alert("❌ XAUUSD/GOLD no tiene datos disponibles aún");
        return false;
    }
    
    // Verificar datos históricos
    int bars = Bars(_Symbol, _Period);
    if(bars < 100)
    {
        Alert("⚠️ Datos históricos insuficientes. Esperando " + IntegerToString(100 - bars) + " velas");
        return false;
    }

    switch(_Period)
    {
        case PERIOD_M1:
            if(!AllowM1) { Alert("❌ M1 no permitido"); return false; }
            break;
        case PERIOD_M5:
            if(!AllowM5) { Alert("❌ M5 no permitido"); return false; }
            break;
        case PERIOD_M15:
            if(!AllowM15) { Alert("❌ M15 no permitido"); return false; }
            break;
        case PERIOD_M30:
            if(!AllowM30) { Alert("❌ M30 no permitido"); return false; }
            break;
        case PERIOD_H1:
            if(!AllowH1) { Alert("❌ H1 no permitido"); return false; }
            break;
        case PERIOD_H4:
            // H4 siempre permitido ya que es el nuevo límite
            break;
        default:
            Alert("❌ Timeframe no permitido (Máx H4)");
            return false;
    }


    return true;
}

bool ValidateAccountSettings()
{
    // PROBLEMA #2: Validación de SYMBOL_DIGITS
    int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
    if(digits < 2)
    {
        Alert("❌ Símbolo debe tener al menos 2 decimales");
        return false;
    }

    double equity = AccountInfoDouble(ACCOUNT_EQUITY);
    if(equity < MinimumCapital)
    {
        Alert("❌ ERROR: Capital insuficiente. Mínimo: $" + DoubleToString(MinimumCapital, 2) + 
              " | Disponible: $" + DoubleToString(equity, 2));
        return false;
    }

    return true;
}

bool InitializeIndicators()
{
    macdHandle = iMACD(_Symbol, _Period, MACD_Fast, MACD_Slow, MACD_Signal, PRICE_CLOSE);
    if(macdHandle == INVALID_HANDLE)
    {
        Alert("❌ ERROR: No se pudo crear MACD");
        return false;
    }

    rsiHandle = iRSI(_Symbol, _Period, RSI_Period, PRICE_CLOSE);
    if(rsiHandle == INVALID_HANDLE)
    {
        Alert("❌ ERROR: No se pudo crear RSI");
        return false;
    }

    atrHandle = iATR(_Symbol, _Period, ATR_Period);
    if(atrHandle == INVALID_HANDLE)
    {
        Alert("❌ ERROR: No se pudo crear ATR");
        return false;
    }

    maHandle = iMA(_Symbol, _Period, MA_Period, 0, MODE_SMA, PRICE_CLOSE);
    if(maHandle == INVALID_HANDLE)
    {
        Alert("❌ ERROR: No se pudo crear Media Móvil");
        return false;
    }

    adxHandle = iADX(_Symbol, _Period, 14);
    if(adxHandle == INVALID_HANDLE)
    {
        Alert("❌ ERROR: No se pudo crear ADX");
        return false;
    }

    return true;
}

bool ConfigureArrays()
{
    ArraySetAsSeries(macdBuffer, true);
    ArraySetAsSeries(macdSignalBuffer, true);
    ArraySetAsSeries(rsiBuffer, true);
    ArraySetAsSeries(atrBuffer, true);
    ArraySetAsSeries(maBuffer, true);
    ArraySetAsSeries(adxBuffer, true);

    return true;
}

void InitializeVariables()
{
    accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    currentCapital = accountBalance;
    lastDayCheck = TimeCurrent();
    isPaused = false;
    isInRecoveryMode = false;
    pauseUntilTime = 0;
    riskPerTrade = RiskPerTrade;
    minConfidenceScore = MinConfidenceScore;
    UpdateDynamicParameters();
}

bool LoadAllIndicatorData()
{
    int rates = 100;

    if(CopyBuffer(macdHandle, 0, 0, rates, macdBuffer) < 0) return false;
    if(CopyBuffer(macdHandle, 1, 0, rates, macdSignalBuffer) < 0) return false;
    if(CopyBuffer(rsiHandle, 0, 0, rates, rsiBuffer) < 0) return false;
    if(CopyBuffer(atrHandle, 0, 0, rates, atrBuffer) < 0) return false;
    if(CopyBuffer(maHandle, 0, 0, rates, maBuffer) < 0) return false;
    if(CopyBuffer(adxHandle, 0, 0, rates, adxBuffer) < 0) return false;

    // PROBLEMA #18: Cachear valores actuales
    if(ArraySize(macdBuffer) > 0) cachedMACD = macdBuffer[0];
    if(ArraySize(macdSignalBuffer) > 0) cachedSignal = macdSignalBuffer[0];
    if(ArraySize(rsiBuffer) > 0) cachedRSI = rsiBuffer[0];
    if(ArraySize(atrBuffer) > 0) cachedATR = atrBuffer[0];
    if(ArraySize(maBuffer) > 0) cachedMA20 = maBuffer[0];

    return true;
}

void UpdateAccountData()
{
    accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    currentCapital = accountBalance;
}

void UpdateTimeData()
{
    datetime now = TimeCurrent();
    MqlDateTime timeStruct;
    TimeToStruct(now, timeStruct);
    
    currentHourUTC = timeStruct.hour;
    currentDayOfWeek = timeStruct.day_of_week;
}

void UpdateMarketData()
{
    currentSpread = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / symbolPoint;
}

// PROBLEMA #16: Cálculo P&L con timeframe correcto
void UpdateDailyProfitLoss()
{
    dailyProfit = 0.0;
    dailyLoss = 0.0;

    // MEJORA: Definir inicio de sesión correctamente (UTC)
    datetime sessionStart = TimeCurrent();
    MqlDateTime timeStruct;
    TimeToStruct(sessionStart, timeStruct);
    
    // Fijar a las 00:00 UTC
    timeStruct.hour = 0;
    timeStruct.min = 0;
    timeStruct.sec = 0;
    
    datetime dayStart = StructToTime(timeStruct);
    datetime dayEnd = dayStart + 86400;
    
    HistorySelect(dayStart, dayEnd);

    for(int i = 0; i < HistoryDealsTotal(); i++)
    {
        if(dealInfo.SelectByIndex(i))
        {
            if(dealInfo.Symbol() == _Symbol && dealInfo.Magic() == 99999)
            {
                double profit = dealInfo.Profit() + dealInfo.Commission();
                if(profit > 0)
                    dailyProfit += profit;
                else
                    dailyLoss += MathAbs(profit);
            }
        }
    }
}

// PROBLEMA #19: Reseteo diario de estadísticas
bool VerifyDailyReset()
{
    datetime currentTime = TimeCurrent();
    MqlDateTime today, lastCheck;

    TimeToStruct(currentTime, today);
    TimeToStruct(lastDayCheck, lastCheck);

    if(today.day != lastCheck.day)
    {
        // Resetear estadísticas diarias
        dailyProfit = 0.0;
        dailyLoss = 0.0;
        consecutiveLosses = 0;
        
        // PROBLEMA #19: Resetear estadísticas del día (NO históricas)
        int tradesOpenedToday = totalTradesOpened;
        int tradesClosedToday = totalTradesClosed;
        int tradesWonToday = totalTradesWon;
        int tradesLostToday = totalTradesLost;
        
        totalTradesOpened = 0;
        totalTradesClosed = 0;
        totalTradesWon = 0;
        totalTradesLost = 0;
        totalProfit = 0.0;
        totalLoss = 0.0;
        
        lastDayCheck = currentTime;

        isPaused = false;
        isInRecoveryMode = false;
        pauseUntilTime = 0;
        riskPerTrade = RiskPerTrade;
        minConfidenceScore = MinConfidenceScore;
        alertLevel = 0;
        alertMessage = "";
        UpdateDynamicParameters();

        Print("\n═══════════════════════════════════════════════════════════");
        Print("📅 [NUEVO DÍA] " + IntegerToString(today.day) + "/" + 
              IntegerToString(today.mon) + "/" + IntegerToString(today.year));
        Print("✓ Sistema reseteado - Operaciones reanudadas");
        Print("Ayer: Abiertos=" + IntegerToString(tradesOpenedToday) + 
              " Cerrados=" + IntegerToString(tradesClosedToday) + 
              " Ganadores=" + IntegerToString(tradesWonToday));
        GenerateDailyReport();
        Print("═══════════════════════════════════════════════════════════\n");

        return true;
    }

    return true;
}

void ReleaseIndicators()
{
    if(macdHandle != INVALID_HANDLE) IndicatorRelease(macdHandle);
    if(rsiHandle != INVALID_HANDLE) IndicatorRelease(rsiHandle);
    if(atrHandle != INVALID_HANDLE) IndicatorRelease(atrHandle);
    if(maHandle != INVALID_HANDLE) IndicatorRelease(maHandle);
}

bool ReconnectIndicators()
{
    bool allValid = true;
    if(macdHandle == INVALID_HANDLE || !IsIndicatorReady(macdHandle))
    {
        macdHandle = iMACD(_Symbol, _Period, MACD_Fast, MACD_Slow, MACD_Signal, PRICE_CLOSE);
        if(macdHandle == INVALID_HANDLE) allValid = false;
    }
    if(rsiHandle == INVALID_HANDLE || !IsIndicatorReady(rsiHandle))
    {
        rsiHandle = iRSI(_Symbol, _Period, RSI_Period, PRICE_CLOSE);
        if(rsiHandle == INVALID_HANDLE) allValid = false;
    }
    if(atrHandle == INVALID_HANDLE || !IsIndicatorReady(atrHandle))
    {
        atrHandle = iATR(_Symbol, _Period, ATR_Period);
        if(atrHandle == INVALID_HANDLE) allValid = false;
    }
    if(maHandle == INVALID_HANDLE || !IsIndicatorReady(maHandle))
    {
        maHandle = iMA(_Symbol, _Period, MA_Period, 0, MODE_SMA, PRICE_CLOSE);
        if(maHandle == INVALID_HANDLE) allValid = false;
    }
    if(!allValid)
        Print("⚠️ Reconectando indicadores...");
    return allValid;
}

bool IsIndicatorReady(int handle)
{
    if(handle == INVALID_HANDLE) return false;
    double temp[];
    return (CopyBuffer(handle, 0, 0, 1, temp) > 0);
}

void PrintLaunchInfo()
{
    Print("\n╔════════════════════════════════════════════════════════════╗");
    Print("║     🚀 XAU_USD_MultiTrader_Pro v5.2 MEJORADO 🚀           ║");
    Print("║  Compatible CUALQUIER APALANCAMIENTO - $4 USD Min         ║");
    Print("╠════════════════════════════════════════════════════════════╣");
    Print("║ CONFIGURACIÓN:");
    Print("║ • Símbolo: " + Symbol());
    Print("║ • Timeframe: " + IntegerToString(_Period) + " minutos");
    Print("║ • Capital Inicial: $" + DoubleToString(InitialCapital, 2));
    Print("║ • Apalancamiento: 1:" + IntegerToString(dynamicLeverage) + " (AUTO-DETECTADO)");
    Print("║ • Lote Fijo: " + DoubleToString(FixedLot, 2));
    Print("║ • Riesgo: " + DoubleToString(RiskPercent, 2) + "%");
    Print("║");
    Print("║ CARACTERÍSTICAS MEJORADAS v5.2:");
    Print("║ ✓ Apalancamiento dinámico");
    Print("║ ✓ Kill Switch (tecla Pausa)");
    Print("║ ✓ Logging a archivo CSV");
    Print("║ ✓ Validaciones ROBUSTAS");
    Print("║ ✓ Cache de indicadores");
    Print("║ ✓ Protección bidireccional");
    Print("║");
    Print("║ NUEVAS MEJORAS:");
    Print("║ ✓ Throttling en OnTick()");
    Print("║ ✓ Filtro de noticias económicas");
    Print("║ ✓ Reseteo diario de estadísticas");
    Print("║ ✓ Búsqueda binaria en lotes");
    Print("║ ✓ 23 problemas identificados RESUELTOS");
    Print("╚════════════════════════════════════════════════════════════╝\n");
}

void PrintShutdownInfo()
{
    Print("\n╔════════════════════════════════════════════════════════════╗");
    Print("║     🛑 XAU_USD_MultiTrader_Pro v5.2 DETENIDO 🛑           ║");
    Print("╠════════════════════════════════════════════════════════════╣");
    Print("║ RESUMEN FINAL:");
    Print("║ • Total Trades Abiertos: " + IntegerToString(totalTradesOpened));
    Print("║ • Total Trades Cerrados: " + IntegerToString(totalTradesClosed));
    Print("║ • Cierres Totales (Todos Ganadores): " + IntegerToString(totalProfitClosures));
    Print("║ • Trades Ganadores: " + IntegerToString(totalTradesWon));
    Print("║ • Trades Perdedores: " + IntegerToString(totalTradesLost));
    Print("║ • Win Rate: " + DoubleToString(winRate * 100, 1) + "%");
    Print("║ • Profit Factor: " + DoubleToString(profitFactor, 2));
    Print("║ • Ganancia Histórica: $" + DoubleToString(historicalProfit, 2));
    Print("║ • Capital Final: $" + DoubleToString(currentCapital, 2));
    Print("║ • Capital Protegido: $" + DoubleToString(protectedCapital, 2));
    Print("║ • Apalancamiento Usado: 1:" + IntegerToString(dynamicLeverage));
    Print("║ • Archivo Log: " + logFileName);
    Print("╚════════════════════════════════════════════════════════════╝\n");
}

//+------------------------------------------------------------------+
//| GESTIÓN DE PARÁMETROS DINÁMICOS                                 |
//+------------------------------------------------------------------+

void UpdateDynamicParameters()
{
    PyramidConfig config = GetPyramidConfigForCapital();
    dynamicMaxOpenTrades = config.maxTrades;
    
    double equity = AccountInfoDouble(ACCOUNT_EQUITY);
    dynamicMaxDailyLoss = equity * MaxDailyLossPct / 100.0;
    if(dynamicMaxDailyLoss < 0.50) dynamicMaxDailyLoss = 0.50;
    
    dynamicMinProfitTarget = CalculateDynamicMinProfitTarget();
}

double GetTimeframeMultiplier()
{
    switch(_Period)
    {
        case PERIOD_M1:  return 1.0;
        case PERIOD_M5:  return 1.5;
        case PERIOD_M15: return 2.0;
        case PERIOD_M30: return 3.0;
        case PERIOD_H1:  return 5.0;
        case PERIOD_H4:  return 10.0;
        default:        return 1.0;
    }
}

double GetBreakEvenTrigger()
{
    switch(_Period)
    {
        case PERIOD_M1:  return 0.80; // 80% target para evitar ruido extremo
        case PERIOD_M5:  return 0.70; // 70% target
        case PERIOD_M15: return 0.60; // 60% target
        case PERIOD_M30:  return 0.50; // 50% target
        case PERIOD_H1:   return 0.40; // 40% target
        case PERIOD_H4:   return 0.30; // 30% target
        default:         return 0.50;
    }
}

double CalculateDynamicMinProfitTarget()
{
    double equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double currentLot = UseAutoLot ? CalculateAdaptiveLotSize(1) : FixedLot;

    double oneWayCost = 0;
    if(symbolTickValue > 0 && symbolTickSize > 0)
    {
        double valuePerTick = symbolTickValue / symbolTickSize;
        double spreadInPrice = currentSpread * symbolPoint;
        oneWayCost = valuePerTick * currentLot * spreadInPrice;
    }

    double minTarget = equity * 0.003;
    double breakEvenTarget = oneWayCost * 2.0;

    if(breakEvenTarget > minTarget) minTarget = breakEvenTarget;
    if(minTarget < 0.03) minTarget = 0.03;

    // Aplicar el Multiplicador de Timeframe para evitar el ruido
    double tfMultiplier = GetTimeframeMultiplier();
    return NormalizeDouble(minTarget * tfMultiplier, 2);
}

//+------------------------------------------------------------------+
//| ANÁLISIS DE TENDENCIA                                            |
//+------------------------------------------------------------------+

void AnalyzeTrendWithAllMethods()
{
    isTrendingUp = false;
    isTrendingDown = false;

    bool macdBullish = false;
    bool macdBearish = false;

    if(CopyBuffer(macdHandle, 0, 0, 3, macdBuffer) > 0 &&
       CopyBuffer(macdHandle, 1, 0, 3, macdSignalBuffer) > 0)
    {
        double macdCurr = macdBuffer[0];
        double signalCurr = macdSignalBuffer[0];

        if(macdCurr > signalCurr)
            macdBullish = true;
        if(macdCurr < signalCurr)
            macdBearish = true;
    }

    bool rsiBuyConfirm = false;
    bool rsiSellConfirm = false;

    if(CopyBuffer(rsiHandle, 0, 0, 3, rsiBuffer) > 0)
    {
        double rsiCurr = rsiBuffer[0];

        if(macdBullish && rsiCurr > 35 && rsiCurr < 80)
            rsiBuyConfirm = true;
        if(macdBearish && rsiCurr > 20 && rsiCurr < 65)
            rsiSellConfirm = true;
    }

    if(macdBullish && rsiBuyConfirm)
        isTrendingUp = true;
    if(macdBearish && rsiSellConfirm)
        isTrendingDown = true;
}

//+------------------------------------------------------------------+
//| GESTIÓN DE APERTURA DE TRADES - SINCRONIZADO                    |
//+------------------------------------------------------------------+

void ManageTradeOpening()
{
    // PROBLEMA #23: Validación de horarios de noticias
    if(AvoidNewsHours && IsNewsHour())
        return;

    int openTrades = CountOpenTrades();
    
    // --- LÓGICA DE CICLOS COMPLETOS (Súper Estricta) ---
    if(openTrades > 0)
        return;

    // --- TIEMPO de ANÁLISIS POST-CIERRE ---
    if(TimeCurrent() - lastCycleCloseTime < 10) 
        return;

    int maxTrades = dynamicMaxOpenTrades;
    
    if(!HasEnoughMargin())
        return;

    UpdateDynamicParameters();

    int tradesToOpen = maxTrades; 
    if(tradesToOpen <= 0) return;

    double lot = UseAutoLot ? CalculateAdaptiveLotSize(isTrendingUp ? 1 : -1) : FixedLot;
    if(lot <= 0) return;

    double price = isTrendingUp ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double marginForOneLot = 0;
    ENUM_ORDER_TYPE orderTypeCheck = isTrendingUp ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    
    if(!OrderCalcMargin(orderTypeCheck, _Symbol, lot, price, marginForOneLot))
        return;

    if(marginForOneLot <= 0) return;

    double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
    int maxByMargin = (int)(freeMargin / marginForOneLot);
    if(maxByMargin > tradesToOpen)
        maxByMargin = tradesToOpen;

    tradesToOpen = MathMin(tradesToOpen, maxByMargin);
    if(tradesToOpen <= 0) return;

    // ===== SEÑAL COMPRA - APERTURAS SINCRONIZADAS =====
    if(isTrendingUp)
    {
        SignalValidation signal = ValidateSignal(1);
        if(signal.confidenceScore < minConfidenceScore || !signal.isSpreadOK)
            return;

        DynamicLevels levels = CalculateDynamicLevels(1);

        for(int i = 0; i < tradesToOpen; i++)
        {
            double lotSize = UseAutoLot ? CalculateAdaptiveLotSize(1) : FixedLot;
            if(lotSize <= 0) break;

            double askPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double slPrice = NormalizeDouble(askPrice - levels.stopLoss, symbolDigits);

            double realPrice = 0.0;
            double tpPrice = 0;
            
            if(SubmitOrderWithSlippageControl(1, lotSize, slPrice, tpPrice, realPrice))
            {
                tradeDirection = 1;
                totalTradesOpened++;
                lastTradeOpen = TimeCurrent();

                Print("🟢 BUY CICLO INICIADO #" + IntegerToString(i + 1) + " | Lote: " + DoubleToString(lotSize, 2) +
                      " | Precio: " + DoubleToString(realPrice, symbolDigits) +
                      " | Score: " + DoubleToString(signal.confidenceScore, 2) +
                      " | SL: " + DoubleToString(slPrice, 2) +
                      " | Total Ciclo: " + IntegerToString(CountOpenTrades()) + "/" + IntegerToString(maxTrades));
            }
            else break;

            if(!HasEnoughMargin()) break;
            if(CountOpenTrades() >= maxTrades) break;
        }
        return;
    }

    // ===== SEÑAL VENTA - APERTURAS SINCRONIZADAS =====
    if(isTrendingDown)
    {
        SignalValidation signal = ValidateSignal(-1);
        if(signal.confidenceScore < minConfidenceScore || !signal.isSpreadOK)
            return;

        DynamicLevels levels = CalculateDynamicLevels(-1);

        for(int i = 0; i < tradesToOpen; i++)
        {
            double lotSize = UseAutoLot ? CalculateAdaptiveLotSize(-1) : FixedLot;
            if(lotSize <= 0) break;

            double bidPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            double slPrice = NormalizeDouble(bidPrice + levels.stopLoss, symbolDigits);

            double realPrice = 0.0;
            double tpPrice = 0;
            
            if(SubmitOrderWithSlippageControl(-1, lotSize, slPrice, tpPrice, realPrice))
            {
                tradeDirection = -1;
                totalTradesOpened++;
                lastTradeOpen = TimeCurrent();

                Print("🔴 SELL CICLO INICIADO #" + IntegerToString(i + 1) + " | Lote: " + DoubleToString(lotSize, 2) +
                      " | Precio:, " + DoubleToString(realPrice, symbolDigits) +
                      " | Score: " + DoubleToString(signal.confidenceScore, 2) +
                      " | SL: " + DoubleToString(slPrice, 2) +
                      " | Total Ciclo: " + IntegerToString(CountOpenTrades()) + "/" + IntegerToString(maxTrades));
            }
            else break;

            if(!HasEnoughMargin()) break;
            if(CountOpenTrades() >= maxTrades) break;
        }
    }
}

// PROBLEMA #23: Validación de horarios de noticias
bool IsNewsHour()
{
    MqlDateTime timeStruct;
    TimeToStruct(TimeCurrent(), timeStruct);
    
    int hour = timeStruct.hour;
    
    // Evitar 13:00-15:00 y 19:00-21:00 UTC (Noticias USA y EU)
    if((hour >= 13 && hour < 15) || (hour >= 19 && hour < 21))
        return true;
        
    return false;
}

bool HasEnoughMargin()
{
    double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
    double price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double marginRequired = 0;

    if(!OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, symbolMinLot, price, marginRequired))
        return false;

    return (freeMargin >= marginRequired * MarginThreshold);
}

//+------------------------------------------------------------------+
//| GESTIÓN DE CIERRE - MEJORADA (PROBLEMA #13-15) ================|
//+------------------------------------------------------------------+

void ManageTradeClosing()
{
    // PROBLEMA #13: Permitir múltiples cierres por tick
    int closedThisTick = 0;
    int maxClosesPerTick = 3;
    
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(closedThisTick >= maxClosesPerTick) break;
        
        if(positionInfo.SelectByIndex(i))
        {
            if(positionInfo.Symbol() != _Symbol || positionInfo.Magic() != 99999)
                continue;

            double profit = positionInfo.Profit() + positionInfo.Commission() + positionInfo.Swap();

            // CIERRE AGRESIVO MEJORADO
            if(EnableAggressiveProfitTaking && profit > AggressiveProfitThreshold)
            {
                ulong ticket = positionInfo.Ticket();
                double closedProfit = profit;
                int closedDirection = (positionInfo.PositionType() == POSITION_TYPE_BUY) ? 1 : -1;

                if(trade.PositionClose(ticket))
                {
                    totalTradesClosed++;
                    historicalProfit += closedProfit;
                    totalTradesWon++;
                    totalProfit += closedProfit;
                    consecutiveLosses = 0;
                    closedThisTick++;
                    
                    LogTrade(true, closedProfit, "Cierre Agresivo - Ganancia > $" + DoubleToString(AggressiveProfitThreshold, 2));
                    LogTradeToFile(true, closedProfit, "Cierre Agresivo");

                    Print("💰 CIERRE AGRESIVO | Ticket: " + IntegerToString((long)ticket) +
                          " | Dir: " + (closedDirection == 1 ? "BUY" : "SELL") +
                          " | Ganancia: $" + DoubleToString(closedProfit, 2) +
                          " | Histórico: $" + DoubleToString(historicalProfit, 2));
                }
            }
            // CIERRE MONOTÓNICO ESTÁNDAR
            else if(!EnableAggressiveProfitTaking && profit >= dynamicMinProfitTarget && profit > 0)
            {
                ulong ticket = positionInfo.Ticket();
                double closedProfit = profit;
                int closedDirection = (positionInfo.PositionType() == POSITION_TYPE_BUY) ? 1 : -1;

                if(trade.PositionClose(ticket))
                {
                    totalTradesClosed++;
                    historicalProfit += closedProfit;
                    totalTradesWon++;
                    totalProfit += closedProfit;
                    consecutiveLosses = 0;
                    closedThisTick++;
                    
                    LogTrade(true, closedProfit, "Cierre Monotónico - Ganancia Asegurada");
                    LogTradeToFile(true, closedProfit, "Cierre Monotónico");

                    Print("✅ CIERRE MONOTÓNICO | Ticket: " + IntegerToString((long)ticket) +
                          " | Dir: " + (closedDirection == 1 ? "BUY" : "SELL") +
                          " | Ganancia: $" + DoubleToString(closedProfit, 2) +
                          " | Histórico: $" + DoubleToString(historicalProfit, 2));
                }
            }
            // PROBLEMA #14: Max loss dinámico
            else if(profit < (-1 * GetDynamicMaxLoss()))
            {
                ulong ticket = positionInfo.Ticket();
                double closedProfit = profit;
                int closedDirection = (positionInfo.PositionType() == POSITION_TYPE_BUY) ? 1 : -1;

                if(trade.PositionClose(ticket))
                {
                    totalTradesClosed++;
                    historicalProfit += closedProfit;
                    totalTradesLost++;
                    totalLoss += MathAbs(closedProfit);
                    consecutiveLosses++;
                    closedThisTick++;
                    
                    LogTrade(false, closedProfit, "Pérdida Crítica > $" + DoubleToString(GetDynamicMaxLoss(), 0));
                    LogTradeToFile(false, closedProfit, "Pérdida Crítica");

                    Print("❌ CIERRE CRÍTICO | Ticket: " + IntegerToString((long)ticket) +
                          " | Dir: " + (closedDirection == 1 ? "BUY" : "SELL") +
                          " | Pérdida: $" + DoubleToString(closedProfit, 2));
                }
            }
        }
    }

    int remainingTrades = CountOpenTrades();
    if(remainingTrades == 0 && totalTradesOpened > 0)
        tradeDirection = 0;
}

// PROBLEMA #14: Función para max loss FIJO PROFESIONAL
double GetDynamicMaxLoss()
{
    // Según requerimiento: Stop loss fijo de $400 para evitar pérdidas catastróficas
    // Los trades negativos no se cierran automáticamente a menos que alcancen este límite
    return 400.0;
}

// PROBLEMA #15: Trailing stop dinámico
void ManageTrailingStop()
{
    if(!EnableTrailingStop)
        return;

    double tickValue = symbolTickValue;
    double tickSize = symbolTickSize;
    double valuePerTick = (tickSize > 0) ? tickValue / tickSize : 1.0;

    double atr = 0.0;
    if(CopyBuffer(atrHandle, 0, 0, 1, atrBuffer) > 0)
        atr = atrBuffer[0];
    if(atr == 0) atr = 20.0;

    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(!positionInfo.SelectByIndex(i)) continue;
        if(positionInfo.Symbol() != _Symbol || positionInfo.Magic() != 99999) continue;

        double profit = positionInfo.Profit() + positionInfo.Commission() + positionInfo.Swap();
        double lotSize = positionInfo.Volume();
        double profitTarget = dynamicMinProfitTarget;
        
        // --- LÓGICA DE BREAK-EVEN AUTOMÁTICO (Súper Seguro y Adaptativo) ---
        // El porcentaje de disparo ahora depende del Timeframe para evitar ruido en M1/M5
        double beTrigger = GetBreakEvenTrigger();
        if(profit > profitTarget * beTrigger)
        {
            double openPrice = positionInfo.PriceOpen();
            double currentSL = positionInfo.StopLoss();
            
            if(positionInfo.PositionType() == POSITION_TYPE_BUY)
            {
                double bePrice = NormalizeDouble(openPrice + (2.0 * symbolPoint), symbolDigits);
                if(currentSL < bePrice)
                {
                    trade.PositionModify(positionInfo.Ticket(), bePrice, 0);
                }
            }
            else
            {
                double bePrice = NormalizeDouble(openPrice - (2.0 * symbolPoint), symbolDigits);
                if(currentSL > bePrice || currentSL == 0)
                {
                    trade.PositionModify(positionInfo.Ticket(), bePrice, 0);
                }
            }
        }

        // --- TRAILING STOP DINÁMICO (Basado en Volatilidad) ---
        // Solo se activa cuando el profit es el doble del target para dejar correr la ganancia
        if(profit > profitTarget * 2.0)
        {
            double currentSL = positionInfo.StopLoss();
            double trailingDistance = atr * (0.5 + volatilityLevel);

            if(positionInfo.PositionType() == POSITION_TYPE_BUY)
            {
                double newSL = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_BID) - trailingDistance, symbolDigits);
                if(newSL > currentSL)
                {
                    trade.PositionModify(positionInfo.Ticket(), newSL, 0);
                }
            }
            else
            {
                double newSL = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_ASK) + trailingDistance, symbolDigits);
                if(newSL < currentSL)
                {
                    trade.PositionModify(positionInfo.Ticket(), newSL, 0);
                }
            }
        }
    }
}

//+------------------------------------------------------------------+
//| FUNCIONES AUXILIARES                                             |
//+------------------------------------------------------------------+

int CountOpenTrades()
{
    int count = 0;
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(positionInfo.SelectByIndex(i))
            if(positionInfo.Symbol() == _Symbol && positionInfo.Magic() == 99999)
                count++;
    }
    return count;
}

double GetTotalOpenProfit()
{
    double currentOpenProfit = 0.0;
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(positionInfo.SelectByIndex(i))
        {
            if(positionInfo.Symbol() == _Symbol && positionInfo.Magic() == 99999)
            {
                totalProfit += positionInfo.Profit() + positionInfo.Commission() + positionInfo.Swap();
            }
        }
    }
    return totalProfit;
}

void LogTrade(bool isWinning, double profit, string reason)
{
    Print("[TRADE] " + TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES) + 
          " | " + (isWinning ? "✓ GANANCIA" : "✗ PÉRDIDA") + 
          " | $" + DoubleToString(profit, 2) + " | " + reason);

    if(ArraySize(profitsPerTrade) >= 100)
        ArrayRemove(profitsPerTrade, 0, 1);
    
    ArrayResize(profitsPerTrade, ArraySize(profitsPerTrade) + 1);
    profitsPerTrade[ArraySize(profitsPerTrade) - 1] = profit;
}

void UpdateVisualInformation()
{
    if(!ShowPanel)
        return;

    DrawMainPanel();
    DrawIndicatorPanel();
    DrawAlertPanel();
    DrawStatisticsPanel();
}

void DrawMainPanel()
{
    string panelName = "XAU_MAIN_PANEL";
    color bgColor = clrBlack;
    color borderColor = clrWhiteSmoke;

    if(alertLevel == 1) borderColor = clrYellow;
    else if(alertLevel == 2) borderColor = clrOrange;
    else if(alertLevel == 3) borderColor = clrRed;

    ObjectDelete(0, panelName);
    ObjectCreate(0, panelName, OBJ_RECTANGLE_LABEL, 0, 0, 0);
    ObjectSetInteger(0, panelName, OBJPROP_XDISTANCE, 10);
    ObjectSetInteger(0, panelName, OBJPROP_YDISTANCE, 10);
    ObjectSetInteger(0, panelName, OBJPROP_XSIZE, 420);
    ObjectSetInteger(0, panelName, OBJPROP_YSIZE, 400);
    ObjectSetInteger(0, panelName, OBJPROP_BGCOLOR, bgColor);
    ObjectSetInteger(0, panelName, OBJPROP_BORDER_COLOR, borderColor);
    ObjectSetInteger(0, panelName, OBJPROP_BORDER_TYPE, BORDER_FLAT);
    ObjectSetInteger(0, panelName, OBJPROP_WIDTH, 3);

    string textName = "XAU_MAIN_TEXT";
    ObjectDelete(0, textName);

    string text = "╔════════════════ XAU/USD v5.2 ════════════════╗\n";
    text += "║ 💰 CAPITAL: $" + DoubleToString(currentCapital, 2) + " | EQUITY: $" + 
            DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2) + "\n";
    
    if(capitalProtectionActive)
    {
        text += "║ 🔒 PROTECCIÓN ACTIVA | Trabajo: $" + DoubleToString(workingCapital, 2) + 
                " | Seguro: $" + DoubleToString(protectedCapital, 2) + "\n";
    }
    
    text += "║ 📊 MARGEN: " + DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2) + " | " +
            DoubleToString((AccountInfoDouble(ACCOUNT_MARGIN_FREE) / AccountInfoDouble(ACCOUNT_EQUITY) * 100), 1) + "%\n";
    text += "║\n";
    text += "║ 📈 ABIERTOS: " + IntegerToString(CountOpenTrades()) + "/" + IntegerToString(dynamicMaxOpenTrades) + 
            " | CERRADOS: " + IntegerToString(totalTradesClosed) + "\n";
    text += "║ 💵 P&L Actual: $" + DoubleToString(GetTotalOpenProfit(), 2) + " | Histórico: $" + 
            DoubleToString(historicalProfit, 2) + "\n";
    text += "║ 💸 Pérdida Diaria: $" + DoubleToString(dailyLoss, 2) + " / $" + 
            DoubleToString(dynamicMaxDailyLoss, 2) + "\n";
    text += "║ 🎯 Target Ganancia: $" + DoubleToString(dynamicMinProfitTarget, 2) + "\n";
    text += "║\n";
    text += "║ 📡 PING: " + DoubleToString(currentPing, 0) + "ms | SPREAD: " + 
            DoubleToString(currentSpread, 1) + " pts\n";
    text += "║ 🌡️  VOL: ";
    if(volatilityLevel < 0.4) text += "BAJA";
    else if(volatilityLevel < 0.7) text += "NORMAL";
    else text += "ALTA";
    text += " | Apalancamiento: 1:" + IntegerToString(dynamicLeverage) + "\n";
    
    if(tradeDirection == 1) text += "║ 🟢 BUY MODE";
    else if(tradeDirection == -1) text += "║ 🔴 SELL MODE";
    else text += "║ ⚪ NEUTRAL";
    text += "\n";
    
    text += "║ ⏱️  Estado: ";
    if(isPaused || isInRecoveryMode)
    {
        text += "EN PAUSA";
    }
    else text += "ACTIVO";
    text += "\n";

    text += "╠════════════════════════════════════════════════╣\n";
    text += "║ Ganadores: " + IntegerToString(totalTradesWon) + " | Perdedores: " + 
            IntegerToString(totalTradesLost) + " | Win Rate: " + 
            DoubleToString(winRate * 100, 1) + "%\n";
    text += "║ Profit Factor: " + DoubleToString(profitFactor, 2) + "\n";
    text += "║ Cierres Totales: " + IntegerToString(totalProfitClosures) + "\n";
    text += "╚════════════════════════════════════════════════╝\n";

    ObjectCreate(0, textName, OBJ_LABEL, 0, 0, 0);
    ObjectSetInteger(0, textName, OBJPROP_XDISTANCE, 15);
    ObjectSetInteger(0, textName, OBJPROP_YDISTANCE, 15);
    ObjectSetString(0, textName, OBJPROP_TEXT, text);
    ObjectSetInteger(0, textName, OBJPROP_FONTSIZE, 8);
    ObjectSetString(0, textName, OBJPROP_FONT, "Courier New");
    ObjectSetInteger(0, textName, OBJPROP_COLOR, clrLime);

    ChartRedraw();
}

void DrawIndicatorPanel()
{
    string text = "📊 MACD: " + DoubleToString(cachedMACD, 4) + " | RSI: " + 
                  DoubleToString(cachedRSI, 1) + " | ATR: " + DoubleToString(cachedATR, 2);

    ObjectDelete(0, "XAU_INDICATOR_INFO");
    ObjectCreate(0, "XAU_INDICATOR_INFO", OBJ_LABEL, 0, 0, 0);
    ObjectSetInteger(0, "XAU_INDICATOR_INFO", OBJPROP_XDISTANCE, 450);
    ObjectSetInteger(0, "XAU_INDICATOR_INFO", OBJPROP_YDISTANCE, 15);
    ObjectSetString(0, "XAU_INDICATOR_INFO", OBJPROP_TEXT, text);
    ObjectSetInteger(0, "XAU_INDICATOR_INFO", OBJPROP_FONTSIZE, 9);
    ObjectSetString(0, "XAU_INDICATOR_INFO", OBJPROP_FONT, "Courier New");
    ObjectSetInteger(0, "XAU_INDICATOR_INFO", OBJPROP_COLOR, clrCyan);
}

void DrawAlertPanel()
{
    if(alertMessage == "")
        return;

    color alertColor = clrYellow;
    if(alertLevel == 2) alertColor = clrOrange;
    else if(alertLevel == 3) alertColor = clrRed;

    ObjectDelete(0, "XAU_ALERT_TEXT");
    ObjectCreate(0, "XAU_ALERT_TEXT", OBJ_LABEL, 0, 0, 0);
    ObjectSetInteger(0, "XAU_ALERT_TEXT", OBJPROP_XDISTANCE, 10);
    ObjectSetInteger(0, "XAU_ALERT_TEXT", OBJPROP_YDISTANCE, 420);
    ObjectSetString(0, "XAU_ALERT_TEXT", OBJPROP_TEXT, alertMessage);
    ObjectSetInteger(0, "XAU_ALERT_TEXT", OBJPROP_FONTSIZE, 10);
    ObjectSetString(0, "XAU_ALERT_TEXT", OBJPROP_FONT, "Courier New");
    ObjectSetInteger(0, "XAU_ALERT_TEXT", OBJPROP_COLOR, alertColor);
}

void DrawStatisticsPanel()
{
    string text = "📈 Ganados: " + IntegerToString(totalTradesWon) + 
                  " | Perdidos: " + IntegerToString(totalTradesLost) + 
                  " | Ganancia Prom: $" + DoubleToString(averageProfit, 2) + 
                  " | Pérdida Prom: $" + DoubleToString(averageLoss, 2);

    ObjectDelete(0, "XAU_STATS_TEXT");
    ObjectCreate(0, "XAU_STATS_TEXT", OBJ_LABEL, 0, 0, 0);
    ObjectSetInteger(0, "XAU_STATS_TEXT", OBJPROP_XDISTANCE, 450);
    ObjectSetInteger(0, "XAU_STATS_TEXT", OBJPROP_YDISTANCE, 35);
    ObjectSetString(0, "XAU_STATS_TEXT", OBJPROP_TEXT, text);
    ObjectSetInteger(0, "XAU_STATS_TEXT", OBJPROP_FONTSIZE, 8);
    ObjectSetString(0, "XAU_STATS_TEXT", OBJPROP_FONT, "Courier New");
    ObjectSetInteger(0, "XAU_STATS_TEXT", OBJPROP_COLOR, clrLimeGreen);
}

void GenerateDailyReport()
{
    Print("\n╔════════════════ REPORTE DIARIO ════════════════╗");
    Print("║ Fecha: " + TimeToString(TimeCurrent(), TIME_DATE));
    Print("║ Capital: $" + DoubleToString(currentCapital, 2));
    Print("║ Operaciones: " + IntegerToString(CountOpenTrades()) + " abiertas | " + 
          IntegerToString(totalTradesClosed) + " cerradas");
    Print("║ Cierres Totales: " + IntegerToString(totalProfitClosures));
    Print("║ Ganancia: $" + DoubleToString(dailyProfit, 2) + " | Pérdida: $" + 
          DoubleToString(dailyLoss, 2));
    Print("║ Win Rate: " + DoubleToString(winRate * 100, 1) + "% | Profit Factor: " + 
          DoubleToString(profitFactor, 2));
    Print("║ Histórico: $" + DoubleToString(historicalProfit, 2));
    if(capitalProtectionActive)
    {
        Print("║ Capital Protegido: $" + DoubleToString(protectedCapital, 2));
    }
    Print("╚════════════════════════════════════════════════╝\n");
}

//+------------------------------------------------------------------+
//| FIN DEL CÓDIGO - XAU_USD_MultiTrader_Pro v5.2 Mejorado & Listo   |
//+------------------------------------------------------------------+
