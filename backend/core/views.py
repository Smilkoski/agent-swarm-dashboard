# backend/core/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .models import AgentRun
from agents.crew_mission import run_swarm_mission


def dashboard(request):
    return render(request, "dashboard.html")


def run_detail(request, run_id):
    get_object_or_404(AgentRun, run_id=run_id)
    return render(request, "dashboard.html", {"run_id": run_id})


@csrf_exempt
def start_mission(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name", "New Mission")
        run_id = run_swarm_mission(name)
        return JsonResponse({"run_id": str(run_id)})
    return JsonResponse({"error": "POST only"}, status=400)
