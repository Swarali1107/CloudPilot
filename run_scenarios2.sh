#!/usr/bin/env bash
cd ~/cloudpilot && source .venv/bin/activate
for s in level unseen; do
  echo "=== $s ==="
  COHORT=data/processed/cohort_$s.npz SCEN=$s OUT=results/store_gbq_$s.parquet python -m cloudpilot.forecast.gbq_fc | tail -2
  python -m cloudpilot.calibrate.cqr results/store_gbq_$s.parquet results/store_gbq_${s}_cal.parquet
  COHORT=data/processed/cohort_$s.npz python -m cloudpilot.gate.sim results/store_gbq_${s}_cal.parquet --action p50 > results/sim_log_$s.txt 2>&1
done
echo ALL DONE
