# Swing-Continuation (étage 2b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tester si un breakout/acceptance au-delà d'un bord de value area porte un edge de niveau directionnel séparable du drift, sur klines multi-années BTCUSDT.

**Architecture:** Extension chirurgicale (comme étages 1 & 2a), zéro réécriture. Nouveau trigger `level_breakout` (corps qui traverse le bord, complément géométrique de `level_rejection`) ; cible continuation rendue **structurelle** dans `ConfluenceEngine` (niveau-suivant + fallback measured-move au lieu de `day_high`/`day_low`) ; gate 2b **noyau kill-fast** drift-contrôlé (`brut_long>0 ∧ brut_short>0`, t>2, miroir, net) avec diagnostic régime. DSR/CSCV = stade full-history post-greenlight (réutilise `scripts/overfit_audit.py`), hors de ce plan.

**Tech Stack:** Python 3.11, pydantic v2, pytest, duckdb/pyarrow (klines 2a). Réutilise tout le moteur 2-passes + `read_market`/`read_klines_as_ticks` (2a) + `simulate_isolated(eod_flat=False)` (étage 1) + `swing_gate` helpers + `plumbing_checks` (2a).

---

> **CONTRAINTES IMPÉRATIVES (lire avant tout commit).**
> - **Python = `.venv/Scripts/python.exe`** (le python du shell est un venv hermes sans pip). Toutes les commandes pytest ci-dessous l'utilisent.
> - **Repo multi-projets enraciné à `C:\Projets`** : `git add` UNIQUEMENT des chemins précis listés. **JAMAIS `git add .` ni `-A`** (a déjà stagé tout le repo une fois). Après chaque `git add`, vérifier `git diff --cached --stat` ne montre QUE les fichiers attendus avant de committer.
> - **Branche : `feat/orderflow-swing-continuation`** (déjà créée, la spec y est commitée). Ne pas merger ni toucher `main`.
> - **Brut = relabel frais=0** (jamais `net + frais/risk0`). Le « net » se mesure en relabelant le MÊME jeu de candidats aux frais réels.
> - Spec de référence : `docs/superpowers/specs/2026-06-17-swing-continuation-design.md`.

---

### Task 1: Trigger `level_breakout_triggers` (cassure body-cross)

Complément géométrique exact de `level_rejection` : au lieu de *mèche pique + clôture revient* (rejet), le **corps traverse le bord** (acceptance). Fonction pure, aucune I/O, même structure que `strategy/level_rejection.py`.

**Files:**
- Create: `src/orderflow_bot/strategy/level_breakout.py`
- Test: `tests/test_level_breakout.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_level_breakout.py
from orderflow_bot.models import FootprintBar
from orderflow_bot.strategy.level_breakout import level_breakout_triggers
from orderflow_bot.strategy.zones import Zone


def _bar(o, h, l, c, ts=1000) -> FootprintBar:
    return FootprintBar(open_ts=ts - 1, close_ts=ts, open=o, high=h, low=l, close=c,
                        volume=0.0, delta=0.0, ask_vol={}, bid_vol={})


def test_long_breakout_picks_nearest_edge():
    z1 = Zone(96.0, 97.0, 0, "lvn", 100.0)
    z2 = Zone(98.5, 99.0, -1, "vah", 100.0)        # bord casse le plus proche sous la cloture
    bar = _bar(o=95.0, h=100.0, l=95.0, c=100.0)   # corps ouvre sous les deux, cloture au-dessus
    trigs = level_breakout_triggers(bar, [z1, z2])
    assert [t.price for t in trigs] == [99.0]      # z2.hi (le plus proche sous la cloture)
    assert trigs[0].side == 1
    assert trigs[0].kind == "level_breakout"
    assert trigs[0].ts == bar.close_ts


def test_short_breakout_emits_trigger():
    z = Zone(103.0, 104.0, 1, "val", 100.0)
    bar = _bar(o=105.0, h=105.0, l=102.0, c=102.0)  # corps ouvre au-dessus, cloture sous z.lo
    trigs = level_breakout_triggers(bar, [z])
    assert len(trigs) == 1
    assert trigs[0].side == -1 and trigs[0].price == 103.0


def test_no_breakout_when_close_inside_zone():
    z = Zone(99.0, 100.0, 0, "npoc", 105.0)
    bar = _bar(o=98.0, h=99.8, l=98.0, c=99.5)      # cloture DANS la zone, pas au-dela
    assert level_breakout_triggers(bar, [z]) == []


def test_no_breakout_when_open_already_beyond():
    z = Zone(96.0, 97.0, 0, "lvn", 100.0)
    bar = _bar(o=98.0, h=101.0, l=98.0, c=100.0)    # corps deja AU-DESSUS au depart -> pas une cassure
    assert level_breakout_triggers(bar, [z]) == []


def test_no_breakout_when_bar_misses_zone():
    z = Zone(90.0, 91.0, 0, "lvn", 95.0)
    bar = _bar(o=100.0, h=101.0, l=99.5, c=100.5)   # n'atteint jamais la zone
    assert level_breakout_triggers(bar, [z]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_level_breakout.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orderflow_bot.strategy.level_breakout'`.

