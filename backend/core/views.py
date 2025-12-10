import uuid

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .models import AgentRun, AgentMessage
from agents.crew_mission import run_swarm_mission


def dashboard(request):
    return render(request, "dashboard.html")


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
        run_swarm_mission(name, run_id)

        return JsonResponse({"run_id": str(run_id)})

    return JsonResponse({"error": "POST only"}, status=400)
