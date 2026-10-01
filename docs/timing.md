# Timing table (trace time vs real time)

Replay speed 5x. 1 trace-minute = 12 real seconds. Lead times are reported in trace-minutes.

| Timer | Default | Our value | Where set |
|---|---|---|---|
| HPA sync period | 15 s | 5 s (verified in kube-controller-manager) | minikube start --extra-config=controller-manager.horizontal-pod-autoscaler-sync-period=5s |
| KEDA pollingInterval | 30 s | 5 s (no effect on CPU trigger; matters for the Phase 3 Prometheus trigger) | k8s/keda/*.yaml |
| Prometheus scrape interval | chart default | 10 s global, 5 s demo-app | helm values / ServiceMonitor |
| Scale-down stabilization | 300 s | 36 s (3 trace-min) | ScaledObject behavior |
| metrics-server refresh | about 15 s | not changed (known limit) | - |
| Pod start-up D | - | 4.7 s = 0.39 trace-min | measured |

Rule: forecast horizon h (trace-minutes) >= D (trace-minutes). h = 3 >= 0.39, OK.
