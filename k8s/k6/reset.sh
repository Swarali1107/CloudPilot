#!/usr/bin/env bash
# Start every run from the same state: exactly 1 ready pod, stable for 40 s, no old k6 job.
kubectl delete job k6-replay --ignore-not-found >/dev/null
kubectl scale deploy/demo-app --replicas=1 >/dev/null
ok=0
for i in $(seq 1 60); do
  ready=$(kubectl get deploy demo-app -o jsonpath='{.status.readyReplicas}')
  total=$(kubectl get deploy demo-app -o jsonpath='{.status.replicas}')
  if [ "$ready" = "1" ] && [ "$total" = "1" ]; then ok=$((ok+1)); else ok=0; fi
  [ "$ok" -ge 4 ] && break
  sleep 10
done
echo "reset done: ready=$ready total=$total stable_checks=$ok"
