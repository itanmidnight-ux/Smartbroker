#property strict

input string ApiURL = "http://127.0.0.1:8000/signal";
input string BrokerMode = "AUTO"; // AUTO|DEMO|LIVE
input double RiskPerTrade = 0.5;

// Estructura base del EA modular para integración con API Python.
// 1) Captura data de mercado.
// 2) Solicita señal a API local.
// 3) Ejecuta orden con validaciones de riesgo.

int OnInit()
{
   Print("SmartBrokerEA iniciado. Modo broker: ", BrokerMode);
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   // TODO: Integrar request HTTP con WebRequest a ApiURL
   // TODO: Parsear JSON de señal
   // TODO: Aplicar límites de riesgo y ejecutar orden
}
