"""Vercel serverless function — streams a travel plan from Claude.

This is the web counterpart of agent-demo2.py. It receives the traveler's
answers as JSON, then streams back the same structured plan the terminal
agent produces, using the same model and system prompt.

The Anthropic API key is read from the ANTHROPIC_API_KEY environment
variable (set in the Vercel project settings — never committed to git).
"""

from http.server import BaseHTTPRequestHandler
import json
import os

import anthropic

MODEL = "claude-opus-4-8"

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

LABELS = {
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


def build_user_message(trip: dict) -> str:
    lines = ["Here are my vacation details:", ""]
    for key, label in LABELS.items():
        value = str(trip.get(key, "") or "—").strip()
        lines.append(f"- {label}: {value}")
    lines.append("")
    lines.append("Please build my vacation plan.")
    return "\n".join(lines)


class handler(BaseHTTPRequestHandler):
    def _send_headers(self, status: int, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key or key == "sk-ant-your-key-here":
            self._send_headers(500, "text/plain; charset=utf-8")
            self.wfile.write(
                b"Server is missing a valid ANTHROPIC_API_KEY. "
                b"Set it in the Vercel project environment variables."
            )
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            trip = json.loads(body.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            self._send_headers(400, "text/plain; charset=utf-8")
            self.wfile.write(b"Invalid request body.")
            return

        client = anthropic.Anthropic(api_key=key)

        # Stream the plan back to the browser as plain text, chunk by chunk,
        # so the floating window fills in live — just like the terminal.
        self._send_headers(200, "text/plain; charset=utf-8")
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_message(trip)}],
            ) as stream:
                for text in stream.text_stream:
                    self.wfile.write(text.encode("utf-8"))
                    self.wfile.flush()
        except anthropic.APIError as exc:
            self.wfile.write(f"\n\n[API error: {exc}]".encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError):
            pass
