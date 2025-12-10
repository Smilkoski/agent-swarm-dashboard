import os
import json
import uuid
import redis
import datetime

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def publish_message(run_id, data: dict):
    """
    Publishes a message to Redis channel `run:{run_id}`
    """
    channel = f"run:{str(run_id)}"
    now = datetime.datetime.now()
    formatted_string = now.strftime("%H:%M:%S.%f")
    print(f"[REDIS DEBUG] Publishing to channel '{channel}' content:{data['content'][:300]} time:{formatted_string}")

    payload = json.dumps(data, cls=UUIDEncoder)

    # Pub/sub (live subscribers)
    result = r.publish(channel, payload)
    print(f"[REDIS DEBUG] Pub/sub result: {result} affected subscribers")
