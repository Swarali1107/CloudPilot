import time
from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, make_asgi_app

app = FastAPI()
REQS = Counter("app_requests_total", "Total /work requests")
LAT = Histogram("app_request_duration_seconds", "Latency of /work requests",
                buckets=[0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5])
app.mount("/metrics", make_asgi_app())

WORK_LOOPS = 150_000   # tune so one /work call burns about 10 ms of CPU (see docs/sla.md)

@app.middleware("http")
async def timing(request: Request, call_next):
    t0 = time.perf_counter()
    resp = await call_next(request)
    if request.url.path == "/work":
        REQS.inc()
        LAT.observe(time.perf_counter() - t0)
    return resp

@app.get("/work")
def work():
    x = 0
    for i in range(WORK_LOOPS):
        x += i * i
    return {"ok": True}

@app.get("/healthz")
def healthz():
    return {"ok": True}
