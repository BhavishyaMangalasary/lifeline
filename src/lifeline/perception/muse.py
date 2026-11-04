"""Muse Spark as a flood judge: is this road piece under water?"""
import base64
import hashlib
import io
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw

load_dotenv()
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])

MODEL = "muse-spark-1.3"
CACHE_DIR = Path(os.environ.get("LIFELINE_MUSE_CACHE", ".cache/muse"))
WINDOW = 320

PROMPT = (
    "This is a satellite photo taken after a hurricane. A cyan line marks one road section. "
    "Is that road section visibly covered by floodwater, mud or debris? "
    'Reply with JSON only: {"flooded": true or false, "confidence": a number from 0 to 1, '
    '"reason": "at most 8 words"}'
)

PAIR_PROMPT = (
    "These two satellite photos show the same place. Left: before a hurricane. Right: after it. "
    "The cyan line marks the same road section in both. "
    "Is that road section visibly covered by floodwater, mud or debris in the right photo "
    "(it was clear on the left)? "
    'Reply with JSON only: {"flooded": true or false, "confidence": a number from 0 to 1, '
    '"reason": "at most 8 words"}'
)


def crop_piece(post_img, line_coords):
    """Cuts a square window around a road piece and draws the piece on it."""
    xs = [p[0] for p in line_coords]
    ys = [p[1] for p in line_coords]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    half = WINDOW // 2
    cx = min(max(cx, half), post_img.width - half)
    cy = min(max(cy, half), post_img.height - half)
    x0, y0 = int(cx - half), int(cy - half)
    crop = post_img.crop((x0, y0, x0 + WINDOW, y0 + WINDOW)).convert("RGB")
    d = ImageDraw.Draw(crop)
    d.line([(x - x0, y - y0) for x, y in line_coords], fill=(0, 255, 255), width=3)
    return crop


def crop_pair(pre_img, post_img, line_coords):
    """Before and after windows side by side, with the same road marked on both."""
    a = crop_piece(pre_img, line_coords)
    b = crop_piece(post_img, line_coords)
    pair = Image.new("RGB", (WINDOW * 2 + 8, WINDOW), (255, 255, 255))
    pair.paste(a, (0, 0))
    pair.paste(b, (WINDOW + 8, 0))
    return pair


def _png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _parse(text):
    try:
        data = json.loads(text[text.index("{") : text.rindex("}") + 1])
        return {
            "flooded": bool(data["flooded"]),
            "confidence": float(data.get("confidence", 0.5)),
            "reason": str(data.get("reason", "")),
        }
    except Exception:
        return None


def judge(crop, prompt=PROMPT):
    png = _png(crop)
    key = hashlib.sha256(png + prompt.encode() + MODEL.encode()).hexdigest()
    path = CACHE_DIR / f"{key}.txt"
    if path.exists():
        return _parse(path.read_text())
    url = "data:image/png;base64," + base64.b64encode(png).decode()
    for attempt in range(3):
        try:
            reply = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": url}},
                ]}],
            )
            text = reply.choices[0].message.content or ""
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            return _parse(text)
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def judge_tile(post, roads, workers=6, pre=None):
    if pre is None:
        crops = [crop_piece(post, list(g.coords)) for g in roads["geometry"]]
        prompt = PROMPT
    else:
        crops = [crop_pair(pre, post, list(g.coords)) for g in roads["geometry"]]
        prompt = PAIR_PROMPT
    crops = [c.resize((c.width * 2, c.height * 2), Image.LANCZOS) for c in crops]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda c: judge(c, prompt), crops))

def perceive_tile(pre, post, roads):
    """Three-way flood state per road piece: flooded / dry / uncertain."""
    a = judge_tile(post, roads)
    b = judge_tile(post, roads, pre=pre)
    states = []
    for x, y in zip(a, b):
        if x is None or y is None:
            states.append("uncertain")
        elif x["flooded"] and y["flooded"]:
            states.append("flooded")
        elif not x["flooded"] and not y["flooded"]:
            states.append("dry")
        else:
            states.append("uncertain")
    return states