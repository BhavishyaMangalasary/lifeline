"""Asks Muse Spark what it sees in a post-flood photo."""
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])

QUESTION = (
    "This is a satellite photo taken after a hurricane. "
    "Is there floodwater on the land? Say where it is (use words like top-left, centre, right edge), "
    "whether roads look underwater, and which buildings look surrounded by water. "
    "Be specific and brief."
)


def data_url(path):
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    return f"data:image/png;base64,{b64}"

def main():
    path = sys.argv[1]
    reply = client.chat.completions.create(
        model="muse-spark-1.3",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": QUESTION},
            {"type": "image_url", "image_url": {"url": data_url(path)}},
        ]}],
    )
    print(reply.choices[0].message.content)


if __name__ == "__main__":
    main()