import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from shapely.geometry import LineString, box

from lifeline.geo.access import classify, classify_uncertain, dispatch


def make_roads(b_flooded):
    """A: dry piece from the map edge. B: continues from A, flooded or not."""
    return pd.DataFrame({
        "geometry": [LineString([(0, 600), (300, 600)]), LineString([(300, 600), (600, 600)])],
        "flooded": [False, b_flooded],
        "length_m": [100.0, 100.0],
        "travel_time_s": [30.0, 60.0],
    })


def house(x, y):
    return pd.DataFrame({"geometry": [box(x, y, x + 20, y + 20)]})


def test_flooded_piece_isolates_house():
    out = classify(make_roads(True), house(440, 610))
    assert out["status"].iloc[0] == "isolated"


def test_dry_road_keeps_house_reachable():
    out = classify(make_roads(False), house(440, 610))
    assert out["status"].iloc[0] == "ok"


def test_house_on_dry_piece_stays_reachable():
    out = classify(make_roads(True), house(140, 610))
    assert out["status"].iloc[0] == "ok"


def test_house_far_from_any_road_has_no_road():
    out = classify(make_roads(False), house(1000, 100))
    assert out["status"].iloc[0] == "no_road"


def test_disagreeing_readings_give_uncertain():
    roads = make_roads(False)
    out = classify_uncertain(roads, house(440, 610), ["dry", "uncertain"])
    assert out["status"].iloc[0] == "uncertain"


def test_dispatch_enters_at_the_dry_end():
    roads = make_roads(True)
    result = classify(roads, house(440, 610))
    groups, per_building = dispatch(roads, result)
    assert len(groups) == 1
    assert groups["buildings"].iloc[0] == 1
    assert groups["entry"].iloc[0] == (300.0, 600.0)
    assert groups["eta_s"].iloc[0] == 30.0  # travel_time_s of piece B, halved