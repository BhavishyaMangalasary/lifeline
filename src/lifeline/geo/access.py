"""Which buildings are cut off by flooded roads."""
import networkx as nx


def _key(point):
    return (round(point[0], 1), round(point[1], 1))


def build_graph(roads):
    g = nx.Graph()
    for i, row in roads.iterrows():
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
    dist = roads["geometry"].apply(shape.distance)
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
