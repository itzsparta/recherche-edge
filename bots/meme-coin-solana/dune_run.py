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
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.dune.com/api/v1"


def _key():
    k = os.environ.get("DUNE_API_KEY")
    if not k:
        raise SystemExit("DUNE_API_KEY absent de l'environnement (ou de votre fichier .env).")
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


def execute(query_id, performance=None, params=None):
    """performance None = tier par defaut du plan (free n'accepte pas 'medium').

    params : dict des parametres Dune ({{day}} etc.). Le tier free plafonne a
    3 executions paralleles ; run_days() serialise en consequence."""
    payload = {"performance": performance} if performance else {}
    if params:
        payload["query_parameters"] = params
    return _req("POST", f"/query/{query_id}/execute", payload)["execution_id"]


def poll(execution_id, timeout_s=600, interval_s=5):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        st = _req("GET", f"/execution/{execution_id}/status")
        state = st.get("state")
        if state == "QUERY_STATE_COMPLETED":
            return st
        if state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED", "QUERY_STATE_EXPIRED"):
            err_msg = json.dumps(st.get("error", st), indent=2)
            raise SystemExit(f"execution {state}:\n{err_msg}")
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


def run_days(query_id, days, out_dir, performance=None):
    """Execute la query parametree une fois par jour, un CSV par jour.

    Un CSV PAR JOUR et pas un seul fichier concatene : une execution qui echoue
    n'oblige pas a tout relancer, et on voit tout de suite quel jour manque.
    Recuperer un resultat ne coute PAS de credit -> un jour deja extrait n'est
    jamais re-execute (skip si le CSV existe).
    """
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for day in days:
        out = os.path.join(out_dir, f"{day}.csv")
        if os.path.exists(out):
            print(f"{day} : deja present, skip (aucun credit depense)")
            continue
        exec_id = execute(query_id, performance, {"day": day})
        print(f"{day} : execution {exec_id}")
        st = poll(exec_id)
        n = st.get("result_metadata", {}).get("total_row_count", "?")
        results_csv(exec_id, out)
        print(f"{day} : {n} lignes -> {out}")
        total += n if isinstance(n, int) else 0
    print(f"run_days termine : {total} lignes sur {len(days)} jours")
    return 0


def daterange(start, end):
    """Liste inclusive de 'YYYY-MM-DD' entre start et end."""
    from datetime import date, timedelta
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    return [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]


def main(argv):
    # Mode 1 : rapatrier une execution DEJA payee (gratuit, ne relance rien).
    if argv and argv[0] == "--fetch":
        if len(argv) < 3:
            print("Usage: python dune_run.py --fetch <execution_id> <out_csv>")
            return 1
        n = results_csv(argv[1], argv[2])
        print(f"OK : ~{n} lignes -> {argv[2]}")
        return 0

    # Mode 1 bis : rapatrier un regime entier depuis son manifeste d'executions
    # deja payees. Aucun credit : sur Dune, executer coute, relire ne coute pas.
    if argv and argv[0] == "--fetch-manifest":
        if len(argv) < 2:
            print("Usage: python dune_run.py --fetch-manifest <dir_contenant_manifest.json>")
            return 1
        d = argv[1]
        with open(os.path.join(d, "manifest.json"), encoding="utf-8") as f:
            man = json.load(f)
        total = 0
        for day, info in sorted(man["days"].items()):
            out = os.path.join(d, f"{day}.csv")
            results_csv(info["execution_id"], out)
            print(f"{day} : {info['rows']} lignes -> {out}")
            total += info["rows"]
        print(f"OK : {total} lignes attendues, regime {man['regime']}, 0 credit depense")
        return 0

    # Mode 2 : extraction jour par jour d'une query parametree {{day}}.
    if argv and argv[0] == "--days":
        if len(argv) < 5:
            print("Usage: python dune_run.py --days <query_id> <start> <end> <out_dir>")
            return 1
        return run_days(int(argv[1]), daterange(argv[2], argv[3]), argv[4])

    # Mode 3 : jours EXPLICITES, espaces dans la fenetre de regime. Les regimes
    # MOYEN et HAUT echantillonnent 4 jours espaces et non un mois continu : un
    # --days sur la plage couterait le mois entier, et surtout 4 jours consecutifs
    # laisseraient l'artefact d'une seule journee porter tout un regime.
    if argv and argv[0] == "--days-list":
        if len(argv) < 4:
            print("Usage: python dune_run.py --days-list <query_id> <out_dir> <j1> <j2> ...")
            return 1
        return run_days(int(argv[1]), list(argv[3:]), argv[2])

    if len(argv) < 2:
        print("Usage: python dune_run.py <sql_file> <out_csv> [query_id]")
        print("       python dune_run.py --fetch <execution_id> <out_csv>")
        print("       python dune_run.py --days <query_id> <start> <end> <out_dir>")
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
