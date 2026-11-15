# Harbor RL Canary — Transaction Reconciliation

A reproducible Harbor coding task for evaluating an AI agent's ability to repair a buggy Python CSV reconciliation program. The project demonstrates controlled ablation, binary versus dense rewards, group-relative advantages, and anti-cheat testing.

## Task

The agent repairs `/app/reconcile.py`, invoked with:

```bash
python3 /app/reconcile.py INPUT.csv
```

The input header must be exactly `tx_id,timestamp,amount,status`. The program must validate each nonblank row (nonempty, case-sensitive transaction ID; timezone-aware ISO 8601 timestamp; finite, nonnegative decimal amount; and status `success`, `failed`, or `pending`). Invalid input must produce a nonzero exit status and an error on stderr.

For repeated transaction IDs, the latest **UTC instant** wins; if instants tie, the later CSV row wins. Among retained rows, only `success` amounts contribute to `total_valid_amount`; `success` rows contribute to `valid_count`; `failed` rows contribute to `failed_count`; `pending` rows are excluded. Output is a single JSON object with those three numeric fields.

The starter program intentionally contains three categories of defects: CLI handling, status/amount aggregation, and UTC-aware deduplication. The task description does not disclose code locations of the bugs.

## Setup and evaluation

- Runtime: Harbor, Docker, Python 3.12
- Agent: `terminus-2` v2.0.0
- Model: `openrouter/openai/gpt-oss-120b`
- Three trials per group, `-k 3 -n 1`
- Original baseline: `jobs/2026-11-15__11-13-47`
- Ablation: `jobs/2026-11-15__11-29-44`

Validate the task:

```bash
harbor run -p ./tasks/reconcile-bug -a nop
harbor run -p ./tasks/reconcile-bug -a oracle
```

To reproduce the LLM evaluation (requires configured model credentials and may incur charges):

```bash
harbor run -p ./tasks/reconcile-bug -a terminus-2 \
  --model openrouter/openai/gpt-oss-120b -k 3 -n 1
```

**Controlled ablation:** Only the wording in `tasks/reconcile-bug/instruction.md` was clarified to state that success amounts alone contribute to `total_valid_amount`; failed amounts are excluded and pending rows contribute to no output fields. The original instruction text is in `baseline_instruction.md`. All other task files and run settings were held constant during the two three-trial evaluations. Each group has only three samples; differences are descriptive, not statistically conclusive.

## Six-trial results

Original binary rewards were taken from the saved Harbor trials. Dense rewards were subsequently obtained by reconstructing the agents' final Python files from recorded tool calls and executing them against the newer randomized verifier in isolated Docker containers. Thus, dense results are **post-hoc rescoring**, not rewards issued during the original LLM rollouts. Check the recovered code against the full trajectories when auditing reconstruction fidelity.

| Group | Trial | Binary reward | Dense reward | Binary advantage | Dense advantage |
|---|---|---:|---:|---:|---:|
| Baseline | `489kKTT` | 1.00 | 1.00 | +0.3333 | +0.2333 |
| Baseline | `FSvhiuw` | 0.00 | 0.30 | −0.6667 | −0.4667 |
| Baseline | `TNEzoQu` | 1.00 | 1.00 | +0.3333 | +0.2333 |
| Ablation | `2tHFABd` | 1.00 | 1.00 | 0.0000 | 0.0000 |
| Ablation | `JKQxwY4` | 1.00 | 1.00 | 0.0000 | 0.0000 |
| Ablation | `yuxnS7h` | 1.00 | 1.00 | 0.0000 | 0.0000 |

| Group | Binary mean | Dense mean | Binary success rate |
|---|---:|---:|---:|
| Baseline | 0.6667 | 0.7667 | 2/3 |
| Ablation | 1.0000 | 1.0000 | 3/3 |

