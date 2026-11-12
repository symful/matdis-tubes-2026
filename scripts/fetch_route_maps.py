# Kemal Ardian (251524053), Ahmad Bukhori (251524033), Hasan Nasrullah (251524051),
# Muhammad Akhtar Khawarizmi (251524055), Kelas 2B
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


def fetch_overpass(query, config):
    payload = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        config["overpass_endpoint"],
        data=payload,
        headers={"User-Agent": config["user_agent"]},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def route_bbox(builder, padding_m, lat0):
    lats = [node["lat"] for node in builder.nodes]
    lons = [node["lon"] for node in builder.nodes]
    lat_pad = padding_m / 110947.0
    lon_pad = padding_m / (111320.0 * math.cos(math.radians(lat0)))
    return (
        min(lats) - lat_pad,
        min(lons) - lon_pad,
        max(lats) + lat_pad,
        max(lons) + lon_pad,
    )


def build_network(config, bbox, lat0, lon0):
    """Fetch every foot-usable road around the corridor with Overpass."""
    south, west, north, east = bbox
    highways = config.get("network_highways", ["footway", "residential", "service"])
    pattern = "|".join(highways)
    query = (
        "[out:json][timeout:90];"
        f'way["highway"~"^({pattern})$"]'
        f"({south:.6f},{west:.6f},{north:.6f},{east:.6f});"
        "out body geom;"
    )
    data = fetch_overpass(query, config)

    net = GraphBuilder(lat0, lon0)
    for element in data.get("elements", []):
        if element.get("type") != "way":
            continue
        tags = element.get("tags", {})
        if tags.get("foot") in ("no", "private"):
            continue
        if tags.get("access") in ("private", "no"):
            continue
        geometry = element.get("geometry") or []
        if len(geometry) < 2:
            continue
        street = tags.get("name") or "Jalan Lingkungan"
        highway = tags.get("highway", "")
        previous = None
        for point in geometry:
            lat = float(point["lat"])
            lon = float(point["lon"])
            node_id = net.node_id(lat, lon, street)
            if previous is not None:
                first = net.nodes[previous]["pos_m"]
                second = net.nodes[node_id]["pos_m"]
                distance = math.hypot(second[0] - first[0], second[1] - first[1])
                duration = distance / 75.0
                net.add_edge(
                    previous, node_id, street, distance, duration, "jaringan", highway
                )
                net.add_edge(
                    node_id, previous, street, distance, duration, "jaringan", highway
                )
            previous = node_id
    return net


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

    def add_edge(self, u, v, street, distance_m, duration_min, corridor, highway=None):
        if u == v or distance_m <= 0.5:
            return
        key = (u, v)
        if key in self.edge_index:
            return
        self.edge_index[key] = len(self.edges)
        edge = {
            "from": u,
            "to": v,
            "street": street,
            "distance_m": round(distance_m, 1),
            "duration_min": round(duration_min, 2),
            "corridor": corridor,
        }
        if highway:
            edge["highway"] = highway
        self.edges.append(edge)

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

    network_path = config.get("network_output_path")
    if network_path:
        try:
            padding = config.get("network_padding_m", 300)
            bbox = route_bbox(builder, padding, origin["lat"])
            print(
                f"Mengambil jaringan jalan sekitar ({padding} m padding) "
                f"dari Overpass ..."
            )
            network_builder = build_network(
                config, bbox, origin["lat"], origin["lon"]
            )
            network = {
                "origin": origin,
                "destination": destination,
                "bbox": {
                    "south": round(bbox[0], 7),
                    "west": round(bbox[1], 7),
                    "north": round(bbox[2], 7),
                    "east": round(bbox[3], 7),
                },
                **network_builder.to_dict(),
            }
            network_out = Path(network_path)
            network_out.parent.mkdir(parents=True, exist_ok=True)
            with open(network_out, "w", encoding="utf-8") as f:
                json.dump(network, f, indent=2, ensure_ascii=False)
            print(f"[SUCCESS] Jaringan jalan disimpan ke: {network_out}")
            print(
                f"  Node: {len(network['nodes'])} | "
                f"Edge: {len(network['edges'])}"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[WARNING] Gagal mengambil jaringan jalan: {exc}")

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
