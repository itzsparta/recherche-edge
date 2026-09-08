/* =====================================================================
   VERDICT dataset — launches pump.fun -> trajectoires de prix (Dune / Trino)
   Source : evenements NATIFS pump.fun (pumpdotfun_solana.pump_evt_*).

   But : echantillon NON BIAISE, RUGS INCLUS, pour trancher l'edge du snipe via
   verdict.py (gardes anti-overfit facon orderflow).

   ---- 1 REGIME PAR EXECUTION ----
   Le join createevent x tradeevent sur 4 jours en une seule query depasse les
   limites du free tier Dune (FAILED ~2 min). On execute donc UN regime (= un
   jour) par run, puis on concatene les CSV (cf. README / boucle dune_run).
   Editer les 2 TIMESTAMP + le label 'regime' ci-dessous pour chaque regime.

   Anti-biais :
   - univers = pump_evt_createevent = TOUTES les creations (rugs inclus, t=0 reel)
     => SURVIVORSHIP corrige.
   - echantillon deterministe par hash du mint (ni survie, ni perf).
   - multi-regime via plusieurs runs (euphorie + crashes) => annule drift / beta.

   Sortie : 1 ligne par (mint, bucket 30 s), 15 premieres minutes.
   price_usd / bucket_vol_usd = stand-ins SOL (scale-free) : les % SL/TP sont
   exacts (echelle annulee), strategy.verdict.json relache les filtres USD.

   Pieges Trino (appris a la dure) :
   - tables decodees : colonne temps = evt_block_time (PAS block_time).
   - hash->bigint : from_big_endian_64(xxhash64(to_utf8(x)))  (xxhash64=varbinary).
   - amounts : coalesce(snake, "camelCase")  (variante peuplee selon l'ere decodeur).
   - prix : CAST(... AS double) AVANT division (amounts bigint -> sinon div entiere=0).
   ===================================================================== */
WITH launches AS (
    SELECT c.mint, c.name, c.evt_block_time AS launch_time,
           'jan_2025_euphoria' AS regime                     -- <-- label du regime
    FROM pumpdotfun_solana.pump_evt_createevent c
    WHERE c.evt_block_time >= TIMESTAMP '2025-01-18 12:00'   -- <-- fenetre de 4h (garantit <2min sur Free Tier)
      AND c.evt_block_time <  TIMESTAMP '2025-01-18 16:00'
      AND mod(abs(from_big_endian_64(xxhash64(to_utf8(c.mint)))), 1000) < 50  -- ~5%
),
swaps AS (
    SELECT l.mint, l.name, l.regime, l.launch_time,
           date_diff('second', l.launch_time, t.evt_block_time) AS t_sec,
           coalesce(t.sol_amount,   t."solAmount")   AS sol_amt,
           coalesce(t.token_amount, t."tokenAmount") AS token_amt
    FROM pumpdotfun_solana.pump_evt_tradeevent t
    JOIN launches l ON t.mint = l.mint
    WHERE t.evt_block_time >= TIMESTAMP '2025-01-18 12:00'
      AND t.evt_block_time <  TIMESTAMP '2025-01-18 16:15'
      AND t.evt_block_time >= l.launch_time
      AND t.evt_block_time <  l.launch_time + INTERVAL '15' MINUTE
)
SELECT
    mint, name, regime,
    to_unixtime(launch_time)                                 AS launch_unix,
    CAST(floor(t_sec / 30) AS INTEGER) * 30                   AS t_bucket,
    CAST(sum(sol_amt) AS double) / NULLIF(sum(token_amt), 0)  AS price_sol,
    CAST(sum(sol_amt) AS double) / NULLIF(sum(token_amt), 0)  AS price_usd,      -- stand-in SOL
    CAST(sum(sol_amt) AS double)                              AS bucket_vol_usd,  -- stand-in SOL (lamports)
    count(*)                                                  AS n_trades
FROM swaps
WHERE sol_amt > 0 AND token_amt > 0
GROUP BY mint, name, regime, launch_time, CAST(floor(t_sec / 30) AS INTEGER) * 30
ORDER BY mint, t_bucket
