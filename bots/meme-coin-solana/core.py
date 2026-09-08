"""Noyau pur du bot meme-coin : décisions de trading sans aucune dépendance
réseau / solana. Tout est testable hors-ligne (pytest)."""
from dataclasses import dataclass, field


@dataclass
class Strategy:
    stop_loss_percent: float = -50.0          # négatif, ex -50 = -50%
    max_hold_seconds: float = 600.0
    take_profit_steps: list = field(default_factory=list)  # [(percent, sell_ratio), ...]
    # --- modèle d'exécution (frais réalistes Solana) ---
    amm_fee_pct: float = 0.0025               # 0.25% Raydium
    slippage_pct: float = 0.10                # 10% défaut snipe memecoin
    priority_fee_sol: float = 0.0
    jito_tip_sol: float = 0.0
    # --- gestion du risque & sorties avancées ---
    max_open_positions: int = 5
    buy_amount_sol: float = 1.0
    trailing_stop_enabled: bool = True
    trailing_stop_activation_pct: float = 40.0
    trailing_stop_distance_pct: float = 20.0
    breakeven_activation_pct: float = 30.0
    # --- filtres ---
    min_liquidity_usd: float = 0.0
    max_liquidity_usd: float = 1e12
    min_ratio_liq_fdv: float = 0.0
    max_ratio_liq_fdv: float = 100.0
    min_volume_24h: float = 0.0
    min_fdv_usd: float = 5000.0
    max_fdv_usd: float = 60000.0
    
    # --- breadth (pre-graduation selection) ---
    min_uniq_buyers: int = 0
    max_curve_span_sec: float = 999999.0
    min_buy_sell_ratio: float = 0.0
    # --- sécurité ---
    check_rug: bool = True
    max_rug_score: int = 500
    allow_mint_authority: bool = False
    allow_freeze_authority: bool = False
    max_dev_allocation_pct: float = 15.0
    require_socials: bool = True
    # --- ciblage ---
    keywords: list = field(default_factory=list)
    trade_mode: str = "SNIPE"
    execution_type: str = "MARKET"

    @classmethod
    def from_dict(cls, cfg):
        """Construit une Strategy depuis strategy.json (source unique, anti-drift).
        Blocs/clés manquants -> défauts du dataclass."""
        d = cls()  # instance défaut pour récupérer chaque défaut
        tr = cfg.get("trading", {})
        fi = cfg.get("filters", {})
        se = cfg.get("security", {})
        ex = cfg.get("execution", {})
        ta = cfg.get("targeting", {})
        steps = [(float(s["percent"]), float(s["sell_ratio"]))
                 for s in tr.get("take_profit_steps", [])]
        return cls(
            stop_loss_percent=tr.get("stop_loss_percent", d.stop_loss_percent),
            max_hold_seconds=tr.get("max_hold_seconds", d.max_hold_seconds),
            take_profit_steps=steps,
            buy_amount_sol=tr.get("buy_amount_sol", d.buy_amount_sol),
            max_open_positions=tr.get("max_open_positions", d.max_open_positions),
            trailing_stop_enabled=tr.get("trailing_stop_enabled", d.trailing_stop_enabled),
            trailing_stop_activation_pct=float(tr.get("trailing_stop_activation_pct", d.trailing_stop_activation_pct)),
            trailing_stop_distance_pct=float(tr.get("trailing_stop_distance_pct", d.trailing_stop_distance_pct)),
            breakeven_activation_pct=float(tr.get("breakeven_activation_pct", d.breakeven_activation_pct)),
            amm_fee_pct=ex.get("amm_fee_pct", d.amm_fee_pct),
            slippage_pct=ex.get("slippage_pct", d.slippage_pct),
            priority_fee_sol=ex.get("priority_fee_sol", d.priority_fee_sol),
            jito_tip_sol=ex.get("jito_tip_sol", d.jito_tip_sol),
            min_liquidity_usd=float(fi.get("min_liquidity_usd", d.min_liquidity_usd)),
            max_liquidity_usd=float(fi.get("max_liquidity_usd", d.max_liquidity_usd)),
            min_ratio_liq_fdv=float(fi.get("min_ratio_liq_fdv", d.min_ratio_liq_fdv)),
            max_ratio_liq_fdv=float(fi.get("max_ratio_liq_fdv", d.max_ratio_liq_fdv)),
            min_volume_24h=float(fi.get("min_volume_24h", d.min_volume_24h)),
            min_fdv_usd=float(fi.get("min_fdv_usd", d.min_fdv_usd)),
            max_fdv_usd=float(fi.get("max_fdv_usd", d.max_fdv_usd)),
            min_uniq_buyers=int(fi.get("min_uniq_buyers", d.min_uniq_buyers)),
            max_curve_span_sec=float(fi.get("max_curve_span_sec", d.max_curve_span_sec)),
            min_buy_sell_ratio=float(fi.get("min_buy_sell_ratio", d.min_buy_sell_ratio)),
            check_rug=se.get("check_rug", d.check_rug),
            max_rug_score=se.get("max_rug_score", d.max_rug_score),
            allow_mint_authority=se.get("allow_mint_authority", d.allow_mint_authority),
            allow_freeze_authority=se.get("allow_freeze_authority", d.allow_freeze_authority),
            max_dev_allocation_pct=float(se.get("max_dev_allocation_pct", d.max_dev_allocation_pct)),
            require_socials=se.get("require_socials", d.require_socials),
            keywords=ta.get("keywords", d.keywords),
            trade_mode=ta.get("trade_mode", d.trade_mode),
            execution_type=ex.get("execution_type", d.execution_type),
        )


