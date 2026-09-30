# Chosen Azure functions (fill after running select_cohort; see data/processed/function_scores.csv)

Pick at most ONE function per app (twins give duplicate data). Timer triggers are excluded (cron jobs, not demand).

| Role | key | trigger | mean/min | daily_ac | notes |
|---|---|---|---|---|---|
| Patterned 1 |  |  |  |  |  |
| Patterned 2 |  |  |  |  |  |
| Patterned 3 |  |  |  |  |  |
| Patterned 4 |  |  |  |  |  |
| Bursty 1 |  |  |  |  |  |
| Bursty 2 |  |  |  |  |  |
| Held-out (Unseen) 1 |  |  |  |  | different trigger group, never used for tuning |
| Held-out (Unseen) 2 |  |  |  |  |  |

Data: Azure Functions Trace 2019, CC-BY. Cite: Shahrad et al., "Serverless in the Wild", USENIX ATC 2020.
