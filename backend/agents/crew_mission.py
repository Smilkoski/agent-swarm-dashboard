import os
import platform
import signal

from pydantic import SecretStr


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
from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
from core.models import AgentRun, AgentMessage
from core.redis_client import publish_message


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


def run_research_mission(mission_name: str = "2025 AI Agent Trends Report", run_id: str = '') -> str:
    run = get_object_or_404(AgentRun, run_id=run_id)
    run.name = mission_name

    publish(run_id, "Manager", f"Starting mission: {mission_name}", "thought")

    llm = ChatGroq(
        model="groq/llama-3.1-8b-instant",
        temperature=0,
        api_key=SecretStr(os.getenv("GROQ_API_KEY",""))
    )

    researcher = Agent(
        role="Senior Research Analyst",
        goal=f"Find the hottest features/ trends for {mission_name}",
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

    task1 = Task(description="List top 5 features/ trends  with sources", expected_output="Bullet list with links", agent=researcher)
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


def run_feasibility_mission(idea: str = "Uber for Dog Walking in Rural Areas", run_id: str = '') -> str:
    mission_name = f"Feasibility Sprint: {idea}"
    run = get_object_or_404(AgentRun, run_id=run_id)
    run.name = mission_name
    publish(run_id, "Manager", f"Starting 6-Agent Sprint for: {idea}", "thought")

    # Limit to 5900 tokens to meet api requirements
    llm = ChatGroq(
        model="groq/llama-3.1-8b-instant",
        temperature=0.3,
        max_tokens=5900,
    )

    # 6 Agents
    product_mgr = Agent(
        role="Product Manager",
        goal="Define the core value proposition concisely.",
        backstory="You focus on viability. You hate fluff. You want to know WHO needs this.",
        llm=llm, verbose=True, allow_delegation=False
    )

    ux_designer = Agent(
        role="Lead UX Designer",
        goal="Identify top 3 user friction points.",
        backstory="You advocate for the user. You foresee usability nightmares in rural settings.",
        llm=llm, verbose=True, allow_delegation=False
    )

    tech_lead = Agent(
        role="Engineering Lead",
        goal="Assess technical feasibility and connectivity issues.",
        backstory="You are a pragmatist. You worry about GPS signals in the woods.",
        llm=llm, verbose=True, allow_delegation=False
    )

    marketer = Agent(
        role="Marketing Specialist",
        goal="Define the target audience and one viral hook.",
        backstory="You know how to sell ice to eskimos, but you need a real market here.",
        llm=llm, verbose=True, allow_delegation=False
    )

    legal_advisor = Agent(
        role="Legal Counsel",
        goal="Spot the biggest liability risk.",
        backstory="You protect the company. You worry about dog bites and trespassing laws.",
        llm=llm, verbose=True, allow_delegation=False
    )

    qa_specialist = Agent(
        role="QA Strategist",
        goal="Define the 'Happy Path' vs 'Edge Cases'.",
        backstory="You break things. You wonder what happens when the dog runs away.",
        llm=llm, verbose=True, allow_delegation=False
    )

    # Tasks

    task_pm = Task(
        description=f"Analyze '{idea}'. Output a 3-bullet executive summary of the value prop. Keep it under 100 words.",
        expected_output="3 bullet points summarizing value.",
        agent=product_mgr
    )

    task_ux = Task(
        description="List the top 3 user interface challenges for rural users (e.g., offline mode). Keep it under 100 words.",
        expected_output="3 bullet points on UX friction.",
        agent=ux_designer
    )

    task_tech = Task(
        description="Assess the technical stack needed. Highlight one major connectivity risk. Keep it under 100 words.",
        expected_output="Tech stack summary + 1 major risk.",
        agent=tech_lead
    )

    task_mkt = Task(
        description="Identify the primary customer persona. Write one catchy tagline. Keep it under 50 words.",
        expected_output="Persona + Tagline.",
        agent=marketer
    )

    task_legal = Task(
        description="Identify the single biggest legal liability for this idea. Keep it under 50 words.",
        expected_output="One major legal risk.",
        agent=legal_advisor
    )

    task_qa = Task(
        description="Describe one critical 'edge case' scenario that could fail the product. Keep it under 50 words.",
        expected_output="One edge case description.",
        agent=qa_specialist
    )

    def process_callback(output):
        text = "No output"
        if hasattr(output, 'raw_output'):
            text = output.raw_output
        elif hasattr(output, 'result'):
            text = output.result
        elif hasattr(output, 'output'):
            text = output.output
        else:
            text = str(output)

        # Enforce content length check on the output side (Double check)
        if len(text) > 23000:
            text = text[:23000] + "... [TRUNCATED]"

        agent_identity = "Agent"
        if "value prop" in text.lower():
            agent_identity = "Product Manager"
        elif "friction" in text.lower():
            agent_identity = "UX Designer"
        elif "connectivity" in text.lower():
            agent_identity = "Engineering Lead"
        elif "persona" in text.lower():
            agent_identity = "Marketing Specialist"
        elif "liability" in text.lower():
            agent_identity = "Legal Counsel"
        elif "edge case" in text.lower():
            agent_identity = "QA Strategist"

        msg_type = "final" if "Final Answer" in text else "thought"
        publish(run_id, agent_identity, text, msg_type)

        # print("[DJANGO DEBUG] Rate-limit pause: sleeping 60 seconds before next agent...")
        # time.sleep(60)

    crew = Crew(
        agents=[product_mgr, ux_designer, tech_lead, marketer, legal_advisor, qa_specialist],
        tasks=[task_pm, task_ux, task_tech, task_mkt, task_legal, task_qa],
        verbose=True,
        step_callback=process_callback
    )

    try:
        publish(run_id, "Manager", "Starting Feasibility Sprint...", "info")
        result = crew.kickoff()

        # Final Format
        final_summary = f"""
        # SPRINT COMPLETE: {idea}

        {result}
        """

        publish(run_id, "Manager", final_summary, "final")

        run.status = "completed"
        run.result = str(result)
        run.finished_at = timezone.now()
        run.save()

    except Exception as e:
        publish(run_id, "System", f"Error: {str(e)}", "error")
        run.status = "failed"
        run.save()

    return run_id


def run_conference_planing(mission_name: str = "Corporate Conference Planning", run_id: str = '') -> str:
    """
    Multi-agent system for planning a corporate conference.
    Each agent handles a specific aspect with rate-limited outputs.
    """
    run = get_object_or_404(AgentRun, run_id=run_id)
    run.name = mission_name
    publish(run_id, "Manager", f"Starting mission: {mission_name}", "thought")

    llm = ChatGroq(
        model="groq/llama-3.1-8b-instant",
        temperature=0.3,
        max_tokens=5900
    )

    venue_scout = Agent(
        role="Venue Scout",
        goal="Find 3 suitable venues for a 200-person tech conference. Output max 400 words.",
        backstory="Event space specialist with 15 years finding perfect venues",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    catering = Agent(
        role="Catering Coordinator",
        goal="Design a menu for breakfast, lunch, and breaks. Output max 350 words.",
        backstory="Executive chef turned event catering expert",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    speaker_liaison = Agent(
        role="Speaker Liaison",
        goal="Create speaker lineup with 5 industry experts. Output max 400 words.",
        backstory="Former TEDx organizer with network of top tech speakers",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    av_tech = Agent(
        role="AV Technical Specialist",
        goal="List all audiovisual equipment and setup needs. Output max 300 words.",
        backstory="Sound engineer with expertise in conference production",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    marketing = Agent(
        role="Marketing Strategist",
        goal="Create promotional campaign for the event. Output max 400 words.",
        backstory="Digital marketing expert who has promoted 50+ conferences",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    budget = Agent(
        role="Budget Analyst",
        goal="Create itemized budget breakdown. Output max 350 words.",
        backstory="Financial planner specializing in event cost management",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    timeline = Agent(
        role="Timeline Coordinator",
        goal="Build day-of schedule with all activities. Output max 300 words.",
        backstory="Operations manager known for flawless event execution",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    task1 = Task(
        description="""Research and recommend 3 venues in San Francisco for a 200-person 
        tech conference on June 15, 2025. Include capacity, pricing, and amenities.""",
        expected_output="Bullet list with 3 venues, max 400 words",
        agent=venue_scout
    )

    task2 = Task(
        description="""Design a full-day catering menu including breakfast, lunch, 
        afternoon snacks, and beverages. Account for dietary restrictions.""",
        expected_output="Menu breakdown by meal, max 350 words",
        agent=catering
    )

    task3 = Task(
        description="""Propose 5 keynote speakers for a conference about AI in enterprise. 
        Include their expertise and suggested talk topics.""",
        expected_output="Speaker list with brief bios, max 400 words",
        agent=speaker_liaison
    )

    task4 = Task(
        description="""List all AV equipment needed: mics, projectors, screens, 
        lighting, recording setup. Include backup systems.""",
        expected_output="Equipment checklist, max 300 words",
        agent=av_tech
    )

    task5 = Task(
        description="""Create a 3-month promotional campaign: email sequence, 
        social media strategy, and early bird pricing.""",
        expected_output="Campaign timeline and tactics, max 400 words",
        agent=marketing
    )

    task6 = Task(
        description="""Build complete budget: venue, catering, speakers, AV, marketing, 
        staff, and contingency fund. Target $80k total.""",
        expected_output="Itemized budget spreadsheet format, max 350 words",
        agent=budget
    )

    task7 = Task(
        description="""Create hour-by-hour schedule for conference day: registration, 
        sessions, breaks, networking, closing.""",
        expected_output="Timeline from 8am-6pm, max 300 words",
        agent=timeline
    )

    def process_callback(output):
        if hasattr(output, 'raw_output'):
            text = output.raw_output
        elif hasattr(output, 'result'):
            text = output.result
        elif hasattr(output, 'output'):
            text = output.output
        else:
            text = str(output)

        # Determine agent name from output
        agent_map = {
            "venue": "Venue Scout",
            "catering": "Catering Coordinator",
            "speaker": "Speaker Liaison",
            "av": "AV Technical Specialist",
            "audiovisual": "AV Technical Specialist",
            "marketing": "Marketing Strategist",
            "budget": "Budget Analyst",
            "timeline": "Timeline Coordinator",
            "schedule": "Timeline Coordinator"
        }

        agent_name = "Manager"
        text_lower = text.lower()
        for keyword, name in agent_map.items():
            if keyword in text_lower:
                agent_name = name
                break

        if "Final Answer" in text:
            publish(run_id, agent_name, text.strip(), "final")
        else:
            publish(run_id, agent_name, text.strip(), "thought")

        print("[DJANGO DEBUG] Rate-limit pause: sleeping 60 seconds before next agent...")
        time.sleep(60)
    crew = Crew(
        agents=[venue_scout, catering, speaker_liaison, av_tech, marketing, budget, timeline],
        tasks=[task1, task2, task3, task4, task5, task6, task7],
        verbose=False,
        process=Process.sequential,
        step_callback=process_callback
    )

    result = crew.kickoff()

    result_str = str(result)

    print("[DJANGO DEBUG] kickoff complete - publishing final")
    publish(run_id, "Manager", f"Mission completed!\n\n{result_str}", "final")

    run.status = "completed"
    run.finished_at = timezone.now()
    run.save()

    return run_id