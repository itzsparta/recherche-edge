-- Étude #29 — markout LVR sur L2 (copie de #15 univ3-lvr/queries/markout_minute.sql,
-- portée Base/Arbitrum). Flux signé/minute × rendement forward = LVR concentration-correcte.
-- Multi-horizon 1/5/15/60 min, on retient le MAX (le plus dur pour le LP = anti-faux-GO).
-- Paramètres : {CHAIN} ∈ {base,arbitrum}, {POOL}, {FEE} (0.0005 pour 0.05%).
-- NOUVEAU vs #15 : bande de prix anti-explosion (sur Arbitrum quelques p_exec aberrants
-- ~1000× off font exploser (r.vwap-m.vwap)/m.vwap ; bande = nettoyage, kill que le garbage,
-- appliquée uniformément ; sur Base sans-bande==avec-bande donc non distordant).
WITH sw AS (
  SELECT date_trunc('minute', block_time) AS mn, amount_usd AS size_usd,
    CASE WHEN token_bought_symbol='WETH' THEN token_sold_amount/token_bought_amount
         ELSE token_bought_amount/token_sold_amount END AS p_exec,
    CASE WHEN token_bought_symbol='WETH' THEN 1 ELSE -1 END AS dir
  FROM dex.trades
  WHERE blockchain='{CHAIN}' AND project='uniswap'
    AND project_contract_address={POOL}
    AND block_month >= date '2024-01-01' AND block_month < date '2025-01-01'
    AND amount_usd>0 AND token_bought_amount>0 AND token_sold_amount>0
),
swf AS (SELECT * FROM sw WHERE p_exec BETWEEN 1000 AND 8000),   -- bande ETH 2024 (300..6000 pour 2022-23)
m AS (SELECT mn, sum(size_usd*p_exec)/sum(size_usd) AS vwap,
        sum(size_usd*dir) AS signed_vol, sum(size_usd) AS vol FROM swf GROUP BY mn)
SELECT sum(m.vol) AS volume_usd, sum(m.vol)*{FEE} AS fees_usd,
  sum(m.signed_vol*(r1.vwap-m.vwap)/m.vwap)  AS lvr_1m,
  sum(m.signed_vol*(r5.vwap-m.vwap)/m.vwap)  AS lvr_5m,
  sum(m.signed_vol*(r15.vwap-m.vwap)/m.vwap) AS lvr_15m,
  sum(m.signed_vol*(r60.vwap-m.vwap)/m.vwap) AS lvr_60m
FROM m
LEFT JOIN m r1  ON r1.mn=m.mn+interval '1' minute
LEFT JOIN m r5  ON r5.mn=m.mn+interval '5' minute
LEFT JOIN m r15 ON r15.mn=m.mn+interval '15' minute
LEFT JOIN m r60 ON r60.mn=m.mn+interval '60' minute;

-- ===== part JIT (Gate C, NOUVEAU vs #15) =====
-- Volume de swap servi par de la liquidité ATOMIQUE même-bloc (signature JIT) / volume total.
-- tight = bloc avec (owner,tickLower,tickUpper) à la fois minté ET burné le même bloc (JIT pur,
--         aucune ambiguïté : personne n'ouvre+ferme une position en 1 bloc sauf JIT).
-- loose = bloc avec ≥1 mint ET ≥1 burn (borne HAUTE, sur-compte la capture).
-- WITH mb AS (mint UNION ALL burn sur uniswap_v3_{chain}.uniswapv3pool_evt_{mint,burn}),
--      tight/loose = blocs qualifiants, vol = dex.trades par bloc → share = jit_vol/total_vol.
-- (requête complète exécutée 2024 : Base tight 0.84%/loose 3.88% ; Arb tight 0.12%/loose 0.92%.)
