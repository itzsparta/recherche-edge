# FINDINGS — Piste 2 : token unlocks (cliff)

Verdict rendu 2026-06-21, contre la spec **pré-enregistrée** ([`SPEC-unlocks.md`](SPEC-unlocks.md)).
Aucun critère modifié après résultats.

## Verdict : KILL — décisif (≈ zéro, pas marginal)

Shorter un cliff unlock ne rapporte **rien** en market-adjusted. La pression du vendeur
forcé est **anticipée et pricée-in** avant la date connue ; il ne reste rien à capturer.

## Le chiffre qui tue : décompo temporelle du CAR market-adjusted (short = −CAR vs BTC)

| Fenêtre | Short net moyen/token | t (clusteré) |
|---|---|---|
| **pré [−10,−1]** | **+1.28 %** | — |
| event [−1,+1] | +0.43 % | +0.58 |
| **post [+1,+10]** | **−0.22 %** | **−0.16** |

Toute la dérive baissière (vs BTC) arrive **AVANT** l'unlock (+1.28 % pré), quasi rien à
l'event, **zéro/positif après**. Signature manuelle de l'efficience : date publique →
le marché l'anticipe → le mouvement est déjà fait quand l'unlock survient. Le tueur
*priced-in* pré-enregistré s'est réalisé.

## Critères (A) — tous échouent sauf un faible

- **[FAIL] significativité** : post +(-0.22 %)/token, t=−0.16 = **nul**.
- **[FAIL] dose-réponse** : quartiles taille non-monotones (Q1 +1.40, Q2 +3.94, Q3 −2.11,
  Q4 −0.62 %). Les gros unlocks ne shortent pas mieux.
- **[PASS faible] années** : 4/6 positives, mais petit et bruité.
- **[FAIL] drop-top-5 tokens** : t tombe à −1.21 (porté par une poignée, pas robuste).
- **[FAIL] DSR(N=6)** = 0.535.
- **(A) FAIL.**

## Critère (B) — capturable net

- Sous-ensemble shortable (perp Binance, 68 tokens) net de coûts : −0.69 %/token, t=−0.47.
- **(B) FAIL.**

## Données (tout gratuit, vérifié)

24 804 cliff events (DefiLlama CDN ; API emissions principale payante contournée). 10 642
exploitables (prix Binance dispo, ≥2021) sur **78 tokens**. Prix Binance klines (spot/perp),
marché = BTC. Fetch parallèle (108 symboles en 10 s).

## Limites honnêtes (pré-enregistrées)

- **Univers = Binance-listed = large caps = le plus arbitré.** Les small-cap unlocks
  (sweet-spot capacité d'un solo) n'ont pas de prix gratuit (CoinGecko `days=max` passé
  payant 401) → non testés. Un KILL ici ne tue pas formellement le small-cap.
- **MAIS** : la thèse unlock est faible aux deux bouts pour un solo — large-cap = priced-in
  (prouvé ici), small-cap = **non shortable** (pas de perp/borrow) donc gate (B) échoue par
  construction. Le mécanisme priced-in (dates publiques) s'appliquerait aussi aux small-caps.
- Survivorship : 338 protocoles DefiLlama = survivants à schedule documenté.

## Conclusion

Piste 2 (unlocks) close. Le flux forcé est **réel mais pricé-in** sur dates publiques =
pas d'edge récoltable. Capital conservé : pipeline event-study (DefiLlama + Binance,
CAR market-adjusted clusteré, audit DSR) réutilisable pour les autres flux forcés
(rebal indices, roll) si on les attaque. Le sous-pivot rebal/roll a le même risque
priced-in (dates connues) — à pondérer avant d'investir.
