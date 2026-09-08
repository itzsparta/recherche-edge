-- EXTRACTION - piste graduation pump.fun -> PumpSwap.
-- Une ligne par graduation, portant la courbe de prix aux checkpoints.
-- Assemblage entrees/sorties/miroirs en Python (dune_adapter) : transforms testables.
--
-- UN JOUR PAR EXECUTION, via le parametre Dune {{day}} (type text, 'YYYY-MM-DD').
--   Le mur n'est PAS la taille de la cohorte mais le scan brut des swaps, partitionne
--   par jour : reduire le nombre de graduations ne reduit rien. Seule la fenetre
--   temporelle compte. 3 timeouts constates a 2 min (free tier) sur 7j / 3j / 1j en
--   ere 2026 ; l'ere 2025 est bien moins dense, d'ou le test jour-entier d'abord.
--
-- PERF : surtout NE PAS faire CROSS JOIN sur une table d'offsets puis ROW_NUMBER
--        (x10 lignes -> timeout). Une seule passe d'agregation avec
--        min_by(...) FILTER (...) donne le meme "premier swap qualifiant" pour tous
--        les checkpoints a la fois.
--
-- BREADTH : extrait par sql/breadth_graduation.sql, joint en Python sur mint.
--        pump_evt_tradeevent est encore plus volumineuse que les swaps AMM ;
--        la garder ici faisait exploser une requete deja au plafond.
--
-- UNIVERS : uniquement les pools NES D'UNE GRADUATION, quote SOL.
--   createpoolevent seul contient ~3,4x trop de pools (creation hors graduation).
--   La jointure sur completeevent DEFINIT l'univers.
--
-- CONVENTIONS VALIDEES : colonnes prefixees evt_ ; montants deja en uint256 ;
--   filtre quote_mint = SOL avant toute lecture de montant.

WITH grad AS (
    SELECT mint, evt_block_slot AS slot_complete
    FROM pumpdotfun_solana.pump_evt_completeevent
    WHERE evt_block_date = DATE '{{day}}'
),

-- Dedup : 416 createpoolevent pour 409 graduations au 2025-04-15. Un mint peut porter
-- plusieurs pools ; on garde le PREMIER (celui de la graduation). Fait en SQL et pas
-- seulement dans l'adaptateur, pour que la concatenation des CSV soit sans ordre impose.
cohorte_raw AS (
    SELECT g.mint, p.pool, p.base_mint_decimals AS base_dec,
           p.evt_block_slot AS slot_pool, p.evt_block_time AS t_pool,
           CAST(p.pool_quote_amount AS double) / 1e9 AS pool_sol_init,
           ROW_NUMBER() OVER (PARTITION BY g.mint ORDER BY p.evt_block_slot) AS rk
    FROM grad g
    JOIN pumpdotfun_solana.pump_amm_evt_createpoolevent p
      ON p.base_mint = g.mint
     AND p.quote_mint = 'So11111111111111111111111111111111111111112'
     AND p.evt_block_date = DATE '{{day}}'
),
cohorte AS (SELECT * FROM cohorte_raw WHERE rk = 1),

swaps AS (
    SELECT c.mint,
           s.evt_block_slot - c.slot_pool                       AS lag_slot,
           date_diff('second', c.t_pool, s.evt_block_time)      AS lag_sec,
           s.evt_block_slot                                     AS slot,
           (CAST(s.quote_res AS double) / 1e9)
             / NULLIF(CAST(s.base_res AS double) / POWER(10, c.base_dec), 0) AS price_sol,
           CAST(s.quote_res AS double) / 1e9                    AS reserve_sol
    FROM cohorte c
    JOIN (
        SELECT pool, evt_block_slot, evt_block_time,
               pool_quote_token_reserves AS quote_res,
               pool_base_token_reserves  AS base_res
        FROM pumpdotfun_solana.pump_amm_evt_buyevent
        WHERE evt_block_date >= DATE '{{day}}'
          AND evt_block_date <  DATE '{{day}}' + INTERVAL '2' DAY
        UNION ALL
        SELECT pool, evt_block_slot, evt_block_time,
               pool_quote_token_reserves, pool_base_token_reserves
        FROM pumpdotfun_solana.pump_amm_evt_sellevent
        WHERE evt_block_date >= DATE '{{day}}'
          AND evt_block_date <  DATE '{{day}}' + INTERVAL '2' DAY
    ) s ON s.pool = c.pool
    WHERE s.evt_block_slot >= c.slot_pool
      AND s.evt_block_time <= c.t_pool + INTERVAL '50' MINUTE
),

