"""TDD adapter Dune CSV -> episodes backtester. Transforms PURS (hors-ligne)."""
import csv

from dune_adapter import rows_to_episodes, build_dataset, SUPPLY


def _row(mint="M1", name="tok", regime="r1", launch="1000",
         t="0", psol="1e-7", pusd="2e-5", vol="500", n="3"):
    """Ligne CSV brute (DictReader -> str partout)."""
    return {"mint": mint, "name": name, "regime": regime, "launch_unix": launch,
            "t_bucket": t, "price_sol": psol, "price_usd": pusd,
            "bucket_vol_usd": vol, "n_trades": n}


def test_groups_buckets_of_one_mint_into_one_episode_with_sorted_path():
    rows = [_row(t="30", psol="2e-7"), _row(t="0", psol="1e-7")]
    eps = rows_to_episodes(rows)
    assert len(eps) == 1
    ep = eps[0]
    assert ep["mint"] == "M1"
    assert ep["name"] == "tok"
    assert ep["launch_time"] == 1000.0
    assert ep["path"] == [[0, 1e-7], [30, 2e-7]]


def test_fdv_is_first_bucket_price_usd_times_supply():
    # 1er bucket (t=0) price_usd=2e-5 -> fdv = 2e-5 * 1e9 = 20000
    rows = [_row(t="0", pusd="2e-5"), _row(t="30", pusd="9e-5")]
    ep = rows_to_episodes(rows)[0]
    assert ep["fdv_usd"] == 2e-5 * SUPPLY


def test_carries_backtester_metadata_fields():
    rows = [_row(regime="crash", vol="500"), _row(t="30", vol="300")]
    ep = rows_to_episodes(rows)[0]
    assert ep["vol24_usd"] == 800.0          # somme des bucket_vol_usd
    assert ep["liq_usd"] == 800.0            # proxy = volume cumule (gate liq off au verdict)
    assert ep["regime"] == "crash"
    assert ep["rug_score"] == 0
    assert ep["risks"] == []


def test_distinct_mints_yield_distinct_episodes():
    rows = [_row(mint="A", t="0"), _row(mint="B", t="0"), _row(mint="A", t="30")]
    eps = rows_to_episodes(rows)
    assert {e["mint"] for e in eps} == {"A", "B"}
    by = {e["mint"]: e for e in eps}
    assert len(by["A"]["path"]) == 2
    assert len(by["B"]["path"]) == 1


def test_single_bucket_mint_keeps_one_point_path():
    # un rug instantane (1 seul bucket de trades) reste un episode valide
    ep = rows_to_episodes([_row(mint="RUG", t="0", psol="5e-7")])[0]
    assert ep["path"] == [[0, 5e-7]]


def test_build_dataset_reads_real_csv_file(tmp_path):
    csv_path = tmp_path / "dune.csv"
    cols = ["mint", "name", "regime", "launch_unix", "t_bucket",
            "price_sol", "price_usd", "bucket_vol_usd", "n_trades"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerow(["A", "tok", "r1", "1000", "0", "1e-7", "2e-5", "500", "3"])
        w.writerow(["A", "tok", "r1", "1000", "30", "2e-7", "4e-5", "200", "2"])
    eps = build_dataset(str(csv_path), str(tmp_path / "out.json"))
    assert len(eps) == 1
    assert eps[0]["path"] == [[0, 1e-7], [30, 2e-7]]
    assert eps[0]["fdv_usd"] == 2e-5 * SUPPLY
