"""Decision-level evaluation: which buildings does Lifeline call isolated, versus the labels?"""
import sys

sys.path.insert(0, "src")

import pandas as pd
from PIL import Image

from lifeline.geo.access import classify, classify_uncertain
from lifeline.geo.labels import load_tile
from lifeline.perception.muse import perceive_tile

MAPPING = "data/Louisiana-East_Training_Public_label_image_mapping.csv"


def run_tile(i):
    mapping = pd.read_csv(MAPPING)
    image_id = mapping.iloc[i]["pre-event image"].replace(".tif", "")
    roads, buildings = load_tile(image_id)
    post = Image.open(f"out/post_{i}.png").convert("RGB").resize((1300, 1300))
    pre = Image.open(f"out/pre_{i}.png").convert("RGB").resize((1300, 1300))
    truth = classify(roads, buildings)["status"]
    states = perceive_tile(pre, post, roads)
    pred = classify_uncertain(roads, buildings, states)["status"]
    return pd.DataFrame({"truth": truth.values, "pred": pred.values, "tile": i})


if __name__ == "__main__":
    df = pd.concat([run_tile(int(a)) for a in sys.argv[1:]])
    df.to_csv("out/decision_eval.csv", index=False)
    print(pd.crosstab(df["truth"], df["pred"]))

    real = df["truth"] == "isolated"
    said = df["pred"] == "isolated"
    unsure = df["pred"] == "uncertain"
    caught = int((real & said).sum())
    print(f"\nbuildings truly isolated (from labels): {int(real.sum())}")
    print(f"Lifeline called isolated: {int(said.sum())}, truly isolated: {caught} "
          f"(precision {caught / max(int(said.sum()), 1):.2f})")
    print(f"recall, isolated only: {caught / max(int(real.sum()), 1):.2f}")
    print(f"recall, counting 'uncertain' as flagged: {(caught + int((real & unsure).sum())) / max(int(real.sum()), 1):.2f}")
    print(f"truly isolated but called ok: {int((real & (df['pred'] == 'ok')).sum())}")