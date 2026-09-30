# CloudPilot

A trust **Gate** for predictive autoscaling on Kubernetes. Forecasts are used only when they look reliable;
otherwise scaling falls back to the normal reactive autoscaler (HPA via KEDA).

See `PLAN.md` for the roadmap and `docs/` for decisions (SLA, timing, cohort).

## Layout
```
cloudpilot/trace/      Azure trace -> series, cohort selection, rates.json for k6
cloudpilot/forecast/   forecasters (Phase 2)
cloudpilot/calibrate/  conformal calibration (Phase 2)
cloudpilot/sim/        mini-simulator (Phase 2)
cloudpilot/gate/       THE GATE (Phase 3)
cloudpilot/live/       recorder now, exporter in Phase 3
k8s/app/               demo app (FastAPI) + deployment
k8s/k6/                trace replay (run.sh)
k8s/keda/              ScaledObjects
docs/  config.yaml  results/  data/ (git-ignored)
```

## Quick start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. data (Azure Functions Trace 2019, CC-BY; cite Shahrad et al., USENIX ATC 2020)
mkdir -p data/raw && cd data/raw
curl -L -O "https://github.com/Azure/AzurePublicDataset/releases/download/dataset-functions-2019/azurefunctions_dataset2019_azurefunctions-dataset2019.tar.xz"
tar -xJf azurefunctions_dataset2019_azurefunctions-dataset2019.tar.xz && cd ../..
python -m cloudpilot.trace.build_series data/raw data/processed 20
python -m cloudpilot.trace.select_cohort data/processed
python -m cloudpilot.trace.make_rates <function_key> <day 1-14> <C_rps>

# 2. cluster pieces
eval $(minikube docker-env)
docker build -t demo-app:v1 k8s/app
kubectl apply -f k8s/app/deployment.yaml
kubectl apply -f k8s/keda/scaledobject-cpu-only.yaml
./k8s/k6/run.sh
```
`k8s/k6/rates.json` in the repo is a sample made with placeholder C = 15. Regenerate it with your measured C.
