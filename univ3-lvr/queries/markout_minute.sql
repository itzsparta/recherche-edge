-- Piste 15 — LVR par markout (mesure FIXE, pré-enregistrée docs/SPEC.md)
-- Flux signé par minute × rendement forward = perte structurelle du LP (LVR),
-- concentration-correcte (prix d'exécution réels, nette arbs vs noise traders).
-- Multi-horizon 1/5/15/60 min = test de robustesse pré-enregistré (sensibilité = KILL prudent).
-- Paramètres à substituer par pool : {POOL_ADDRESS}, {BASE_SYMBOL}, {FEE_TIER}.
-- Exécuté sur Dune engine 'free' (medium/large non supportés sur dex.trades pour ce plan).
WITH sw AS (
  SELECT
    date_trunc('minute', block_time) AS mn,
    amount_usd AS size_usd,
    CASE WHEN token_bought_symbol = '{BASE_SYMBOL}'
         THEN token_sold_amount / token_bought_amount
         ELSE token_bought_amount / token_sold_amount END AS p_exec,
    CASE WHEN token_bought_symbol = '{BASE_SYMBOL}' THEN 1 ELSE -1 END AS dir
  FROM dex.trades
  WHERE blockchain = 'ethereum' AND project = 'uniswap'
    AND project_contract_address = {POOL_ADDRESS}
    AND block_month >= date '2024-01-01' AND block_month < date '2025-01-01'
    AND amount_usd > 0 AND token_bought_amount > 0 AND token_sold_amount > 0
),
m AS (
  SELECT mn,
    sum(size_usd * p_exec) / sum(size_usd) AS vwap,
    sum(size_usd * dir) AS signed_vol,
    sum(size_usd) AS vol
  FROM sw GROUP BY mn
)
SELECT
  sum(m.vol) AS volume_usd,
  sum(m.vol) * {FEE_TIER} AS fees_usd,
  sum(m.signed_vol * (r1.vwap  - m.vwap) / m.vwap) AS lvr_1m,
  sum(m.signed_vol * (r5.vwap  - m.vwap) / m.vwap) AS lvr_5m,
  sum(m.signed_vol * (r15.vwap - m.vwap) / m.vwap) AS lvr_15m,
  sum(m.signed_vol * (r60.vwap - m.vwap) / m.vwap) AS lvr_60m
FROM m
LEFT JOIN m r1  ON r1.mn  = m.mn + interval '1' minute
LEFT JOIN m r5  ON r5.mn  = m.mn + interval '5' minute
LEFT JOIN m r15 ON r15.mn = m.mn + interval '15' minute
LEFT JOIN m r60 ON r60.mn = m.mn + interval '60' minute;

-- NB block-level (block_number+k) testé AUSSI : inexploitable — VWAP par bloc sur blocs
-- creux explose la division (lvr_5blk = $501 milliards = outliers), sans winsorisation.
-- La granularité minute lisse ce bruit et donne une LVR stable 1-60 min : c'est la mesure retenue.
