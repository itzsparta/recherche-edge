# Validation & Robustesse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compléter le bot orderflow v1 avec la couche « Évaluation & validation » de la spec : frais + slippage dans le simulateur de fills, métriques Sortino/Calmar, walk-forward out-of-sample, Monte Carlo par resampling des trades réels (distribution des drawdowns, risque de ruine), calculateur Kelly fractionné 1/4 (offline uniquement), et roadmap de mise en production.

**Architecture:** Tout s'appuie sur l'existant : le `PaperBroker` apprend les frais maker/taker et le slippage (les fills limit = maker, les fills market stop/EOD = taker + slippage défavorable) ; `ClosedTrade` gagne un champ `fees` et son `pnl` devient net. Le walk-forward réutilise le `Pipeline` partagé backtest/live via une fenêtre de trading (`trading_enabled` n'autorise les entrées que dans le fold, le warmup alimente profils/zones sans trader). Monte Carlo et Kelly sont des fonctions pures sur la liste des R-multiples du journal — **offline uniquement, jamais en input de décision live** (règle de la spec).

**Tech Stack:** Python ≥3.11 stdlib (`random`, `math`), DuckDB (déjà présent) pour lister les jours disponibles. Pas de pandas/numpy (YAGNI).

**Racine projet :** `C:\Projets\code python\orderflow-bot` — toutes les commandes s'exécutent depuis ce dossier. Repo git enraciné à `C:\Projets`. Python du venv : `.venv\Scripts\python`.

**Hors scope (sous-systèmes séparés, plans futurs) :**
- v1.2 — TPO : balance/imbalance, single prints, poor highs/lows (couche 1 enrichie)
- v1.5 — Options/GEX : GEX net, gamma flip, call/put walls, régime engine couche 0 (nécessite flux options, ex. Deribit pour crypto)
- v2 — DOM L2 (liquidité passive consommée vs affichée, anti-spoofing) + Kelly comme plafond live (après ~100 trades réels)

Ces jalons sont documentés dans `docs/ROADMAP.md` (Task 8).

**Précaution générale :** la valeur par défaut des frais devient non nulle (Binance USDT-M : maker 0,02 %, taker 0,05 %). Tout test existant qui vérifie un `pnl` exact via `BotConfig` par défaut doit passer des frais à zéro explicitement (voir Task 2, Step 6).

---

### Task 1: Config frais + champ `fees` sur ClosedTrade

**Files:**
- Modify: `src/orderflow_bot/config.py`
- Modify: `src/orderflow_bot/models.py`
- Modify: `config.yaml`
- Test: `tests/test_config.py`, `tests/test_models.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/test_config.py` :

```python
def test_fees_defaults():
    from orderflow_bot.config import BotConfig
    cfg = BotConfig()
    assert cfg.fees.maker_pct == 0.0002
    assert cfg.fees.taker_pct == 0.0005
    assert cfg.fees.slippage_ticks == 2
```

Ajouter à `tests/test_models.py` :

```python
def test_closed_trade_fees_default():
    from orderflow_bot.models import ClosedTrade, OrderPlan
    plan = OrderPlan(ts=0, side=1, entry=100.0, stop=98.0, target=106.0)
    ct = ClosedTrade(plan=plan, qty=1.0, fills=[], pnl=0.0, r_multiple=0.0,
                     opened_ts=0, closed_ts=0)
    assert ct.fees == 0.0
```

- [ ] **Step 2: Vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_config.py::test_fees_defaults tests/test_models.py::test_closed_trade_fees_default -v`
Expected: FAIL — `AttributeError: 'BotConfig' object has no attribute 'fees'` et `TypeError` (champ `fees` inconnu).

- [ ] **Step 3: Implémenter**

Dans `src/orderflow_bot/config.py`, ajouter après `ImbalanceCfg` :

```python
class FeesCfg(StrictModel):
    """Frais Binance USDT-M par defaut. Les fills limit (entry/partial/target)
    paient maker, les fills market (stop/eod) paient taker + slippage."""

    maker_pct: float = 0.0002        # 0.02 %
    taker_pct: float = 0.0005        # 0.05 %
    slippage_ticks: int = 2          # decalage defavorable des fills market
```

Dans `BotConfig`, ajouter le champ (à côté de `risk`) :

```python
    fees: FeesCfg = FeesCfg()
```

Dans `src/orderflow_bot/models.py`, ajouter à `ClosedTrade` (en dernier champ, avec défaut — compatible avec les anciens journaux JSONL qui n'ont pas la clé) :

```python
@dataclass(slots=True)
class ClosedTrade:
    plan: OrderPlan
    qty: float
    fills: list[Fill]
    pnl: float                 # NET de frais
    r_multiple: float          # calcule sur le pnl net
    opened_ts: int
    closed_ts: int
    fees: float = 0.0          # total des frais payes sur tous les fills
```

Dans `config.yaml`, ajouter après le bloc `risk:` :

```yaml
fees:
  maker_pct: 0.0002
  taker_pct: 0.0005
  slippage_ticks: 2
```

- [ ] **Step 4: Vérifier le passage**

Run: `.venv\Scripts\python -m pytest tests/test_config.py tests/test_models.py -v`
Expected: PASS (tous).

- [ ] **Step 5: Commit**

```bash
git add orderflow-bot/src/orderflow_bot/config.py orderflow-bot/src/orderflow_bot/models.py orderflow-bot/config.yaml orderflow-bot/tests/test_config.py orderflow-bot/tests/test_models.py
git commit -m "feat(orderflow): config frais maker/taker + slippage, champ fees sur ClosedTrade"
```

---

### Task 2: PaperBroker — frais sur chaque fill + slippage sur stop/EOD

**Files:**
- Modify: `src/orderflow_bot/execution/paper.py`
- Modify: `src/orderflow_bot/pipeline.py:49` (construction du broker)
- Test: `tests/test_paper.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Dans `tests/test_paper.py`, remplacer l'en-tête et le helper `_broker` par :

```python
from orderflow_bot.config import FeesCfg, RiskCfg
from orderflow_bot.execution.paper import PaperBroker
from orderflow_bot.models import Cancelled, ClosedTrade, OrderPlan

from .conftest import make_trade

# long : entry 100, stop 98 (risk 2.0), target 106 (RR 3)
PLAN = OrderPlan(ts=1_000, side=1, entry=100.0, stop=98.0, target=106.0)

ZERO_FEES = FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0)
# frais ronds pour des assertions exactes : maker 0.1 %, taker 0.2 %, slip 10 ticks = 1.0
TEST_FEES = FeesCfg(maker_pct=0.001, taker_pct=0.002, slippage_ticks=10)


def _broker(fees: FeesCfg = ZERO_FEES) -> PaperBroker:
    return PaperBroker(RiskCfg(partial_at_r=1.0, partial_fraction=0.5),
                       expire_ms=900_000, fees=fees, tick_size=0.1)
```

Ajouter en fin de fichier les nouveaux tests :

```python
def test_fees_deducted_on_target():
    br = _broker(TEST_FEES)
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))                  # entry @100, maker
    br.on_trade(make_trade(3_000, 102.1))                 # partiel 0.5 @102, maker
    ct = br.on_trade(make_trade(4_000, 106.1))            # target 0.5 @106, maker
    assert isinstance(ct, ClosedTrade)
    # brut = 0.5*2 + 0.5*6 = 4.0
    # frais maker : 100*1*0.001 + 102*0.5*0.001 + 106*0.5*0.001 = 0.204
    assert ct.fees == 0.204
    assert ct.pnl == 4.0 - 0.204
    assert ct.r_multiple == (4.0 - 0.204) / 2.0           # risk0 = 2.0, qty = 1


def test_stop_pays_taker_and_slippage():
    br = _broker(TEST_FEES)
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))                  # entry @100
    ct = br.on_trade(make_trade(3_000, 97.5))             # gap sous le stop
    assert isinstance(ct, ClosedTrade)
    # pire prix 97.5, slip 10 ticks * 0.1 = 1.0 defavorable -> fill @96.5
    assert ct.fills[-1].price == 96.5
    # brut = 96.5 - 100 = -3.5 ; frais = 100*0.001 (maker entry) + 96.5*0.002 (taker stop)
    assert ct.fees == round(0.1 + 0.193, 10)
    assert ct.pnl == round(-3.5 - 0.293, 10)


def test_eod_pays_taker_and_slippage():
    br = _broker(TEST_FEES)
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))                  # entry @100
    ct = br.force_close(make_trade(5_000, 101.0))
    assert isinstance(ct, ClosedTrade)
    assert ct.fills[-1].price == 100.0                     # 101 - slip 1.0
    assert ct.fills[-1].kind == "eod"


def test_short_stop_slippage_is_adverse():
    plan = OrderPlan(ts=1_000, side=-1, entry=100.0, stop=102.0, target=94.0)
    br = _broker(TEST_FEES)
    br.submit(plan, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 100.1))                  # fill short @100
    ct = br.on_trade(make_trade(3_000, 102.5))             # gap au-dessus du stop
    assert isinstance(ct, ClosedTrade)
    assert ct.fills[-1].price == 103.5                     # 102.5 + slip 1.0 (racheter plus haut)


def test_zero_fees_keeps_old_behavior():
    br = _broker()                                         # ZERO_FEES
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))
    br.on_trade(make_trade(3_000, 102.1))
    ct = br.on_trade(make_trade(4_000, 106.1))
    assert ct.pnl == 4.0
    assert ct.fees == 0.0
```

- [ ] **Step 2: Vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_paper.py -v`
Expected: FAIL — `TypeError: PaperBroker.__init__() got an unexpected keyword argument 'fees'`.

- [ ] **Step 3: Implémenter**

Dans `src/orderflow_bot/execution/paper.py` :

Imports — remplacer la ligne d'import config :

```python
from orderflow_bot.config import FeesCfg, RiskCfg
```

Constructeur — remplacer `__init__` :

```python
    def __init__(self, cfg: RiskCfg, expire_ms: int, fees: FeesCfg, tick_size: float):
        self.cfg = cfg
        self.expire_ms = expire_ms
        self.fees = fees
        self.tick_size = tick_size
        self._pos: _Position | None = None
```

Slippage — dans `on_trade`, remplacer la branche stop :

```python
        # position ouverte : pire cas d'abord
        if (t.price - p.stop) * s <= 0:
            worst = min(p.stop, t.price) if s == 1 else max(p.stop, t.price)
            return self._close(t.ts, worst - s * self._slip(), "stop")
```

Dans `force_close`, remplacer la dernière ligne :

```python
        return self._close(t.ts, t.price - p.plan.side * self._slip(), "eod")
```

Frais — remplacer `_close` et ajouter les deux helpers :

```python
    def _slip(self) -> float:
        return self.fees.slippage_ticks * self.tick_size

    def _fee_rate(self, kind: str) -> float:
        # limit (entry/partial/target) = maker ; market (stop/eod) = taker
        return self.fees.taker_pct if kind in ("stop", "eod") else self.fees.maker_pct

    def _close(self, ts: int, price: float, kind: str) -> ClosedTrade:
        p = self._pos
        assert p is not None
        p.fills.append(Fill(ts=ts, price=price, qty=p.remaining, kind=kind))
        s = p.plan.side
        entry = p.plan.entry
        gross = sum((f.price - entry) * s * f.qty for f in p.fills if f.kind != "entry")
        fees = sum(f.price * f.qty * self._fee_rate(f.kind) for f in p.fills)
        pnl = gross - fees
        risk0 = (entry - p.plan.stop) * s
        r = pnl / (risk0 * p.qty) if risk0 > 0 and p.qty > 0 else 0.0
        ct = ClosedTrade(plan=p.plan, qty=p.qty, fills=p.fills, pnl=round(pnl, 10),
                         r_multiple=round(r, 10), opened_ts=p.opened_ts, closed_ts=ts,
                         fees=round(fees, 10))
        self._pos = None
        return ct
```

Dans `src/orderflow_bot/pipeline.py`, remplacer la construction du broker (ligne ~49) :

```python
        self.broker = PaperBroker(cfg.risk, st.entry_expire_minutes * 60_000,
                                  cfg.fees, cfg.tick_size)
```

- [ ] **Step 4: Vérifier le passage**

Run: `.venv\Scripts\python -m pytest tests/test_paper.py -v`
Expected: PASS (tous, anciens inclus — ZERO_FEES préserve les valeurs exactes).

- [ ] **Step 5: Neutraliser les frais dans le backtest synthétique + suite complète**

`tests/test_backtest.py` construit sa config via `_cfg(tmp_path)` sans frais explicites — la valeur par défaut est maintenant non nulle et fausserait les seuils de pnl synthétiques. Dans `_cfg`, ajouter l'import et le champ :

```python
from orderflow_bot.config import (
    AbsorptionCfg, BotConfig, FeesCfg, RiskCfg, SessionCfg, StrategyCfg,
)
```

```python
    return BotConfig(
        tick_size=0.1, bin_size=1.0, bar_minutes=1, equity=10_000.0,
        journal_path=str(tmp_path / "journal.jsonl"),
        fees=FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0),
        risk=RiskCfg(),
        ...  # reste inchangé
    )
