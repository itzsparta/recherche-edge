# Research roadmap V2 — l'axe non-testé : assurance, calendrier, relative-value

> Suite de [`RESEARCH-ROADMAP.md`](RESEARCH-ROADMAP.md). La V1 (3 pistes structurelles)
> a rendu 3 KILL propres. Ce document ouvre l'axe qu'elle **n'a jamais touché**.

## Ce que la V1 a prouvé (et ce qu'elle n'a pas testé)

Les 3 pistes V1 partagent un motif unifié : **tout edge à déclencheur ou prix PUBLIC est
mangé** — signal trend (premium compressé), date d'unlock (priced-in), quote cross-venue
(arbitrée jusqu'au top-of-book vide). Conclusion solide : un solo sans latence/infra **ne
récolte pas d'edge prédictif sur l'info publique**.

Mais les 3 pistes V1 cherchaient toutes le **même type d'edge** : *deviner une direction de
prix*. Trend = direction. Unlock = direction (short). Niche = direction (capter un spread
directionnel). Une catégorie entière est restée **non testée** :

> **L'edge qui n'est ni prédictif ni un arbitrage de prix public — la prime d'ASSURANCE.**
> On n'essaie pas de deviner le prix. On se fait **payer pour porter un risque que d'autres
> veulent fuir**. Le vendeur d'assurance ne prédit rien ; il encaisse une prime et absorbe
> le sinistre. Cette prime persiste *parce que* le risque est réel — la publier ne la tue pas.

C'est exactement le « risque rémunéré » que la piste 1 effleurait (trend = crisis-alpha),
mais la piste 1 testait le **timing** du trend, pas la **vente d'assurance** elle-même.

## Le reframe V2 — 3 axes neufs

1. **Convexité / assurance** (piste 4, VRP) — se faire payer pour vendre de la protection.
   Dimension entièrement neuve : la V1 n'a jamais touché les options / la vol.
2. **Calendrier de contrainte** (piste 5) — prime concentrée sur des fenêtres
   institutionnelles fixes (pré-FOMC, overnight). Cousin du flux forcé, mais c'est une
   prime de risque d'annonce, pas un flux à front-runner.
3. **Structure relative-value** (piste 7, transverse) — pas une source d'edge : le
   **correctif méthodo** qui annule le drift de régime ayant tué 2 runs swing (étage 1 :
   miroir +0.27R = drift pur, both_halves False). À appliquer à toute piste directionnelle.

Pistes classées par espérance pour ce profil (solo, capital modeste, fort build/data,
zéro edge latence).

---

## Piste 4 — Volatility Risk Premium (convexité / assurance) ★ top EV

**Thèse.** La vol implicite est **structurellement > vol réalisée** (VIX² > variance
réalisée). Vendre de la variance/vol = vendre de l'assurance → prime positive moyenne.
Récolter cette prime de façon systématique, basse fréquence.

**Pourquoi ça persiste.** Ce n'est **pas une inefficience d'information** — c'est le prix
d'une assurance. Les gens **surpaient** la protection contre les krachs (aversion au risque,
hedging mandaté, demande de puts). Bollerslev-Tauchen-Zhou, Carr-Wu : VRP robustement négatif
(realized < implied) sur des décennies. Le publier ne le tue pas, car il **paie pour porter
le risque de queue** que le marché fuit. Échappe au motif V1 : l'info (VIX) est publique,
mais l'edge n'est pas dans l'info — il est dans le **transfert de risque**.

**Pourquoi toi.** Dimension neuve (zéro option dans la V1). Data **gratuite** (`^VIX` +
`^GSPC` via yfinance, historique 1990+). Pas de latence requise (mensuel). Et la leçon
multi-régime s'applique pile : un test VRP honnête **exige** d'inclure 2008 / Feb-2018
(Volmageddon) / Mar-2020 — là où le short-vol explose.

