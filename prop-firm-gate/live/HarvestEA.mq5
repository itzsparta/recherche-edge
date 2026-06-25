//+------------------------------------------------------------------+
//|                                                    HarvestEA.mq5  |
//|   Buffer-harvest constant-vol (etude #26) — portage NATIF de     |
//|   harvest_ea.py. EA MQL5 => tourne sur MetaQuotes VPS SANS        |
//|   terminal ouvert (Rent a Virtual Server). PAS un bot d'alpha :   |
//|   recolte le buffer STATIQUE d'une firme a plancher fixe          |
//|   (FTMO 2-Step, compte SWING). Aucune prediction de direction.    |
//|                                                                   |
//|   Mecanisme (cf. ../docs/FINDINGS-repeated.md) : sous drift nul,  |
//|   equity + skim cumule est une martingale => E[skim] = buffer.    |
//|   On tient une exposition a vol CONSTANTE (sigma_day cible),       |
//|   plafonnee par une GARDE pour qu'un move de guard_sigma·sigma ne  |
//|   casse NI le daily-DD NI le max-DD statique ; on banke par cycle. |
//|                                                                   |
//|   Calibre pour majors a quote USD (EURUSD) : P&L ~ notionnel ·     |
//|   variation fractionnaire. Autre symbole => ajuster la devise P&L. |
//+------------------------------------------------------------------+
#property copyright "etude #26 — prop-firm-gate"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

//--- compte (FTMO 2-Step : plancher STATIQUE — verifie 2026) -------
input double InpInitialBalance   = 0;       // solde initial $ ; 0 = lire au demarrage
input double InpMaxDD            = 0.10;     // max loss 10% STATIQUE (ne trail pas)
input double InpDailyDD          = 0.05;     // daily loss 5%
input double InpPhase1Target     = 0.10;     // cible phase 1 (+10%)
input double InpPhase2Target     = 0.05;     // cible phase 2 (+5%)
input bool   InpAlreadyFunded    = false;    // true = compte deja finance (skip phases)
//--- recolte -------------------------------------------------------
input double InpTargetSigma      = 0.020;    // vol P&L quotidienne cible (sizing)
input int    InpDirection        = -1;       // -1 short / +1 long. EURUSD live : SHORT swap ~+0.28 vs LONG ~-11.4/lot/nuit (long paie le diff. de taux). Arbitraire pour le P&L sous no-edge => prendre le cote swap-positif. VERIFIER swap_long/short par symbole.
input double InpGuardSigma       = 3.0;      // la taille tient un move de N sigma sans casser le plancher
input int    InpPayoutDays       = 14;       // cadence de bank (funded uniquement)
input bool   InpFlatBeforeWeekend= true;     // flat le vendredi (anti-gap week-end)
//--- instrument / execution ---------------------------------------
input int    InpVolLookback      = 20;       // jours pour estimer la vol de l'instrument
input int    InpMagic            = 260626;
input int    InpDeviation        = 20;

CTrade trade;

//--- etat (persiste en GlobalVariables -> survit restart / migration VPS)
double g_A, g_static_floor, g_day_start_equity, g_bank_baseline, g_skim_total;
int    g_phase, g_day_count, g_last_yday;
bool   g_funded, g_breached;

//+------------------------------------------------------------------+
//| Persistance d'etat (cles GlobalVariables prefixees magic+symbole) |
//+------------------------------------------------------------------+
string K(const string s) { return StringFormat("HARV_%s_%d_%s", _Symbol, InpMagic, s); }

void SaveState()
{
   GlobalVariableSet(K("A"),         g_A);
   GlobalVariableSet(K("floor"),     g_static_floor);
   GlobalVariableSet(K("phase"),     (double)g_phase);
   GlobalVariableSet(K("funded"),    g_funded ? 1.0 : 0.0);
   GlobalVariableSet(K("breached"),  g_breached ? 1.0 : 0.0);
   GlobalVariableSet(K("baseline"),  g_bank_baseline);
   GlobalVariableSet(K("skim"),      g_skim_total);
   GlobalVariableSet(K("daycount"),  (double)g_day_count);
   GlobalVariableSet(K("daystart"),  g_day_start_equity);
   GlobalVariableSet(K("lastyday"),  (double)g_last_yday);
}

bool LoadState()
{
   if(!GlobalVariableCheck(K("A"))) return false;
   g_A                = GlobalVariableGet(K("A"));
   g_static_floor     = GlobalVariableGet(K("floor"));
   g_phase            = (int)GlobalVariableGet(K("phase"));
   g_funded           = GlobalVariableGet(K("funded"))   > 0.5;
   g_breached         = GlobalVariableGet(K("breached")) > 0.5;
   g_bank_baseline    = GlobalVariableGet(K("baseline"));
   g_skim_total       = GlobalVariableGet(K("skim"));
   g_day_count        = (int)GlobalVariableGet(K("daycount"));
   g_day_start_equity = GlobalVariableGet(K("daystart"));
   g_last_yday        = (int)GlobalVariableGet(K("lastyday"));
   return true;
}