```

Run: `.venv\Scripts\python -m pytest -q`
Expected: PASS. Si `test_live_bootstrap.py` échoue aussi sur un pnl exact, appliquer le même `fees=FeesCfg(...)` zéro à sa config.

- [ ] **Step 6: Commit**

```bash
git add orderflow-bot/src/orderflow_bot/execution/paper.py orderflow-bot/src/orderflow_bot/pipeline.py orderflow-bot/tests/
git commit -m "feat(orderflow): frais maker/taker + slippage dans PaperBroker (pnl net)"
```

---

### Task 3: Métriques Sortino + Calmar

**Files:**
- Modify: `src/orderflow_bot/backtest/metrics.py`
- Test: `tests/test_journal_metrics.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/test_journal_metrics.py` (`compute_metrics` est déjà importé en tête de ce fichier ; ajouter seulement `import math` en première ligne) :

```python
import math


def _row(pnl: float, r: float) -> dict:
    return {"pnl": pnl, "r_multiple": r}


def test_sortino_on_r_multiples():
    # rs = [2.0, -1.0] : mean = 0.5, downside dev = sqrt((0 + 1)/2)
    m = compute_metrics([_row(200.0, 2.0), _row(-100.0, -1.0)])
    assert math.isclose(m["sortino_r"], 0.5 / math.sqrt(0.5))


