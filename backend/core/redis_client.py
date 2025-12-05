# backend/core/redis_client.py
import os
import json
import uuid
import redis
from datetime import datetime

# Connect to Redis
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def publish_message(run_id: uuid.UUID | str, data: dict):
    """
    Publishes a message to Redis channel `run:{run_id}`
    Automatically converts UUID → str and datetime → isoformat
    """
    channel = f"run:{run_id}"
    payload = json.dumps(data, cls=UUIDEncoder)
    r.publish(channel, payload)