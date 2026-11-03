import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ["MODEL_API_KEY"],
)

print("Models enabled for this key:")
for m in client.models.list().data:
    print(" -", m.id)

reply = client.chat.completions.create(
    model="muse-spark-1.3",
    messages=[
        {
            "role": "user",
            "content": "In one sentence, what does it mean for a building to be isolated by a flood?",
        }
    ],
)
print("\nMuse Spark says:", reply.choices[0].message.content)
