#!/usr/bin/env bash
# Replays k8s/k6/rates.json against demo-app. Prints the start/end unix times for recorder.py
set -e
cd "$(dirname "$0")"
kubectl delete job k6-replay --ignore-not-found
kubectl delete configmap k6-script --ignore-not-found
kubectl create configmap k6-script --from-file=replay.js --from-file=rates.json
START=$(date +%s)
kubectl apply -f k6-job.yaml
kubectl wait --for=condition=Ready pod -l job-name=k6-replay --timeout=120s || true
kubectl logs -f job/k6-replay || true
END=$(date +%s)
echo
echo "RUN START=$START END=$END"
echo "Save it:  python -m cloudpilot.live.recorder --start $START --end $END --out results/<name>.parquet"
