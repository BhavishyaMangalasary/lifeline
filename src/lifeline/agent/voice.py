"""Speech to text with Meta's realtime Muse Voice endpoint (WebSocket, 24 kHz mono PCM16)."""
import asyncio
import json
import os
import uuid

import websockets
from dotenv import load_dotenv

load_dotenv()
RATE = 24_000
FRAME_BYTES = RATE * 2 * 80 // 1000  # 80 ms of audio


async def _transcribe(pcm):
    uri = f"wss://api.meta.ai/v1/asr/realtime?sessionId=lifeline-{uuid.uuid4()}"
    finals, last = [], ""
    async with websockets.connect(uri, open_timeout=30) as ws:
        await ws.send(json.dumps({
            "authorization": {"accessToken": f"Bearer {os.environ['MODEL_API_KEY']}"},
            "audioEncoding": "PCM_24KHZ",
            "model": "muse-voice-transcribe-1.0",
            "mode": "PUSH_TO_TALK",
        }))
        handshake = json.loads(await ws.recv())
        if "sessionId" not in handshake:
            raise RuntimeError("handshake failed")

        async def receive():
            nonlocal last
            async for message in ws:
                if isinstance(message, bytes):
                    continue
                event = json.loads(message)
                if event.get("type") == "error":
                    raise RuntimeError(event.get("message", "error"))
                if event.get("type") == "transcript":
                    last = event["transcript"]
                    if event.get("final"):
                        finals.append(event["transcript"])

        task = asyncio.create_task(receive())
        for i in range(0, len(pcm), FRAME_BYTES):
            await ws.send(pcm[i:i + FRAME_BYTES])
            await asyncio.sleep(0.08)  # real-time pacing is required
        await ws.send(json.dumps({"type": "endStream"}))
        await task
    return " ".join(finals).strip() or last.strip()


def transcribe(pcm):
    """pcm: raw 16-bit little-endian mono PCM at 24 kHz. Returns the transcript text."""
    return asyncio.run(_transcribe(pcm))