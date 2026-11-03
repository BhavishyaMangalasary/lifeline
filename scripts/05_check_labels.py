import sys

sys.path.insert(0, "src")

from lifeline.geo.labels import load_tile

roads, buildings = load_tile("105001001A0FFC00_0_21_20")
print("road pieces:", len(roads), "| flooded:", roads["flooded"].sum())
print("buildings:", len(buildings), "| flooded:", buildings["flooded"].sum())
print(roads[["geometry", "length_m", "travel_time_s", "flooded"]].head(3))
print(buildings[["geometry", "flooded"]].head(3))