def test_sortino_inf_when_no_loss():
    m = compute_metrics([_row(100.0, 1.0), _row(50.0, 0.5)])
    assert m["sortino_r"] == float("inf")


def test_calmar_total_pnl_over_max_dd():
    # equity 100 -> 50 : peak 100, dd 50, total 50 -> calmar 1.0
    m = compute_metrics([_row(100.0, 1.0), _row(-50.0, -0.5)])
    assert m["calmar"] == 1.0


def test_calmar_inf_when_no_drawdown():
    m = compute_metrics([_row(100.0, 1.0)])
    assert m["calmar"] == float("inf")
```

- [ ] **Step 2: Vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_journal_metrics.py -v`
Expected: FAIL — `KeyError: 'sortino_r'`.

- [ ] **Step 3: Implémenter**

Remplacer `src/orderflow_bot/backtest/metrics.py` :

```python
import math


def compute_metrics(rows: list[dict]) -> dict:
    """Metriques de performance depuis les lignes du journal.

    Sortino sur les R-multiples (mieux que Sharpe en intraday asymetrique),
    Calmar simplifie sur la periode (pnl total / max drawdown en monnaie).
    Usage : comparaison entre iterations, offline uniquement."""
    if not rows:
        return {"trades": 0}
    pnls = [r["pnl"] for r in rows]
    rs = [r["r_multiple"] for r in rows]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    eq = peak = dd = 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    mean_r = sum(rs) / len(rs)
    downside = math.sqrt(sum(min(r, 0.0) ** 2 for r in rs) / len(rs))
    return {
        "trades": len(rows),
        "win_rate": len(wins) / len(rows),
        "profit_factor": sum(wins) / abs(sum(losses)) if losses else float("inf"),
        "expectancy_r": mean_r,
        "total_pnl": sum(pnls),
        "max_drawdown": dd,
        "sortino_r": mean_r / downside if downside > 0 else float("inf"),
        "calmar": sum(pnls) / dd if dd > 0 else float("inf"),
    }
```

