# backend/core/crew_mission.py
import os
import uuid
from datetime import datetime

from crewai import Agent, Task, Crew
from langchain_groq import ChatGroq
from django.utils import timezone

from core.models import AgentRun, AgentMessage
from core.redis_client import publish_message


llm = ChatGroq(
    model="groq/llama-3.1-8b-instant",
    temperature=0,
)

def publish(run_id: uuid.UUID, agent_name: str, content: str, msg_type: str = "thought", tool: str = ""):
    data = {
        "run_id": run_id,
        "agent_name": agent_name,
        "content": content,
        "type": msg_type,
        "tool": tool,
        "timestamp": datetime.utcnow().isoformat()
    }
    publish_message(run_id, data)

    run = AgentRun.objects.get(run_id=run_id)
    AgentMessage.objects.create(
        run=run,
        agent_name=agent_name,
        content=content,
        message_type=msg_type,
        tool_used=tool,
    )


def run_swarm_mission(mission_name: str = "2025 AI Agent Trends Report") -> uuid.UUID:
    run_id = uuid.uuid4()
    run = AgentRun.objects.create(run_id=run_id, name=mission_name)

    original_print = print
    def custom_print(*args, **kwargs):
        text = " ".join(map(str, args))
        if any(k in text for k in ["Thought:", "Final Answer:", "Action:", "Observation:"]):
            agent_name = text.split(" - ")[0] if " - " in text else "Agent"
            publish(run_id, agent_name, text.strip(), "thought")
        original_print(*args, **kwargs)

    import builtins
    builtins.print = custom_print

    publish(run_id, "Manager", f"Starting mission: {mission_name}", "thought")

    researcher = Agent(
        role="Senior Research Analyst",
        goal="Find the hottest AI agent trends for 2025",
        backstory="World-class researcher at top VC firm",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    writer = Agent(
        role="Tech Writer",
        goal="Write viral LinkedIn posts",
        backstory="Ex-tech journalist with 2M followers",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    task1 = Task(
        description="List top 5 AI agent trends for 2025 with sources",
        expected_output="Bullet list with links",
        agent=researcher,
    )

    task2 = Task(
        description="Turn the research into a single viral LinkedIn post <280 words",
        expected_output="Ready-to-post LinkedIn text",
        agent=writer,
    )

    crew = Crew(agents=[researcher, writer], tasks=[task1, task2], verbose=True)
    result = crew.kickoff()
    print("[DJANGO DEBUG] kickoff complete - publishing final")

    publish(run_id, "Manager", f"Mission completed!\n\n{result}", "final")

    run.status = "completed"
    run.finished_at = timezone.now()
    run.save()

    builtins.print = original_print
    return run_id