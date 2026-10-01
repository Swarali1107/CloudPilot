# Chosen Azure functions (from select_cohort; Person B to confirm against plots in Phase 2)

One function per app (owner_app prefix is different for all eight). Timer triggers excluded.

| Role | key | trigger | mean/min | daily_ac |
|---|---|---|---|---|
| Patterned 1 | 6352f922_6d52e936_f375f0228b10 | http | 106.75 | 0.99 |
| Patterned 2 | 65ae55ea_d27d1fdd_5336bda8faa5 | event | 2868.06 | 0.98 |
| Patterned 3 | cec35dbb_076b740a_14f72e22ca86 | http | 137.48 | 0.98 |
| Patterned 4 | 7656026e_9aba8d35_2aec780b74ed | http | 693.80 | 0.98 |
| Bursty 1 | 612a94f7_43f752c7_17b64d842f96 | http | 819.18 | 0.20 |
| Bursty 2 | f96d34ee_bf415a17_cba2d4a3cb55 | event | 736.80 | 0.13 |
| Held-out (Unseen) 1 | 6e26c53b_70856110_9467f3a82699 | orchestration | 319.47 | 0.95 |
| Held-out (Unseen) 2 | 6aeca4ea_36bc5682_bde06c0fbc47 | storage | 182.41 | 0.73 |

Avoided: the two dca12906_* functions (peak 1300x mean, twins of one app).
Data: Azure Functions Trace 2019, CC-BY. Cite: Shahrad et al., "Serverless in the Wild", USENIX ATC 2020.
