import platform
import signal



def patch_signals_for_windows():
    """Define missing POSIX signals on Windows for CrewAI's SignalType enum."""
    if platform.system() != 'Windows':
        return  # POSIX systems (Linux/macOS) have these natively

    # Standard Unix signal values (from <signal.h>); dummies for Windows
    missing_signals = {
        'SIGHUP': 1,
        'SIGINT': 2,  # Actually available on Windows, but ensure
        'SIGQUIT': 3,
        'SIGILL': 4,
        'SIGTRAP': 5,
        'SIGABRT': 6,  # Available
        'SIGBUS': 7,
        'SIGFPE': 8,   # Available
        'SIGKILL': 9,
        'SIGUSR1': 10,
        'SIGSEGV': 11, # Available
        'SIGUSR2': 12,
        'SIGPIPE': 13,
        'SIGALRM': 14,
        'SIGTERM': 15, # Available
        'SIGSTKFLT': 16,
        'SIGCHLD': 17,
        'SIGCONT': 18,
        'SIGSTOP': 19,
        'SIGTSTP': 20, # The new culprit
        'SIGTTIN': 21,
        'SIGTTOU': 22,
        'SIGURG': 23,
        'SIGXCPU': 24,
        'SIGXFSZ': 25,
        'SIGVTALRM': 26,
        'SIGPROF': 27,
        'SIGWINCH': 28,
        'SIGIO': 29,
        'SIGPWR': 30,
        'SIGSYS': 31,
        'SIGRTMIN': 34,  # Real-time signals (extend as needed)
        'SIGRTMAX': 64,
    }

    for attr, value in missing_signals.items():
        if not hasattr(signal, attr):
            setattr(signal, attr, value)

    print("[DJANGO DEBUG] Full Windows signal patch applied for CrewAI")

patch_signals_for_windows()

import time
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