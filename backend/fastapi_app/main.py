# backend/fastapi_app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import redis
import json
import os
import asyncio

app = FastAPI(title="Swarm Stream")

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

async def event_stream(run_id: str):
    pubsub = r.pubsub()
    pubsub.subscribe(f"run:{run_id}")
    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                data = json.loads(message["data"])
                yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(0.1)
    finally:
        pubsub.unsubscribe()
        pubsub.close()

@app.get("/stream/{run_id}")
async def stream(run_id: str, request: Request):
    return StreamingResponse(event_stream(run_id), media_type="text/event-stream")