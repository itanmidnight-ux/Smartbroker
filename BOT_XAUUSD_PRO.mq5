//+------------------------------------------------------------------+
//|                                              BOT_XAUUSD_PRO.mq5 |
//|                                 Copyright 2024, Trading Pro Sys |
//|                                             https://example.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, Trading Pro Sys"
#property link      "https://example.com"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "══════ MONEY MANAGEMENT ══════"
input double Inp_InitialLot     = 0.01;        // Lote inicial
input double Inp_MaxLot         = 0.30;        // Lote máximo
input int    Inp_MaxOpenTrades  = 16;          // Máximo trades simultáneos
input double Inp_TargetProfit   = 0.50;        // Ganancia objetivo (USD)
input int    Inp_CorrectionTime = 6;           // Tiempo validación (segundos)

input group "══════ INDICADORES ══════"
input int    Inp_EMA_Fast       = 9;           // EMA rápida
input int    Inp_EMA_Slow       = 21;          // EMA lenta
input int    Inp_RSI_Period     = 14;          // Período RSI
input int    Inp_MACD_Fast      = 12;          // MACD rápido
input int    Inp_MACD_Slow      = 26;          // MACD lento
input int    Inp_MACD_Signal    = 9;           // MACD señal
input int    Inp_ATR_Period     = 14;          // Período ATR
input double Inp_MinATR         = 0.5;         // ATR mínimo (volatilidad)
input double Inp_SLMultiplier   = 1.5;         // Multiplicador SL

input group "══════ FILTROS ══════"
input int    Inp_RSI_Min        = 30;          // RSI mínimo compra
input int    Inp_RSI_Max        = 70;          // RSI máximo venta
input bool   Inp_UseTimeFilter  = true;        // Usar filtro horario
input int    Inp_StartHour      = 8;           // Hora inicio (UTC)
input int    Inp_EndHour        = 20;          // Hora fin (UTC)

input group "══════ AVANZADO ══════"
input int    Inp_MagicNumber    = 20241215;    // Número mágico
input string Inp_Comment        = "XAUUSD_PRO";// Comentario trades
input bool   Inp_ShowLogs       = true;        // Mostrar logs

//+------------------------------------------------------------------+
//| Global Variables                                                  |
//+------------------------------------------------------------------+
int    g_EMAFastHandle;
int    g_EMASlowHandle;
int    g_RSIHandle;
int    g_MACDHandle;
int    g_ATRHandle;

double g_CurrentLot = 0.0;
int    g_TotalTrades = 0;
int    g_WinTrades = 0;
int    g_LossTrades = 0;
double g_TotalProfit = 0.0;

