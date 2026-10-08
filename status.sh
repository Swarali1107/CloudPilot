#!/usr/bin/env bash
cd "$(dirname "$0")"
echo "=== cluster ==="
minikube status 2>/dev/null | head -4
kubectl get nodes --no-headers
bad=$(kubectl get pods -A --no-headers | awk '{split($3,a,"/"); if ($4!="Completed" && (a[1]!=a[2] || $4!="Running")) print "  "$0}')
echo "pods not ready:"; [ -z "$bad" ] && echo "  none" || echo "$bad"
echo; echo "=== app and autoscaler ==="
kubectl get pods --no-headers | grep demo-app
kubectl get scaledobject --no-headers
echo; echo "=== constants (config.yaml) ==="
grep -E "C_rps|D_seconds|p95_threshold" config.yaml
echo; echo "=== git ==="
git log --oneline | head -6
git status --short | head
echo; echo "=== saved results ==="
ls -1 results | head -30
echo; echo "=== Phase 2 files ==="
ls cloudpilot/forecast cloudpilot/calibrate 2>/dev/null | grep -v __pycache__