-- Premier swap observable a chaque checkpoint. On n'entre JAMAIS a un prix theorique.
--   s0/s1  = balayage de latence (zone des bots Rust ; edge qui n'y survit pas = KILL)
--   t1800  = entree du miroir placebo, t2700 = sa sortie
curve AS (
    SELECT
        mint,
        min_by(price_sol,   slot) FILTER (WHERE lag_slot >= 0)    AS px_s0,
        min_by(price_sol,   slot) FILTER (WHERE lag_slot >= 1)    AS px_s1,
        min_by(price_sol,   slot) FILTER (WHERE lag_sec  >= 5)    AS px_t5,
        min_by(price_sol,   slot) FILTER (WHERE lag_sec  >= 30)   AS px_t30,
        min_by(price_sol,   slot) FILTER (WHERE lag_sec  >= 120)  AS px_t120,
        min_by(price_sol,   slot) FILTER (WHERE lag_sec  >= 300)  AS px_t300,
        min_by(price_sol,   slot) FILTER (WHERE lag_sec  >= 600)  AS px_t600,
        min_by(price_sol,   slot) FILTER (WHERE lag_sec  >= 900)  AS px_t900,
        min_by(price_sol,   slot) FILTER (WHERE lag_sec  >= 1800) AS px_t1800,
        min_by(price_sol,   slot) FILTER (WHERE lag_sec  >= 2700) AS px_t2700,
        -- Reserve a CHAQUE checkpoint : le slippage est PAR TRADE, jamais une constante
        -- de config. Il en faut une a l'entree ET a la sortie, donc partout : le miroir
        -- placebo entre a t1800 et sort a t2700, sans res_t2700 son cout est incalculable.
        -- Meme passe d'agregation que les prix => zero scan supplementaire.
        min_by(reserve_sol, slot) FILTER (WHERE lag_slot >= 0)    AS res_s0,
        min_by(reserve_sol, slot) FILTER (WHERE lag_slot >= 1)    AS res_s1,
        min_by(reserve_sol, slot) FILTER (WHERE lag_sec  >= 5)    AS res_t5,
        min_by(reserve_sol, slot) FILTER (WHERE lag_sec  >= 30)   AS res_t30,
        min_by(reserve_sol, slot) FILTER (WHERE lag_sec  >= 120)  AS res_t120,
        min_by(reserve_sol, slot) FILTER (WHERE lag_sec  >= 300)  AS res_t300,
        min_by(reserve_sol, slot) FILTER (WHERE lag_sec  >= 600)  AS res_t600,
        min_by(reserve_sol, slot) FILTER (WHERE lag_sec  >= 900)  AS res_t900,
        min_by(reserve_sol, slot) FILTER (WHERE lag_sec  >= 1800) AS res_t1800,
        min_by(reserve_sol, slot) FILTER (WHERE lag_sec  >= 2700) AS res_t2700,
        -- DERNIER etat observe. Un checkpoint tardif NULL n'est pas une donnee manquante
        -- au hasard : mesure au 2025-07-25, les 3 episodes sans px_t2700 ont 20 SOL de
        -- reserve mediane contre 83 pour les autres, et sont a -95%. Les laisser tomber
        -- retire exactement les pires issues = survivorship qui flatte la strategie.
        -- On expose donc la derniere marque connue pour marquer la position sans la jeter.
        max_by(price_sol,   slot)                                 AS px_last,
        max_by(reserve_sol, slot)                                 AS res_last,
        max(lag_sec)                                              AS lag_last,
        COUNT(*)                                                  AS n_swaps_50min
    FROM swaps
    GROUP BY mint
)

SELECT
    c.mint, c.pool, c.t_pool, c.pool_sol_init,
    v.px_s0, v.px_s1, v.px_t5, v.px_t30, v.px_t120,
    v.px_t300, v.px_t600, v.px_t900, v.px_t1800, v.px_t2700,
    v.res_s0, v.res_s1, v.res_t5, v.res_t30, v.res_t120,
    v.res_t300, v.res_t600, v.res_t900, v.res_t1800, v.res_t2700,
    v.px_last, v.res_last, v.lag_last,
    v.n_swaps_50min
FROM cohorte c
LEFT JOIN curve v ON v.mint = c.mint
ORDER BY c.t_pool;
