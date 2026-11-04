"""Scores Muse Spark's flood judgement against the dataset's labels, one road piece at a time."""
import sys

sys.path.insert(0, "src")

import pandas as pd
from PIL import Image

from lifeline.geo.labels import load_tile
from lifeline.perception.muse import judge_tile

MAPPING = "data/Louisiana-East_Training_Public_label_image_mapping.csv"


def run(i, pair=False):
    mapping = pd.read_csv(MAPPING)
    image_id = mapping.iloc[i]["pre-event image"].replace(".tif", "")
    roads, _ = load_tile(image_id)
    post = Image.open(f"out/post_{i}.png").convert("RGB").resize((1300, 1300))
    pre = Image.open(f"out/pre_{i}.png").convert("RGB").resize((1300, 1300)) if pair else None
    results = judge_tile(post, roads, pre=pre)
    out = roads[["flooded", "length_m"]].copy()
    out["muse"] = [r["flooded"] if r else None for r in results]
    out["conf"] = [r["confidence"] if r else None for r in results]
    out["reason"] = [r["reason"] if r else "" for r in results]
    out["tile"] = i
    return out


def score(df):
    ok = df.dropna(subset=["muse"])
    y, p = ok["flooded"].astype(bool), ok["muse"].astype(bool)
    tp, tn = int((y & p).sum()), int((~y & ~p).sum())
    fp, fn = int((~y & p).sum()), int((y & ~p).sum())
    print(f"pieces: {len(df)} (unparsed: {len(df) - len(ok)})")
    print(f"flooded called flooded: {tp} | dry called dry: {tn}")
    print(f"dry called flooded: {fp} | flooded called dry: {fn}")
    print(f"accuracy: {(tp + tn) / max(len(ok), 1):.2f}")


if __name__ == "__main__":
    args = sys.argv[1:]
    pair = args[0] == "pair"
    tiles = [int(a) for a in (args[1:] if pair else args)]
    df = pd.concat([run(i, pair) for i in tiles])
    df.to_csv("out/muse_eval_pair.csv" if pair else "out/muse_eval.csv", index=False)
    score(df)