# quote tokens acceptés (paire adossée au SOL)
SOL_QUOTES = {"SOL", "WSOL"}

# mints des quotes connus (pour isoler le mint "base" d'une nouvelle pool)
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
QUOTE_MINTS = {WSOL, USDC, USDT}


def select_base_mint(mints):
    """Depuis les mints d'une pool, isole l'unique mint non-quote (le token visé).
    None si zéro ou plusieurs candidats (ambigu = on s'abstient).
    Remplace l'index codé en dur keys[8]."""
    bases = [m for m in mints if m not in QUOTE_MINTS]
    if len(bases) != 1:
        return None
    return bases[0]


@dataclass
class Fill:
    tokens: float
    cost_basis_sol: float       # SOL total sorti (frais inclus)
    price_per_token: float      # cost_basis_sol / tokens (prix de revient)
    entry_price: float = 0.0    # prix marché à l'entrée (hors frais)


def simulate_buy(amount_sol, entry_price, strat, pool_reserve_sol=None):
    """Achat réaliste : AMM + slippage dynamique (produit constant) rognent les tokens reçus,
    priority fee + tip Jito s'ajoutent au coût."""
    if pool_reserve_sol and pool_reserve_sol > 0:
        slippage = amount_sol / (pool_reserve_sol + amount_sol)
    else:
        slippage = strat.slippage_pct
        
    effective_sol = amount_sol * (1 - strat.amm_fee_pct) * (1 - slippage)
    tokens = effective_sol / entry_price
    cost_basis = amount_sol + strat.priority_fee_sol + strat.jito_tip_sol
    return Fill(tokens=tokens, cost_basis_sol=cost_basis,
                price_per_token=cost_basis / tokens, entry_price=entry_price)


def simulate_sell(tokens, exit_price, strat, pool_reserve_sol=None):
    """Vente réaliste : AMM + slippage dynamique rognent le produit,
    priority fee + tip retranchés. Retourne le net SOL."""
    gross_est = tokens * exit_price
    if pool_reserve_sol and pool_reserve_sol > 0:
        slippage = gross_est / (pool_reserve_sol + gross_est)
    else:
        slippage = strat.slippage_pct
        
    gross = gross_est * (1 - strat.amm_fee_pct) * (1 - slippage)
    return gross - strat.priority_fee_sol - strat.jito_tip_sol


DUST_TOKENS = 1e-9   # en dessous = position considérée fermée


@dataclass
class Position:
    mint: str
    name: str
    tokens: float
    cost_basis_sol: float       # coût restant alloué aux tokens restants
    price_per_token: float      # prix de revient (cost/token, frais inclus)
    buy_timestamp: float
    entry_market_price: float = 0.0   # prix marché d'entrée (base du pct_gain)
    steps_reached: list = field(default_factory=list)
    highest_price: float = 0.0
    highest_pct_gain: float = 0.0


