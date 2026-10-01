# SLA definition (fixed, never change)

A 12-second window (= 1 trace-minute) is an **SLA violation** if:
- p95 latency > 200 ms, OR
- traffic was being sent but no valid p95 came back (NaN: pod too overloaded to answer), OR
- more than 1% of requests failed / timed out (from k6, added in Phase 3).

p95 query: histogram_quantile(0.95, sum(rate(app_request_duration_seconds_bucket[30s])) by (le))
The 200 ms threshold is a histogram bucket boundary (buckets are coarse: 10/20/50/100/200/300 ms).

## Measured constants (also in config.yaml)
- C = 8 req/s per pod. One pod saturates at about 11.5 req/s (step tests: p95 76 ms at 8, 151 ms at 10,
  904 ms at 12, pod unready at 14). C is about 70% of saturation.
- D = 7.4 s to Ready (5 tries: 8.4, 6.1, 7.6, 6.7, 8.4) = 0.62 trace-minutes.
- WORK_LOOPS = 150000, about 12-16 ms CPU per request.
- Readiness probe loosened (timeout 5 s, 6 failures) so a saturated pod keeps serving instead of being ejected.

## Reactive baseline (results/baseline_burst2.parquet)
Burst 4 -> 16 req/s for 120 s, CPU-only KEDA: second pod at about 120 s into the burst,
9 of 33 windows violated (27%). HPA could not read CPU from the overloaded pod.

## Methodology note: connection reuse (found in Phase 1)
k6 reused HTTP connections, and kube-proxy balances per connection. A pod added mid-run got about 0.2 req/s
while the old pod carried 25 req/s (test: 1 -> 2 pods at 25 req/s). All replay runs now use
noConnectionReuse: true in k8s/k6/replay.js (same setup for every system, so comparisons stay fair).
Runs made before this fix are stored as results/old_reuse_*.parquet and are NOT valid baselines.
C and D were measured on a single pod and are unaffected.

## Reactive baseline (valid, noConnectionReuse on) - results/baseline_real_rise2.parquet
Real trace: function 6352f922_6d52e936_f375f0228b10, day 11, minutes 910-1030 (+5 warm-up), C = 16, CPU-only KEDA.
Violating windows: 8 of 121. Peak replicas: 3. Cost: 48.0 replica-minutes. k6 failures: 0.12%.
Violations cluster in the steepest rise (about 36 -> 62 req/s): two pods were not enough and the third arrived late.
Single run; repeat before quoting as a mean.
