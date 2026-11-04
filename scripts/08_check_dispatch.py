import sys

sys.path.insert(0, "src")

from lifeline.geo.access import classify, dispatch
from lifeline.geo.labels import load_tile

roads, buildings = load_tile("105001001A0FFC00_0_21_20")
result = classify(roads, buildings)
groups, per_building = dispatch(roads, result)
print(groups.head(6).to_string())
print("isolated buildings routed:", len(per_building))