class Portfolio:
    """État du portefeuille simulé : solde cash + positions + PnL réalisé.
    Toute la compta passe par ici (fini les calculs ad-hoc dans le scanner)."""

    def __init__(self, balance_sol):
        self.balance_sol = balance_sol
        self.realized_pnl_sol = 0.0
        self.positions = {}

    @property
    def n_open(self):
        return len(self.positions)

    def has(self, mint):
        return mint in self.positions

    def open(self, mint, name, fill, buy_timestamp):
        self.balance_sol -= fill.cost_basis_sol
        self.positions[mint] = Position(
            mint=mint, name=name, tokens=fill.tokens,
            cost_basis_sol=fill.cost_basis_sol,
            price_per_token=fill.price_per_token,
            buy_timestamp=buy_timestamp,
            entry_market_price=fill.entry_price,
            highest_price=fill.entry_price,
            highest_pct_gain=0.0)

    def sell(self, mint, fraction, proceeds_sol):
        """Vend `fraction` (0..1) des tokens restants au produit net `proceeds_sol`.
        Crédite le solde, alloue le coût au prorata pour le PnL réalisé.
        Ferme la position si tout vendu. Retourne False si mint inconnu."""
        pos = self.positions.get(mint)
        if pos is None:
            return False
        cost_alloc = pos.cost_basis_sol * fraction
        self.balance_sol += proceeds_sol
        self.realized_pnl_sol += proceeds_sol - cost_alloc
        pos.tokens *= (1 - fraction)
        pos.cost_basis_sol *= (1 - fraction)
        if fraction >= 1.0 or pos.tokens <= DUST_TOKENS:
            del self.positions[mint]
        return True

    def save_state(self, filepath: str):
        """Sauvegarde l'état actuel du portfolio dans un fichier JSON."""
        import json
        state = {
            "balance_sol": self.balance_sol,
            "realized_pnl_sol": self.realized_pnl_sol,
            "positions": {}
        }
        for mint, pos in self.positions.items():
            state["positions"][mint] = {
                "mint": pos.mint,
                "name": pos.name,
                "tokens": pos.tokens,
                "cost_basis_sol": pos.cost_basis_sol,
                "price_per_token": pos.price_per_token,
                "buy_timestamp": pos.buy_timestamp,
                "entry_market_price": pos.entry_market_price,
                "steps_reached": pos.steps_reached,
                "highest_price": pos.highest_price,
                "highest_pct_gain": pos.highest_pct_gain,
            }
        
        # Ecriture atomique pour eviter la corruption
        temp_path = filepath + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            import os
            os.replace(temp_path, filepath)
        except Exception:
            pass

    @classmethod
    def load_state(cls, filepath: str) -> "Portfolio":
        """Charge l'état d'un portfolio depuis un fichier JSON."""
        import json
        import os
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            p = cls(balance_sol=state.get("balance_sol", 0.0))
            p.realized_pnl_sol = state.get("realized_pnl_sol", 0.0)
            
            for mint, pos_dict in state.get("positions", {}).items():
                pos = Position(
                    mint=pos_dict["mint"],
                    name=pos_dict["name"],
                    tokens=pos_dict["tokens"],
                    cost_basis_sol=pos_dict["cost_basis_sol"],
                    price_per_token=pos_dict["price_per_token"],
                    buy_timestamp=pos_dict["buy_timestamp"],
                    entry_market_price=pos_dict.get("entry_market_price", 0.0),
                    steps_reached=pos_dict.get("steps_reached", []),
                    highest_price=pos_dict.get("highest_price", 0.0),
                    highest_pct_gain=pos_dict.get("highest_pct_gain", 0.0)
                )
                p.positions[mint] = pos
            return p
        except Exception:
            return None


def can_open(n_open, balance_sol, strat):
    """Cap positions concurrentes + garde solde (empêche solde négatif)."""
    if n_open >= strat.max_open_positions:
        return False
    needed = strat.buy_amount_sol + strat.priority_fee_sol + strat.jito_tip_sol
    return balance_sol >= needed


