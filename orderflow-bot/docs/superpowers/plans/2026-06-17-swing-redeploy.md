# Swing redeploy — étage 1 (smoke gate brut) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire le harnais minimal qui produit le **verdict gate 1** du redeploy swing (fade-vers-value) sur le stock 6 mois : brut directionnel positif → greenlight klines, sinon KILL.

**Architecture:** Extension chirurgicale du pipeline existant (approche A du spec). On ajoute (1) un flag `eod_flat` que `simulate_isolated` honore pour laisser courir les holds multi-jours, (2) un déclencheur swing pur `level_rejection_triggers` (rejet de zone sur barre resamplée), (3) son branchement dans `PlanGenerator` derrière un flag config `trigger`, (4) une config swing + un script smoke qui calcule le gate 1. Tout le reste (VP, zones, `ConfluenceEngine`, `PaperBroker`, labeling, metrics) est réutilisé **intact**.

**Tech Stack:** Python 3, pydantic (config), pytest. Pas de nouvelle dépendance.

**Référence spec :** [`docs/superpowers/specs/2026-06-17-swing-redeploy-design.md`](../specs/2026-06-17-swing-redeploy-design.md).

**Hors scope étage 1 (→ plan séparé après greenlight)** : ingestion klines 1m multi-années, `eod_flat` dans `OrderExecutor` (chemin portefeuille/paper), variantes `simulate_isolated_blocked/_parallel` pour eod_flat=False (UNSAFE : un hold peut traverser une frontière de bloc — l'étage 1 reste mono-flux), gate 2 (DSR/CSCV purgée). Ne PAS toucher ces chemins ici.

---

## File Structure

- **Modifie** `src/orderflow_bot/config.py` : `BotConfig.eod_flat` (défaut `True`), `StrategyCfg.trigger` (défaut `"footprint"`).
- **Modifie** `src/orderflow_bot/pipeline.py` : `simulate_isolated(..., eod_flat=True)` + branchement du trigger swing dans `PlanGenerator`.
- **Crée** `src/orderflow_bot/strategy/level_rejection.py` : déclencheur swing pur (sans état).
- **Crée** `config.swing.yaml` : config du run swing.
- **Crée** `scripts/swing_smoke.py` : helpers analytiques purs + orchestration du gate 1.
- **Crée** `tests/test_swing_eod_flat.py`, `tests/test_level_rejection.py`, `tests/test_swing_plan_gen.py`, `tests/test_swing_smoke.py`.

---

## Task 1 : flag `eod_flat` + `simulate_isolated` le respecte (+ censure en fin de data)

**Files:**
- Modify: `src/orderflow_bot/config.py` (BotConfig, après `bar_minutes`)
- Modify: `src/orderflow_bot/pipeline.py:347-389` (`simulate_isolated`)
- Test: `tests/test_swing_eod_flat.py`

- [ ] **Step 1 : écrire les tests qui échouent**

```python
# tests/test_swing_eod_flat.py
import pytest

from orderflow_bot.config import BotConfig, FeesCfg, RiskCfg, StrategyCfg
from orderflow_bot.models import OrderPlan, Trade
from orderflow_bot.pipeline import simulate_isolated

DAY = 86_400_000


def _cfg() -> BotConfig:
    # fees=0 -> r exact ; partial desactive (partial_at_r enorme) -> exit plein au target
    return BotConfig(
        tick_size=0.1,
        fees=FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0),
        risk=RiskCfg(partial_at_r=999.0, move_to_be=False, trail_r=None,
                     min_stop_friction_mult=0.0),
        strategy=StrategyCfg(entry_expire_minutes=600),
    )


def test_eod_flat_false_runs_past_day_to_target():
    cfg = _cfg()
    t0 = 20_000 * DAY
    plan = OrderPlan(ts=t0, side=1, entry=100.0, stop=99.0, target=102.0, meta={})
    trades = [
        Trade(t0, 100.0, 1.0, False),               # cree le broker (submit)
        Trade(t0 + 1_000, 99.9, 1.0, False),        # limit fill (franchissement strict) -> entry_px=100
        Trade(t0 + 2_000, 100.5, 1.0, False),       # ni stop ni target
        Trade(t0 + DAY, 100.8, 1.0, False),         # jour+1 : PAS de flat (eod_flat=False)
        Trade(t0 + DAY + 1_000, 102.1, 1.0, False), # target @102 -> r=+2
        Trade(t0 + DAY + 2_000, 102.0, 1.0, False),
    ]
    out = simulate_isolated(cfg, [plan], trades, eod_flat=False)
    assert len(out) == 1
    assert out[0].fills[-1].kind == "target"
    assert out[0].r_multiple == pytest.approx(2.0)


def test_eod_flat_true_default_force_closes_at_day_boundary():
    cfg = _cfg()
    t0 = 20_000 * DAY
    plan = OrderPlan(ts=t0, side=1, entry=100.0, stop=99.0, target=102.0, meta={})
    trades = [
        Trade(t0, 100.0, 1.0, False),
        Trade(t0 + 1_000, 99.9, 1.0, False),
        Trade(t0 + DAY, 100.8, 1.0, False),         # jour+1 : flat EOD @100.8 -> r=+0.8
        Trade(t0 + DAY + 1_000, 102.1, 1.0, False),
    ]
    out = simulate_isolated(cfg, [plan], trades)     # eod_flat=True par defaut
    assert out[0].fills[-1].kind == "eod"
    assert out[0].r_multiple == pytest.approx(0.8)


def test_eod_flat_false_censors_position_open_at_data_end():
    cfg = _cfg()
    t0 = 20_000 * DAY
    plan = OrderPlan(ts=t0, side=1, entry=100.0, stop=99.0, target=110.0, meta={})  # target jamais atteint
    trades = [
        Trade(t0, 100.0, 1.0, False),
        Trade(t0 + 1_000, 99.9, 1.0, False),         # fill
        Trade(t0 + DAY, 101.0, 1.0, False),          # court toujours
        Trade(t0 + 2 * DAY, 101.5, 1.0, False),      # fin des donnees -> censure
    ]
    out = simulate_isolated(cfg, [plan], trades, eod_flat=False)
    assert len(out) == 1
    assert out[0].fills[-1].kind == "eod"            # censure = fermeture forcee en fin de data
    assert out[0].r_multiple == pytest.approx(1.5)
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `python -m pytest tests/test_swing_eod_flat.py -v`
Expected: FAIL — `simulate_isolated()` ne prend pas encore `eod_flat` (TypeError: unexpected keyword argument).

- [ ] **Step 3 : ajouter le flag config**

Dans `src/orderflow_bot/config.py`, classe `BotConfig`, juste après `bar_minutes: int = 1` :

```python
    bar_minutes: int = 1
    eod_flat: bool = True                        # swing tourne en False : holds multi-jours
```

- [ ] **Step 4 : modifier `simulate_isolated`**

Remplacer la signature et la boucle (`src/orderflow_bot/pipeline.py`, fonction `simulate_isolated`) :

```python
def simulate_isolated(
    cfg: BotConfig, plans: list[OrderPlan], trades: Iterable[Trade],
    eod_flat: bool = True,
) -> list[ClosedTrade]:
    """Outcome intrinseque de chaque plan candidat, pris isolement (cf. docstring
    d'origine). eod_flat=True : flat au changement de jour (intraday). eod_flat=False
    (swing) : les positions courent jusqu'au stop/target structurel sur plusieurs
    jours ; le restant ouvert en fin de fenetre est ferme (kind 'eod' = censure)."""
    pending = sorted(plans, key=lambda p: p.ts)
    i, n = 0, len(pending)
    expire = cfg.strategy.entry_expire_minutes * 60_000
    active: list[PaperBroker] = []
    out: list[ClosedTrade] = []
    day = -1
    last_t: Trade | None = None
    for t in trades:
        last_t = t
        d = t.ts // _DAY_MS
        if d != day:
            if day >= 0 and eod_flat:               # flat EOD seulement si demande
                for b in active:
                    ct = b.force_close(t)
                    if ct is not None:
                        out.append(ct)
                active = []
            day = d
        still: list[PaperBroker] = []
        for b in active:
            ev = b.on_trade(t)
            if isinstance(ev, ClosedTrade):
                out.append(ev)
            elif ev is None:                        # toujours pending/ouvert -> garder
                still.append(b)
            # Cancelled (expire sans fill) -> abandonne
        active = still
        while i < n and pending[i].ts <= t.ts:
            b = PaperBroker(cfg.risk, expire, cfg.fees, cfg.tick_size,
                            entry_mode=cfg.strategy.entry_mode,
                            confirm_frac=cfg.strategy.entry_confirm_frac)
            b.submit(pending[i], 1.0, pending[i].ts)
            active.append(b)
            i += 1
    if not eod_flat and last_t is not None:         # censure : ferme le restant en fin de data
        for b in active:
            ct = b.force_close(last_t)
            if ct is not None:
                out.append(ct)
    return out
```

(Ne PAS toucher `simulate_isolated_blocked` / `_parallel` : ils restent eod_flat=True implicite, unsafe pour les holds swing — voir « hors scope ».)

- [ ] **Step 5 : lancer, vérifier le succès**

Run: `python -m pytest tests/test_swing_eod_flat.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6 : non-régression**

Run: `python -m pytest tests/test_backtest.py -v`
Expected: PASS (le défaut `eod_flat=True` préserve le comportement intraday).

- [ ] **Step 7 : commit**

```bash
git add src/orderflow_bot/config.py src/orderflow_bot/pipeline.py tests/test_swing_eod_flat.py
git commit -m "feat(swing): flag eod_flat + simulate_isolated holds multi-jours + censure"
```

---

## Task 2 : déclencheur swing `level_rejection_triggers` (unité pure)

**Files:**
- Create: `src/orderflow_bot/strategy/level_rejection.py`
- Test: `tests/test_level_rejection.py`

- [ ] **Step 1 : écrire les tests qui échouent**

```python
# tests/test_level_rejection.py
from orderflow_bot.models import FootprintBar
from orderflow_bot.strategy.level_rejection import level_rejection_triggers
from orderflow_bot.strategy.zones import Zone


def _bar(o, h, l, c, ts=1000) -> FootprintBar:
    return FootprintBar(open_ts=ts - 1, close_ts=ts, open=o, high=h, low=l, close=c,
                        volume=0.0, delta=0.0, ask_vol={}, bid_vol={})


def test_long_rejection_picks_nearest_support():
    z1 = Zone(96.0, 97.0, 0, "lvn", 105.0)
    z2 = Zone(98.5, 99.0, 1, "val", 105.0)        # support le plus proche sous la cloture
    bar = _bar(o=100.0, h=100.2, l=96.5, c=99.5)  # tape les deux, cloture au-dessus
    trigs = level_rejection_triggers(bar, [z1, z2])
    assert [t.price for t in trigs] == [99.0]     # z2.hi (le plus proche)
    assert trigs[0].side == 1
    assert trigs[0].kind == "level_rejection"
    assert trigs[0].ts == bar.close_ts


def test_short_rejection_emits_trigger():
    z = Zone(103.0, 104.0, -1, "vah", 100.0)
    bar = _bar(o=102.0, h=103.5, l=101.8, c=102.5) # high tape [103,104], cloture < 103
    trigs = level_rejection_triggers(bar, [z])
    assert len(trigs) == 1
    assert trigs[0].side == -1 and trigs[0].price == 103.0


def test_no_trigger_when_close_inside_zone():
    z = Zone(99.0, 100.0, 1, "val", 105.0)
    bar = _bar(o=99.5, h=99.9, l=99.1, c=99.5)     # reste dans la zone
    assert level_rejection_triggers(bar, [z]) == []


def test_no_trigger_when_bar_misses_zone():
    z = Zone(90.0, 91.0, 1, "val", 95.0)
    bar = _bar(o=100.0, h=101.0, l=99.5, c=100.5)  # n'atteint jamais la zone
    assert level_rejection_triggers(bar, [z]) == []
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `python -m pytest tests/test_level_rejection.py -v`
Expected: FAIL — `ModuleNotFoundError: orderflow_bot.strategy.level_rejection`.

- [ ] **Step 3 : écrire l'implémentation minimale**

```python
# src/orderflow_bot/strategy/level_rejection.py
"""Couche 3 swing : rejet d'un niveau de volume profile sur barre resamplee.

Une barre qui teste une zone puis re-cloture en dehors = rejet du niveau ->
Trigger reversal (fade vers value). On n'emet qu'un trigger par sens, sur la
zone testee la PLUS PROCHE de la cloture (evite les candidats correles d'un
meme grand mouvement). La compatibilite du sens est validee ensuite par
ConfluenceEngine (zone VAL/VAH contrainte, npoc/lvn libre)."""

from orderflow_bot.models import FootprintBar
from orderflow_bot.strategy.confluence import Trigger
from orderflow_bot.strategy.zones import Zone


def level_rejection_triggers(bar: FootprintBar, zones: list[Zone]) -> list[Trigger]:
    # support teste par le bas, cloture revenue au-dessus de la zone -> long
    longs = [z for z in zones if bar.low <= z.hi < bar.close]
    # resistance testee par le haut, cloture revenue sous la zone -> short
    shorts = [z for z in zones if bar.close < z.lo <= bar.high]
    out: list[Trigger] = []
    if longs:
        z = max(longs, key=lambda z: z.hi)        # support le plus proche sous la cloture
        out.append(Trigger(ts=bar.close_ts, side=1, kind="level_rejection", price=z.hi))
    if shorts:
        z = min(shorts, key=lambda z: z.lo)       # resistance la plus proche au-dessus
        out.append(Trigger(ts=bar.close_ts, side=-1, kind="level_rejection", price=z.lo))
    return out
```

- [ ] **Step 4 : lancer, vérifier le succès**

Run: `python -m pytest tests/test_level_rejection.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5 : commit**

```bash
git add src/orderflow_bot/strategy/level_rejection.py tests/test_level_rejection.py
git commit -m "feat(swing): declencheur level_rejection (rejet de zone, nearest)"
```

---

## Task 3 : brancher le trigger swing dans `PlanGenerator` (flag config)

**Files:**
- Modify: `src/orderflow_bot/config.py` (`StrategyCfg`, après `entry_confirm_frac`)
- Modify: `src/orderflow_bot/pipeline.py` (import + `PlanGenerator.__init__` + `PlanGenerator.on_trade`)
- Test: `tests/test_swing_plan_gen.py`

- [ ] **Step 1 : écrire le test end-to-end qui échoue**

```python
# tests/test_swing_plan_gen.py
import pytest

from orderflow_bot.config import BotConfig, FeesCfg, RiskCfg, StrategyCfg
from orderflow_bot.models import Trade
from orderflow_bot.pipeline import generate_plans

DAY = 86_400_000
H4 = 240 * 60_000


def _swing_synth() -> list[Trade]:
    out: list[Trade] = []
    base = 20_000 * DAY
    # jour 1 : profil pyramidal POC=100, value autour de 97..103
    ts = base
    for p in range(95, 106):
        for _ in range(10 - abs(p - 100)):
            out.append(Trade(ts, float(p), 1.0, ts % 2 == 0))
            ts += 1_000
    # jour 2, 1ere fenetre 4h : rejet d'un support (dip dans la value puis cloture au-dessus)
    d2 = base + DAY
    out.append(Trade(d2 + 1_000, 96.9, 1.0, False))   # dip dans/sous la value basse
    out.append(Trade(d2 + 2_000, 97.1, 1.0, False))
    out.append(Trade(d2 + 3_000, 99.0, 1.0, False))   # cloture de la fenetre nettement au-dessus
    # 1er trade de la fenetre 4h suivante -> flush du bar precedent -> evaluation du trigger
    out.append(Trade(d2 + H4 + 1_000, 99.2, 1.0, False))
    return out


def test_level_rejection_generates_reversal_plan():
    cfg = BotConfig(
        tick_size=0.1, bar_minutes=240,
        fees=FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0),
        strategy=StrategyCfg(trigger="level_rejection", profile_days=1,
                             npoc_lookback_days=1, zone_margin_pct=0.002,
                             stop_buffer_ticks=5, entry_expire_minutes=600),  # buffer 5 -> RR ~3.1 (evite la borne RR=2.0 knife-edge en float)
        risk=RiskCfg(min_rr=2.0, min_stop_friction_mult=0.0),
    )
    plans = generate_plans(cfg, _swing_synth())
    assert len(plans) >= 1
    p = plans[0]
    assert p.side == 1                              # rejet d'un support -> long
    assert p.target == pytest.approx(100.0)        # target = POC veille
    assert p.meta["trigger"] == "level_rejection"
    assert p.entry < p.target and p.stop < p.entry  # geometrie reversal coherente
```

(La non-régression du chemin footprint par défaut est couverte par `test_backtest.py`
et le `pytest -q` du Step 6 — pas de test fragile « == [] » ici.)

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `python -m pytest tests/test_swing_plan_gen.py -v`
Expected: FAIL — `StrategyCfg` n'accepte pas `trigger` (pydantic `extra=forbid` → ValidationError).

- [ ] **Step 3 : ajouter le champ config**

Dans `src/orderflow_bot/config.py`, classe `StrategyCfg`, juste après `entry_confirm_frac: float = 0.0` :

```python
    entry_confirm_frac: float = 0.0      # stop : confirme apres frac*risk0 dans le sens du trade
    # footprint : declencheurs intraday (absorption/cvd/imbalance empilees).
    # level_rejection : declencheur swing (rejet de zone sur barre resamplee).
    trigger: Literal["footprint", "level_rejection"] = "footprint"
```

(`Literal` est déjà importé dans `config.py`.)

- [ ] **Step 4 : brancher dans `PlanGenerator`**

Dans `src/orderflow_bot/pipeline.py`, ajouter l'import près des autres imports `strategy` :

```python
from orderflow_bot.strategy.level_rejection import level_rejection_triggers
```

Dans `PlanGenerator.__init__`, après la construction de `self.confluence` (avant `self.profile_bin = ...`) :

```python
        self._level_rejection = st.trigger == "level_rejection"
```

Remplacer `PlanGenerator.on_trade` par :

```python
    def on_trade(self, t: Trade) -> list[OrderPlan]:
        self._maybe_rollover(t)
        self._day_profile.add(t.price, t.qty)
        self._day_high = max(self._day_high, t.price)
        self._day_low = min(self._day_low, t.price)
        trigs = []
        bar = self.aggregator.on_trade(t)
        if bar is not None:
            if self._level_rejection:
                trigs += level_rejection_triggers(bar, self.confluence.zones)
            else:
                trigs += self.triggers.on_bar(bar)
        if not self._level_rejection:
            trigs += self.triggers.on_trade(t)
        plans = []
        for trig in trigs:
            plan = self.confluence.evaluate(trig)
            if plan is not None:
                plans.append(plan)
        return plans
```

- [ ] **Step 5 : lancer, vérifier le succès**

Run: `python -m pytest tests/test_swing_plan_gen.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6 : non-régression complète**

Run: `python -m pytest -q`
Expected: PASS (toute la suite ; le défaut `trigger="footprint"` préserve l'intraday).

- [ ] **Step 7 : commit**

```bash
git add src/orderflow_bot/config.py src/orderflow_bot/pipeline.py tests/test_swing_plan_gen.py
git commit -m "feat(swing): branche level_rejection dans PlanGenerator via config.trigger"
```

---

## Task 4 : config swing + script smoke gate 1

**Files:**
- Create: `config.swing.yaml`
- Create: `scripts/swing_smoke.py`
- Test: `tests/test_swing_smoke.py`

- [ ] **Step 1 : écrire les tests des helpers (échouent)**

```python
# tests/test_swing_smoke.py
import pytest

from orderflow_bot.models import ClosedTrade, Fill, OrderPlan
from scripts.swing_smoke import brut, dead_born_rate, both_halves_positive, gate1, mirror_plan


def _ct(r, mfe, opened, kind="target") -> ClosedTrade:
    return ClosedTrade(
        plan=OrderPlan(opened, 1, 100.0, 99.0, 102.0, {}), qty=1.0,
        fills=[Fill(opened, 100.0, 1.0, "entry"), Fill(opened + 1, 102.0, 1.0, kind)],
        pnl=r, r_multiple=r, opened_ts=opened, closed_ts=opened + 1,
        mfe_r=mfe, mae_r=0.0,
    )


def test_brut_excludes_censored_labels():
    labels = [_ct(2.0, 2.0, 1, "target"), _ct(-1.0, 0.2, 2, "stop"), _ct(5.0, 5.0, 3, "eod")]
    assert brut(labels) == pytest.approx((2.0 - 1.0) / 2)   # le 'eod' (censure) est exclu


def test_dead_born_rate_excludes_censored():
    labels = [_ct(2.0, 2.0, 1), _ct(-1.0, 0.2, 2, "stop"), _ct(5.0, 5.0, 3, "eod")]
    assert dead_born_rate(labels) == pytest.approx(0.5)     # 1 mort-ne (mfe 0.2) sur 2 realises


def test_mirror_plan_reflects_through_entry():
    m = mirror_plan(OrderPlan(1, 1, 100.0, 99.0, 102.0, {}))
    assert m.side == -1 and m.entry == 100.0 and m.stop == 101.0 and m.target == 98.0


def test_gate1_greenlights_directional_positive():
    fade = [_ct(2.0, 2.0, 1), _ct(1.0, 1.5, 2), _ct(2.0, 2.0, 3), _ct(1.0, 1.2, 4)]
    mirror = [_ct(-2.0, 0.1, 1, "stop"), _ct(-1.0, 0.1, 2, "stop"),
              _ct(-1.5, 0.1, 3, "stop"), _ct(-1.0, 0.1, 4, "stop")]
    assert gate1(fade, mirror)["greenlight"] is True


def test_gate1_kills_when_brut_flat():
    fade = [_ct(0.1, 0.6, 1), _ct(-0.1, 0.2, 2, "stop"), _ct(0.05, 0.6, 3), _ct(-0.2, 0.1, 4, "stop")]
    mirror = [_ct(-0.1, 0.1, 1, "stop"), _ct(0.1, 0.6, 2), _ct(-0.05, 0.1, 3, "stop"), _ct(0.2, 0.6, 4)]
    assert gate1(fade, mirror)["greenlight"] is False
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `python -m pytest tests/test_swing_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.swing_smoke`.

- [ ] **Step 3 : écrire la config swing**

```yaml
# config.swing.yaml — run swing (fade-vers-value), etage 1 smoke
symbol: BTCUSDT
market: spot
tick_size: 0.01
bin_size: 1.0
profile_bin_size: 25.0
bar_minutes: 240            # barres 4h pour le declencheur de rejet
eod_flat: false            # holds swing multi-jours (pas de flat EOD)
data_dir: data
journal_path: journal.swing.jsonl
equity: 10000

risk:
  risk_pct: 0.0075
  daily_stop_pct: 1.0          # relache : le gate brut juge le signal nu
  max_consecutive_losses: 100000
  max_trades_per_day: 100000
  min_rr: 2.0
  partial_at_r: 1.0
  partial_fraction: 0.5
  min_stop_friction_mult: 3.0

fees:
  maker_pct: 0.0002
  taker_pct: 0.0005
  slippage_ticks: 2

strategy:
  trigger: level_rejection
  signal_mode: reversal
  entry_mode: stop             # entree sur confirmation : quasi-gratuite au swing
  entry_confirm_frac: 0.0      # la cloture de rejet est la confirmation
  zone_margin_pct: 0.002
  stop_buffer_ticks: 20
  entry_expire_minutes: 240
  profile_days: 5
  npoc_lookback_days: 20

sessions: []                   # pas de filtre de session au swing
```

- [ ] **Step 4 : écrire le script smoke (helpers purs + orchestration)**

```python
# scripts/swing_smoke.py
"""Gate 1 du redeploy swing (cf. spec 2026-06-17). Mesure le BRUT (frais=0) du
fade-vers-value sur le stock, exclut les labels censures, et tranche :
greenlight klines si brut>0 ET signe stable sur les 2 moities ET brut_fade >
brut_miroir (info directionnelle, null #5). Sinon KILL."""

from orderflow_bot.config import BotConfig, load_config
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.models import ClosedTrade, OrderPlan
from orderflow_bot.pipeline import generate_plans, simulate_isolated


def mirror_plan(p: OrderPlan) -> OrderPlan:
    """Null directionnel : meme entry, sens inverse, stop/target reflechis a
    travers l'entry. Un signal sans info -> brut_fade ~ brut_miroir."""
    return OrderPlan(ts=p.ts, side=-p.side, entry=p.entry,
                     stop=2 * p.entry - p.stop, target=2 * p.entry - p.target,
                     meta={**p.meta, "mirror": True})


def _realized(labels: list[ClosedTrade]) -> list[ClosedTrade]:
    # censure = fermeture forcee en fin de data (kind 'eod' en mode eod_flat=False)
    return [ct for ct in labels if ct.fills[-1].kind != "eod"]


def brut(labels: list[ClosedTrade]) -> float:
    real = _realized(labels)
    return sum(ct.r_multiple for ct in real) / len(real) if real else 0.0


def dead_born_rate(labels: list[ClosedTrade]) -> float:
    real = _realized(labels)
    return sum(1 for ct in real if ct.mfe_r < 0.5) / len(real) if real else 1.0


def both_halves_positive(labels: list[ClosedTrade]) -> bool:
    real = sorted(_realized(labels), key=lambda ct: ct.opened_ts)
    if len(real) < 2:
        return False
    mid = len(real) // 2
    h1, h2 = real[:mid], real[mid:]
    a1 = sum(c.r_multiple for c in h1) / len(h1)
    a2 = sum(c.r_multiple for c in h2) / len(h2)
    return a1 > 0 and a2 > 0


def gate1(fade: list[ClosedTrade], mirror: list[ClosedTrade]) -> dict:
    b_fade, b_mirror = brut(fade), brut(mirror)
    halves = both_halves_positive(fade)
    return {
        "n": len(_realized(fade)),
        "brut_fade": round(b_fade, 4),
        "brut_mirror": round(b_mirror, 4),
        "dead_born": round(dead_born_rate(fade), 3),
        "both_halves_pos": halves,
        "greenlight": bool(b_fade > 0 and halves and b_fade > b_mirror),
    }


def _zero_fees(cfg: BotConfig) -> BotConfig:
    d = cfg.model_dump()
    d["fees"] = {"maker_pct": 0.0, "taker_pct": 0.0, "slippage_ticks": 0}
    return BotConfig(**d)


def main() -> None:
    cfg = _zero_fees(load_config("config.swing.yaml"))   # brut = frais=0

    def ticks():
        return read_trades(cfg.market_data_dir, cfg.symbol)

    plans = generate_plans(cfg, ticks())
    fade = simulate_isolated(cfg, plans, ticks(), eod_flat=cfg.eod_flat)
    mirror = simulate_isolated(cfg, [mirror_plan(p) for p in plans], ticks(),
                               eod_flat=cfg.eod_flat)
    verdict = gate1(fade, mirror)
    print(f"plans generes      : {len(plans)}")
    print(f"gate 1             : {verdict}")
    print("VERDICT            :",
          "GREENLIGHT klines" if verdict["greenlight"] else "KILL (brut non directionnel)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5 : lancer les tests des helpers, vérifier le succès**

Run: `python -m pytest tests/test_swing_smoke.py -v`
Expected: PASS (5 tests).

> Si l'import `scripts.swing_smoke` échoue (scripts non packagé) : ajouter un
> `tests/__init__.py` absent ? Non — lancer pytest depuis la racine du repo
> (`rootdir` contient `scripts/`). Si besoin, créer `scripts/__init__.py` vide.

- [ ] **Step 6 : commit**

```bash
git add config.swing.yaml scripts/swing_smoke.py tests/test_swing_smoke.py
git commit -m "feat(swing): config swing + script smoke gate 1 (brut/miroir/moities)"
```

- [ ] **Step 7 : exécuter le gate 1 sur le stock (le verdict réel)**

Run: `python scripts/swing_smoke.py`
Expected: affiche `plans generes`, le dict `gate 1`, et `VERDICT`.

**Interprétation (pré-enregistrée, ne pas rationaliser après coup) :**
- `GREENLIGHT klines` ⇒ brut directionnel positif et stable → étage 2 justifié (écrire le plan klines).
- `KILL` ⇒ brut ≈ 0 / non directionnel → thèse fade-vers-value morte comme l'intraday. NE PAS construire l'ingestion klines. Documenter le verdict dans `FINDINGS.md` et regeler.

---

## Self-Review

**Couverture du spec :**
- §1 hypothèse H1 (brut directionnel) → testée par le gate 1 (script Task 4).
- §2 trigger `LevelRejectionTrigger` 4h → Task 2 (unité) + Task 3 (branchement) + `bar_minutes: 240` (config Task 4).
- §2 entrée stop/confirmation → `entry_mode: stop`, `entry_confirm_frac: 0.0` (config Task 4 ; réutilise PaperBroker existant).
- §3 horizon structurel sans limite + eod_flat=False + censure → Task 1.
- §3 découplage rollover-profil / force-close → respecté (Task 1 ne touche que la fermeture de position de `simulate_isolated` ; `_maybe_rollover` intact).
- §4 étage 1 sur stock 6mo → Task 4 (mono-flux ; klines = hors scope, plan séparé).
- §5 gate 1 (brut>0 ∧ signe stable ∧ brut_fade>miroir ; brut via frais=0) → Task 4 (`gate1`, `_zero_fees`).
- §5 gate 2 / CSCV purgée / Monte Carlo → hors scope étage 1 (déclaré).
- §6 frontière de code → respectée (réutilise VP/zones/ConfluenceEngine/PaperBroker/metrics intacts).
- §7 garde-fous : brut via relabel frais=0 (✓ `_zero_fees`) ; seuils figés au spec avant exécution (✓) ; kill-fast (✓ Step 7 Task 4).

**Placeholders :** aucun TBD/TODO ; tout le code des steps est complet.

**Cohérence des types :** `simulate_isolated(cfg, plans, trades, eod_flat=...)` signature identique entre Task 1 (def) et Task 4 (appels) ; `level_rejection_triggers(bar, zones)` identique Task 2 (def) / Task 3 (appel) ; `Trigger(ts, side, kind, price)` conforme à `confluence.Trigger` ; `mirror_plan`/`brut`/`gate1` cohérents test (Task 4 Step 1) ↔ impl (Step 4) ; `Zone(lo, hi, side, kind, target)` conforme à `zones.Zone`.

**Scope :** focalisé étage 1 (gate brut). Étage 2 explicitement reporté à un plan ultérieur conditionné au greenlight.

---

## Execution Handoff

Voir la section finale de la conversation pour le choix subagent-driven vs inline.
