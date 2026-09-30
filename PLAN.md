# CloudPilot roadmap (turn each checkbox into a GitHub issue; one milestone per phase)

## Phase 1: the stage (Oct 1 - Nov 8)
- [ ] Tools installed (Docker, minikube, kubectl, helm, Python)  - DONE if you followed the setup
- [ ] Minikube + metrics-server running
- [ ] kube-prometheus-stack (Alertmanager off) + Grafana reachable
- [ ] KEDA installed
- [ ] demo app deployed (k8s/app), graphs for rps / p95 / pods in Grafana
- [ ] k6 replay works with k8s/k6/rates.json (run k8s/k6/run.sh)
- [ ] Measure C and D, write them in config.yaml
- [ ] SLA rule written in docs/sla.md
- [ ] KEDA CPU-only baseline applied, burst run shows the reactive lag
- [ ] recorder saves a run to results/*.parquet
- [ ] Timing table done (docs/timing.md)  -> "Done when": one Grafana page shows load, replicas, p95 in a burst

## Phase 2: the predictor (Oct 26 - Dec 13)
- [ ] Azure data downloaded, build_series + select_cohort run, cohort chosen (docs/cohort.md)
- [ ] Forecaster interface + forecast-store schema agreed: function, scenario, seed, t, y, p10, p50, p90, L, U, q, forecaster
- [ ] Chronos-2 forecasts cached (h = 1..5, primary h = 3) + "same as last minute" and "same as yesterday" baselines
- [ ] Prophet forecaster
- [ ] LSTM forecaster (neuralforecast or darts)
- [ ] CQR calibration + rolling recalibration + ACI; coverage-over-time plot
- [ ] Scenario injector (Normal, Noisy, Spike, Drift, Pattern change, Unseen) with tuning seeds and test seeds
- [ ] Mini-simulator (ready pods, start-up delay D, violation if demand > ready x C), checked against one live run

## Phase 3: the Gate (Nov 16 - Mar 14)
- [ ] 3A offline: four signals S1 width, S2 error, S3 coverage shortfall, S4 drift (KS on de-seasonalized demand)
- [ ] Labels from the simulator on TUNING scenarios (not test seeds)
- [ ] Weights: uniform vs grid vs logistic (AUROC), freeze the winner
- [ ] Hysteresis gate + grid-search of thresholds; naive-threshold comparison
- [ ] Policies: always-blind, HPA-only, SLO-fallback, CloudPilot
- [ ] Offline experiments: ablation, weights, hysteresis, main table
- [ ] 3B live: exporter (prometheus_client) publishing cloudpilot_desired_replicas, mode, risk, signals
- [ ] KEDA ScaledObject with cpu trigger + prometheus trigger; test by setting the gauge by hand
- [ ] Grafana dashboard JSON exported to the repo
- [ ] 3C: 72 live runs (6 scenarios x 4 systems x 3 seeds, Chronos-2); other forecasters offline
- [ ] Metrics: SLA violations, replica-minutes, switches/hour, lead time, false alarms in Normal
- [ ] 3D: report, paper, demo video, README reproduction

## Traps
- Kubernetes timers are real seconds; your trace is 5x compressed. Set them consistently.
- Forecast horizon must be >= pod start-up time D (in trace-minutes).
- Never use a forecast's error before its target minute has arrived.
- Tune only on tuning seeds. Never touch test seeds.
- Check each reference repo's licence before copying code.
