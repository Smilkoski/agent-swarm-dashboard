# backend/fastapi_app/main.py
import asyncio
import datetime
import json
import os

import redis
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Swarm Stream")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


@app.get("/health")
async def health():
    return {"status": "OK", "redis_connected": r.ping()}


async def event_stream(run_id: str):
    now = datetime.datetime.now()
    formatted_string = now.strftime("%H:%M:%S.%f")
    channel = f"run:{str(run_id)}"

    pubsub = r.pubsub()
    pubsub.subscribe(channel)

    print(f"[FASTAPI DEBUG] Subscribed to live channel 'run:{run_id}' time:{formatted_string}")

    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data = json.loads(message["data"])
                yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)
    finally:
        pubsub.unsubscribe()
        pubsub.close()
        print(f"[FASTAPI DEBUG] Stream ended for {run_id}")

@app.get("/stream/{run_id}")
async def stream(run_id: str, request: Request):
    print(f"[FASTAPI DEBUG] Route hit: /stream/{run_id} from {request.client.host}")
    return StreamingResponse(event_stream(run_id), media_type="text/event-stream")