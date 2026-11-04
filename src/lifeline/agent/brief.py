"""Muse Spark writes a dispatch brief from a tile's results; every claim cites a numbered fact."""
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])
MODEL = "muse-spark-1.3"


def load_facts(i):
    data = json.loads(Path(f"app/data/tile_{i}.geojson").read_text())
    s = data["summary"]
    b = s["buildings"]
    facts = {
        "F1": (f"{s['road_pieces']} road pieces were checked: {s['roads_flooded']} judged flooded, "
               f"{s['roads_uncertain']} uncertain, the rest judged dry."),
        "F2": (f"Buildings: {b.get('isolated', 0)} isolated (cut off from every exit road), "
               f"{b.get('uncertain', 0)} uncertain, {b.get('ok', 0)} still reachable, "
               f"{b.get('no_road', 0)} with no mapped road nearby."),
    }
    entries = [f for f in data["features"] if f["properties"]["kind"] == "entry"]
    entries.sort(key=lambda f: f["properties"]["rank"])
    n = 3
    for f in entries[:4]:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        facts[f"F{n}"] = (f"Priority {p['rank']}: enter at map reference ({lat:.5f}, {lon:.5f}); "
                        f"a crew entering here is closest to {p['buildings']} isolated building{'s' if p['buildings'] != 1 else ''}.")
        n += 1
    facts[f"F{n}"] = ("In testing on 5 SpaceNet 8 tiles, none of the 27 truly cut-off buildings was "
                      "marked reachable, but about half of the buildings marked isolated were in fact "
                      "reachable. Treat 'isolated' as a reason to check, not a confirmed cut-off.")
    n += 1
    facts[f"F{n}"] = ("Flood judgements come from a vision model reading satellite photos and are "
                      "not field-verified; uncertain roads need a drone or ground check.")
    return facts


def check(brief, facts):
    problems = []
    for sent in re.split(r"(?<=[.!?])\s+", brief):
        ids = re.findall(r"\[(F\d+)\]", sent)
        if not ids:
            problems.append(f"no citation: {sent}")
        for f in ids:
            if f not in facts:
                problems.append(f"unknown fact {f}: {sent}")
        cited = " ".join(facts[f] for f in ids if f in facts)
        body = re.sub(r"\[F\d+\]", "", sent)
        for num in re.findall(r"\d+(?:\.\d+)?", body):
            if not re.search(rf"(?<![\d.]){re.escape(num)}(?![\d])", cited):
                problems.append(f"number {num} not in the cited facts: {sent}")
    return problems


PROMPT = """You are writing a short flood dispatch brief for an emergency coordinator.
Use ONLY the numbered facts below. Write exactly one sentence per fact and end it with that fact's id, like [F2]. Never combine facts in one sentence.
Do not add any number, place or claim that is not in the facts. Start with the single most important action.
Keep it under 140 words, no headings. Write complete, grammatical sentences with correct punctuation.

Facts:
{facts}
"""


def write_brief(i):
    facts = load_facts(i)
    text = "\n".join(f"{k}: {v}" for k, v in facts.items())
    reply = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT.format(facts=text)}],
    )
    brief = (reply.choices[0].message.content or "").strip()
    result = {"brief": brief, "facts": facts, "problems": check(brief, facts)}
    Path(f"app/data/brief_{i}.json").write_text(json.dumps(result, indent=2))
    return result