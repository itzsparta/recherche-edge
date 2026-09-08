-- BREADTH pre-graduation : la variable de conditionnement de la piste 3.
-- Une ligne par graduation du jour {{day}}, jointe en Python sur `mint`.
--
-- POURQUOI SEPAREE de sql/verdict_graduation.sql : pump_evt_tradeevent (toute
-- l'activite de courbe de bonding) est plus volumineuse que les swaps AMM. La
-- garder en CTE faisait exploser une requete deja au plafond des 2 min du free tier.
--
-- POURQUOI ELLE COMPTE MAINTENANT : mesure du 2026-09-08 sur le regime BAS, a
-- l'entree s1 (la premiere executable), les 10 meilleurs trades font 145 % du PnL
-- total — retires, la strategie est negative. L'espoir n'est donc pas dans la
-- moyenne mais dans la SELECTION : si la queue epaisse se concentre sur les tokens
-- a forte accumulation organique, breadth transforme la loterie en edge ; si elle
-- est repartie uniformement, c'est un KILL et la piste est close.
--
-- FUITE : le filtre porte sur evt_block_slot < slot_complete, PAS sur le temps.
-- Deux evenements du meme bloc sont simultanes ; comparer des timestamps
-- laisserait entrer l'activite du bloc de graduation lui-meme.
--
-- LOOKBACK : un token peut passer des jours sur la courbe avant de graduer.
-- 2 jours couvrent l'ecrasante majorite. Si la requete depasse les 2 min,
-- descendre a 1 jour et NOTER la troncature (elle sous-estime n_buyers_pre pour
-- les tokens lents, ce qui est un biais a declarer, pas a ignorer).

WITH grad AS (
    SELECT mint, evt_block_slot AS slot_complete
    FROM pumpdotfun_solana.pump_evt_completeevent
    WHERE evt_block_date = DATE '{{day}}'
),

trades AS (
    SELECT t.mint, t.user, COALESCE(t.is_buy, t."isBuy") AS is_buy, t.evt_block_slot, t.evt_block_time
    FROM pumpdotfun_solana.pump_evt_tradeevent t
    JOIN grad g ON g.mint = t.mint
    WHERE t.evt_block_slot < g.slot_complete
      AND t.evt_block_date >= DATE '{{day}}' - INTERVAL '2' DAY
      AND t.evt_block_date <= DATE '{{day}}'
)

SELECT
    g.mint,
    COUNT(DISTINCT t.user)                                  AS n_buyers_pre,
    COUNT(DISTINCT t.user) FILTER (WHERE t.is_buy)          AS n_uniq_buyers,
    COUNT(*) FILTER (WHERE t.is_buy)                        AS n_buys,
    COUNT(*) FILTER (WHERE NOT t.is_buy)                    AS n_sells,
    -- ratio achats/ventes : le seuil 3:1 de la piste 3
    CAST(COUNT(*) FILTER (WHERE t.is_buy) AS double)
      / NULLIF(COUNT(*) FILTER (WHERE NOT t.is_buy), 0)     AS buy_sell_ratio,
    -- vitesse d'accumulation : secondes entre le premier trade et la graduation.
    -- Le critere de la piste 3 (">40 acheteurs uniques en <90 s") a besoin des deux.
    date_diff('second', min(t.evt_block_time), max(t.evt_block_time)) AS curve_span_sec,
    min(t.evt_block_time)                                   AS t_first_trade
FROM grad g
LEFT JOIN trades t ON t.mint = g.mint
GROUP BY g.mint;
