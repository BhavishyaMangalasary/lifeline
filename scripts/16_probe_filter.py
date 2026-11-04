import sys

sys.path.insert(0, "src")

from lifeline.agent.ask import MODEL, SCHEMAS, SYSTEM, client

Q = "Which analysed tile has the most cut-off buildings, and how sure are we?"


def attempt(name, messages, tools=None):
    try:
        kwargs = {"tools": tools} if tools else {}
        r = client.chat.completions.create(model=MODEL, messages=messages, **kwargs)
        m = r.choices[0].message
        print(f"{name}: OK (tool calls: {len(m.tool_calls or [])})")
    except Exception as e:
        print(f"{name}: FAIL - {str(e)[:90]}")


user = [{"role": "user", "content": Q}]
sysm = [{"role": "system", "content": SYSTEM}]
attempt("A question only", user)
attempt("B system + question", sysm + user)
attempt("C question + tools", user, SCHEMAS)
attempt("D system + question + tools", sysm + user, SCHEMAS)
attempt("E trivial question + tools", [{"role": "user", "content": "List the tiles."}], SCHEMAS)