- [ ] **Step 4: Vérifier le passage**

Run: `.venv\Scripts\python -m pytest tests/test_journal_metrics.py tests/test_backtest.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add orderflow-bot/src/orderflow_bot/backtest/metrics.py orderflow-bot/tests/test_journal_metrics.py
git commit -m "feat(orderflow): metriques Sortino (R-multiples) et Calmar"
```

---

### Task 4: Monte Carlo — distribution des drawdowns + risque de ruine

**Files:**
- Create: `src/orderflow_bot/backtest/montecarlo.py`
- Test: `tests/test_montecarlo.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/test_montecarlo.py` :

```python
from orderflow_bot.backtest.montecarlo import simulate


def test_empty_journal():
    assert simulate([], risk_pct=0.01) == {"sims": 0}


def test_all_winners_no_drawdown():
    out = simulate([2.0, 2.0, 2.0], risk_pct=0.01, n_sims=200, seed=1)
    assert out["dd_p99"] == 0.0
    assert out["ruin_prob"] == 0.0
    assert out["final_p50"] > 1.0


def test_all_losers_hits_ruin():
    # -1R a chaque trade, risque 10 %, horizon 100 : DD depasse 50 % a coup sur
    out = simulate([-1.0], risk_pct=0.10, n_sims=200, horizon=100, ruin_dd=0.5, seed=1)
    assert out["ruin_prob"] == 1.0
    assert out["final_p50"] < 0.5


def test_deterministic_with_seed():
    rs = [2.0, -1.0, 1.5, -1.0, 3.0]
    a = simulate(rs, risk_pct=0.0075, n_sims=500, seed=42)
    b = simulate(rs, risk_pct=0.0075, n_sims=500, seed=42)
    assert a == b


def test_percentiles_ordered():
    rs = [2.0, -1.0, 1.5, -1.0, 3.0, -1.0]
    out = simulate(rs, risk_pct=0.0075, n_sims=1000, horizon=200, seed=7)
    assert 0.0 <= out["dd_p50"] <= out["dd_p90"] <= out["dd_p99"] <= 1.0
```

- [ ] **Step 2: Vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_montecarlo.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orderflow_bot.backtest.montecarlo'`.

- [ ] **Step 3: Implémenter**

Créer `src/orderflow_bot/backtest/montecarlo.py` :

