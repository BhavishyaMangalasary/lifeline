"""Does disagreement or confidence tell us when Muse Spark is wrong?"""
import pandas as pd

a = pd.read_csv("out/muse_eval.csv")        # after photo only
b = pd.read_csv("out/muse_eval_pair.csv")   # before + after
assert len(a) == len(b) and (a["flooded"] == b["flooded"]).all()

y = a["flooded"].astype(bool)
pa, pb = a["muse"].astype(bool), b["muse"].astype(bool)


def stats(name, p):
    tp, tn = int((y & p).sum()), int((~y & ~p).sum())
    fp, fn = int((~y & p).sum()), int((y & ~p).sum())
    print(f"{name:26s} flooded caught {tp/max(tp+fn,1):.2f} | dry right {tn/max(tn+fp,1):.2f} | acc {(tp+tn)/len(y):.2f}")


stats("after only", pa)
stats("before + after", pb)
stats("both say flooded (AND)", pa & pb)
stats("either says flooded (OR)", pa | pb)

agree = pa == pb
print(f"\nthe two modes agree on {agree.mean():.0%} of pieces; correct when they agree: {(pa == y)[agree].mean():.0%}")
for label, mask in [("both say flooded", pa & pb), ("both say dry", ~pa & ~pb)]:
    print(f"  {label}: {int(mask.sum())} pieces, correct {(y == pa)[mask].mean():.0%}")
print(f"  disagree (uncertain): {int((~agree).sum())} pieces")

print()
for name, d in [("after only", a), ("before + after", b)]:
    for t in (0.6, 0.7, 0.8, 0.9):
        keep = d["conf"] >= t
        right = (d["flooded"].astype(bool) == d["muse"].astype(bool))[keep]
        print(f"{name:14s} confidence >= {t}: answers {keep.mean():.0%} of pieces, correct {right.mean():.0%}")