The baseline trial `FSvhiuw` failed the CLI/status (0.20) and UTC deduplication/tie-break (0.50) categories but passed invalid-input validation (0.30). Its trajectory shows the agent interpreted the total as including amounts that should not contribute. The clarified ablation instructions were followed by three successful trials. This association does not establish causation with such a small sample.

## Dense reward and RL advantage

The original verifier was binary: all tests pass = 1, otherwise 0. The hardened verifier sums weights for independently passed categories:

| Category | Weight |
|---|---:|
| CLI and status aggregation | 0.20 |
| UTC deduplication and equal-instant tie-breaking | 0.50 |
| Invalid input rejection | 0.30 |
| **Maximum** | **1.00** |

For a group of three trials, group-relative advantage is

\[
A_i = R_i - \overline{R}, \quad \overline{R}=\frac{R_1+R_2+R_3}{3}.
\]

Baseline binary mean: `(1 + 0 + 1) / 3 = 0.6667`; advantages: `(+0.3333, −0.6667, +0.3333)`.

Baseline dense mean: `(1 + 0.3 + 1) / 3 = 0.7667`; advantages: `(+0.2333, −0.4667, +0.2333)`.

All ablation rewards were 1.00, so all within-group advantages are zero. Dense scoring makes partial progress visible (0.30 instead of 0.00), but does not create a within-group signal when all responses earn the same reward. Reward saturation is a potential local optimum/learning-signal problem.

## Verifier and anti-cheat evidence

The current verifier uses independently generated random transaction IDs, amounts, timestamps, and temporary filenames. It checks numeric JSON output, timezone-aware deduplication/ties, and invalid inputs. `solution/hack.sh` demonstrates a hardcoded-output shortcut against a naive verifier; the hardened verifier rejects it.

| Candidate | Observed reward | Job |
|---|---:|---|
| Initial buggy program (`nop`) | 0.00 | `2026-11-15__11-47-29` |
| Correct reference (`oracle`) | 1.00 | `2026-11-15__12-03-49` |
| Cheating stub (`hack.sh` temporarily substituted as oracle) | 0.00 | `2026-11-15__11-48-46` |
| Partial solution lacking deduplication | 0.50 | `2026-11-15__11-52-23` |

The 0.50 score demonstrates non-binary partial credit. The test scripts are `tasks/reconcile-bug/tests/test.sh` and `test_state.py`. The original binary versions are preserved under `verifier_backups/`.

**Residual vulnerabilities:** randomized tests do not guarantee security. A program might fingerprint particular test patterns, inspect accessible test fixtures or environmental details, or exploit untested edge cases. Docker confinement and adding diverse independent cases reduce but do not eliminate such risks. For production-grade evaluation, further isolate verifier assets and minimize observable testing patterns.

## Repository guide

- `tasks/reconcile-bug/`: Harbor task, original buggy program, reference and hack/partial solutions, and hardened tests
- `baseline_instruction.md`: baseline instruction wording for the controlled ablation
- `verifier_backups/`: original binary verifier
- `jobs_summary/baseline/`, `jobs_summary/ablation/`: six original result files and agent trajectories
- `jobs_summary/recovered_solutions/`: reconstructed final agent scripts
- `jobs_summary/rescore_results.csv` and `.json`: measured reward and advantage table
- `jobs_summary/rescore_solutions.py`: local Docker-based rescoring procedure
- `ai_transcripts/`: exported records of AI-assisted task development (add real exports before submission)

Do not commit credentials, `.env` files, local virtual environments, or Docker images. The entire `jobs/` runtime directory can remain local if `jobs_summary/` includes the required reproducibility evidence.

## Demo video

**Video URL:**   https://drive.google.com/file/d/1DzNrO-NofG_DHLbLE_poZcNDCZvkiM9S/view?usp=sharing

The unedited recording (maximum five minutes) should show the partial-credit result (0.50), restored oracle (1.00), hack rejection (0.00), failed baseline and ablation trajectories side by side, group-relative reward calculations, observed improvement, and remaining cheating routes.