//+------------------------------------------------------------------+
//| Vol quotidienne realisee de l'instrument (stdev log-rendements D1)|
//+------------------------------------------------------------------+
double DailyVol()
{
   double c[];
   ArraySetAsSeries(c, true);
   int need = InpVolLookback + 1;
   int n = CopyClose(_Symbol, PERIOD_D1, 0, need, c);
   if(n < need) return 0.01;                 // fallback prudent 1%
   double s = 0.0, s2 = 0.0; int m = 0;
   for(int i = 0; i < InpVolLookback; i++)
   {
      if(c[i+1] <= 0.0) continue;
      double r = MathLog(c[i] / c[i+1]);
      s += r; s2 += r * r; m++;
   }
   if(m < 2) return 0.01;
   double mean = s / m;
   double var  = s2 / m - mean * mean;
   return (var > 0.0) ? MathSqrt(var) : 0.01;
}

//+------------------------------------------------------------------+
//| Cible de lots : vol-cible, PLAFONNEE par la distance au plancher  |
//+------------------------------------------------------------------+
double TargetLots(double equity)
{
   double iv = MathMax(DailyVol(), 1e-4);
   // 1) taille par vol cible : notionnel tel que notionnel·iv = sigma_day·equity
   double pv_vol = InpTargetSigma * equity / iv;
   // 2) plafond garde : un move de guard_sigma·iv ne doit casser aucun plancher
   double daily_floor = g_day_start_equity - g_A * InpDailyDD;
   double floor       = MathMax(g_static_floor, daily_floor);
   double headroom    = MathMax(equity - floor, 0.0);
   double pv_guard    = headroom / (InpGuardSigma * iv);
   double pv          = MathMin(pv_vol, pv_guard);

   double contract = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   double price    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(contract <= 0.0 || price <= 0.0) return 0.0;
   return pv / (contract * price);
}

double NormalizeLots(double lots)
{
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0.0) step = 0.01;
   lots = MathFloor(lots / step) * step;     // arrondi BAS = garde conservatrice
   if(lots < mn) return 0.0;                  // sous le min => flat (de-risk pres du plancher)
   if(lots > mx) lots = mx;
   return lots;
}

double CurrentSignedLots()
{
   if(!PositionSelect(_Symbol)) return 0.0;
   if(PositionGetInteger(POSITION_MAGIC) != InpMagic) return 0.0;
   double v = PositionGetDouble(POSITION_VOLUME);
   long   t = PositionGetInteger(POSITION_TYPE);
   return (t == POSITION_TYPE_BUY) ? v : -v;
}

void Flatten()
{
   if(PositionSelect(_Symbol) && PositionGetInteger(POSITION_MAGIC) == InpMagic)
      trade.PositionClose(_Symbol);
}

//+------------------------------------------------------------------+
//| Re-dimensionne la position vers la cible (taille constante /jour) |
//+------------------------------------------------------------------+
void Rebalance(double equity)
{
   if(g_breached) return;
   double tgt  = NormalizeLots(TargetLots(equity));
   double want = InpDirection * tgt;
   double cur  = CurrentSignedLots();
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0) step = 0.01;
   double delta = want - cur;
   if(MathAbs(delta) < step) return;
   double vol = NormalizeDouble(MathAbs(delta), 2);
   if(vol < SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN)) return;
   if(delta > 0) trade.Buy(vol, _Symbol);
   else          trade.Sell(vol, _Symbol);
}

//+------------------------------------------------------------------+
//| Fenetre flat anti-gap : vendredi soir + week-end                  |
//+------------------------------------------------------------------+
bool WeekendFlat()
{
   if(!InpFlatBeforeWeekend) return false;
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   if(dt.day_of_week == 6) return true;                  // samedi
   if(dt.day_of_week == 0) return true;                  // dimanche (avant reouverture)
   if(dt.day_of_week == 5 && dt.hour >= 20) return true; // vendredi soir
   return false;
}

