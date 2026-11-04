import sys

sys.path.insert(0, "src")

from lifeline.agent.ask import ask

QUESTIONS = sys.argv[1:] or [
    "Which analysed tile has the most cut-off buildings, and how sure are we?",
    "In tile 233, where should the first crew go and why?",
    "Is tile 497 more flooded than tile 170?",
]
for q in QUESTIONS:
    r = ask(q)
    print("Q:", q)
    print(r["answer"])
    print("unsupported citations:", r["unsupported"] or "none")
    print()