```python
import random


def simulate(
    rs: list[float],
    risk_pct: float,
    n_sims: int = 5_000,
    horizon: int | None = None,
    ruin_dd: float = 0.5,
    seed: int = 0,
) -> dict:
    """Monte Carlo par resampling (bootstrap avec remise) des R-multiples
    reels du journal. Equity multiplicative : chaque trade risque risk_pct
    de l'equity courante. Sort la distribution des max drawdowns, la
    probabilite de ruine (DD >= ruin_dd) et la mediane d'equity finale.

    OFFLINE UNIQUEMENT : calibration du Kelly fractionne et comparaison
    d'iterations, jamais en input de decision live."""
    if not rs:
        return {"sims": 0}
    h = horizon or len(rs)
    rng = random.Random(seed)
    dds: list[float] = []
    finals: list[float] = []
    for _ in range(n_sims):
        eq = peak = 1.0
        dd = 0.0
        for _ in range(h):
            eq *= 1.0 + risk_pct * rng.choice(rs)
            peak = max(peak, eq)
            dd = max(dd, 1.0 - eq / peak)
        dds.append(dd)
        finals.append(eq)
    dds.sort()
    finals.sort()

    def q(xs: list[float], p: float) -> float:
        return xs[min(int(p * len(xs)), len(xs) - 1)]

    return {
        "sims": n_sims,
        "horizon": h,
        "risk_pct": risk_pct,
        "dd_p50": q(dds, 0.50),
        "dd_p90": q(dds, 0.90),
        "dd_p99": q(dds, 0.99),
        "ruin_prob": sum(d >= ruin_dd for d in dds) / n_sims,
        "final_p50": q(finals, 0.50),
    }
```

- [ ] **Step 4: Vérifier le passage**

Run: `.venv\Scripts\python -m pytest tests/test_montecarlo.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add orderflow-bot/src/orderflow_bot/backtest/montecarlo.py orderflow-bot/tests/test_montecarlo.py
git commit -m "feat(orderflow): Monte Carlo bootstrap des R reels (DD, risque de ruine)"
```

---

### Task 5: Kelly fractionné 1/4 (calculateur offline)

**Files:**
- Create: `src/orderflow_bot/risk/kelly.py`
- Test: `tests/test_kelly.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/test_kelly.py` :

```python
from orderflow_bot.risk.kelly import kelly_fraction, kelly_quarter


def test_zero_when_no_trades():
    assert kelly_fraction([]) == 0.0


def test_zero_when_negative_expectancy():
    assert kelly_fraction([1.0, -1.0, -1.0]) == 0.0


def test_binary_distribution_matches_theory():
    # p = 0.6 gagne +1R, perd -1R : Kelly theorique = 2p - 1 = 0.2
    rs = [1.0] * 6 + [-1.0] * 4
    f = kelly_fraction(rs)
    assert abs(f - 0.2) < 0.01


def test_quarter_is_quarter():
    rs = [1.0] * 6 + [-1.0] * 4
    assert kelly_quarter(rs) == kelly_fraction(rs) / 4.0


def test_capped_below_blowup():
    # pire trade -2R (slippage) : f doit rester < 0.5 sinon log(1 + f*r) explose
    rs = [3.0, 3.0, 3.0, -2.0]
    f = kelly_fraction(rs)
    assert 0.0 < f < 0.5
```

- [ ] **Step 2: Vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_kelly.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orderflow_bot.risk.kelly'`.

- [ ] **Step 3: Implémenter**

Créer `src/orderflow_bot/risk/kelly.py` :

```python
import math


def kelly_fraction(rs: list[float], f_max: float = 1.0, steps: int = 500) -> float:
    """Fraction f qui maximise la croissance log E[ln(1 + f*R)] sur la
    distribution EMPIRIQUE des R du journal (aucune hypothese de forme).
    Recherche sur grille. 0 si expectancy <= 0."""
    if not rs or sum(rs) / len(rs) <= 0:
        return 0.0
    worst = min(rs)
    # eviter ln(<= 0) : f * worst > -1 strictement
    cap = f_max if worst >= 0 else min(f_max, -0.999 / worst)
    best_f = best_g = 0.0
    for i in range(1, steps + 1):
        f = cap * i / steps
        g = sum(math.log(1.0 + f * r) for r in rs) / len(rs)
        if g > best_g:
            best_f, best_g = f, g
    return best_f


def kelly_quarter(rs: list[float]) -> float:
    """Kelly 1/4 : PLAFOND offline du risque par trade (v2 de la spec,
    apres ~100 trades reels). Jamais full Kelly, jamais une consigne
    automatique injectee dans le live."""
    return kelly_fraction(rs) / 4.0
```

- [ ] **Step 4: Vérifier le passage**

Run: `.venv\Scripts\python -m pytest tests/test_kelly.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add orderflow-bot/src/orderflow_bot/risk/kelly.py orderflow-bot/tests/test_kelly.py
git commit -m "feat(orderflow): Kelly fractionne 1/4 sur distribution empirique (offline)"
```

---

### Task 6: Walk-forward out-of-sample

**Files:**
- Modify: `src/orderflow_bot/ingestion/reader.py` (ajout `available_days`)
- Modify: `src/orderflow_bot/pipeline.py` (ajout `window_active`, `run_backtest_window` ; `run_backtest` délègue)
- Create: `src/orderflow_bot/backtest/walkforward.py`
- Test: `tests/test_walkforward.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/test_walkforward.py` :

