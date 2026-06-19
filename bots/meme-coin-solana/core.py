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
    # --- gestion du risque ---
    max_open_positions: int = 5
    buy_amount_sol: float = 1.0
    # --- filtres ---
    min_liquidity_usd: float = 0.0
    max_liquidity_usd: float = 1e12
    min_ratio_liq_fdv: float = 0.0
    max_ratio_liq_fdv: float = 100.0
    min_volume_24h: float = 0.0
    # bande FDV/mcap : pertinente sur bonding curve pump.fun (acheter pré-graduation).
    # Remplace le ratio liq/fdv (mort sur courbe de bonding). Large par défaut.
    min_fdv_usd: float = 0.0
    max_fdv_usd: float = 1e12
    # --- sécurité ---
    check_rug: bool = True
    max_rug_score: int = 500
    allow_mint_authority: bool = False
    allow_freeze_authority: bool = False
    # --- ciblage ---
    keywords: list = field(default_factory=list)

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
            amm_fee_pct=ex.get("amm_fee_pct", d.amm_fee_pct),
            slippage_pct=ex.get("slippage_pct", d.slippage_pct),
            priority_fee_sol=ex.get("priority_fee_sol", d.priority_fee_sol),
            jito_tip_sol=ex.get("jito_tip_sol", d.jito_tip_sol),
            min_liquidity_usd=fi.get("min_liquidity_usd", d.min_liquidity_usd),
            max_liquidity_usd=fi.get("max_liquidity_usd", d.max_liquidity_usd),
            min_ratio_liq_fdv=fi.get("min_ratio_liq_fdv", d.min_ratio_liq_fdv),
            max_ratio_liq_fdv=fi.get("max_ratio_liq_fdv", d.max_ratio_liq_fdv),
            min_volume_24h=fi.get("min_volume_24h", d.min_volume_24h),
            min_fdv_usd=fi.get("min_fdv_usd", d.min_fdv_usd),
            max_fdv_usd=fi.get("max_fdv_usd", d.max_fdv_usd),
            check_rug=se.get("check_rug", d.check_rug),
            max_rug_score=se.get("max_rug_score", d.max_rug_score),
            allow_mint_authority=se.get("allow_mint_authority", d.allow_mint_authority),
            allow_freeze_authority=se.get("allow_freeze_authority", d.allow_freeze_authority),
            keywords=ta.get("keywords", d.keywords),
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


def simulate_buy(amount_sol, entry_price, strat):
    """Achat réaliste : AMM + slippage rognent les tokens reçus,
    priority fee + tip Jito s'ajoutent au coût."""
    effective_sol = amount_sol * (1 - strat.amm_fee_pct) * (1 - strat.slippage_pct)
    tokens = effective_sol / entry_price
    cost_basis = amount_sol + strat.priority_fee_sol + strat.jito_tip_sol
    return Fill(tokens=tokens, cost_basis_sol=cost_basis,
                price_per_token=cost_basis / tokens, entry_price=entry_price)


def simulate_sell(tokens, exit_price, strat):
    """Vente réaliste : AMM + slippage rognent le produit,
    priority fee + tip retranchés. Retourne le net SOL."""
    gross = tokens * exit_price * (1 - strat.amm_fee_pct) * (1 - strat.slippage_pct)
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
            entry_market_price=fill.entry_price)

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


def can_open(n_open, balance_sol, strat):
    """Cap positions concurrentes + garde solde (empêche solde négatif)."""
    if n_open >= strat.max_open_positions:
        return False
    needed = strat.buy_amount_sol + strat.priority_fee_sol + strat.jito_tip_sol
    return balance_sol >= needed


def passes_filters(liq_usd, fdv_usd, vol24_usd, strat):
    """Filtres marché. fdv==0 rejeté (token sans cap = donnée invalide)."""
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


def decide_exit(pct_gain, held_seconds, steps_reached, strat):
    """Une décision par appel. Priorité : SL > TIME > TP > HOLD."""
    if pct_gain <= strat.stop_loss_percent:
        return ExitDecision("SELL_ALL", "STOP_LOSS")
    if held_seconds >= strat.max_hold_seconds:
        return ExitDecision("SELL_ALL", "TIME_STOP")
    for percent, sell_ratio in sorted(strat.take_profit_steps):
        if percent not in steps_reached and pct_gain >= percent:
            return ExitDecision("SELL_PARTIAL", "TAKE_PROFIT",
                                sell_ratio=sell_ratio, step_percent=percent)
    return ExitDecision("HOLD", "HOLD")
