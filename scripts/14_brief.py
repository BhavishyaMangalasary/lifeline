import sys

sys.path.insert(0, "src")

from lifeline.agent.brief import write_brief

for a in sys.argv[1:]:
    r = write_brief(int(a))
    print(f"=== tile {a}")
    print(r["brief"])
    print("problems:", r["problems"] or "none")