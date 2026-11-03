"""SAM 3.1 client for Lifeline.

segment(image, prompt) sends an image and one noun phrase to sam-3.1 on Meta Model API and
returns every match as a Detection (box + full-frame boolean mask). Raw responses are cached
on disk, so the same (image, prompt) is never paid for twice.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import os
import time
from dataclasses import dataclass
from pathlib import Path

import meta_sam_parser as msp
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()

CACHE_DIR = Path(os.environ.get("LIFELINE_CACHE", ".cache/sam"))
MASK_ENCODING = os.environ.get("LIFELINE_MASK_ENCODING", "lossless")  # or "one_bit"


@dataclass
class Detection:
    object_id: int
    box: tuple  # (left, top, right, bottom) in image pixels, right/bottom exclusive
    mask: np.ndarray  # bool array, shape (image_height, image_width)


def _png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _call_sam(png: bytes, prompt: str) -> str:
    """Call sam-3.1 over the Responses API and return the raw special-token text."""
    client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])
    data_url = "data:image/png;base64," + base64.b64encode(png).decode()
    kwargs = {}
    if MASK_ENCODING != "lossless":
        kwargs["metadata"] = {"mask_encoding": MASK_ENCODING}
    last_error = None
    for attempt in range(3):
        try:
            events = client.responses.create(
                model="sam-3.1",
                input=[
                    {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
                stream=True,
                **kwargs,
            )
            parts = []
            for event in events:
                if event.type == "response.output_text.delta":
                    parts.append(event.delta)
            return "".join(parts)
        except Exception as error:  # rate limits, transient network errors
            last_error = error
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"SAM request failed after 3 attempts: {last_error}")


_LANE = {"item_id": "sam", "output_index": 0, "content_index": 0}


async def _events(text: str):
    yield {"type": "response.output_text.delta", "delta": text, **_LANE}
    yield {"type": "response.output_text.done", "text": text, **_LANE}
    yield {"type": "response.completed"}


async def _parse(raw: str):
    parsed = msp.parse_responses_stream(_events(raw), msp.image_segmentation_format())
    return await parsed.final_result()


def parse_raw(raw: str, width: int, height: int) -> list:
    """Parse SAM's raw output text into Detections. Empty output means no matches."""
    if not raw.strip():
        return []
    result = asyncio.run(_parse(raw))
    boxes = {r.object_id: r for r in result.records if r.kind == "box"}
    detections = []
    for rec in result.records:
        if rec.kind != "mask":
            continue
        raster = np.frombuffer(msp.decode_mask_to_raster(rec.mask), dtype=np.uint8)
        raster = raster.reshape(rec.mask.height, rec.mask.width)
        full = np.zeros((height, width), dtype=bool)
        top, left = max(rec.bounds.top, 0), max(rec.bounds.left, 0)
        bottom = min(rec.bounds.top + raster.shape[0], height)
        right = min(rec.bounds.left + raster.shape[1], width)
        if bottom > top and right > left:
            full[top:bottom, left:right] = raster[: bottom - top, : right - left].astype(bool)
        b = boxes.get(rec.object_id)
        box = (int(b.left), int(b.top), int(b.right), int(b.bottom)) if b else (left, top, right, bottom)
        detections.append(Detection(int(rec.object_id), box, full))
    return detections


def segment(image: Image.Image, prompt: str) -> list:
    """Segment every match of one noun phrase in an image. Cached on disk."""
    png = _png_bytes(image)
    key = hashlib.sha256(png + b"|" + prompt.encode() + b"|" + MASK_ENCODING.encode()).hexdigest()
    path = CACHE_DIR / f"{key}.txt"
    if path.exists():
        raw = path.read_text()
    else:
        raw = _call_sam(png, prompt)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(raw)
    return parse_raw(raw, image.width, image.height)


def union_mask(detections: list, height: int, width: int) -> np.ndarray:
    """Combine all detections into one boolean mask."""
    out = np.zeros((height, width), dtype=bool)
    for d in detections:
        out |= d.mask
    return out
