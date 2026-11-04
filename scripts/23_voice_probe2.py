import asyncio
import json
import os

import websockets
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["MODEL_API_KEY"]
URL = "wss://api.meta.ai/v1/asr/realtime"
MODEL = "muse-voice-transcribe-1.0"


def base():
    return {"type": "session.update", "session": {"type": "transcription", "audio": {"input": {
        "format": {"type": "audio/pcm", "rate": 16000, "channels": 1},
        "transcription": {"model": MODEL, "language": "en"},
        "turn_detection": None,
    }}}}


def variants():
    out = []
    for enc in ["pcm16", "PCM16", "LINEAR16", "pcm_s16le"]:
        m = base(); m["audioEncoding"] = enc; out.append(("top level", enc, m))
        m = base(); m["session"]["audioEncoding"] = enc; out.append(("session", enc, m))
        m = base(); m["session"]["audio"]["input"]["audioEncoding"] = enc; out.append(("audio.input", enc, m))
        m = base(); m["session"]["audio"]["input"]["format"]["audioEncoding"] = enc; out.append(("format", enc, m))
        m = base(); m["session"]["audio"]["input"]["transcription"]["audioEncoding"] = enc; out.append(("transcription", enc, m))
    return out


async def try_one(place, enc, msg):
    print(f"\n[{place} = {enc}]")
    try:
        async with websockets.connect(URL, additional_headers={"Authorization": f"Bearer {KEY}"}) as ws:
            await ws.send(json.dumps(msg))
            for _ in range(2):
                try:
                    reply = await asyncio.wait_for(ws.recv(), 2.5)
                    text = json.loads(reply)
                    text.pop("sessionId", None)
                    print("  reply:", json.dumps(text)[:250])
                except asyncio.TimeoutError:
                    print("  (no reply in 2.5 s: possibly accepted)")
                    break
    except Exception as e:
        print("  closed:", type(e).__name__)


async def main():
    for place, enc, msg in variants():
        await try_one(place, enc, msg)


asyncio.run(main())