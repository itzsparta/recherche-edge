-- PROBE DE CALIBRATION - piste graduation. VERSION EXECUTEE 2026-09-07 (Dune q.8636809 / 8636818).
--
-- PIEGES DE SCHEMA CONFIRMES PAR L'ECHEC DES V1/V2 :
--   * colonnes bloc/tx prefixees `evt_` (evt_block_date/_time/_slot) sur les tables decodees Solana.
--     Le catalogue MCP les annonce SANS prefixe = FAUX. Deja documente dans FINDINGS.md.
--   * les montants sont deja en uint256, PAS en varbinary : aucun decodage endianness necessaire.
--     bytearray_to_uint256() echoue dessus. La question Q1 initiale etait sans objet.
--   * la CTE frais DOIT filtrer quote_mint = SOL : sans ce filtre, les pools a quote non-SOL
--     (decimales differentes) polluent la mediane (clip median lu a 1716 SOL au lieu de 0,14).

WITH grad AS (
    SELECT mint, evt_block_time AS t_complete, evt_block_slot AS slot_complete
    FROM pumpdotfun_solana.pump_evt_completeevent
    WHERE evt_block_date >= DATE '2026-06-01'
      AND evt_block_date <  DATE '2026-06-08'
),

pool AS (
    SELECT
        base_mint, quote_mint, pool,
        evt_block_time AS t_pool,
        evt_block_slot AS slot_pool,
        CAST(pool_quote_amount AS double) / 1e9 AS pool_sol
    FROM pumpdotfun_solana.pump_amm_evt_createpoolevent
    WHERE evt_block_date >= DATE '2026-06-01'
      AND evt_block_date <  DATE '2026-06-09'   -- +1j de marge
),

joined AS (
    SELECT
        g.mint, p.pool, p.quote_mint, p.pool_sol,
        date_diff('second', g.t_complete, p.t_pool) AS delay_sec,
        p.slot_pool - g.slot_complete               AS delay_slots
    FROM grad g
    LEFT JOIN pool p ON p.base_mint = g.mint
),

fees AS (
    SELECT
        approx_percentile(CAST(lp_fee_basis_points           AS double), 0.5) AS lp_bps,
        approx_percentile(CAST(protocol_fee_basis_points     AS double), 0.5) AS protocol_bps,
        approx_percentile(CAST(coin_creator_fee_basis_points AS double), 0.5) AS creator_bps,
        COUNT(*) AS n_swaps
    FROM pumpdotfun_solana.pump_amm_evt_buyevent
    WHERE evt_block_date = DATE '2026-06-02'
)

SELECT
    COUNT(*)                                              AS n_graduations_7j,
    COUNT(j.pool)                                         AS n_avec_pool_apparie,
    COUNT(*) - COUNT(j.pool)                              AS n_orphelines,
    approx_percentile(CAST(j.delay_sec AS double), 0.5)   AS delay_p50_sec,
    approx_percentile(CAST(j.delay_sec AS double), 0.9)   AS delay_p90_sec,
    MAX(j.delay_sec)                                      AS delay_max_sec,
    approx_percentile(CAST(j.delay_slots AS double), 0.5) AS delay_p50_slots,
    approx_percentile(j.pool_sol, 0.1)                    AS pool_sol_p10,
    approx_percentile(j.pool_sol, 0.5)                    AS pool_sol_median,
    SUM(CASE WHEN j.quote_mint IS NOT NULL
              AND j.quote_mint <> 'So11111111111111111111111111111111111111112'
             THEN 1 ELSE 0 END)                           AS n_quote_non_sol,
    MAX(f.lp_bps) AS lp_bps, MAX(f.protocol_bps) AS protocol_bps, MAX(f.creator_bps) AS creator_bps
FROM joined j
CROSS JOIN fees f;
