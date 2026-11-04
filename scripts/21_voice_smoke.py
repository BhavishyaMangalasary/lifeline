import sys
import wave

sys.path.insert(0, "src")

from lifeline.agent.voice import transcribe

with wave.open(sys.argv[1]) as w:
    assert w.getframerate() == 24000 and w.getnchannels() == 1 and w.getsampwidth() == 2
    pcm = w.readframes(w.getnframes())

print("sending", round(len(pcm) / 2 / 24000, 1), "seconds of audio...")
print("transcript:", transcribe(pcm))