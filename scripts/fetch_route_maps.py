# Kemal Ardian, 251524053, Kelas 2B
# Ambil rute jalan kaki asli dari OpenStreetMap (Nominatim + OSRM foot)
# lalu simpan sebagai graph JSON untuk Kasus 1: Kobra Banjir Path Finding.
# Rute langsung A->B diambil sebagai koridor utama; bila config punya via_query,
# rute A->via->B diambil sebagai koridor alternatif dan digabung ke graf yang sama.
# Tidak butuh API key. Jalankan dari root repo: python scripts/fetch_route_maps.py

import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG_PATH = Path("config/maps.json")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def http_get_json(url, user_agent):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geocode(query, config):
    params = urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
    )
    url = f"{config['nominatim_endpoint']}?{params}"
    results = http_get_json(url, config["user_agent"])
    if not results:
        raise RuntimeError(f"Nominatim tidak menemukan: {query}")
    top = results[0]
    return {
        "query": query,
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
        "display_name": top["display_name"],
    }


def fetch_foot_route(waypoints, config):
    coords = ";".join(f"{w['lon']},{w['lat']}" for w in waypoints)
    url = f"{config['osrm_endpoint']}/{coords}?steps=true&overview=false"
    return http_get_json(url, config["user_agent"])


def project_m(lat, lon, lat0, lon0):
    x = (lon - lon0) * 111320.0 * math.cos(math.radians(lat0))
    y = (lat - lat0) * 110947.0
    return [round(x, 1), round(y, 1)]


class GraphBuilder:

    def __init__(self, lat0, lon0):
        self.lat0 = lat0
        self.lon0 = lon0
        self.nodes = []
        self.edges = []
        self.node_index = {}
        self.edge_index = {}

    def node_id(self, lat, lon, label):
        key = (round(lat, 7), round(lon, 7))
        if key not in self.node_index:
            self.node_index[key] = len(self.nodes)
            self.nodes.append(
                {
                    "id": self.node_index[key],
                    "label": label,
                    "lat": key[0],
                    "lon": key[1],
                    "pos_m": project_m(key[0], key[1], self.lat0, self.lon0),
                }
            )
        return self.node_index[key]

    def add_edge(self, u, v, street, distance_m, duration_min, corridor):
        if u == v or distance_m <= 0.5:
            return
        key = (u, v)
        if key in self.edge_index:
            return
        self.edge_index[key] = len(self.edges)
        self.edges.append(
            {
                "from": u,
                "to": v,
                "street": street,
                "distance_m": round(distance_m, 1),
                "duration_min": round(duration_min, 2),
                "corridor": corridor,
            }
        )

    def absorb_route(self, route_json, corridor, origin_label, destination_label):
        route = route_json["routes"][0]
        total_distance_m = sum(leg["distance"] for leg in route["legs"])
        total_duration_min = sum(leg["duration"] for leg in route["legs"]) / 60.0

        steps = [
            s for leg in route["legs"] for s in leg["steps"] if s["distance"] > 0.5
        ]
        if not steps:
            return None

        # Endpoint snaps to OSRM waypoints (tahan terhadap step kedatangan 0 m)
        start_loc = route_json["waypoints"][0]["location"]
        end_loc = route_json["waypoints"][-1]["location"]
        self.node_id(start_loc[1], start_loc[0], origin_label)

        for i, step in enumerate(steps):
            street = step.get("name") or "Jalan Lingkungan"
            start_loc = step["maneuver"]["location"]
            if i + 1 < len(steps):
                end_loc = steps[i + 1]["maneuver"]["location"]
            else:
                end_loc = route_json["waypoints"][-1]["location"]

            from_lat, from_lon = start_loc[1], start_loc[0]
            to_lat, to_lon = end_loc[1], end_loc[0]

            if i + 1 < len(steps):
                u_label = f"Persimpangan {street}"
            else:
                u_label = street
            u = self.node_id(from_lat, from_lon, u_label)
            v = self.node_id(to_lat, to_lon, street)
            self.add_edge(
                u, v, street, step["distance"], step["duration"] / 60.0, corridor
            )

        self.nodes[-1]["label"] = destination_label
        return {
            "total_distance_m": round(total_distance_m, 1),
            "total_duration_min": round(total_duration_min, 2),
        }

    def to_dict(self):
        return {"nodes": self.nodes, "edges": self.edges}


def main():
    config = load_config()

    print(f"Provider: {config['provider']}")
    origin = geocode(config["origin_query"], config)
    print(f"Origin  : {origin['display_name']}")
    destination = geocode(config["destination_query"], config)
    print(f"Dest    : {destination['display_name']}")

    builder = GraphBuilder(origin["lat"], origin["lon"])
    origin_label = f"Titik A: {origin['display_name'].split(',')[0]}"
    destination_label = f"Titik B: {destination['display_name'].split(',')[0]}"

    direct = fetch_foot_route([origin, destination], config)
    direct_summary = builder.absorb_route(
        direct, "utama", origin_label, destination_label
    )
    print(
        f"Koridor utama   : {direct_summary['total_distance_m']} m, "
        f"{direct_summary['total_duration_min']} menit"
    )

    via_summary = None
    via_query = config.get("via_query")
    if via_query:
        via = geocode(via_query, config)
        print(f"Via             : {via['display_name']}")
        alt_route = fetch_foot_route([origin, via, destination], config)
        via_summary = builder.absorb_route(
            alt_route, "alternatif", origin_label, destination_label
        )
        print(
            f"Koridor alternatif: {via_summary['total_distance_m']} m, "
            f"{via_summary['total_duration_min']} menit"
        )

    graph = {
        "origin": origin,
        "destination": destination,
        "direct": direct_summary,
        "via": via_summary,
        **builder.to_dict(),
    }

    out_path = Path(config["output_path"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"[SUCCESS] Graph JSON disimpan ke: {out_path}")
    print(f"  Node: {len(graph['nodes'])} | Edge: {len(graph['edges'])}")

    dist_ok = (
        abs(graph["direct"]["total_distance_m"] - config["expected_distance_m"])
        <= config["distance_tolerance_m"]
    )
    dur_ok = (
        abs(graph["direct"]["total_duration_min"] - config["expected_duration_min"])
        <= config["duration_tolerance_min"]
    )
    if dist_ok and dur_ok:
        print("[CHECK] Rute langsung sesuai target kasus (plus minus 1,2 km / 15 menit).")
    else:
        print(
            "[WARNING] Rute langsung di luar band target. "
            f"(jarak ok={dist_ok}, durasi ok={dur_ok})"
        )


if __name__ == "__main__":
    main()
