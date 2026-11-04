"""Which buildings are cut off by flooded roads, and where responders should go first."""
import networkx as nx
import pandas as pd


def _key(point):
    return (round(point[0], 1), round(point[1], 1))


def build_graph(roads):
    g = nx.Graph()
    for i, row in roads.iterrows():
        if row["geometry"].is_empty:
            continue
        pts = list(row["geometry"].coords)
        g.add_edge(
            _key(pts[0]),
            _key(pts[-1]),
            piece=i,
            flooded=bool(row["flooded"]),
            length=row["length_m"],
            time=row["travel_time_s"],
        )
    return g


def exit_nodes(g, size=1300, margin=3):
    return {n for n in g.nodes if min(n) <= margin or max(n) >= size - margin}


def _reaches_exit(g, exits):
    good = set()
    for comp in nx.connected_components(g):
        if comp & exits:
            good |= comp
    return good


def nearest_piece(shape, roads, max_px=80):
    if shape.is_empty or roads.empty:
        return None
    dist = roads["geometry"].apply(shape.distance).dropna()
    if dist.empty:
        return None
    i = dist.idxmin()
    return i if dist[i] <= max_px else None


def classify(roads, buildings, max_px=80, size=1300):
    g = build_graph(roads)
    exits = exit_nodes(g, size)
    before = _reaches_exit(g, exits)
    open_edges = [(u, v) for u, v, d in g.edges(data=True) if not d["flooded"]]
    after = _reaches_exit(g.edge_subgraph(open_edges), exits)

    out = buildings.copy()
    status, piece = [], []
    for _, b in out.iterrows():
        i = nearest_piece(b["geometry"], roads, max_px)
        if i is None:
            status.append("no_road")
            piece.append(None)
            continue
        r = roads.loc[i]
        ends = {_key(r["geometry"].coords[0]), _key(r["geometry"].coords[-1])}
        could = bool(ends & before)
        can = (not r["flooded"]) and bool(ends & after)
        status.append("ok" if can else ("isolated" if could else "unconnected"))
        piece.append(i)
    out["status"] = status
    out["piece"] = piece
    return out


def _dry_nodes(g, exits):
    open_edges = [(u, v) for u, v, d in g.edges(data=True) if not d["flooded"]]
    return _reaches_exit(g.edge_subgraph(open_edges), exits)


def dispatch(roads, result):
    g = build_graph(roads)
    exits = exit_nodes(g)
    sources = exits | _dry_nodes(g, exits)
    if not sources:
        return pd.DataFrame(), pd.DataFrame()
    dist, paths = nx.multi_source_dijkstra(g, sources, weight="time")

    rows = []
    for j, b in result[result["status"] == "isolated"].iterrows():
        r = roads.loc[b["piece"]]
        ends = [_key(r["geometry"].coords[0]), _key(r["geometry"].coords[-1])]
        reachable = [n for n in ends if n in dist]
        if not reachable:
            continue
        end = min(reachable, key=lambda n: dist[n])
        rows.append({"building": j, "entry": paths[end][0], "eta_s": dist[end] + r["travel_time_s"] / 2})
    if not rows:
        return pd.DataFrame(), pd.DataFrame()

    per_building = pd.DataFrame(rows)
    groups = per_building.groupby("entry").agg(
        buildings=("building", "count"), eta_s=("eta_s", "max")
    ).reset_index()
    groups["priority"] = groups["buildings"] / (groups["eta_s"] / 60 + 1)
    groups = groups.sort_values("priority", ascending=False).reset_index(drop=True)
    return groups, per_building


def classify_uncertain(roads, buildings, states):
    opt = roads.copy()
    opt["flooded"] = [s == "flooded" for s in states]
    pes = roads.copy()
    pes["flooded"] = [s != "dry" for s in states]
    a = classify(opt, buildings)
    b = classify(pes, buildings)

    out = a.copy()
    final = []
    for sa, sb in zip(a["status"], b["status"]):
        if sa == "isolated":
            final.append("isolated")
        elif sb == "ok":
            final.append("ok")
        elif sa == "ok" and sb == "isolated":
            final.append("uncertain")
        else:
            final.append(sa)
    out["status"] = final
    return out