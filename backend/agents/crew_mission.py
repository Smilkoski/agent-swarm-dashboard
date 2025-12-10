from core.models import AgentRun, AgentMessage
from core.redis_client import publish_message
from django.shortcuts import get_object_or_404
from django.utils import timezone
from crewai import Agent, Task, Crew
from langchain_groq import ChatGroq


def publish(run_id, agent_name, content, msg_type="thought"):
    data = {
        "run_id": str(run_id),
        "agent_name": agent_name,
        "content": content,
        "type": msg_type,
        "timestamp": timezone.now().isoformat()
    }
    publish_message(run_id, data)

    AgentMessage.objects.create(
        run_id=run_id,
        agent_name=agent_name,
        content=content,
        message_type=msg_type,
    )


def run_swarm_mission(mission_name: str = "2025 AI Agent Trends Report", run_id: str = 0) -> str:
    run = get_object_or_404(AgentRun, run_id=run_id)
    run.name = mission_name

    publish(run_id, "Manager", f"Starting mission: {mission_name}", "thought")

    llm = ChatGroq(
        model="groq/llama-3.1-8b-instant",
        temperature=0
    )

    researcher = Agent(
        role="Senior Research Analyst",
        goal="Find the hottest AI agent trends for 2025",
        backstory="World-class researcher at top VC firm",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    writer = Agent(
        role="Tech Writer",
        goal="Write viral LinkedIn posts",
        backstory="Ex-tech journalist with 2M followers",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    task1 = Task(description="List top 5 AI agent trends for 2025 with sources", expected_output="Bullet list with links", agent=researcher)
    task2 = Task(description="Turn the research into a viral LinkedIn post <280 words", expected_output="Ready-to-post text", agent=writer)

    def process_callback(output):
        if hasattr(output, 'raw_output'):
            text = output.raw_output
        elif hasattr(output, 'result'):
            text = output.result
        elif hasattr(output, 'output'):
            text = output.output
        else:
            text = str(output)

        if "Final Answer" in text:
            agent_name = "Tech Writer" if "writer" in text.lower() else "Senior Research Analyst"
            publish(run_id, agent_name, text.strip(), "final")
        else:
            agent_name = "Senior Research Analyst" if "researcher" in text.lower() else "Tech Writer"
            publish(run_id, agent_name, text.strip(), "thought")

    crew = Crew(
        agents=[researcher, writer],
        tasks=[task1, task2],
        verbose=False,
        step_callback=process_callback,
    )

    result = crew.kickoff()
    print("[DJANGO DEBUG] kickoff complete - publishing final")

    publish(run_id, "Manager", f"Mission completed!\n\n{result}", "final")

    run.status = "completed"
    run.finished_at = timezone.now()
    run.save()

    return run_id