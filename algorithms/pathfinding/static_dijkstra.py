import heapq
import networkx as nx
from algorithms.registry import AlgorithmRegistry
from core.base_algorithm import BaseGraphAlgorithm


class StaticDijkstra(BaseGraphAlgorithm):

    SUPPORTED_EVENT_TYPES = frozenset(
        {
            "DYNAMIC_EDGE_WEIGHT",
            "BLOCK_NODE",
            "UNBLOCK_NODE",
            "BLOCK_EDGE",
            "UNBLOCK_EDGE",
        }
    )

    def __init__(self, graph: nx.DiGraph):
        super().__init__(graph)
        self.dist = {}
        self.parent = {}
        self.blocked_nodes = set()
        self.blocked_edges = set()

    def _edge_blocked(self, u, v):
        return (u, v) in self.blocked_edges or (v, u) in self.blocked_edges

    def _snapshot(self):
        return {
            "blocked_nodes": sorted(self.blocked_nodes),
            "blocked_edges": [list(e) for e in sorted(self.blocked_edges)],
        }

    def run(self, start_node: int, goal_node: int):
        if start_node in self.blocked_nodes or goal_node in self.blocked_nodes:
            self.log_step(
                event_type="PATH_NOT_FOUND",
                state_mutations={
                    "start_node": start_node,
                    "goal_node": goal_node,
                    "reason": "start atau goal terblokir",
                    **self._snapshot(),
                },
            )
            return [], float("inf")

        self.dist = {node: float("inf") for node in self.graph.nodes}
        self.parent = {node: None for node in self.graph.nodes}
        self.dist[start_node] = 0
        pq = [(0, start_node)]

        self.log_step(
            event_type="INITIALIZATION",
            state_mutations={
                "start_node": start_node,
                "distance_table": self.dist.copy(),
                "priority_queue": pq.copy(),
                **self._snapshot(),
            },
        )

        while pq:
            current_dist, u = heapq.heappop(pq)

            if current_dist > self.dist[u]:
                continue

            if u == goal_node:
                path = []
                curr = goal_node
                while curr is not None:
                    path.append(curr)
                    curr = self.parent[curr]
                path.reverse()

                self.log_step(
                    event_type="PATH_FOUND",
                    state_mutations={
                        "target_node": u,
                        "active_path": path,
                        "total_cost": current_dist,
                        "distance_table": self.dist.copy(),
                        **self._snapshot(),
                    },
                )
                return path, current_dist

            for v, edge_data in self.graph[u].items():
                if v in self.blocked_nodes:
                    continue
                if self._edge_blocked(u, v):
                    continue
                weight = edge_data.get("weight", 1)
                new_dist = current_dist + weight

                if new_dist < self.dist[v]:
                    old_dist = self.dist[v]
                    self.dist[v] = new_dist
                    self.parent[v] = u
                    heapq.heappush(pq, (new_dist, v))

                    self.log_step(
                        event_type="RELAX_EDGE",
                        state_mutations={
                            "current_node": u,
                            "evaluated_edge": [u, v],
                            "edge_weight": weight,
                            "old_dist": old_dist,
                            "new_dist": new_dist,
                            "priority_queue": pq.copy(),
                            "distance_table": self.dist.copy(),
                            "parent_table": self.parent.copy(),
                        },
                    )

        self.log_step(
            event_type="PATH_NOT_FOUND",
            state_mutations={
                "start_node": start_node,
                "goal_node": goal_node,
                "reason": "goal tidak terjangkau dari keadaan saat ini",
                **self._snapshot(),
            },
        )
        return [], float("inf")

    def _apply_event(self, event_data: dict) -> None:
        etype = event_data["type"]
        entity_id = event_data.get("entity_id")

        if etype == "DYNAMIC_EDGE_WEIGHT":
            edge = tuple(event_data["edge"])
            new_weight = event_data["new_weight"]
            old_weight = self.graph[edge[0]][edge[1]].get("weight", 1)
            self.graph[edge[0]][edge[1]]["weight"] = new_weight
            if self.graph.has_edge(edge[1], edge[0]):
                self.graph[edge[1]][edge[0]]["weight"] = new_weight
            self.log_step(
                event_type="UPDATE_WEIGHT_EVENT",
                state_mutations={
                    "target_edge": list(edge),
                    "old_weight": old_weight,
                    "new_weight": new_weight,
                    "entity_id": entity_id,
                },
            )
            return

        if etype in ("BLOCK_NODE", "UNBLOCK_NODE"):
            node = event_data["target_node"]
            if etype == "BLOCK_NODE":
                self.blocked_nodes.add(node)
            else:
                self.blocked_nodes.discard(node)
            self.log_step(
                event_type="BLOCK_INJECTED" if etype == "BLOCK_NODE" else "BLOCK_REMOVED",
                state_mutations={
                    "target_node": node,
                    "entity_id": entity_id,
                    **self._snapshot(),
                },
            )
            return

        if etype in ("BLOCK_EDGE", "UNBLOCK_EDGE"):
            edge = tuple(event_data["edge"])
            pairs = [edge, (edge[1], edge[0])]
            if etype == "BLOCK_EDGE":
                self.blocked_edges.update(pairs)
            else:
                for pair in pairs:
                    self.blocked_edges.discard(pair)
            self.log_step(
                event_type="BLOCK_INJECTED" if etype == "BLOCK_EDGE" else "BLOCK_REMOVED",
                state_mutations={
                    "target_edge": list(edge),
                    "entity_id": entity_id,
                    **self._snapshot(),
                },
            )
            return

        raise KeyError(f"Tipe event tidak dikenal: {etype}")

    def apply_initial_state(self, events):
        for event in events:
            self._apply_event(self._normalize(event))

    def handle_dynamic_event(self, event_data: dict):
        self._apply_event(self._normalize(event_data))
        return self.run(event_data["start"], event_data["goal"])

    def _normalize(self, event: dict) -> dict:
        normalized = dict(event)
        if "target_edge" in normalized:
            normalized["edge"] = tuple(normalized["target_edge"])
        return normalized


AlgorithmRegistry.register("static_dijkstra", StaticDijkstra)
AlgorithmRegistry.register_alias("pathfinding", "static_dijkstra")
