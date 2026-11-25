import sys
from pathlib import Path
from .core import check_dir, load_bundle, task_order

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
cfg = load_bundle(root)
for name, job in cfg["resources"]["jobs"].items():
    print(f"{name}: " + " -> ".join(task_order(job["tasks"])))
problems = check_dir(root)
for p in problems:
    print("FAIL:", p)
print("OK: bundle is safe to deploy" if not problems else f"{len(problems)} problem(s)")
sys.exit(1 if problems else 0)
