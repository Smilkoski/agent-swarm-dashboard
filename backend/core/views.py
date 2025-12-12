import math
import uuid
from collections import defaultdict
import json

from django.db.models import F
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import AgentRun, AgentMessage
from agents.crew_mission import run_feasibility_mission, run_swarm_mission, run_conference_planing


def dashboard(request):
    context = {
        "history": get_history()
    }

    return render(request, "dashboard.html", context)


def run_detail(request, run_id):
    agent = get_object_or_404(AgentRun, run_id=run_id)
    messages = []

    if agent and agent.status == "completed":
        messages = (
                    AgentMessage.objects.filter(run_id=run_id)
                        .values("agent_name","content","message_type","timestamp")
                        .order_by("timestamp")
                )
        messages = [
            {
                **msg,
                "timestamp": msg["timestamp"].strftime("%H:%M:%S") if msg["timestamp"] else "—"
            }
            for msg in messages
        ]
    context = {
        "messages_json": json.dumps(messages),
        "history": get_history()
    }
    return render(request, "dashboard.html", context)


@csrf_exempt
def create_agent(request):
    run_id = uuid.uuid4()
    print(f'run_id {run_id}')
    run = AgentRun.objects.create(run_id=run_id)
    run.save()

    return JsonResponse({"run_id": str(run_id)})


@csrf_exempt
def start_mission(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name", "New Mission")
        run_id = data.get("run_id", 0)
        mission_type = data.get("type", "feasibility")

        if mission_type == "swarm":
            run_swarm_mission(name, run_id)
        elif mission_type == "feasibility":
            run_feasibility_mission(idea=name, run_id=run_id)
        elif mission_type == "conference":
            run_conference_planing(mission_name=name, run_id=run_id)
        else:
            return JsonResponse({"error": "Invalid mission type"}, status=400)

        return JsonResponse({"run_id": str(run_id)})
    return JsonResponse({"error": "POST only"}, status=400)

def get_history():
    history = list(
        AgentMessage.objects
        .filter(
            run__status="completed"
        )
        .select_related('run')
        .values(
            'content',
            run_uuid=F('run__run_id'),
            run_name=F('run__name'),
            run_started_at=F('run__started_at'),
        )
        .order_by('timestamp')
    )
    run_ids = set([str(h['run_uuid']) for h in history])
    new_history = defaultdict(lambda: {"tokens": 0})

    for msg in history:
        rid = str(msg["run_uuid"])
        if rid not in run_ids:
            continue

        if "run_id" not in new_history[rid]:
            new_history[rid].update({
                "run_id": rid,
                "name": msg.get("run_name", "Untitled Mission"),
                "started_at": (
                    msg["run_started_at"].strftime("%H:%M:%S")
                    if msg["run_started_at"] else "—"
                ),
            })

        new_history[rid]["tokens"] += count_tokens(msg["content"])

    new_history = dict(new_history)
    return new_history.values()


def count_tokens(text):
    return math.ceil(len(text) / 4)