- [ ] **Step 3: Write the implementation**

```python
# src/orderflow_bot/strategy/level_breakout.py
"""Couche 3 swing : cassure/acceptance d'un niveau de volume profile sur barre
resamplee. Le CORPS de la barre traverse le bord (open d'un cote, close de
l'autre) = acceptance au-dela de la value -> Trigger continuation. Complement
geometrique exact de level_rejection (meche pique + cl, retour = rejet). On
n'emet qu'un trigger par sens, sur la zone cassee la PLUS PROCHE de la cloture
(evite les candidats correles d'un meme grand mouvement). La compatibilite du
sens (VAH casse en haut=long, VAL casse en bas=short) est validee ensuite par
ConfluenceEngine mode continuation."""

from orderflow_bot.models import FootprintBar
from orderflow_bot.strategy.confluence import Trigger
from orderflow_bot.strategy.zones import Zone


def level_breakout_triggers(bar: FootprintBar, zones: list[Zone]) -> list[Trigger]:
    # corps ouvre au/sous le bord-haut, cloture au-dessus -> cassure haussiere
    longs = [z for z in zones if bar.open <= z.hi < bar.close]
    # corps ouvre au/sur le bord-bas, cloture en-dessous -> cassure baissiere
    shorts = [z for z in zones if bar.close < z.lo <= bar.open]
    out: list[Trigger] = []
    if longs:
        z = max(longs, key=lambda z: z.hi)        # bord casse le plus proche sous la cloture
        out.append(Trigger(ts=bar.close_ts, side=1, kind="level_breakout", price=z.hi))
    if shorts:
        z = min(shorts, key=lambda z: z.lo)       # bord casse le plus proche au-dessus
        out.append(Trigger(ts=bar.close_ts, side=-1, kind="level_breakout", price=z.lo))
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_level_breakout.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/strategy/level_breakout.py tests/test_level_breakout.py
git diff --cached --stat   # verifier : EXACTEMENT ces 2 fichiers
git commit -m "feat(orderflow): trigger level_breakout (cassure body-cross) [2b]"
```

---

### Task 2: Cible continuation structurelle dans `ConfluenceEngine`

Le mode continuation existant cible `day_high`/`day_low` (cassé pour swing : reward<0 si déjà dépassé, R petit). Remplacé par **niveau structurel le plus proche au-delà de l'entrée** (fallback measured-move `entry + side×(vah−val)`). Modif ciblée ; la logique `eff_side`/stop/RR/reversal reste intacte.

**Files:**
- Modify: `src/orderflow_bot/strategy/confluence.py` (`__init__`, `update_day`, `evaluate`, + helper `_continuation_target`)
- Test: `tests/test_continuation_target.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_continuation_target.py
from orderflow_bot.strategy.confluence import ConfluenceEngine, Trigger
from orderflow_bot.strategy.context import Bias
from orderflow_bot.strategy.zones import Zone


def _engine(mode):
    return ConfluenceEngine(min_rr=2.0, stop_buffer_ticks=1, tick_size=1.0,
                            fees=None, min_stop_friction_mult=0.0, mode=mode)


def test_continuation_target_nearest_structural_level():
    eng = _engine("continuation")
    eng.update_day([Zone(99.0, 100.0, -1, "vah", 0.0)], Bias.BOTH,
                   struct_levels=[95.0, 105.0, 110.0], va_width=8.0)
    plan = eng.evaluate(Trigger(ts=1, side=1, kind="level_breakout", price=100.0))
    assert plan is not None
    assert plan.target == 105.0          # niveau le plus proche AU-DELA de l'entree (100)
    assert plan.side == 1 and plan.meta["mode"] == "continuation"
    assert plan.stop < plan.entry < plan.target


def test_continuation_target_fallback_measured_move():
    eng = _engine("continuation")
    eng.update_day([Zone(99.0, 100.0, -1, "vah", 0.0)], Bias.BOTH,
                   struct_levels=[95.0], va_width=8.0)   # aucun niveau au-dela de 100
    plan = eng.evaluate(Trigger(ts=1, side=1, kind="level_breakout", price=100.0))
    assert plan is not None
    assert plan.target == 108.0          # entry + side * va_width = 100 + 8


def test_continuation_no_plan_when_no_target():
    eng = _engine("continuation")
    eng.update_day([Zone(99.0, 100.0, -1, "vah", 0.0)], Bias.BOTH,
                   struct_levels=[95.0], va_width=None)   # ni niveau au-dela ni measured-move
    assert eng.evaluate(Trigger(ts=1, side=1, kind="level_breakout", price=100.0)) is None


def test_reversal_target_unchanged():
    eng = _engine("reversal")
    eng.update_day([Zone(98.5, 99.0, 1, "val", 103.0)], Bias.BOTH)  # struct_levels absents
    plan = eng.evaluate(Trigger(ts=1, side=1, kind="level_rejection", price=99.0))
    assert plan is not None
    assert plan.target == 103.0          # reversal cible toujours z.target (POC), inchange
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_continuation_target.py -v`
Expected: FAIL — `update_day() got an unexpected keyword argument 'struct_levels'` (et la cible continuation vaut encore day_high/day_low).

