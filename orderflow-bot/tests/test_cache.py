"""Cache disque des plans candidats (passe 1) : round-trip JSONL.
Permet de generer la passe 1 une fois puis iterer le filtre dessus."""
from orderflow_bot.cache import load_plans, save_plans
from orderflow_bot.models import OrderPlan


def test_save_load_roundtrip(tmp_path):
    plans = [
        OrderPlan(ts=1000, side=1, entry=100.0, stop=99.0, target=102.0,
                  meta={"trigger": "absorption", "zone": "val", "bias": 1}),
        OrderPlan(ts=2000, side=-1, entry=200.0, stop=201.5, target=197.0, meta={}),
    ]
    f = tmp_path / "plans.jsonl"
    save_plans(f, plans)
    assert load_plans(f) == plans


def test_load_missing_returns_empty(tmp_path):
    assert load_plans(tmp_path / "nope.jsonl") == []


def test_save_creates_parent_dir(tmp_path):
    f = tmp_path / "sub" / "dir" / "plans.jsonl"
    save_plans(f, [OrderPlan(ts=1, side=1, entry=1.0, stop=0.5, target=2.0)])
    assert len(load_plans(f)) == 1