//+------------------------------------------------------------------+
//| Rollover de journee : maj day_start, bank (funded), re-size /jour |
//+------------------------------------------------------------------+
void CheckNewDay(double equity)
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.day_of_year == g_last_yday) return;

   g_last_yday        = dt.day_of_year;
   g_day_start_equity = equity;        // baseline daily-DD = equite a l'ouverture (~minuit serveur)
   g_day_count++;

   // BANK (funded) : tous les payout_days, signaler le retrait de l'exces
   if(g_funded && (g_day_count % InpPayoutDays) == 0 && equity > g_bank_baseline)
   {
      double excess = equity - g_bank_baseline;
      g_skim_total += excess;
      PrintFormat("[BANK] jour=%d exces=$%.2f skim_cumul=$%.2f => DEMANDER LE PAYOUT sur le dashboard FTMO, puis reset",
                  g_day_count, excess, g_skim_total);
      Alert(StringFormat("HarvestEA BANK : demander payout $%.0f (dashboard FTMO)", excess));
      g_bank_baseline = g_A;           // reset (suppose le payout pris ; le mouvement d'argent est MANUEL)
   }

   if(!WeekendFlat())                  // pas de re-size en fenetre week-end
      Rebalance(equity);
   SaveState();
}

//+------------------------------------------------------------------+
//| Breach : equite <= plancher (statique OU daily) => flat + stop    |
//+------------------------------------------------------------------+
bool CheckBreach(double equity)
{
   double daily_floor = g_day_start_equity - g_A * InpDailyDD;
   double floor       = MathMax(g_static_floor, daily_floor);
   if(equity <= floor)
   {
      g_breached = true;
      Flatten();
      PrintFormat("[BREACH] equite=$%.2f <= plancher=$%.2f (statique=$%.2f daily=$%.2f) — flat + stop",
                  equity, floor, g_static_floor, daily_floor);
      Alert("HarvestEA BREACH : plancher casse — flat + stop");
      SaveState();
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Transitions de phase / passage finance                            |
//+------------------------------------------------------------------+
void CheckTargets(double equity)
{
   if(g_funded) return;
   double frac = (g_phase == 0) ? InpPhase1Target : InpPhase2Target;
   double tgt  = g_A * (1.0 + frac);
   if(equity < tgt) return;

   g_phase++;
   PrintFormat("[PHASE_PASS] phase=%d equite=$%.2f", g_phase, equity);
   if(g_phase >= 2)
   {
      g_funded        = true;
      g_bank_baseline = g_A;
      PrintFormat("[FUNDED] equite=$%.2f — passage au mode recolte", equity);
      Alert("HarvestEA : compte FUNDED");
   }
   else
   {
      Flatten();                       // reset entre phases
   }
   Rebalance(equity);
   SaveState();
}

//+------------------------------------------------------------------+
//| OnInit                                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviation);
   trade.SetTypeFillingBySymbol(_Symbol);

   if(!SymbolSelect(_Symbol, true))
      Print("[WARN] SymbolSelect a echoue pour ", _Symbol);

   if(LoadState())
   {
      PrintFormat("[HarvestEA] etat RESTAURE : A=$%.0f phase=%d funded=%s breached=%s skim=$%.2f jour=%d",
                  g_A, g_phase, (g_funded?"oui":"non"), (g_breached?"oui":"non"), g_skim_total, g_day_count);
   }
   else
   {
      g_A             = (InpInitialBalance > 0.0) ? InpInitialBalance : AccountInfoDouble(ACCOUNT_BALANCE);
      g_static_floor  = g_A * (1.0 - InpMaxDD);
      g_phase         = InpAlreadyFunded ? 2 : 0;
      g_funded        = InpAlreadyFunded;
      g_breached      = false;
      g_skim_total    = 0.0;
      g_day_count     = 0;
      double eq0      = AccountInfoDouble(ACCOUNT_EQUITY);
      g_day_start_equity = eq0;
      g_bank_baseline    = g_A;
      MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
      g_last_yday     = dt.day_of_year;
      PrintFormat("[HarvestEA] INIT : A=$%.0f plancher_statique=$%.0f sigma_cible=%.1f%% direction=%d funded=%s",
                  g_A, g_static_floor, InpTargetSigma * 100.0, InpDirection, (g_funded?"oui":"non"));
      SaveState();
   }

   if(!g_breached)
      Rebalance(AccountInfoDouble(ACCOUNT_EQUITY));
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| OnTick : breach a chaque tick, re-size 1x/jour, phases            |
//+------------------------------------------------------------------+
void OnTick()
{
   if(g_breached) return;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   CheckNewDay(eq);            // maj day_start + bank + re-size 1x/jour
   if(CheckBreach(eq)) return; // securite a chaque tick
   if(WeekendFlat())           // fenetre week-end : flat, pas d'exposition
   {
      if(CurrentSignedLots() != 0.0) { Flatten(); SaveState(); }
      return;
   }
   CheckTargets(eq);           // transitions phase/funded
}

//+------------------------------------------------------------------+
//| OnDeinit                                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   SaveState();
   PrintFormat("[HarvestEA] arret (reason=%d). Etat sauvegarde. NB : la position reste ouverte.", reason);
}
//+------------------------------------------------------------------+