- [ ] **Step 3: Write the implementation**

Dans `src/orderflow_bot/strategy/confluence.py` :

**3a.** Dans `ConfluenceEngine.__init__`, après `self.day_low: float | None = None` (fin du `__init__`), ajouter :

```python
        self.struct_levels: list[float] = []
        self.va_width: float | None = None
```

**3b.** Remplacer la méthode `update_day` entière par :

```python
    def update_day(self, zones: list[Zone], bias: Bias,
                   day_high: float | None = None, day_low: float | None = None,
                   struct_levels: list[float] | None = None,
                   va_width: float | None = None) -> None:
        self.zones = zones
        self.bias = bias
        self.day_high = day_high
        self.day_low = day_low
        self.struct_levels = struct_levels or []
        self.va_width = va_width
```

**3c.** Ajouter la méthode helper `_continuation_target` juste avant `evaluate` :

```python
    def _continuation_target(self, entry: float, side: int) -> float | None:
        """Cible swing du breakout : niveau structurel le plus proche AU-DELA de
        l'entree dans le sens du trade ; fallback = mesure de range (entry +
        side*largeur_VA). None si aucun des deux -> pas de plan."""
        beyond = [lv for lv in self.struct_levels if (lv - entry) * side > 0]
        if beyond:
            return min(beyond, key=lambda lv: (lv - entry) * side)
        if self.va_width and self.va_width > 0:
            return entry + side * self.va_width
        return None
```

**3d.** Dans `evaluate`, remplacer la ligne du bloc continuation :

```python
            target = self.day_high if trig.side == 1 else self.day_low
```

par :

```python
            target = self._continuation_target(trig.price, trig.side)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_continuation_target.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the existing confluence/reversal suite (no regression)**

Run: `.venv/Scripts/python.exe -m pytest tests/test_confluence.py tests/test_swing_plan_gen.py -q`
Expected: PASS (le mode reversal et le plan-gen level_rejection sont inchangés ; les appels `update_day` existants utilisent les défauts).

- [ ] **Step 6: Commit**

```bash
git add src/orderflow_bot/strategy/confluence.py tests/test_continuation_target.py
git diff --cached --stat   # EXACTEMENT ces 2 fichiers
git commit -m "feat(orderflow): cible continuation structurelle (niveau-suivant + measured-move) [2b]"
```

---

### Task 3: Câbler `level_breakout` dans `PlanGenerator` + niveaux structurels au rollover

Généralise le flag `_level_rejection` en dispatch de trigger niveau-based, et passe les niveaux structurels candidats à `update_day` au finalize du jour. Bout-en-bout : barre 4h qui casse VAH → plan continuation long ciblant le niveau structurel suivant.

**Files:**
- Modify: `src/orderflow_bot/pipeline.py` (imports, `PlanGenerator.__init__`, `on_trade`, `_finalize_day`)
- Test: `tests/test_continuation_plan_gen.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_continuation_plan_gen.py
from orderflow_bot.config import BotConfig, FeesCfg, RiskCfg, StrategyCfg
from orderflow_bot.models import Trade
from orderflow_bot.pipeline import generate_plans

DAY = 86_400_000
H4 = 240 * 60_000


def _breakout_synth() -> list[Trade]:
    out: list[Trade] = []
    base = 20_000 * DAY
    ts = base
    # jour 1 : profil pyramidal POC=100, value ~97..103
    for p in range(95, 106):
        for _ in range(10 - abs(p - 100)):
            out.append(Trade(ts, float(p), 1.0, ts % 2 == 0))
            ts += 1_000
    # pic mince a 110 -> prev.high=110 = niveau structurel au-dessus de VAH (cible du breakout)
    out.append(Trade(ts, 110.0, 1.0, False)); ts += 1_000
    # jour 2, 1ere fenetre 4h : corps casse AU-DESSUS de VAH (~103) et cloture nettement au-dessus
    d2 = base + DAY
    out.append(Trade(d2 + 1_000, 102.0, 1.0, False))   # open juste sous VAH
    out.append(Trade(d2 + 2_000, 103.0, 1.0, False))
    out.append(Trade(d2 + 3_000, 106.0, 1.0, False))   # cloture de fenetre au-dessus de VAH
    # 1er trade de la fenetre 4h suivante -> flush du bar precedent -> evaluation du trigger
    out.append(Trade(d2 + H4 + 1_000, 106.2, 1.0, False))
    return out


