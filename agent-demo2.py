#!/usr/bin/env python3
"""
agent-demo2 — a terminal travel-planning agent powered by Claude.

Run it from the terminal:

    python agent-demo2.py

It collects the details of a typical vacation plan (dates, budget, party,
interests, ...), then asks Claude to suggest destinations and sample flight
options, and prints a structured plan.

The Anthropic API key is read from config.env (ANTHROPIC_API_KEY=...).
"""

import os
import sys
from pathlib import Path

import anthropic

MODEL = "claude-opus-4-8"
CONFIG_FILE = Path(__file__).with_name("config.env")

# Windows terminals often default to cp1252, which can't render emoji or many
# place names. Force UTF-8 so output (and Claude's streamed text) prints cleanly.
for _stream in (sys.stdout, sys.stdin, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def load_config(path: Path) -> None:
    """Load KEY=VALUE lines from config.env into the process environment.

    Existing environment variables win, so an already-exported
    ANTHROPIC_API_KEY is not overwritten.
    """
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_client() -> anthropic.Anthropic:
    load_config(CONFIG_FILE)
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key or key == "sk-ant-your-key-here":
        sys.exit(
            "No valid ANTHROPIC_API_KEY found.\n"
            f"Edit {CONFIG_FILE.name} and set ANTHROPIC_API_KEY to your real key."
        )
    return anthropic.Anthropic(api_key=key)


# --------------------------------------------------------------------------- #
# Interview
# --------------------------------------------------------------------------- #
def ask(prompt: str, default: str = "") -> str:
    """Prompt the user, returning the default on empty input."""
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(0)
    return answer or default


QUESTIONS = [
    ("origin", "Where will you be departing from (city / airport)", ""),
    ("destination", "Any destination in mind? (leave blank for suggestions)", "open to ideas"),
    ("dates", "When do you want to travel (dates or month)", "flexible"),
    ("duration", "How many nights", "7"),
    ("travelers", "Who's going (e.g. 2 adults, 1 child)", "2 adults"),
    ("budget", "Approximate total budget (with currency)", "flexible"),
    ("interests", "Interests / vibe (beach, hiking, food, culture, nightlife...)", "a bit of everything"),
    ("pace", "Preferred pace (relaxed / balanced / packed)", "balanced"),
    ("constraints", "Any constraints? (dietary, mobility, visa, weather...)", "none"),
]


def collect_trip() -> dict:
    print("=" * 60)
    print("  🌍  agent-demo2 — your terminal travel planner")
    print("=" * 60)
    print("Answer a few questions (press Enter to accept the default).\n")
    trip = {}
    for key, question, default in QUESTIONS:
        trip[key] = ask(question, default)
    print()
    return trip


# --------------------------------------------------------------------------- #
# Planning
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = (
    "You are an expert travel planner. Based on the traveler's details, "
    "produce a concise, practical vacation plan. Structure your answer with "
    "these sections:\n"
    "1. Recommended destination(s) — if the traveler named one, tailor to it; "
    "otherwise suggest 2-3 spots that fit their budget, dates, and interests, "
    "with a one-line reason for each.\n"
    "2. Suggested itinerary — a short day-by-day or thematic outline for the "
    "trip length.\n"
    "3. Sample flight options — 2-3 realistic routing/airline options from the "
    "traveler's origin (approximate typical price ranges and durations; note "
    "these are estimates, not live fares).\n"
    "4. Budget snapshot — rough split across flights, lodging, food, activities.\n"
    "5. Practical tips — best time to book, weather, visas, or packing notes "
    "relevant to their constraints.\n\n"
    "Be specific and realistic. Clearly flag that prices are estimates and "
    "should be confirmed on a booking site."
)


def build_user_message(trip: dict) -> str:
    lines = ["Here are my vacation details:", ""]
    labels = {
        "origin": "Departing from",
        "destination": "Destination preference",
        "dates": "Travel dates",
        "duration": "Nights",
        "travelers": "Travelers",
        "budget": "Budget",
        "interests": "Interests",
        "pace": "Pace",
        "constraints": "Constraints",
    }
    for key, label in labels.items():
        lines.append(f"- {label}: {trip[key]}")
    lines.append("")
    lines.append("Please build my vacation plan.")
    return "\n".join(lines)


def plan_trip(client: anthropic.Anthropic, trip: dict) -> None:
    print("Planning your trip with Claude...\n")
    print("-" * 60)
    with client.messages.stream(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(trip)}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print("\n" + "-" * 60)
    print("\nSafe travels! ✈️  (Prices shown are estimates — confirm before booking.)")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    client = get_client()
    trip = collect_trip()
    try:
        plan_trip(client, trip)
    except anthropic.APIError as exc:
        sys.exit(f"\nAPI error: {exc}")


if __name__ == "__main__":
    main()