def passes_filters(ep, strat):
    """Filtres marché et sélection pre-graduation."""
    fdv_usd = ep.get("fdv_usd", 0.0)
    liq_usd = ep.get("liq_usd", 0.0)
    vol24_usd = ep.get("vol24_usd", 0.0)
    
    if fdv_usd <= 0:
        return False
    if not (strat.min_fdv_usd <= fdv_usd <= strat.max_fdv_usd):
        return False
    ratio = (liq_usd / fdv_usd) * 100
    if not (strat.min_ratio_liq_fdv <= ratio <= strat.max_ratio_liq_fdv):
        return False
    if not (strat.min_liquidity_usd <= liq_usd <= strat.max_liquidity_usd):
        return False
    if vol24_usd < strat.min_volume_24h:
        return False
        
    # Nouveaux filtres de breadth (optionnels dans strat)
    if hasattr(strat, "min_buy_sell_ratio"):
        bs_ratio = ep.get("buy_sell_ratio", 0.0)
        if bs_ratio < strat.min_buy_sell_ratio:
            return False
            
    if hasattr(strat, "min_uniq_buyers"):
        uniq_buyers = ep.get("n_uniq_buyers", 0)
        if uniq_buyers < strat.min_uniq_buyers:
            return False
            
    if hasattr(strat, "max_curve_span_sec"):
        span_sec = ep.get("curve_span_sec", 999999)
        if span_sec > strat.max_curve_span_sec:
            return False
            
    return True


def security_ok(score, risks, strat):
    """Gate sécurité RugCheck. Désactivable via check_rug."""
    if not strat.check_rug:
        return True
    if score > strat.max_rug_score:
        return False
    if not strat.allow_mint_authority and "Mint Authority" in risks:
        return False
    if not strat.allow_freeze_authority and "Freeze Authority" in risks:
        return False
    return True


def match_keyword(name, keywords):
    """Retourne le mot-clé (sous-chaîne, insensible à la casse) trouvé dans `name`.
    "" si aucun mot-clé non-vide (filtre désactivé = on passe).
    None si des mots-clés existent mais aucun ne matche (= rejet).
    Évite le bug keywords:[""] qui matchait tous les tokens."""
    real = [k for k in keywords if k and k.strip()]
    if not real:
        return ""
    upper = name.upper()
    for kw in real:
        if kw.upper() in upper:
            return kw
    return None


# venues memecoin acceptées côté DexScreener (dexId). Inclut pump.fun & dérivés.
DEXSCREENER_VENUES = frozenset({"raydium", "pumpfun", "pumpswap", "meteora"})


def pick_pair(pairs, venues=DEXSCREENER_VENUES):
    """Choisit la paire (venue memecoin) adossée au SOL la plus liquide.
    Remplace le pairs[0] aveugle. None si aucune valide."""
    candidates = [
        p for p in pairs
        if p.get("dexId") in venues
        and p.get("quoteToken", {}).get("symbol", "").upper() in SOL_QUOTES
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.get("liquidity", {}).get("usd", 0))


@dataclass
class ExitDecision:
    action: str                 # HOLD | SELL_ALL | SELL_PARTIAL
    reason: str                 # HOLD | STOP_LOSS | TIME_STOP | TAKE_PROFIT
    sell_ratio: float = 0.0
    step_percent: float = None


def decide_exit(pct_gain, held_seconds, steps_reached, strat, highest_pct_gain=None):
    """Une décision par appel. Priorité : SL > TRAILING_STOP > BREAKEVEN > TIME > TP > HOLD."""
    # 1. Stop-Loss fixe standard
    if pct_gain <= strat.stop_loss_percent:
        return ExitDecision("SELL_ALL", "STOP_LOSS")

    # 2. Trailing Stop et Breakeven
    peak = pct_gain if highest_pct_gain is None else max(highest_pct_gain, pct_gain)
    if getattr(strat, "trailing_stop_enabled", True):
        # Trailing stop : si le sommet a atteint au moins le seuil d'activation
        if peak >= getattr(strat, "trailing_stop_activation_pct", 40.0):
            distance = getattr(strat, "trailing_stop_distance_pct", 20.0)
            if pct_gain <= (peak - distance):
                return ExitDecision("SELL_ALL", "TRAILING_STOP")

        # Breakeven stop : si le token a dépassé le seuil breakeven et retombe à 0 ou négatif
        if peak >= getattr(strat, "breakeven_activation_pct", 30.0):
            if pct_gain <= 0.0:
                return ExitDecision("SELL_ALL", "BREAKEVEN_STOP")

    # 3. Time-Stop
    if held_seconds >= strat.max_hold_seconds:
        return ExitDecision("SELL_ALL", "TIME_STOP")

    # 4. Take-Profit par paliers
    for percent, sell_ratio in sorted(strat.take_profit_steps):
        if percent not in steps_reached and pct_gain >= percent:
            return ExitDecision("SELL_PARTIAL", "TAKE_PROFIT",
                                sell_ratio=sell_ratio, step_percent=percent)
    return ExitDecision("HOLD", "HOLD")
