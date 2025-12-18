import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from .routers import auth as r_auth, devices as r_devices, map as r_map, charts as r_charts, tenants as r_tenants
from .mqtt_runtime import run_mqtt_forever

app = FastAPI(title="IoT Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://5.129.250.254:1883",
        "https://nikolay56615-pvz-cdc9.twc1.net",
        "http://nikolay56615-pvz-cdc9.twc1.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(r_auth.router)
app.include_router(r_devices.router)
app.include_router(r_map.router)
app.include_router(r_charts.router)
app.include_router(r_tenants.router)

logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
logger.setLevel(logging.DEBUG)
def _log_task_result(task: asyncio.Task):
    try:
        task.result()
    except asyncio.CancelledError:
        logger.warning("MQTT task cancelled")
    except Exception:
        logger.exception("MQTT task crashed")

@app.on_event("startup")
async def _startup():
    t = asyncio.create_task(run_mqtt_forever())
    t.add_done_callback(_log_task_result)
    app.state.mqtt_task = t
    logger.info("MQTT task created: %r", t)

@app.on_event("shutdown")
async def _shutdown():
    app.state.mqtt_task.cancel()

@app.get("/")
async def root():
    return {"message": "IoT Backend is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    return {"status": "ready"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)