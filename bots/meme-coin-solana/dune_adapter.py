import argparse
import csv
import json
import sys
from datetime import datetime, timezone

def parse_dune_time(t_str):
    if not t_str:
        return 0.0
    t_str = t_str.replace("T", " ").replace("Z", "").strip()
    if "." in t_str:
        t_str = t_str.split(".")[0]
    # Bug 3: interpret as UTC, not local time
    dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.timestamp()

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    
    parser = argparse.ArgumentParser(description="Convert Dune CSV to backtest JSON.")
    parser.add_argument("files", nargs="+", help="Input CSV files from Dune, followed by the output JSON file")
    parser.add_argument("--lag", default="px_s0", help="Entry lag column to require (e.g. px_s0, px_t5)")
    parser.add_argument("--regime", required=True,
                        help="Regime label for every episode of this CSV")
    parser.add_argument("--breadth-dir", help="Directory containing breadth CSVs to merge")
    args = parser.parse_args(argv)
    
    if len(args.files) < 2:
        parser.error("Must provide at least one input CSV and one output JSON")
        
    output_json = args.files[-1]
    input_patterns = args.files[:-1]

    import glob
    input_files = []
    for pattern in input_patterns:
        expanded = glob.glob(pattern)
        if expanded:
            input_files.extend(expanded)
        else:
            input_files.append(pattern)

    # Load breadth data if provided
    breadth_data = {}
    if args.breadth_dir:
        import os
        for bfile in glob.glob(os.path.join(args.breadth_dir, "*.csv")):
            with open(bfile, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mint = row.get("mint")
                    if mint:
                        def parse_float(val, default):
                            if not val or val == "<nil>": return default
                            try: return float(val)
                            except: return default
                        breadth_data[mint] = {
                            "n_uniq_buyers": int(row.get("n_uniq_buyers") or 0),
                            "buy_sell_ratio": parse_float(row.get("buy_sell_ratio"), 0.0),
                            "curve_span_sec": parse_float(row.get("curve_span_sec"), 999999.0)
                        }

    episodes = []
    seen_mints = set() # Bug 1: deduplicate pools by mint
    
    for input_csv in input_files:
        with open(input_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mint = row.get("mint", "unknown")
                if mint in seen_mints:
                    continue
                seen_mints.add(mint)

                t_pool = row.get("t_pool", "")
                launch_time = parse_dune_time(t_pool)
                
                regime = args.regime

                # Checkpoints : (offset_sec, colonne_prix, colonne_reserve)
                checkpoints = [
                    (0.0,    "px_s0",    "res_s0"),
                    (0.4,    "px_s1",    "res_s1"),
                    (5.0,    "px_t5",    "res_t5"),
                    (30.0,   "px_t30",   "res_t30"),
                    (120.0,  "px_t120",  "res_t120"),
                    (300.0,  "px_t300",  "res_t300"),
                    (600.0,  "px_t600",  "res_t600"),
                    (900.0,  "px_t900",  "res_t900"),
                    (1800.0, "px_t1800", "res_t1800"),
                    (2700.0, "px_t2700", "res_t2700"),
                ]

                # Bug 4 : le checkpoint d'ENTREE est exige. Sans lui l'episode demarrerait
                # a un lag plus tardif en se faisant passer pour une entree normale, et le
                # balayage de latence — le test decisif de la these — melangerait les lags.
                if not row.get(args.lag):
                    continue

                lag_offset = next((off for off, col, _ in checkpoints if col == args.lag), 0.0)

                # Bug 4 bis : un checkpoint TARDIF absent n'est pas une donnee manquante au
                # hasard. Mesure au 2025-07-25 : les 3 episodes sans px_t2700 ont 20 SOL de
                # reserve mediane contre 83 pour les autres, et sont a -95%. Un NULL tardif
                # veut dire "plus personne ne trade", c'est-a-dire l'issue la PIRE. Raccourcir
                # ou jeter ces episodes retire exactement les pires resultats : du survivorship
                # qui flatte la strategie. On reporte donc la derniere marque connue — pas de
                # trade depuis, donc le prix ne bouge plus — et l'episode garde sa longueur.
                path, reserves = [], {}
                last_px = last_res = None
                n_carried = 0
                for offset, px_col, res_col in checkpoints:
                    if offset < lag_offset:
                        continue
                    raw_px, raw_res = row.get(px_col), row.get(res_col)
                    if raw_px:
                        try:
                            last_px = float(raw_px)
                            if raw_res:
                                last_res = float(raw_res)
                        except ValueError:
                            pass
                    elif last_px is not None:
                        n_carried += 1
                    if last_px is None:
                        continue
                    path.append([offset, last_px])
                    if last_res is not None:
                        reserves[str(offset)] = last_res

                if not path:
                    continue

                n_buyers_pre = int(row.get("n_buyers_pre") or 0)
                
                # Bug 2: Neutralize FDV/Liq filters explicitly instead of injecting passing values
                # Setting to 1.0. We will use a strategy.graduation.json config to allow any FDV > 0
                ep = {
                    "mint": mint,
                    "name": f"Grad_{mint[:4]}",
                    "launch_time": launch_time,
                    "regime": regime,
                    "path": path,
                    # Donnees analytiques
                    "n_buyers_pre": n_buyers_pre,
                    "pool_sol_init": float(row.get("pool_sol_init") or 0.0),
                    # Reserve SOL a chaque offset du path : sert au slippage PAR TRADE
                    # (impact = clip / (reserve + clip)), jamais une constante de config.
                    "reserves": reserves,
                    # Auditabilite du report de marque : combien de checkpoints sont des
                    # marques reportees et non des trades observes.
                    "n_carried": n_carried,
                    "lag_last": float(row.get("lag_last") or 0.0),
                    # Mocks neutralises (on laissera la config accepter [0, inf])
                    "liq_usd": 1.0,
                    "fdv_usd": 1.0,
                    "vol24_usd": 1.0,
                    "rug_score": 0,
                    "risks": []
                }
                if mint in breadth_data:
                    ep.update(breadth_data[mint])
                episodes.append(ep)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(episodes, f, indent=2)

    print(f"dune_adapter: converted {len(episodes)} episodes "
          f"(regime={args.regime}, lag={args.lag}, {len(seen_mints)} unique mints seen).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
