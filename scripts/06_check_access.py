import sys

sys.path.insert(0, "src")

from lifeline.geo.access import classify
from lifeline.geo.labels import load_tile

roads, buildings = load_tile("105001001A0FFC00_0_21_20")
result = classify(roads, buildings)
print(result["status"].value_counts())