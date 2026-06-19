"""Driver REST Dune : fichier .sql -> execution -> CSV. Automatise l'export manuel.

Cle API : variable d'environnement DUNE_API_KEY UNIQUEMENT (jamais en dur, jamais
committee). Free tier : queries PUBLIQUES seulement, credits limites -> probe petit
avant de scaler (fenetre/sample du SQL).

Usage :
    export DUNE_API_KEY=...                       # (PowerShell : $env:DUNE_API_KEY=...)
    python dune_run.py sql/verdict_pumpfun.sql data/dune_pumpfun.csv [query_id]

Sans query_id : cree une query publique (affiche l'id a reutiliser ensuite).
Avec query_id : met a jour le SQL de cette query (evite d'accumuler des queries).
"""
import os
import sys
import time
import json
import urllib.request
import urllib.error

BASE = "https://api.dune.com/api/v1"


def _key():
    k = os.environ.get("DUNE_API_KEY")
    if not k:
        raise SystemExit("DUNE_API_KEY absent de l'environnement.")
    return k


def _req(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"X-Dune-API-Key": _key(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Dune HTTP {e.code}: {e.read().decode()[:500]}")


def create_query(sql, name="memebot_verdict"):
    return _req("POST", "/query", {"name": name, "query_sql": sql, "is_private": False})["query_id"]


def update_query(query_id, sql):
    _req("PATCH", f"/query/{query_id}", {"query_sql": sql})
    return query_id


def execute(query_id, performance=None):
    """performance None = tier par defaut du plan (free n'accepte pas 'medium')."""
    payload = {"performance": performance} if performance else {}
    return _req("POST", f"/query/{query_id}/execute", payload)["execution_id"]


def poll(execution_id, timeout_s=600, interval_s=5):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        st = _req("GET", f"/execution/{execution_id}/status")
        state = st.get("state")
        if state == "QUERY_STATE_COMPLETED":
            return st
        if state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED", "QUERY_STATE_EXPIRED"):
            raise SystemExit(f"execution {state}: {json.dumps(st)[:400]}")
        print(f"  ... {state}")
        time.sleep(interval_s)
    raise SystemExit("timeout poll execution")


def results_csv(execution_id, out_path):
    req = urllib.request.Request(
        f"{BASE}/execution/{execution_id}/results/csv",
        headers={"X-Dune-API-Key": _key()})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    with open(out_path, "wb") as f:
        f.write(raw)
    return raw.count(b"\n")


def main(argv):
    if len(argv) < 2:
        print("Usage: python dune_run.py <sql_file> <out_csv> [query_id]")
        return 1
    sql_file, out_csv = argv[0], argv[1]
    query_id = int(argv[2]) if len(argv) > 2 else None
    with open(sql_file, "r", encoding="utf-8") as f:
        sql = f.read()

    if query_id:
        update_query(query_id, sql)
        print(f"query {query_id} mise a jour")
    else:
        query_id = create_query(sql)
        print(f"query creee : {query_id}  (reutilise-la : python dune_run.py {sql_file} {out_csv} {query_id})")

    exec_id = execute(query_id)
    print(f"execution {exec_id} lancee")
    st = poll(exec_id)
    n_rows = results_csv(exec_id, out_csv)
    print(f"OK : ~{n_rows} lignes -> {out_csv}  (datapoints={st.get('result_metadata',{}).get('total_row_count','?')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