def test_level_breakout_generates_continuation_plan():
    cfg = BotConfig(
        tick_size=0.1, bar_minutes=240,
        fees=FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0),
        strategy=StrategyCfg(trigger="level_breakout", signal_mode="continuation",
                             profile_days=1, npoc_lookback_days=1, zone_margin_pct=0.002,
                             stop_buffer_ticks=5, entry_expire_minutes=600),
        risk=RiskCfg(min_rr=2.0, min_stop_friction_mult=0.0),
    )
    plans = generate_plans(cfg, _breakout_synth())
    assert len(plans) >= 1
    p = plans[0]
    assert p.side == 1                              # cassure au-dessus de VAH -> long
    assert p.meta["trigger"] == "level_breakout"
    assert p.meta["mode"] == "continuation"
    assert p.entry < p.target and p.stop < p.entry  # geometrie continuation coherente
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_continuation_plan_gen.py -v`
Expected: FAIL — aucun plan généré (`trigger="level_breakout"` non câblé, tombe dans la branche footprint qui ne produit rien sur ces ticks).

- [ ] **Step 3: Write the implementation**

Dans `src/orderflow_bot/pipeline.py` :

**3a.** Après l'import `from orderflow_bot.strategy.level_rejection import level_rejection_triggers`, ajouter :

```python
from orderflow_bot.strategy.level_breakout import level_breakout_triggers
```

**3b.** Dans `PlanGenerator.__init__`, remplacer la ligne :

```python
        self._level_rejection = st.trigger == "level_rejection"
```

par :

```python
        # triggers niveau-based (barre resamplee), vs triggers footprint (tick/bar)
        self._level_fn = {
            "level_rejection": level_rejection_triggers,
            "level_breakout": level_breakout_triggers,
        }.get(st.trigger)
```

**3c.** Dans `PlanGenerator.on_trade`, remplacer le bloc :

```python
        bar = self.aggregator.on_trade(t)
        if bar is not None:
            if self._level_rejection:
                trigs += level_rejection_triggers(bar, self.confluence.zones)
            else:
                trigs += self.triggers.on_bar(bar)
        if not self._level_rejection:
            trigs += self.triggers.on_trade(t)
```

par :

```python
        bar = self.aggregator.on_trade(t)
        if bar is not None:
            if self._level_fn is not None:
                trigs += self._level_fn(bar, self.confluence.zones)
            else:
                trigs += self.triggers.on_bar(bar)
        if self._level_fn is None:
            trigs += self.triggers.on_trade(t)
```

**3d.** Dans `PlanGenerator._finalize_day`, remplacer le bloc final (de `prev = self._levels[-1]` jusqu'à l'appel `self.confluence.update_day(...)` inclus) par :

```python
        prev = self._levels[-1]
        npocs = naked_pocs(self._levels)
        zones = build_zones(prev, npocs, lvn_prices, st.zone_margin_pct)
        # niveaux structurels candidats pour la cible continuation (ignores en reversal)
        struct = sorted({*npocs, prev.vah, prev.val, prev.high, prev.low})
        self.confluence.update_day(zones, market_bias(self._levels),
                                   day_high=prev.high, day_low=prev.low,
                                   struct_levels=struct, va_width=prev.vah - prev.val)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_continuation_plan_gen.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Run the level_rejection plan-gen + parallel suites (no regression)**

