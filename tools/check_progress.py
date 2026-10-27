"""Print only progress of saved artifacts, without touching inference."""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("run", type=Path)
a = p.parse_args()
tasks_path = a.run/"tasks_public.json"
if not tasks_path.exists():
    raise SystemExit("Run has not started")
tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
counts = dict.fromkeys(["B0", "visual", "B1", "B2", "B3"], 0)
invalid = 0
for task in tasks:
    for mode in counts:
        path = a.run/task["id"]/mode/"status.json"
        if path.exists():
            counts[mode] += 1
            if mode == "B0" and not json.loads(path.read_text()).get("valid"):
                invalid += 1
print(json.dumps({"tasks": len(tasks), "completed": counts, "initial_invalid": invalid}))