```python
import pyarrow as pa
import pyarrow.parquet as pq

from orderflow_bot.backtest.walkforward import fold_bounds, walk_forward
from orderflow_bot.config import BotConfig, FeesCfg
from orderflow_bot.ingestion.reader import available_days
from orderflow_bot.pipeline import window_active

_DAY = 86_400_000


def _write_parquet(tmp_path, symbol="BTCUSDT"):
    folder = tmp_path / symbol
    folder.mkdir()
    t = pa.table({
        "ts": [5 * _DAY + 1, 5 * _DAY + 2, 7 * _DAY + 1],
        "price": [100.0, 101.0, 102.0],
        "qty": [1.0, 1.0, 1.0],
        "is_buyer_maker": [False, True, False],
    })
    pq.write_table(t, folder / "x.parquet")


def test_available_days(tmp_path):
    _write_parquet(tmp_path)
    assert available_days(tmp_path, "BTCUSDT") == [5, 7]


def test_available_days_empty(tmp_path):
    assert available_days(tmp_path, "BTCUSDT") == []


def test_fold_bounds_consecutive():
    # 10 jours en 3 folds : tailles 4, 3, 3 — bornes [debut, fin_exclu)
    b = fold_bounds(list(range(100, 110)), 3)
    assert b == [(100, 104), (104, 107), (107, 110)]


def test_window_active():
    assert window_active(50, None, None) is True
    assert window_active(50, 100, None) is False
    assert window_active(150, 100, 200) is True
    assert window_active(200, 100, 200) is False


def test_walk_forward_smoke(tmp_path):
    _write_parquet(tmp_path)
    cfg = BotConfig(data_dir=str(tmp_path), journal_path=str(tmp_path / "j.jsonl"),
                    fees=FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0))
    out = walk_forward(cfg, n_folds=2, warmup_days=0)
    assert len(out["folds"]) == 2
    assert out["folds"][0]["from_day"] == 5
    assert out["folds"][1]["from_day"] == 7
    assert all(f["trades"] == 0 for f in out["folds"])    # 3 ticks ne produisent rien


def test_walk_forward_not_enough_days(tmp_path):
    _write_parquet(tmp_path)
    out = walk_forward(BotConfig(data_dir=str(tmp_path)), n_folds=5)
    assert out["folds"] == []
    assert "error" in out
```

- [ ] **Step 2: Vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_walkforward.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orderflow_bot.backtest.walkforward'`.

- [ ] **Step 3: Implémenter `available_days`**

Ajouter à la fin de `src/orderflow_bot/ingestion/reader.py` :

```python
def available_days(data_dir: str | Path, symbol: str) -> list[int]:
    """Jours (epoch ms // 86_400_000) presents dans les Parquet, tries."""
    folder = Path(data_dir) / symbol
    if not folder.exists() or not any(folder.glob("*.parquet")):
        return []
    con = duckdb.connect()
    try:
        rows = con.execute(
            "SELECT DISTINCT ts // 86400000 AS d FROM read_parquet(?) ORDER BY d",
            [str(folder / "*.parquet")],
        ).fetchall()
    finally:
        con.close()
    return [int(r[0]) for r in rows]
```

- [ ] **Step 4: Implémenter la fenêtre de trading dans le pipeline**

Dans `src/orderflow_bot/pipeline.py`, remplacer `run_backtest` par :

```python
def window_active(ts: int, from_ts: int | None, to_ts: int | None) -> bool:
    """Fenetre [from_ts, to_ts) pendant laquelle les ENTREES sont autorisees."""
    return (from_ts is None or ts >= from_ts) and (to_ts is None or ts < to_ts)


def run_backtest_window(
    cfg: BotConfig,
    trades: Iterable[Trade],
    trade_from_ts: int | None = None,
    trade_to_ts: int | None = None,
) -> dict:
    """Replay du pipeline complet. Les trades AVANT trade_from_ts servent de
    warmup : profils, zones et CVD s'alimentent mais aucune entree n'est prise.
    Une position ouverte dans la fenetre se gere normalement (stop/target/EOD)
    meme apres la fin de la fenetre."""
    # journal purge en debut de run : le rapport ne doit refleter que ce replay
    Path(cfg.journal_path).unlink(missing_ok=True)
    journal = TradeJournal(cfg.journal_path)
    pipe = Pipeline(cfg, journal)
    for t in trades:
        pipe.trading_enabled = window_active(t.ts, trade_from_ts, trade_to_ts)
        pipe.on_trade(t)
    return compute_metrics(TradeJournal.load(cfg.journal_path))


def run_backtest(cfg: BotConfig, trades: Iterable[Trade]) -> dict:
    return run_backtest_window(cfg, trades)
```

- [ ] **Step 5: Implémenter le walk-forward**

Créer `src/orderflow_bot/backtest/walkforward.py` :