Run: `.venv/Scripts/python.exe -m pytest tests/test_swing_plan_gen.py tests/test_pipeline_parallel.py -q`
Expected: PASS (le câblage level_rejection et l'équivalence parallèle restent inchangés). *Note : si `tests/test_pipeline_parallel.py` n'existe pas sous ce nom, lancer `.venv/Scripts/python.exe -m pytest -q` complet à la place.*

- [ ] **Step 6: Commit**

```bash
git add src/orderflow_bot/pipeline.py tests/test_continuation_plan_gen.py
git diff --cached --stat   # EXACTEMENT ces 2 fichiers
git commit -m "feat(orderflow): cable trigger level_breakout + niveaux structurels au rollover [2b]"
```

---

### Task 4: Gate 2b — `swing_gate2.py` (noyau drift-contrôlé + diagnostic régime)

Helpers PURS. Réutilise `brut`/`mirror_plan`/`_realized` d'étage 1 (DRY). KILL dur central = `brut_long>0 ∧ brut_short>0` (un edge qui gagne dans les deux sens ne vit pas du drift). Régime = diagnostic non-gating.

**Files:**
- Create: `src/orderflow_bot/backtest/swing_gate2.py`
- Test: `tests/test_swing_gate2.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_swing_gate2.py
import pytest

from orderflow_bot.backtest.swing_gate2 import (
    brut_by_side, gate2, regime_fn_from_closes, regime_split, t_stat,
)
from orderflow_bot.models import ClosedTrade, Fill, OrderPlan


def _ct(r, opened, side=1, mfe=2.0, kind="target") -> ClosedTrade:
    return ClosedTrade(
        plan=OrderPlan(opened, side, 100.0, 99.0, 102.0, {}), qty=1.0,
        fills=[Fill(opened, 100.0, 1.0, "entry"), Fill(opened + 1, 102.0, 1.0, kind)],
        pnl=r, r_multiple=r, opened_ts=opened, closed_ts=opened + 1,
        mfe_r=mfe, mae_r=0.0,
    )


def test_brut_by_side_splits_long_short():
    labels = [_ct(2.0, 1, side=1), _ct(1.0, 2, side=1), _ct(-1.0, 3, side=-1)]
    bl, bs = brut_by_side(labels)
    assert bl == pytest.approx(1.5) and bs == pytest.approx(-1.0)


def test_brut_by_side_excludes_censored():
    labels = [_ct(2.0, 1, side=1), _ct(5.0, 2, side=1, kind="eod")]   # 'eod' = censure
    bl, bs = brut_by_side(labels)
    assert bl == pytest.approx(2.0) and bs == 0.0


def test_t_stat_known_value():
    assert t_stat([_ct(2.0, 1), _ct(-1.0, 2)]) == pytest.approx(1 / 3, abs=1e-3)


def test_t_stat_zero_when_no_variance():
    assert t_stat([_ct(1.0, 1), _ct(1.0, 2)]) == 0.0


def test_regime_fn_from_closes_sign_of_90d_return():
    closes = {0: 100.0, 90: 120.0, 200: 80.0, 290: 60.0}
    fn = regime_fn_from_closes(closes, lookback_days=90)
    DAY = 86_400_000
    assert fn(90 * DAY) == 1       # 120 > 100 (J0)
    assert fn(290 * DAY) == -1     # 60 < 80 (J200)
    assert fn(5 * DAY) == 0        # pas de close a J-85 -> regime inconnu


def test_regime_split_buckets_by_regime():
    DAY = 86_400_000
    labels = [_ct(2.0, 1 * DAY, side=1), _ct(1.0, 2 * DAY, side=-1), _ct(-1.0, 9 * DAY, side=1)]
    reg = regime_split(labels, lambda ts: 1 if ts < 5 * DAY else -1)
    assert reg[1]["n"] == 2 and reg[-1]["n"] == 1
    assert reg[1]["brut"] == pytest.approx(1.5)


def test_gate2_core_greenlight_when_both_sides_positive():
    fade = [_ct(2.0, i, side=1) for i in range(1, 8)] + [_ct(1.5, i, side=-1) for i in range(8, 15)]
    mirror = [_ct(-1.5, i, side=-1) for i in range(1, 15)]
    net = [_ct(1.6, i, side=1) for i in range(1, 8)] + [_ct(1.1, i, side=-1) for i in range(8, 15)]
    v = gate2(fade, mirror, net, lambda ts: 1)
    assert v["brut_long"] > 0 and v["brut_short"] > 0 and v["t"] > 2
    assert v["core_greenlight"] is True


def test_gate2_kills_when_one_side_negative_drift():
    # scenario drift : longs gagnent (vent porteur), shorts perdent -> PAS un edge de niveau
    fade = [_ct(2.0, i, side=1) for i in range(1, 8)] + [_ct(-1.0, i, side=-1) for i in range(8, 15)]
    mirror = [_ct(0.0, i, side=1) for i in range(1, 15)]
    net = [_ct(1.6, i, side=1) for i in range(1, 8)] + [_ct(-1.2, i, side=-1) for i in range(8, 15)]
    v = gate2(fade, mirror, net, lambda ts: 1)
    assert v["brut_short"] < 0
    assert v["core_greenlight"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_swing_gate2.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orderflow_bot.backtest.swing_gate2'`.

- [ ] **Step 3: Write the implementation**

```python
# src/orderflow_bot/backtest/swing_gate2.py
"""Gate 2b du redeploy swing-continuation (cf. spec 2026-06-17-swing-continuation).

Helpers PURS du NOYAU kill-fast, drift-controle. Reutilise brut/_realized/
mirror_plan d'etage 1 (swing_gate). Le brut se mesure sur des labels frais=0 ;
le 'net' se mesure en passant le MEME jeu relabele aux frais reels. DSR/CSCV
(stade full-history post-greenlight) vivent dans scripts/overfit_audit.py, hors
de ce noyau. Le KILL dur central est brut_long>0 ET brut_short>0 : un edge qui
gagne long ET short ne peut pas vivre du drift directionnel."""

import math
from collections.abc import Callable

from orderflow_bot.backtest.swing_gate import _realized, brut
from orderflow_bot.models import ClosedTrade

_DAY_MS = 86_400_000


def brut_by_side(labels: list[ClosedTrade]) -> tuple[float, float]:
    """(brut_long, brut_short) sur les labels realises (censure 'eod' exclue)."""
    real = _realized(labels)
    longs = [c for c in real if c.plan.side == 1]
    shorts = [c for c in real if c.plan.side == -1]
    bl = sum(c.r_multiple for c in longs) / len(longs) if longs else 0.0
    bs = sum(c.r_multiple for c in shorts) / len(shorts) if shorts else 0.0
    return bl, bs


def t_stat(labels: list[ClosedTrade]) -> float:
    """t de Student sur la serie des R par trade (H0 : moyenne = 0)."""
    real = _realized(labels)
    n = len(real)
    if n < 2:
        return 0.0
    rs = [c.r_multiple for c in real]
    mean = sum(rs) / n
    var = sum((r - mean) ** 2 for r in rs) / (n - 1)
    sd = math.sqrt(var)
    if sd == 0.0:
        return 0.0
    return mean / (sd / math.sqrt(n))


def regime_fn_from_closes(
    closes: dict[int, float], lookback_days: int = 90
) -> Callable[[int], int]:
    """Construit regime(opened_ts) -> +1 (retour 90j > 0) / -1 (< 0) / 0 (inconnu).
    `closes` : {epoch_day -> close du jour}. Diagnostic, pas de gating."""
    def regime(ts: int) -> int:
        day = ts // _DAY_MS
        prev = day - lookback_days
        if day not in closes or prev not in closes:
            return 0
        d = closes[day] - closes[prev]
        return 1 if d > 0 else (-1 if d < 0 else 0)
    return regime


def regime_split(
    labels: list[ClosedTrade], regime_of_ts: Callable[[int], int]
) -> dict[int, dict]:
    """Diagnostic NON-gating : brut / brut_long / brut_short / n par regime."""
    real = _realized(labels)
    out: dict[int, dict] = {}
    for reg in (1, -1, 0):
        grp = [c for c in real if regime_of_ts(c.opened_ts) == reg]
        if not grp:
            continue
        bl, bs = brut_by_side(grp)
        out[reg] = {
            "n": len(grp),
            "brut": round(sum(c.r_multiple for c in grp) / len(grp), 4),
            "brut_long": round(bl, 4),
            "brut_short": round(bs, 4),
        }
    return out


def gate2(
    labels: list[ClosedTrade],
    mirror: list[ClosedTrade],
    net_labels: list[ClosedTrade],
    regime_of_ts: Callable[[int], int],
) -> dict:
    """Noyau kill-fast du gate 2b. core_greenlight = brut>0 ET t>2 ET
    brut_long>0 ET brut_short>0 ET net>0 ET brut>brut_miroir. DSR/CSCV
    (full-history) ajoutes en aval par l'orchestrateur si le noyau passe."""
    b = brut(labels)                       # frais=0
    bl, bs = brut_by_side(labels)
    t = t_stat(labels)
    b_mirror = brut(mirror)
    net = brut(net_labels)                 # MEME jeu relabele aux frais reels -> R net moyen
    core = bool(b > 0 and t > 2 and bl > 0 and bs > 0 and net > 0 and b > b_mirror)
    return {
        "n": len(_realized(labels)),
        "brut": round(b, 4),
        "t": round(t, 2),
        "brut_long": round(bl, 4),
        "brut_short": round(bs, 4),
        "brut_mirror": round(b_mirror, 4),
        "net": round(net, 4),
        "regime": regime_split(labels, regime_of_ts),
        "core_greenlight": core,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_swing_gate2.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/backtest/swing_gate2.py tests/test_swing_gate2.py
git diff --cached --stat   # EXACTEMENT ces 2 fichiers
git commit -m "feat(orderflow): gate 2b swing_gate2 (drift-controle both-sides + diagnostic regime) [2b]"
```

---

### Task 5: Config `level_breakout` + `config.continuation.yaml`

Autorise `trigger: level_breakout` dans le schéma StrictModel et crée la config du run continuation (klines + continuation + eod_flat false).

**Files:**
- Modify: `src/orderflow_bot/config.py:53` (Literal `trigger`)
- Create: `config.continuation.yaml`
- Test: `tests/test_config.py` (ajout)

- [ ] **Step 1: Write the failing test**

Ajouter à la fin de `tests/test_config.py` :

```python
def test_trigger_level_breakout_accepted():
    from orderflow_bot.config import StrategyCfg
    st = StrategyCfg(trigger="level_breakout", signal_mode="continuation")
    assert st.trigger == "level_breakout"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py::test_trigger_level_breakout_accepted -v`
Expected: FAIL — pydantic `ValidationError` (`level_breakout` absent du Literal).

- [ ] **Step 3: Write the implementation**

**3a.** Dans `src/orderflow_bot/config.py`, remplacer la ligne 53 :

```python
    trigger: Literal["footprint", "level_rejection"] = "footprint"
```

par :

```python
    trigger: Literal["footprint", "level_rejection", "level_breakout"] = "footprint"
```

**3b.** Créer `config.continuation.yaml` :

```yaml
# config.continuation.yaml — run swing-continuation (etage 2b), gate drift-controle
symbol: BTCUSDT
market: spot
data_format: klines           # adaptateur synthetic-tick 2a (4 ticks/kline)
tick_size: 0.01
bin_size: 1.0
profile_bin_size: 10.0
bar_minutes: 240              # barres 4h pour le declencheur de cassure
eod_flat: false               # holds swing multi-jours (pas de flat EOD)
data_dir: data
journal_path: journal.continuation.jsonl
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
  maker_pct: 0.0001            # plancher maker BTC-spot atteignable
  taker_pct: 0.0005
  slippage_ticks: 2

strategy:
  trigger: level_breakout
  signal_mode: continuation
  entry_mode: stop             # entree sur confirmation : quasi-gratuite au swing
  entry_confirm_frac: 0.0      # la cloture de cassure est la confirmation
  zone_margin_pct: 0.002
  stop_buffer_ticks: 20
  entry_expire_minutes: 240
  profile_days: 5
  npoc_lookback_days: 20

sessions: []                   # pas de filtre de session au swing
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -q`
Expected: PASS (tous, dont le nouveau).

- [ ] **Step 5: Verify the config loads end-to-end**

Run: `.venv/Scripts/python.exe -c "from orderflow_bot.config import load_config; c = load_config('config.continuation.yaml'); print(c.strategy.trigger, c.strategy.signal_mode, c.eod_flat, c.data_format)"`
Expected: `level_breakout continuation False klines`

- [ ] **Step 6: Commit**

```bash
git add src/orderflow_bot/config.py config.continuation.yaml tests/test_config.py
git diff --cached --stat   # EXACTEMENT ces 3 fichiers
git commit -m "feat(orderflow): config level_breakout + config.continuation.yaml [2b]"
```

---

### Task 6: Orchestrateur `scripts/continuation_run.py` (verdict gate 2b noyau)

Glue : lit les klines, génère les plans `level_breakout`/continuation, étiquette à frais=0 (brut), miroir, et frais réels (net) — MÊME jeu de candidats —, vérifie la plomberie, construit la fonction régime depuis les closes journaliers, tranche via `gate2`. Mirroir de `klines_smoke.py` + `swing_smoke.py`. Le run multi-régime réel (download 2021-2023) est l'étape post-build qui produit le vrai verdict 2b.

**Files:**
- Create: `scripts/continuation_run.py`

- [ ] **Step 1: Write the orchestrator**

```python
# scripts/continuation_run.py
"""Gate 2b swing-continuation : lit les klines, genere les plans (cassure de
niveau + continuation), etiquette a frais=0 (brut), miroir et frais reels (net)
sur le MEME jeu de candidats, verifie la plomberie, puis tranche via
backtest.swing_gate2.gate2 (noyau drift-controle + diagnostic regime).
Usage: .venv/Scripts/python.exe -u scripts/continuation_run.py

Verdict pre-enregistre (spec 2026-06-17-swing-continuation, NE PAS rationaliser
apres coup) :
- core_greenlight True  -> noyau passe ; lancer le DSR/CSCV full-history
  (scripts/overfit_audit.py) pour le verdict final.
- core_greenlight False -> KILL ; documenter dans FINDINGS, geler la these swing.
ATTENTION : un run mono-regime / petit echantillon ne PROUVE rien (cf. etage 1).
Le verdict reel exige la slice multi-regime (>= bull + bear)."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orderflow_bot.backtest.plumbing_checks import (
    label_violations, plan_violations, zone_violations,
)
from orderflow_bot.backtest.swing_gate import mirror_plan
from orderflow_bot.backtest.swing_gate2 import gate2, regime_fn_from_closes
from orderflow_bot.config import BotConfig, load_config
from orderflow_bot.ingestion.reader import available_days, read_klines_as_ticks
from orderflow_bot.pipeline import PlanGenerator, simulate_isolated

_DAY_MS = 86_400_000


def _zero_fees(cfg: BotConfig) -> BotConfig:
    d = cfg.model_dump()
    d["fees"] = {"maker_pct": 0.0, "taker_pct": 0.0, "slippage_ticks": 0}
    return BotConfig(**d)


def _collect(cfg: BotConfig):
    """Une passe sequentielle : DailyLevels finalises, plans candidats, et close
    journalier (dernier prix du jour) pour la fonction regime."""
    gen = PlanGenerator(cfg)
    plans = []
    closes: dict[int, float] = {}
    for t in read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol):
        plans.extend(gen.on_trade(t))
        closes[t.ts // _DAY_MS] = t.price
    return gen._levels, plans, closes


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    cfg = load_config("config.continuation.yaml")
    cfg0 = _zero_fees(cfg)                      # brut = frais=0
    days = available_days(cfg.kline_data_dir, cfg.symbol)
    if not days:
        print("FAIL: aucune kline dans", cfg.kline_data_dir, "/", cfg.symbol)
        return 1

    # plans generes a frais=0 (le filtre de friction ne doit pas culler le jeu),
    # puis relabel du MEME jeu a frais=0 (brut), miroir, et frais reels (net).
    levels, plans, closes = _collect(cfg0)

    def ticks():
        return read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol)

    brut_l = simulate_isolated(cfg0, plans, ticks(), eod_flat=False)
    mirror = simulate_isolated(cfg0, [mirror_plan(p) for p in plans], ticks(), eod_flat=False)
    net_l = simulate_isolated(cfg, plans, ticks(), eod_flat=False)

    problems = (zone_violations(levels)
                + plan_violations(plans, cfg.risk.min_rr)
                + label_violations(brut_l))

    verdict = gate2(brut_l, mirror, net_l, regime_fn_from_closes(closes))

    print(f"jours={len(days)} plans={len(plans)} labels={len(brut_l)}")
    if problems:
        print("PLOMBERIE FAIL — violations:")
        for p in problems[:20]:
            print("  -", p)
        return 1
    print("PLOMBERIE PASS")
    print(f"gate 2b (noyau)    : {verdict}")
    print("VERDICT            :",
          "CORE GREENLIGHT (lancer DSR/CSCV full-history)" if verdict["core_greenlight"]
          else "KILL (noyau drift-controle echoue)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Ensure a klines slice is present (réutilise le downloader 2a)**

Si `data/klines/spot/BTCUSDT` est vide, télécharger une petite tranche (preuve de plomberie ; le vrai gate exigera plusieurs années) :

Run: `.venv/Scripts/python.exe scripts/download_klines.py config.continuation.yaml 2022 1 2022 3`
Expected: 3 fichiers mensuels Parquet écrits sous `data/klines/spot/BTCUSDT` (idempotent ; si déjà présents depuis 2a, rien à faire).

- [ ] **Step 3: Run the orchestrator**

Run: `.venv/Scripts/python.exe -u scripts/continuation_run.py`
Expected: une ligne `jours=… plans=… labels=…`, puis `PLOMBERIE PASS`, puis le dict `gate 2b (noyau)` et une ligne `VERDICT`. **Le verdict sur 3 mois mono-régime ne PROUVE rien** (échantillon trop petit/mono-régime) — cette étape prouve seulement que le pipe tourne et que la plomberie est saine.

- [ ] **Step 4: Confirm no data is staged**

```bash
git status --short
```
Expected: `data/` n'apparaît PAS (gitignoré depuis 2a). Seul `scripts/continuation_run.py` est non suivi.

- [ ] **Step 5: Commit**

```bash
git add scripts/continuation_run.py
git diff --cached --stat   # EXACTEMENT ce fichier
git commit -m "feat(orderflow): orchestrateur continuation_run gate 2b noyau [2b]"
```

---

## Après les 6 tâches

1. **Suite complète** : `.venv/Scripts/python.exe -m pytest -q` → tout vert (208 d'étage 2a + ~18 neufs ≈ 226).
2. **Revue finale** (subagent code-reviewer sur tout le diff de branche).
3. **finishing-a-development-branch** : tests → options → merge/PR/keep/discard.
4. **Run réel du gate 2b** (étape post-merge, déclenchée par l'utilisateur) : télécharger une slice multi-régime (≈ 2021 bull + 2022 bear + 2023 reprise) via `download_klines.py`, relancer `continuation_run.py` → lecture kill-fast du noyau. Si `core_greenlight` → full-history + DSR/CSCV (`scripts/overfit_audit.py`) pour le verdict final. Sinon → KILL documenté dans FINDINGS, thèse swing (fade + continuation) gelée.

---

## Self-review (rempli par l'auteur du plan)

**Couverture spec :** §2 trigger → Task 1 ; §2 compat sens → réutilisé (Task 3 wiring) ; §2 cible structurelle → Task 2 ; §3 horizon eod_flat → réutilisé étage 1 (Task 6 l'invoque) ; §4 data klines → réutilisé 2a (Task 6) + staging documenté (Après §4) ; §5 plomberie → réutilisé 2a (Task 6) ; §5 gate noyau (brut/t/both-sides/miroir/net) → Task 4 ; §5 diagnostic régime → Task 4 ; §5 DSR/CSCV → explicitement différés full-history post-greenlight (spec §4 staging) ; §6 frontière code → Tasks 1-6 couvrent neuf + modif ciblée. Aucune exigence de gate-noyau sans tâche.

**Placeholders :** aucun — chaque step a code/commande/sortie attendue concrets.

**Cohérence des types :** `Trigger(ts, side, kind, price)` (confluence.py) cohérent Tasks 1/2/3 ; `level_breakout_triggers(bar, zones)` même signature que `level_rejection_triggers` ; `update_day(..., struct_levels, va_width)` défini Task 2 et appelé Task 3 ; `gate2(labels, mirror, net_labels, regime_of_ts)` défini Task 4 et appelé Task 6 ; `regime_fn_from_closes(closes, lookback_days)` défini Task 4 et appelé Task 6 ; `_zero_fees` répliqué de swing_smoke (pattern établi). `meta["mode"]=="continuation"` posé par ConfluenceEngine (confluence.py:141), asserté Task 3.