datetime g_LastCorrectionCheck = 0;
bool     g_CorrectionMode = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit()
{
   // Validate symbol
   if(Symbol() != "XAUUSD")
   {
      Print("❌ ERROR: Este bot SOLO funciona con XAUUSD");
      return(INIT_FAILED);
   }
   
   // Initialize indicators
   g_EMAFastHandle = iMA(Symbol(), PERIOD_CURRENT, Inp_EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
   g_EMASlowHandle = iMA(Symbol(), PERIOD_CURRENT, Inp_EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
   g_RSIHandle     = iRSI(Symbol(), PERIOD_CURRENT, Inp_RSI_Period, PRICE_CLOSE);
   g_MACDHandle    = iMACD(Symbol(), PERIOD_CURRENT, Inp_MACD_Fast, Inp_MACD_Slow, Inp_MACD_Signal, PRICE_CLOSE);
   g_ATRHandle     = iATR(Symbol(), PERIOD_CURRENT, Inp_ATR_Period);
   
   if(g_EMAFastHandle == INVALID_HANDLE || g_EMASlowHandle == INVALID_HANDLE ||
      g_RSIHandle == INVALID_HANDLE || g_MACDHandle == INVALID_HANDLE ||
      g_ATRHandle == INVALID_HANDLE)
   {
      Print("❌ ERROR: Fallo al inicializar indicadores");
      return(INIT_FAILED);
   }
   
   // Initialize lot size
   g_CurrentLot = Inp_InitialLot;
   
   Print("✅ BOT XAUUSD PRO iniciado correctamente");
   Print("📊 Símbolo: ", Symbol());
   Print("📈 Lote inicial: ", DoubleToString(Inp_InitialLot, 2));
   Print("🎯 Ganancia objetivo: $", DoubleToString(Inp_TargetProfit, 2));
   Print("⏱️  Tiempo corrección: ", Inp_CorrectionTime, " segundos");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(g_EMAFastHandle);
   IndicatorRelease(g_EMASlowHandle);
   IndicatorRelease(g_RSIHandle);
   IndicatorRelease(g_MACDHandle);
   IndicatorRelease(g_ATRHandle);
   
   Print("👋 Bot detenido. Estadísticas finales:");
   Print("📊 Trades totales: ", g_TotalTrades);
   Print("✅ Ganados: ", g_WinTrades);
   Print("❌ Perdidos: ", g_LossTrades);
   Print("💰 Profit total: $", DoubleToString(g_TotalProfit, 2));
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check time filter
   if(Inp_UseTimeFilter && !IsWithinTradingHours())
   {
      return;
   }
   
   // Check correction mode
   CheckCorrectionMode();
   
   // Count open trades
   int openTrades = CountOpenTrades();
   
   // Check if we can open new trades
   if(openTrades >= Inp_MaxOpenTrades)
   {
      return;
   }
   
   // Get indicator values
   double emaFast[], emaSlow[], rsiValues[], macdMain[], macdSignal[], atrValues[];
   
   ArraySetAsSeries(emaFast, true);
   ArraySetAsSeries(emaSlow, true);
   ArraySetAsSeries(rsiValues, true);
   ArraySetAsSeries(macdMain, true);
   ArraySetAsSeries(macdSignal, true);
   ArraySetAsSeries(atrValues, true);
   
   if(CopyBuffer(g_EMAFastHandle, 0, 0, 3, emaFast) < 3 ||
      CopyBuffer(g_EMASlowHandle, 0, 0, 3, emaSlow) < 3 ||
      CopyBuffer(g_RSIHandle, 0, 0, 3, rsiValues) < 3 ||
      CopyBuffer(g_MACDHandle, 0, 0, 3, macdMain) < 3 ||
      CopyBuffer(g_MACDHandle, 1, 0, 3, macdSignal) < 3 ||
      CopyBuffer(g_ATRHandle, 0, 0, 3, atrValues) < 3)
   {
      return;
   }
   
   // Check minimum volatility
   if(atrValues[0] < Inp_MinATR)
   {
      return;
   }
   
   // Detect EMA crossover
   bool buySignal = (emaFast[1] <= emaSlow[1] && emaFast[0] > emaSlow[0]);
   bool sellSignal = (emaFast[1] >= emaSlow[1] && emaFast[0] < emaSlow[0]);
   
   // Confirm with RSI
   bool rsiBuyConfirm = (rsiValues[0] > Inp_RSI_Min && rsiValues[0] < 50);
   bool rsiSellConfirm = (rsiValues[0] < Inp_RSI_Max && rsiValues[0] > 50);
   
   // Confirm with MACD
   bool macdBuyConfirm = (macdMain[0] > macdSignal[0] && macdMain[1] <= macdSignal[1]);
   bool macdSellConfirm = (macdMain[0] < macdSignal[0] && macdMain[1] >= macdSignal[1]);
   
   // Calculate dynamic SL/TP
   double slPoints = atrValues[0] * Inp_SLMultiplier * 10; // Convert to points
   double tpPoints = slPoints * 2.0; // Risk/Reward 1:2
   
   // Execute BUY
   if(buySignal && rsiBuyConfirm && macdBuyConfirm)
   {
      if(Inp_ShowLogs) Print("🟢 Señal BUY detectada - Confluencia confirmada");
      
      double ask = SymbolInfoDouble(Symbol(), SYMBOL_ASK);
      double sl = ask - slPoints * Point();
      double tp = ask + tpPoints * Point();
      
      if(OpenTrade(ORDER_TYPE_BUY, g_CurrentLot, sl, tp))
      {
         // Pyramid: increase lot for next trade
         IncreaseLot();
      }
   }
   
   // Execute SELL
   if(sellSignal && rsiSellConfirm && macdSellConfirm)
   {
      if(Inp_ShowLogs) Print("🔴 Señal SELL detectada - Confluencia confirmada");
      
      double bid = SymbolInfoDouble(Symbol(), SYMBOL_BID);
      double sl = bid + slPoints * Point();
      double tp = bid - tpPoints * Point();
      
      if(OpenTrade(ORDER_TYPE_SELL, g_CurrentLot, sl, tp))
      {
         // Pyramid: increase lot for next trade
         IncreaseLot();
      }
   }
   
   // Check existing trades for profit target
   ManageOpenTrades();
}

//+------------------------------------------------------------------+
//| Open trade function                                               |
//+------------------------------------------------------------------+
bool OpenTrade(ENUM_ORDER_TYPE orderType, double lots, double sl, double tp)
{
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = Symbol();
   request.volume = lots;
   request.type = orderType;
   request.price = (orderType == ORDER_TYPE_BUY) ? 
                   SymbolInfoDouble(Symbol(), SYMBOL_ASK) : 
                   SymbolInfoDouble(Symbol(), SYMBOL_BID);
   request.sl = sl;
   request.tp = tp;
   request.deviation = 10;
   request.magic = Inp_MagicNumber;
   request.comment = Inp_Comment;
   request.type_filling = ORDER_FILLING_IOC;
   
   // Send order
   if(!OrderSend(request, result))
   {
      Print("❌ Error al abrir trade: ", GetLastError());
      return false;
   }
   
   if(result.retcode != TRADE_RETCODE_DONE)
   {
      Print("❌ Trade rechazado: ", result.retcode, " - ", result.comment);
      return false;
   }
   
   g_TotalTrades++;
   
   if(Inp_ShowLogs)
   {
      string typeStr = (orderType == ORDER_TYPE_BUY) ? "BUY" : "SELL";
      Print("✅ Trade ", typeStr, " abierto: ", lots, " lotes @ ", DoubleToString(request.price, 2));
      Print("   SL: ", DoubleToString(sl, 2), " | TP: ", DoubleToString(tp, 2));
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Manage open trades                                                |
//+------------------------------------------------------------------+
void ManageOpenTrades()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      
      if(PositionGetString(POSITION_SYMBOL) != Symbol()) continue;
      if(PositionGetInteger(POSITION_MAGIC) != Inp_MagicNumber) continue;
      
      double profit = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      
      // Close if profit target reached
      if(profit >= Inp_TargetProfit)
      {
         ClosePosition(ticket, "Profit target alcanzado");
         g_WinTrades++;
         g_TotalProfit += profit;
         
         // Reset lot after successful trade
         g_CurrentLot = Inp_InitialLot;
         
         if(Inp_ShowLogs)
            Print("💰 Trade cerrado con ganancia: $", DoubleToString(profit, 2));
      }
      // Check for loss and activate correction mode
      else if(profit < -Inp_TargetProfit)
      {
         MarkForCorrection(ticket);
      }
   }
}

//+------------------------------------------------------------------+
//| Close position                                                    |
//+------------------------------------------------------------------+
bool ClosePosition(ulong ticket, string reason)
{
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   if(!PositionSelectByTicket(ticket))
      return false;
   
   request.action = TRADE_ACTION_DEAL;
   request.position = ticket;
   request.symbol = PositionGetString(POSITION_SYMBOL);
   request.volume = PositionGetDouble(POSITION_VOLUME);
   request.type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 
                  ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price = (request.type == ORDER_TYPE_SELL) ? 
                   SymbolInfoDouble(Symbol(), SYMBOL_BID) : 
                   SymbolInfoDouble(Symbol(), SYMBOL_ASK);
   request.deviation = 10;
   request.magic = Inp_MagicNumber;
   request.comment = reason;
   
   if(!OrderSend(request, result))
   {
      Print("❌ Error al cerrar trade: ", GetLastError());
      return false;
   }
   
   if(result.retcode != TRADE_RETCODE_DONE)
   {
      Print("❌ Cierre rechazado: ", result.retcode);
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Count open trades                                                 |
//+------------------------------------------------------------------+
int CountOpenTrades()
{
   int count = 0;
   
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      
      if(PositionGetString(POSITION_SYMBOL) != Symbol()) continue;
      if(PositionGetInteger(POSITION_MAGIC) != Inp_MagicNumber) continue;
      
      count++;
   }
   
   return count;
}

//+------------------------------------------------------------------+
//| Increase lot (pyramid system)                                     |
//+------------------------------------------------------------------+
void IncreaseLot()
{
   double step = Inp_InitialLot;
   double newLot = g_CurrentLot + step;
   
   if(newLot <= Inp_MaxLot)
   {
      g_CurrentLot = newLot;
      
      if(Inp_ShowLogs)
         Print("📈 Lote aumentado a: ", DoubleToString(g_CurrentLot, 2));
   }
}

//+------------------------------------------------------------------+
//| Check if within trading hours                                     |
//+------------------------------------------------------------------+
bool IsWithinTradingHours()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   
   int currentHour = dt.hour;
   
   if(currentHour >= Inp_StartHour && currentHour < Inp_EndHour)
      return true;
   
   return false;
}

//+------------------------------------------------------------------+
//| Mark position for correction                                      |
//+------------------------------------------------------------------+
void MarkForCorrection(ulong ticket)
{
   // Store ticket for correction check
   // Correction logic will be checked every tick
   g_LastCorrectionCheck = TimeCurrent();
   g_CorrectionMode = true;
   
   if(Inp_ShowLogs)
      Print("⚠️  Trade #", ticket, " marcado para corrección");
}

//+------------------------------------------------------------------+
//| Check correction mode                                             |
//+------------------------------------------------------------------+
void CheckCorrectionMode()
{
   if(!g_CorrectionMode)
      return;
   
   datetime currentTime = TimeCurrent();
   double elapsedSeconds = (double)(currentTime - g_LastCorrectionCheck);
   
   if(elapsedSeconds >= Inp_CorrectionTime)
   {
      // Perform correction analysis
      PerformCorrectionAnalysis();
      
      // Reset correction mode
      g_CorrectionMode = false;
      g_LastCorrectionCheck = 0;
   }
}

//+------------------------------------------------------------------+
//| Perform correction analysis                                       |
//+------------------------------------------------------------------+
void PerformCorrectionAnalysis()
{
   // Get current indicator values for validation
   double rsiValues[], macdMain[], macdSignal[];
   
   ArraySetAsSeries(rsiValues, true);
   ArraySetAsSeries(macdMain, true);
   ArraySetAsSeries(macdSignal, true);
   
   if(CopyBuffer(g_RSIHandle, 0, 0, 3, rsiValues) < 3 ||
      CopyBuffer(g_MACDHandle, 0, 0, 3, macdMain) < 3 ||
      CopyBuffer(g_MACDHandle, 1, 0, 3, macdSignal) < 3)
   {
      return;
   }
   
   // Check all open positions
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      
      if(PositionGetString(POSITION_SYMBOL) != Symbol()) continue;
      if(PositionGetInteger(POSITION_MAGIC) != Inp_MagicNumber) continue;
      
      double profit = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      
      // Only check losing trades
      if(profit >= 0)
         continue;
      
      ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      
      bool shouldClose = false;
      string reason = "";
      
      // BUY position validation
      if(posType == POSITION_TYPE_BUY)
      {
         // If RSI is overbought or MACD signals sell, close the trade
         if(rsiValues[0] > Inp_RSI_Max || (macdMain[0] < macdSignal[0]))
         {
            shouldClose = true;
            reason = "Corrección: Indicadores en contra de BUY";
         }
      }
      // SELL position validation
      else if(posType == POSITION_TYPE_SELL)
      {
         // If RSI is oversold or MACD signals buy, close the trade
         if(rsiValues[0] < Inp_RSI_Min || (macdMain[0] > macdSignal[0]))
         {
            shouldClose = true;
            reason = "Corrección: Indicadores en contra de SELL";
         }
      }
      
      if(shouldClose)
      {
         ClosePosition(ticket, reason);
         g_LossTrades++;
         g_TotalProfit += profit;
         
         if(Inp_ShowLogs)
            Print("🛑 Trade cerrado por corrección: ", reason, " | P&L: $", DoubleToString(profit, 2));
         
         // Reset lot after loss
         g_CurrentLot = Inp_InitialLot;
      }
      else
      {
         if(Inp_ShowLogs)
            Print("✓ Trade validado en corrección - Mantener abierto");
      }
   }
}

//+------------------------------------------------------------------+
//| Get current spread in points                                      |
//+------------------------------------------------------------------+
double GetSpreadPoints()
{
   double spread = SymbolInfoInteger(Symbol(), SYMBOL_SPREAD);
   return spread * Point();
}

//+------------------------------------------------------------------+
//| Normalize lot size                                                |
//+------------------------------------------------------------------+
double NormalizeLot(double lot)
{
   double minLot = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_STEP);
   
   if(lot < minLot) lot = minLot;
   if(lot > maxLot) lot = maxLot;
   
   lot = MathRound(lot / lotStep) * lotStep;
   
   return lot;
}
//+------------------------------------------------------------------+
