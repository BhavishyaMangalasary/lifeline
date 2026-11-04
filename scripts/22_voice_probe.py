import asyncio
import json
import os

import websockets
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["MODEL_API_KEY"]
URL = "wss://api.meta.ai/v1/asr/realtime"
MODEL = "muse-voice-transcribe-1.0"

CANDIDATES = []
for enc in ["pcm16", "PCM16", "LINEAR16", "pcm_s16le", "audio/pcm", "pcm"]:
    CANDIDATES.append({"audioEncoding": enc, "sampleRate": 16000, "language": "en"})
CANDIDATES.append({"type": "config", "audioEncoding": "pcm16", "sampleRate": 16000, "channels": 1, "model": MODEL})
CANDIDATES.append({"type": "start", "audioEncoding": "pcm16", "sampleRateHertz": 16000, "model": MODEL})


async def try_one(msg):
    print("\nSEND:", json.dumps(msg))
    try:
        async with websockets.connect(URL, additional_headers={"Authorization": f"Bearer {KEY}"}) as ws:
            await ws.send(json.dumps(msg))
            for _ in range(3):
                try:
                    reply = await asyncio.wait_for(ws.recv(), 2.5)
                    print("  reply:", str(reply)[:300])
                except asyncio.TimeoutError:
                    print("  (no reply in 2.5 s, not an error)")
                    break
    except Exception as e:
        print("  closed:", type(e).__name__, str(e)[:120])


async def main():
    for c in CANDIDATES:
        await try_one(c)


asyncio.run(main())