**Tueur probable.** **Pas « no-edge »** (la prime est réelle et bien documentée) — mais
**« ramasser des pièces devant un rouleau compresseur »** : la prime *est* la juste
compensation d'un risque de queue catastrophique. Skew très négatif, kurtosis énorme. Le
vrai risque = net du tail, le Sharpe ne bat pas un simple SPY buy-hold, et un solo **ne peut
pas porter le moment** (Feb-2018 : -vol ETN wipeout en une séance). → Critère de kill =
*bat le passif en risk-adjusted TAIL-INCLUS*, pas *Sharpe brut > 0*. Verdict honnête le plus
probable = **DOWNGRADE** (prime réelle mais non-portable solo).

**Pré-test cheap.** Phase 0 = mesurer le premium (`VIX²` vs variance réalisée forward 21j,
mensuel non-chevauchant, par régime). Phase 1 = rendement net d'un short-variance synthétique,
Sharpe vs SPY tail-inclus. Spec pré-enregistrée → [`vol-risk-premium/docs/SPEC.md`](vol-risk-premium/docs/SPEC.md).

**Statut : DOWNGRADE (2026-06-22).** Premium **réel** (mean VRP_var t=4.03 sur 436 mois,
DSR 0.977, 4/6 régimes — négatif seulement dans les krachs GFC/COVID = signature d'assurance)
mais **non récoltable solo** : la forme tradable (SVXY) fait **−95.2 % de drawdown**, pire jour
−83 % (Volmageddon 6 fév 2018, VIX +116 % en une séance) vs SPY −33.7 %. Le Sharpe net 1.86 /
t=11.19 = **mirage** (Sharpe aveugle au skew −3.30/kurt 24.9 ; l'échantillon mensuel lisse le
krach intramois). Faux GO du runner naïf **attrapé** par durcissement du gate tail (σ-normalisé
→ drawdown absolu quotidien). (A)∧¬(B). Détail : [`vol-risk-premium/docs/FINDINGS.md`](vol-risk-premium/docs/FINDINGS.md).

---

## Piste 5 — Calendrier de contrainte (pré-FOMC, overnight) ★ bon EV, kill très cheap

**Thèse.** Le rendement actions n'est pas uniforme dans le temps : il se concentre sur des
fenêtres institutionnelles fixes. (a) **Pré-FOMC drift** : Lucca-Moench 2015 (J. Finance) —
une fraction majeure de l'equity premium réalisée dans les **24 h avant** l'annonce FOMC.
(b) **Overnight** : Lou-Polk-Skouras (JFE) — close→open porte le rendement, open→close
plat/négatif.

**Pourquoi ça persiste.** Prime de **résolution d'incertitude** (pré-FOMC) et de **portage
du risque overnight** (illiquidité nocturne, gap risk). Structurel, pas une inefficience à
arbitrer : on est payé pour détenir l'actif au moment précis où le risque est le plus
inconfortable.

**Pourquoi toi.** Data **triviale** (SPY daily + calendrier FOMC public ; close/open pour
overnight). Test ultra-cheap → quelques heures pour un verdict propre, peu importe le signe.
Gros ratio EV/effort pour le **portfolio de kills** même si négatif.

**Tueur probable.** **Priced-in** (cousin du verdict unlocks) : la fenêtre est publique,
l'effet peut s'être érodé / déplacé depuis publication (2015). Coûts + slippage sur une
fenêtre courte. Effet overnight = peut-être non-capturable net (spread open/close, frais
quotidiens). → Tester si un résidu **net** survit *post-publication* et *post-coûts*.

**Pré-test cheap.** Event-study rendement [-1j, +1j] autour des dates FOMC ; décompo
overnight/intraday sur SPY. Données : SPY/^GSPC OHLC + dates FOMC (Fed publique).

**Statut : 5a overnight = DOWNGRADE (2026-06-22).** Effet **réel et robuste** (overnight porte
+10 à +14 %/an, t>5, sur SPY/QQQ/IWM ; intraday ~nul) mais **non capturable net** : 252 cycles/an
× 5 bps = 12.6 %/an de coût > la prime → net −2.5 %, Sharpe −0.23 vs SPY buy-hold 0.65. Brut, le
Sharpe overnight (0.95) bat le buy-hold — c'est le coût du turnover quotidien qui tue. Verdict
cost-driven (breakeven ≈1.3 bps, bord optimiste retail). Détail : [`calendar-premium/docs/FINDINGS-overnight.md`](calendar-premium/docs/FINDINGS-overnight.md).

**5b pré-FOMC = KILL priced-in (2026-06-22).** Drift FOMC **réel et fort 1994-2014** (+31 bps/event
sur le jour du statement, t=3.34) mais **effondré à la publication** Lucca-Moench : 2015→ = +2.3 bps,
t=0.20 (magnitude −93 %, pas un souci de puissance). Coût non en cause (8 events/an) — c'est la
**diffusion de l'info** qui tue, comme les unlocks (piste 2). McLean-Pontiff en direct. Calendrier
FOMC 262 annonces (CSV 1994-2018 + Fed vérifiée 2019-2026). Détail :
[`calendar-premium/docs/FINDINGS-fomc.md`](calendar-premium/docs/FINDINGS-fomc.md).

**Bilan piste 5** : prime de calendrier morte aux deux bouts — overnight réelle mais mangée par le
turnover (DOWNGRADE), pré-FOMC réelle mais priced-in post-publication (KILL).

---

## Piste 6 — Carry (FX / commodités / crypto-funding) — EV moyen

**Thèse.** Porter l'actif à rendement de portage positif, financer celui à portage négatif.
Crypto-funding cash-and-carry : la demande de levier long paie un funding au porteur de la
jambe spot/short-perp.

**Pourquoi ça persiste.** Risque rémunéré (carry crash, dévaluation) + demande structurelle
de levier (crypto). Différent *kind* de tout ce qui précède : **porter, pas timer**.

**Pourquoi toi.** Pipes Binance/Dune déjà construites (meme-coin). Funding = data gratuite.

**Tueur probable.** Yield **compressé** (cash-and-carry crypto arbitré, ~basis fin), crowdé,
risque exchange (cf. niche). Capacité $ réelle à mesurer avant d'écrire une ligne.

**Statut : non démarré.**

---

## Piste 7 (transverse) — Relative-value / market-neutral : le correctif au drift

**Pas une source d'edge — une STRUCTURE.** Toutes les pistes single-instrument
directionnelles V1 ont mangé le **drift de régime** : étage-1 swing, miroir +0.27R = drift
pur (BTC -29.6 %), `both_halves=False` ; le total flatteur venait du marché qui montait/baissait,
pas du signal. Une construction **market-neutral** (pairs cointégrées, momentum
cross-sectionnel long/short, dollar-neutral) **annule le drift par construction** : le P&L
ne peut pas venir d'une dérive directionnelle commune.

À **appliquer à toute piste future** où le confound drift est plausible. Ce n'est pas un
test à lancer seul ; c'est la forme qu'on donne aux autres pistes pour qu'un GO soit crédible.

---

## Reco

Ordre EV : **piste 4 (VRP)** → **piste 5 (calendrier, kill le plus cheap)** → piste 6, avec
la **structure piste 7** appliquée dès qu'une piste redevient directionnelle.

Piste 4 d'abord : dimension entièrement neuve + prime la mieux documentée qui existe. Même
le verdict probable (DOWNGRADE « prime réelle mais non-portable ») est un **6e kill propre,
pré-enregistré** — le vrai capital du programme reste le pipeline, pas le P&L.

> **Piste 4 rendue (2026-06-22) : DOWNGRADE — exactement le verdict anticipé.** Le pipeline a
> converti un Sharpe 1.86 (que la plupart auraient tradé) en kill motivé, en attrapant son propre
> faux GO. Prochaine : **piste 5 (calendrier)**, kill le plus cheap.

## Protocole partagé

Inchangé — voir [`RESEARCH-ROADMAP.md` § Protocole partagé](RESEARCH-ROADMAP.md). Tout
pré-test franchit : pré-enregistrement, multi-régime obligatoire, net de frais, audit
anti-overfit (DSR/PBO) dès J1, miroir/drop-one, kill franc.
