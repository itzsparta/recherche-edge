import json
import os
import pytest
from dune_adapter import main

def test_dune_adapter_conversion(tmp_path):
    csv_file = tmp_path / "input.csv"
    json_file = tmp_path / "output.json"
    
    csv_content = """mint,pool,t_pool,pool_sol_init,n_buyers_pre,px_s0,px_s1,px_t5,px_t30,px_t120,px_t300,px_t600,px_t900,px_t1800,px_t2700,res_s0,res_t5,res_t30,res_t1800,n_swaps_50min
MintA,PoolA,2025-08-01 12:00:00Z,85.5,150,0.001,0.0011,0.0012,0.0015,,,,,,,85.5,86.0,,,10
MintB,PoolB,2025-08-05 15:30:00Z,100.0,40,,0.005,,,,,,,0.002,0.001,100.0,,,,5
MintB,PoolB_dup,2025-08-05 15:30:00Z,100.0,40,,0.005,,,,,,,0.002,0.001,100.0,,,,5
MintC_Empty,PoolC,2025-08-10 10:00:00Z,50.0,10,,,,,,,,,,,,,,,0
"""
    csv_file.write_text(csv_content, encoding="utf-8")
    
    res = main([str(csv_file), str(json_file), "--regime", "BAS"]) # defaults to lag=px_s0
    assert res == 0
    assert json_file.exists()
    
    with open(json_file, "r", encoding="utf-8") as f:
        episodes = json.load(f)
        
    # MintB has no px_s0, MintC has no path, MintB dup should be deduplicated
    assert len(episodes) == 1 
    
    ep_a = episodes[0]
    assert ep_a["mint"] == "MintA"
    assert ep_a["regime"] == "BAS"
    assert ep_a["n_buyers_pre"] == 150
    assert ep_a["pool_sol_init"] == 85.5
    assert ep_a["reserves"]["0.0"] == 85.5
    assert ep_a["liq_usd"] == 1.0 # Verify explicitly neutralized mock
    
    # Check path mapping (now fills missing with carried values)
    # px_s0=0.001, px_s1=0.0011, px_t5=0.0012, px_t30=0.0015
    # Then it carries 0.0015 for the rest!
    path = ep_a["path"]
    assert path[0] == [0.0, 0.001]
    assert path[3] == [30.0, 0.0015]
    assert path[4] == [120.0, 0.0015] # Carried
    assert path[-1] == [2700.0, 0.0015] # Carried
    assert ep_a["n_carried"] == 6

def test_dune_adapter_with_lag(tmp_path):
    csv_file = tmp_path / "input.csv"
    json_file = tmp_path / "output.json"
    
    csv_content = """mint,pool,t_pool,pool_sol_init,n_buyers_pre,px_s0,px_s1,px_t5,px_t30,px_t120,px_t300,px_t600,px_t900,px_t1800,px_t2700,res_s0,res_t5,res_t30,res_t1800,n_swaps_50min,lag_last
MintB,PoolB,2025-08-05 15:30:00Z,100.0,40,,0.005,,,,,,,0.002,0.001,100.0,,,,5,
"""
    csv_file.write_text(csv_content, encoding="utf-8")
    
    # Require px_s1 instead of px_s0
    res = main([str(csv_file), str(json_file), "--lag", "px_s1", "--regime", "BAS"])
    assert res == 0
    
    with open(json_file, "r", encoding="utf-8") as f:
        episodes = json.load(f)
        
    assert len(episodes) == 1
    path = episodes[0]["path"]
    assert path[0] == [0.4, 0.005]
    assert path[1] == [5.0, 0.005] # Carried
    assert path[-2] == [1800.0, 0.002]
    assert path[-1] == [2700.0, 0.001]
    assert episodes[0]["n_carried"] == 6
