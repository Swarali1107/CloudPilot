# SLA definition (fixed, never change)

A 12-second window (= 1 trace-minute) is an **SLA violation** if:
- p95 latency > 200 ms (a histogram bucket boundary), OR
- traffic was being sent but no valid p95 came back (NaN: pod too overloaded to answer), OR
- more than 1% of requests failed (from k6; recorded per run).

p95 query: histogram_quantile(0.95, sum(rate(app_request_duration_seconds_bucket[30s])) by (le))

## Measured constants (also in config.yaml)
- C = 16 req/s per pod. Re-measured in a fast laptop state: one pod saturates near 27 req/s
  (clean at 26, failing at 28). C is about 60% of saturation, matching the CPU trigger (60%).
  An earlier measurement gave saturation near 11.5 req/s, so capacity depends on the laptop state.
- D = 4.7 s to Ready (5 tries: 5.8, 4.0, 5.0, 4.5, 4.5) = 0.39 trace-minutes.
- WORK_LOOPS = 150000, about 12-16 ms CPU per request. Probe: timeout 5 s, 6 failures.

## Rule for every experiment
Laptop plugged in, power mode Best performance, other apps closed.
Before a batch run k8s/k6/probe.sh: 12 req/s on one pod must give p95 <= 50 ms, otherwise do not start.
Before every run use k8s/k6/reset.sh (exactly 1 ready pod, stable 40 s).

## Methodology note: connection reuse
k6 reused HTTP connections and kube-proxy balances per connection: a pod added mid-run got 0.2 req/s while the
old pod carried 25 req/s. All replay runs use noConnectionReuse: true (k8s/k6/replay.js).
Runs made before the fix are results/old_reuse_*.parquet and are NOT valid. C and D (single pod) are unaffected.

## Reactive baselines (CPU-only KEDA, valid runs)
| Scenario | Run file | Violating windows | Peak replicas | Replica-minutes |
|---|---|---|---|---|
| Real trace, fn 6352f922.. day 11 min 910-1030 (+5 warm-up), C=16 | baseline_real_rise2 | 8 of 121 | 3 | 48.0 |
| Burst 10 -> 60 req/s for 120 s (clean start) | baseline_burst4 | 12 of 36 | 2 | 9.8 |
Single runs. burst3 (16 of 36) started with 2 pods and is not a clean repeat. Repeat before quoting means.
