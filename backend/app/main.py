import asyncio
from fastapi import FastAPI
import uvicorn
from .routers import auth as r_auth, devices as r_devices, map as r_map, charts as r_charts
from .mqtt_runtime import run_mqtt_forever

app = FastAPI(title="IoT Backend", version="0.1.0")

app.include_router(r_auth.router)
app.include_router(r_devices.router)
app.include_router(r_map.router)
app.include_router(r_charts.router)

@app.on_event("startup")
async def _startup():
    app.state.mqtt_task = asyncio.create_task(run_mqtt_forever())

@app.on_event("shutdown")
async def _shutdown():
    app.state.mqtt_task.cancel()
    try:
        await app.state.mqtt_task
    except asyncio.CancelledError:
        print("MQTT task cancelled")
        raise

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