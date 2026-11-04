import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from lifeline.agent.ask import ask

QUESTIONS = [
    "Which analysed tile has the most isolated buildings, and how sure are we?",
    "In tile 233, where should the first crew go and why?",
    "Is tile 497 more flooded than tile 170?",
    "How reliable are the isolated-building calls?",
    "Which tile has the most uncertain buildings that need checking?",
    "In tile 500, how many buildings are isolated and how many are uncertain?",
]

PATH = Path("app/data/ask_examples.json")
saved = json.loads(PATH.read_text()) if PATH.exists() else []
done = {s["question"] for s in saved}

for q in QUESTIONS:
    if q in done:
        continue
    print("Q:", q)
    r = None
    for attempt in range(2):
        try:
            r = ask(q)
            break
        except Exception as e:
            print("  error:", e)
    if r is None:
        print("  -> not saved\n")
        continue
    print(r["answer"])
    print("unsupported citations:", r["unsupported"] or "none")
    if r["unsupported"] or r["answer"].startswith("(stopped"):
        print("  -> not saved\n")
        continue
    saved.append({"question": q, "answer": r["answer"], "unsupported": []})
    print()

saved.sort(key=lambda s: QUESTIONS.index(s["question"]) if s["question"] in QUESTIONS else 99)
PATH.write_text(json.dumps(saved, indent=2))
print(f"saved {len(saved)} answers to {PATH}")