"""Demo: a stock-price pipeline as a DAG. Run: PYTHONPATH=src python3 -m dagrun.cli"""
from dagrun.dag import DAG

dag = DAG()
calls = {"n": 0}


@dag.task()
def extract_prices(_):
    return [{"t": "AAPL", "c": 190.0}, {"t": "MSFT", "c": 410.0}]


@dag.task()
def extract_news(_):
    calls["n"] += 1
    if calls["n"] < 2:
        raise TimeoutError("news API slow")  # first try fails, retry wins
    return ["AAPL beats earnings"]


@dag.task(deps=["extract_prices"])
def clean_prices(up):
    return [r for r in up["extract_prices"] if r["c"] > 0]


@dag.task(deps=["clean_prices", "extract_news"], retries=0)
def build_gold(up):
    return {"rows": len(up["clean_prices"]), "headlines": len(up["extract_news"])}


dag.tasks["extract_news"].retries = 2

if __name__ == "__main__":
    print("waves:", dag.levels())
    for name, r in dag.run().items():
        print(f"{name:15} {r['status']:8} {r.get('result', r.get('error', r.get('reason')))}")
