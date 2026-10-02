"""Does the agent really learn? This script measures it.

Hidden rule: every answer must be ONLY the bare number (no words, no units).
The tasks never say so. The agent has to discover the rule from feedback.

  Phase A  baseline : no memory, run the TEST tasks.
  Phase B  learning : memory on, run the TRAIN tasks and give automatic
                      feedback from the checker; the agent reflects and stores lessons.
  Phase C  with memory : memory on, run the TEST tasks again.

If Phase C scores higher than Phase A, the memory loop is working.
"""

import re
from pathlib import Path

import memory
from agent import Agent

EVAL_DB = Path(__file__).parent / "eval_memory.db"

# (task, expected number)
TRAIN = [
    ("What is 15% of 240?", 36),
    ("A train travels at 60 km/h for 2.5 hours. How far does it go?", 150),
    ("How many seconds are there in 3 hours?", 10800),
]
TEST = [
    ("What is 12% of 500?", 60),
    ("A car moves at 80 km/h for 1.5 hours. How far does it travel?", 120),
    ("How many minutes are there in 7 hours?", 420),
    ("What is 25% of 88?", 22),
]


def check(answer, expected):
    """Pass only if the answer is exactly the bare number."""
    text = answer.strip().replace(",", "")
    if not re.fullmatch(r"-?\d+(\.\d+)?", text):
        return False, "Wrong format: the answer must be ONLY the bare number, with no words or units."
    if abs(float(text) - expected) > 1e-6:
        return False, "Wrong value."
    return True, "Correct."


def score(agent, tasks, learn=False):
    passed = 0
    for task, expected in tasks:
        answer = agent.run(task)
        ok, feedback = check(answer, expected)
        passed += ok
        print(f"  {'PASS' if ok else 'FAIL'}  {task}  ->  {answer!r}")
        if learn:
            lesson = agent.reflect(task, answer, feedback)
            print(f"        learned: {lesson}")
    return passed


def main():
    memory.clear(EVAL_DB)

    print("Phase A: baseline (no memory)")
    a = score(Agent(use_memory=False, db_path=EVAL_DB), TEST)

    print("\nPhase B: learning from feedback")
    score(Agent(use_memory=True, db_path=EVAL_DB), TRAIN, learn=True)

    print("\nPhase C: same test tasks, with memory")
    c = score(Agent(use_memory=True, db_path=EVAL_DB), TEST)

    print(f"\nResult: without memory {a}/{len(TEST)}  |  with memory {c}/{len(TEST)}")


if __name__ == "__main__":
    main()