```python
"""Walk-forward out-of-sample : decoupe les jours disponibles en folds
consecutifs ; chaque fold est rejoue avec un warmup de warmup_days jours
(profils/zones alimentes, trading coupe), puis trading actif dans le fold.
Robustesse = stabilite de l'expectancy d'un fold a l'autre, pas le total."""

from orderflow_bot.config import BotConfig
from orderflow_bot.ingestion.reader import available_days, read_trades
from orderflow_bot.pipeline import run_backtest_window

_DAY_MS = 86_400_000


def fold_bounds(days: list[int], n_folds: int) -> list[tuple[int, int]]:
    """Decoupe les jours en n_folds consecutifs ~egaux.
    Retourne [(premier_jour, dernier_jour_exclu)] en jours epoch."""
    assert n_folds >= 1 and len(days) >= n_folds
    days = sorted(days)
    base, extra = divmod(len(days), n_folds)
    bounds: list[tuple[int, int]] = []
    i = 0
    for k in range(n_folds):
        n = base + (1 if k < extra else 0)
        chunk = days[i:i + n]
        bounds.append((chunk[0], chunk[-1] + 1))
        i += n
    return bounds


def walk_forward(cfg: BotConfig, n_folds: int = 4, warmup_days: int = 20) -> dict:
    days = available_days(cfg.data_dir, cfg.symbol)
    if len(days) < n_folds:
        return {"folds": [],
                "error": f"{len(days)} jours disponibles < {n_folds} folds"}
    # journal dedie : ne jamais ecraser le journal paper/backtest courant
    wf_cfg = cfg.model_copy(update={"journal_path": cfg.journal_path + ".wf"},
                            deep=True)
    folds: list[dict] = []
    for start_day, end_day in fold_bounds(days, n_folds):
        trades = read_trades(cfg.data_dir, cfg.symbol,
                             start_ms=(start_day - warmup_days) * _DAY_MS,
                             end_ms=end_day * _DAY_MS)
        m = run_backtest_window(wf_cfg, trades, trade_from_ts=start_day * _DAY_MS)
        m["from_day"], m["to_day"] = start_day, end_day
        folds.append(m)
    exps = [f["expectancy_r"] for f in folds if f["trades"] > 0]
    return {
        "folds": folds,
        "folds_with_trades": len(exps),
        "folds_positive": sum(1 for e in exps if e > 0),
        "expectancy_mean": sum(exps) / len(exps) if exps else 0.0,
        "expectancy_spread": (max(exps) - min(exps)) if exps else 0.0,
    }
```

- [ ] **Step 6: Vérifier le passage**

Run: `.venv\Scripts\python -m pytest tests/test_walkforward.py tests/test_backtest.py -v`
Expected: PASS (y compris `test_backtest.py` — `run_backtest` délègue sans changement de comportement).

- [ ] **Step 7: Commit**

```bash
git add orderflow-bot/src/orderflow_bot/ingestion/reader.py orderflow-bot/src/orderflow_bot/pipeline.py orderflow-bot/src/orderflow_bot/backtest/walkforward.py orderflow-bot/tests/test_walkforward.py
git commit -m "feat(orderflow): walk-forward OOS par folds de jours avec warmup sans trading"
```

---

### Task 7: CLI `validate` + `walkforward`

**Files:**
- Modify: `src/orderflow_bot/__main__.py`

- [ ] **Step 1: Implémenter** (pas de test unitaire : glue argparse, vérifiée par smoke test en Step 2)

Remplacer `src/orderflow_bot/__main__.py` :

