"""'Ask the map': Muse Spark answers questions by calling tools over the exported results."""
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])
MODEL = "muse-spark-1.3"
DATA = Path("app/data")


def _load(tile):
    return json.loads((DATA / f"tile_{tile}.geojson").read_text())


def list_tiles():
    rows = []
    for p in sorted(DATA.glob("tile_*.geojson")):
        s = json.loads(p.read_text())["summary"]
        rows.append({
            "tile": s["tile"],
            "isolated_buildings": s["buildings"].get("isolated", 0),
            "uncertain_buildings": s["buildings"].get("uncertain", 0),
            "roads_flooded": s["roads_flooded"],
            "road_pieces": s["road_pieces"],
        })
    return {"evidence": "tiles:overview", "tiles": rows}


def tile_summary(tile):
    s = _load(tile)["summary"]
    s = {k: v for k, v in s.items() if k != "buildings_truth"}
    return {"evidence": f"tile{tile}:summary", **s}


def dispatch_priorities(tile):
    feats = [f for f in _load(tile)["features"] if f["properties"]["kind"] == "entry"]
    feats.sort(key=lambda f: f["properties"]["rank"])
    rows = []
    for f in feats:
        lon, lat = f["geometry"]["coordinates"]
        rows.append({
            "rank": f["properties"]["rank"],
            "isolated_buildings_served": f["properties"]["buildings"],
            "lat": round(lat, 5),
            "lon": round(lon, 5),
        })
    return {"evidence": f"tile{tile}:priorities", "entry_points": rows}


def known_limits():
    return {
        "evidence": "limits:testing",
        "text": ("Tested on 5 SpaceNet 8 tiles against ground-truth labels: none of 27 truly cut-off "
                 "buildings was marked reachable, but about half of the buildings marked isolated "
                 "were in fact reachable. Flood judgements are not field-verified."),
    }


FUNCS = {
    "list_tiles": list_tiles,
    "tile_summary": tile_summary,
    "dispatch_priorities": dispatch_priorities,
    "known_limits": known_limits,
}


def _schema(name, description, with_tile):
    props = {"tile": {"type": "integer", "description": "tile number"}} if with_tile else {}
    return {"type": "function", "function": {
        "name": name,
        "description": description,
        "parameters": {"type": "object", "properties": props,
                       "required": ["tile"] if with_tile else []},
    }}


SCHEMAS = [
    _schema("list_tiles", "Overview of every analysed tile: isolated buildings and flooded roads.", False),
    _schema("tile_summary", "Counts of flooded, uncertain and dry roads and building statuses for one tile.", True),
    _schema("dispatch_priorities", "Ranked entry points for responders in one tile, with buildings served.", True),
    _schema("known_limits", "Measured reliability of the isolated-building calls.", False),
]

SYSTEM = """You are Lifeline's map assistant for a flood dispatch coordinator.
Answer ONLY from tool results. Call tools to get facts; never guess numbers.
Cite the evidence ids you used in square brackets, like [tile497:summary].
Keep answers under 120 words. If the tools cannot answer, say so.
Whenever you report isolated buildings, mention the uncertainty."""


def ask(question, max_steps=6):
    messages = [{"role": "user", "content": SYSTEM + "\n\nQuestion: " + question}]
    seen = set()
    for _ in range(max_steps):
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=SCHEMAS)
        msg = reply.choices[0].message
        if not msg.tool_calls:
            answer = (msg.content or "").strip()
            cited = set(re.findall(r"\[([^\]]+)\]", answer))
            return {"answer": answer, "unsupported": sorted(c for c in cited if c not in seen)}
        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            try:
                result = FUNCS[call.function.name](**args)
            except Exception as e:
                result = {"error": str(e)}
            if "evidence" in result:
                seen.add(result["evidence"])
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    return {"answer": "(stopped: too many tool calls)", "unsupported": []}