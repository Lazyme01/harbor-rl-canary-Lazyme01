import csv
import json
import re
import subprocess
from pathlib import Path

root = Path.cwd()
solutions = root / "jobs_summary/recovered_solutions"
verifier = root / "tasks/reconcile-bug/tests/test_state.py"

baseline_rewards = {
    "baseline_489kKTT": 1.0,
    "baseline_FSvhiuw": 0.0,
    "baseline_TNEzoQu": 1.0,
    "ablation_2tHFABd": 1.0,
    "ablation_JKQxwY4": 1.0,
    "ablation_yuxnS7h": 1.0,
}

results = []

for name, binary in baseline_rewards.items():
    solution = solutions / f"{name}.py"

    command = [
        "docker", "run", "--rm",
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "64",
        "--memory", "256m",
        "--cpus", "1",
        "--user", "65534:65534",
        "--tmpfs", "/app:rw,mode=1777",
        "--tmpfs", "/tmp:rw,mode=1777",
        "-v", f"{solution}:/source/reconcile.py:ro",
        "-v", f"{verifier}:/tests/test_state.py:ro",
        "-w", "/app",
        "python:3.12-slim",
        "sh", "-c",
        "cp /source/reconcile.py /app/reconcile.py && "
        "python3 /tests/test_state.py",
    ]

    print(f"\nEvaluating {name}...", flush=True)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=90,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        output = result.stdout.strip()
        if not re.fullmatch(r"(?:0|1)\.\d{2}", output):
            raise RuntimeError(f"Invalid verifier output: {output!r}")

        dense = float(output)
        print(f"Binary: {binary:.2f} | Dense: {dense:.2f}")
        print(result.stderr[-1200:])

    except Exception as error:
        dense = None
        print("ERROR:", error)

    results.append({
        "trial": name,
        "group": name.split("_")[0],
        "binary_reward": binary,
        "dense_reward": dense,
    })

for group in ("baseline", "ablation"):
    group_rows = [r for r in results if r["group"] == group]

    binary_mean = sum(r["binary_reward"] for r in group_rows) / 3

    dense_values = [r["dense_reward"] for r in group_rows]
    dense_mean = (
        sum(dense_values) / 3
        if all(v is not None for v in dense_values)
        else None
    )

    for row in group_rows:
        row["binary_advantage"] = round(
            row["binary_reward"] - binary_mean, 4
        )
        row["dense_advantage"] = (
            round(row["dense_reward"] - dense_mean, 4)
            if dense_mean is not None else None
        )

    print(f"\n{group.upper()}")
    print(f"Binary mean: {binary_mean:.4f}")
    print(
        f"Dense mean: {dense_mean:.4f}"
        if dense_mean is not None else "Dense mean: unavailable"
    )

output = root / "jobs_summary"

(output / "rescore_results.json").write_text(
    json.dumps(results, indent=2) + "\n"
)

with (output / "rescore_results.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

print("\nFINAL RESULTS")
for row in results:
    print(row)

print("\nSaved jobs_summary/rescore_results.json")
print("Saved jobs_summary/rescore_results.csv")