```python
import argparse
import asyncio
import json
import logging

from orderflow_bot.config import load_config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="orderflow_bot")
    ap.add_argument("command",
                    choices=["record", "backtest", "paper", "validate", "walkforward"])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (backtest)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD (backtest)")
    ap.add_argument("--journal", default=None, help="journal JSONL (validate)")
    ap.add_argument("--sims", type=int, default=5_000, help="simulations Monte Carlo")
    ap.add_argument("--ruin-dd", type=float, default=0.5,
                    help="drawdown considere comme ruine (fraction)")
    ap.add_argument("--folds", type=int, default=4, help="folds walk-forward")
    ap.add_argument("--warmup-days", type=int, default=20,
                    help="jours de warmup sans trading avant chaque fold")
    args = ap.parse_args()
    cfg = load_config(args.config)

    if args.command == "record":
        from orderflow_bot.live import run_record
        asyncio.run(run_record(cfg))
    elif args.command == "backtest":
        from datetime import datetime, timezone

        from orderflow_bot.ingestion.reader import read_trades
        from orderflow_bot.pipeline import run_backtest

        def _ms(d: str | None) -> int | None:
            if d is None:
                return None
            dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)

        trades = read_trades(cfg.data_dir, cfg.symbol,
                             start_ms=_ms(args.start), end_ms=_ms(args.end))
        print(json.dumps(run_backtest(cfg, trades), indent=2))
    elif args.command == "validate":
        from orderflow_bot.backtest.metrics import compute_metrics
        from orderflow_bot.backtest.montecarlo import simulate
        from orderflow_bot.execution.journal import TradeJournal
        from orderflow_bot.risk.kelly import kelly_fraction, kelly_quarter

        rows = TradeJournal.load(args.journal or cfg.journal_path)
        rs = [r["r_multiple"] for r in rows]
        report = {
            "metrics": compute_metrics(rows),
            "monte_carlo": simulate(rs, cfg.risk.risk_pct,
                                    n_sims=args.sims, ruin_dd=args.ruin_dd),
            "kelly_full": kelly_fraction(rs),
            "kelly_quarter_cap": kelly_quarter(rs),
            "risk_pct_current": cfg.risk.risk_pct,
        }
        print(json.dumps(report, indent=2))
    elif args.command == "walkforward":
        from orderflow_bot.backtest.walkforward import walk_forward

        print(json.dumps(walk_forward(cfg, n_folds=args.folds,
                                      warmup_days=args.warmup_days), indent=2))
    else:
        from orderflow_bot.live import run_paper
        asyncio.run(run_paper(cfg))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test**

Run (depuis `orderflow-bot/`) :

```bash
.venv\Scripts\python -m orderflow_bot validate
.venv\Scripts\python -m orderflow_bot walkforward --folds 2 --warmup-days 0
```

Expected: JSON valide sur stdout pour chacun (`{"metrics": {"trades": 0}, ...}` si journal vide ; `walkforward` sort soit des folds, soit `{"folds": [], "error": "..."}` si pas assez de jours collectés). Aucune trace d'exception.

- [ ] **Step 3: Suite complète**

Run: `.venv\Scripts\python -m pytest -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add orderflow-bot/src/orderflow_bot/__main__.py
git commit -m "feat(orderflow): commandes CLI validate (MC + Kelly) et walkforward"
```

---

### Task 8: Roadmap de mise en production + jalons futurs

**Files:**
- Create: `docs/ROADMAP.md`

- [ ] **Step 1: Écrire le document**

Créer `docs/ROADMAP.md` :

```markdown
# Roadmap orderflow-bot

## Protocole de mise en production (spec « Évaluation & validation »)

1. **Collecte** : `record` en continu (plusieurs semaines de ticks Parquet).
2. **Backtest** : `backtest` sur tout l'historique — frais + slippage inclus
   d'office. Comparer les itérations sur Sortino, Calmar, max DD, profit
   factor (offline uniquement, jamais en input de décision live).
3. **Robustesse** : `walkforward --folds 4` — exiger une expectancy_r stable
   et positive sur la majorité des folds, pas un total flatteur tiré par un
   seul fold. Puis `validate` — Monte Carlo sur les trades réels : dd_p99 et
   ruin_prob doivent rester compatibles avec le stop journalier (-2 %).
4. **Paper trading** : 1 à 2 mois via `paper`. Go/no-go : ≥ 100 trades,
   expectancy_r > 0, comportement conforme au backtest (pas de divergence
   inexpliquée de win rate ou de slippage).
5. **Live taille minimale** : risque réduit (ex. 0,25 %/trade), mêmes règles.
6. **Montée progressive** : retour au risque nominal (0,75 %) seulement après
   validation des stats live ; plafond v2 = Kelly 1/4 (`validate` →
   `kelly_quarter_cap`), calibré sur la distribution empirique du journal —
   jamais full Kelly, jamais automatique.

## Jalons fonctionnels

- **v1.2 — TPO** : balance/imbalance du profil, single prints, poor
  highs/lows (cibles + réparation). Enrichit la couche 1 (contexte HTF).
- **v1.5 — Options/GEX** : GEX net, gamma flip, call/put walls, gros strikes
  0DTE. Ajoute la couche 0 (régime) : gamma positif → fades aux extrêmes
  uniquement ; gamma négatif → breakouts/momentum uniquement. Crypto :
  options Deribit ; CME : OI CBOE maison (approximatif) ou SpotGamma/MenthorQ.
- **v2 — DOM L2** : liquidité passive consommée vs affichée (pondération
  anti-spoofing) comme déclencheur couche 3 supplémentaire. Nécessite la
  collecte depth (extension du Recorder par type d'événement, prévue dès v1).
- **v2 — Kelly live** : après ~100 trades réels, Kelly 1/4 comme PLAFOND du
  risque par trade (le risque fixe reste la consigne par défaut).
- **Migration CME (NQ/ES)** : Databento ou Rithmic quand le setup est validé
  sur crypto. Le pipeline est agnostique du flux : seul `ingestion/` change.
```

- [ ] **Step 2: Commit**

```bash
git add orderflow-bot/docs/ROADMAP.md
git commit -m "docs(orderflow): roadmap mise en prod + jalons TPO/GEX/DOM/Kelly"
```
