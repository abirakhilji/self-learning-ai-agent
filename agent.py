"""Self-learning agent, powered by Google's free Gemini API.

Loop per task:
  1. RETRIEVE  relevant lessons from memory  -> put them in the system prompt
  2. ACT       call the model, let it use tools until it answers
  3. REFLECT   ask the model what should be remembered (using feedback if any)
  4. STORE     save that lesson so the next task benefits

The model's weights never change. The agent improves because its memory does.
"""

import json
import os
import time

import requests
from dotenv import load_dotenv

import memory
from tools import GEMINI_TOOLS, run_tool

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("AGENT_MODEL", "gemini-3.8-flash")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
MAX_STEPS = 8

BASE_PROMPT = (
    "You are a careful, concise assistant with access to tools. "
    "Use tools when they help (e.g. the calculator for arithmetic). "
    "Give a direct final answer."
)


TRANSIENT_CODES = {429, 500, 503}
MAX_RETRIES = 4


def _call_gemini(contents, system, tools=None):
    """One request to the Gemini REST API, with automatic retries for busy-server errors."""
    if not API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Put it in your .env file (see .env.example)."
        )
    body = {"system_instruction": {"parts": [{"text": system}]}, "contents": contents}
    if tools:
        body["tools"] = [{"function_declarations": tools}]

    last_error = None
    for attempt in range(MAX_RETRIES):
        resp = requests.post(API_URL, params={"key": API_KEY}, json=body, timeout=60)
        if resp.status_code == 200:
            return resp.json()
        last_error = f"Gemini API error {resp.status_code}: {resp.text[:500]}"
        if resp.status_code not in TRANSIENT_CODES or attempt == MAX_RETRIES - 1:
            raise RuntimeError(last_error)
        wait = 2 ** attempt
        print(f"  (server busy, retrying in {wait}s...)")
        time.sleep(wait)
    raise RuntimeError(last_error)


class Agent:
    def __init__(self, use_memory=True, db_path=memory.DB_PATH, verbose=False):
        self.use_memory = use_memory
        self.db_path = db_path
        self.verbose = verbose

    # ---------- 1 + 2: retrieve and act ----------
    def _system_prompt(self, task):
        if not self.use_memory:
            return BASE_PROMPT
        lessons = memory.retrieve(task, db_path=self.db_path)
        if not lessons:
            return BASE_PROMPT
        bullets = "\n".join(f"- {l}" for l in lessons)
        return f"{BASE_PROMPT}\n\nLessons learned from earlier tasks (follow them):\n{bullets}"

    def run(self, task):
        """Solve `task` and return the final answer text."""
        system = self._system_prompt(task)
        contents = [{"role": "user", "parts": [{"text": task}]}]
        for _ in range(MAX_STEPS):
            data = _call_gemini(contents, system, tools=GEMINI_TOOLS)
            candidates = data.get("candidates")
            if not candidates:
                return f"Error: no response from model ({data.get('promptFeedback', data)})"
            parts = candidates[0]["content"]["parts"]
            calls = [p["functionCall"] for p in parts if "functionCall" in p]
            if not calls:
                return "".join(p.get("text", "") for p in parts).strip()
            contents.append({"role": "model", "parts": parts})
            response_parts = []
            for call in calls:
                name, args = call["name"], call.get("args", {})
                result = run_tool(name, args)
                if self.verbose:
                    print(f"  [tool] {name}({args}) -> {str(result)[:80]}")
                response_parts.append(
                    {"functionResponse": {"name": name, "response": {"result": result}}}
                )
            contents.append({"role": "user", "parts": response_parts})
        return "Stopped: too many tool steps."

    # ---------- 3 + 4: reflect and store ----------
    def reflect(self, task, answer, feedback=None):
        """Turn what just happened into one reusable lesson and save it."""
        prompt = (
            "You are reviewing your own work to improve next time.\n\n"
            f"Task: {task}\nYour answer: {answer}\n"
            f"Feedback received: {feedback or 'none'}\n\n"
            "Reply with ONLY a JSON object, no other text: "
            '{"outcome": "success" or "failure", '
            '"lesson": "one short, general, reusable sentence, or empty string if nothing useful"}. '
            "The lesson must help on FUTURE similar tasks, not restate this one."
        )
        data = _call_gemini(
            [{"role": "user", "parts": [{"text": prompt}]}],
            "You are a precise reviewer. Reply with raw JSON only, no markdown fences.",
        )
        candidates = data.get("candidates")
        if not candidates:
            return None
        raw = "".join(p.get("text", "") for p in candidates[0]["content"]["parts"])
        try:
            parsed = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        except ValueError:
            return None
        lesson = str(parsed.get("lesson", "")).strip()
        if self.use_memory and lesson:
            memory.save_lesson(task, str(parsed.get("outcome", "unknown")), lesson, self.db_path)
        return lesson or None


def main():
    print("Self-learning agent (Gemini). Commands: /lessons  /forget  /quit\n")
    agent = Agent(verbose=True)
    while True:
        task = input("You: ").strip()
        if not task:
            continue
        if task == "/quit":
            break
        if task == "/lessons":
            for lid, outcome, lesson in memory.all_lessons():
                print(f"  #{lid} [{outcome}] {lesson}")
            continue
        if task == "/forget":
            memory.clear()
            print("  Memory cleared.")
            continue
        try:
            answer = agent.run(task)
        except RuntimeError as exc:
            print(f"\n  {exc}\n")
            continue
        print(f"\nAgent: {answer}\n")
        fb = input("Feedback (Enter to skip, or type what was wrong/right): ").strip()
        try:
            lesson = agent.reflect(task, answer, fb or None)
        except RuntimeError as exc:
            print(f"  (could not save a lesson this time: {exc})\n")
            continue
        print(f"  Learned: {lesson}\n" if lesson else "  Nothing new to learn.\n")


if __name__ == "__main__":
    main()