import pandas as pd

d = pd.read_csv("out/decision_eval.csv")
d["real"] = d["truth"] == "isolated"
d["said"] = d["pred"] == "isolated"
d["correct"] = d["real"] & d["said"]
print(d.groupby("tile")[["real", "said", "correct"]].sum().rename(
    columns={"real": "truly_isolated", "said": "called_isolated"}))
print("\nthe missed building(s):")
print(d[d["real"] & (d["pred"] == "ok")])