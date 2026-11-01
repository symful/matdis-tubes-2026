from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml
from core.graph_model import SpatialGraphModel


class ScenarioLoader:

    METADATA_KEYS = ("case_id", "title", "description", "author")
    NODE_BLOCK_TYPES = ("BLOCK_NODE", "UNBLOCK_NODE")
    EDGE_BLOCK_TYPES = ("BLOCK_EDGE", "UNBLOCK_EDGE")
    WEIGHT_TYPES = ("DYNAMIC_EDGE_WEIGHT",)

    def __init__(self, yaml_file_path: Union[str, Path]):
        with open(yaml_file_path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

    def get_metadata(self) -> Dict[str, Any]:
        metadata = self.data.get("metadata")
        if isinstance(metadata, dict):
            return metadata
        return {key: self.data[key] for key in self.METADATA_KEYS if key in self.data}

    def get_problem(self) -> Dict[str, Any]:
        return self.data.get("problem", {})

    def get_entities(self) -> Dict[str, Any]:
        return self.data.get("entities", {})

    def get_fishbone(self) -> Dict[str, Any]:
        return self.data.get("fishbone", {})

    def get_sample(self) -> Dict[str, Any]:
        return self.data.get("sample", {})

    def get_entity_ids(self) -> List[str]:
        ids: List[str] = []
        entities = self.get_entities()
        for group in ("snakes", "trash", "flood"):
            for entity in entities.get(group, []):
                ids.append(entity["id"])
        return ids

    def build_graph_model(self) -> SpatialGraphModel:
        model = SpatialGraphModel()

        for node in self.data.get("nodes", []):
            model.add_spatial_node(
                node_id=node["id"],
                label=node.get("label", f"Node_{node['id']}"),
                pos=node.get("pos", [0.0, 0.0]),
                lat=node.get("lat"),
                lon=node.get("lon"),
            )

        for edge in self.data.get("edges", []):
            attrs = {
                key: edge[key]
                for key in ("street", "distance_m", "flooded")
                if key in edge
            }
            model.add_weighted_edge(
                u=edge["from"], v=edge["to"], weight=edge["weight"], attrs=attrs
            )
            if edge.get("direction", "dua_arah") == "dua_arah":
                model.add_weighted_edge(
                    u=edge["to"], v=edge["from"], weight=edge["weight"], attrs=attrs
                )

        return model

    def get_execution_plan(self) -> Dict[str, Any]:
        return self.data.get("execution_plan", {})

    def validate(self, model: Optional[SpatialGraphModel] = None) -> bool:
        if model is None:
            model = self.build_graph_model()
        graph = model.nx_graph
        plan = self.get_execution_plan()
        errors: List[str] = []

        if plan.get("start_node") not in graph.nodes:
            errors.append(f"start_node {plan.get('start_node')} tidak ada di graf")
        if plan.get("goal_node") not in graph.nodes:
            errors.append(f"goal_node {plan.get('goal_node')} tidak ada di graf")

        entities = self.get_entities()
        for snake in entities.get("snakes", []):
            for window in snake.get("windows", []):
                if window.get("node") not in graph.nodes:
                    errors.append(
                        f"ular {snake['id']}: window node {window.get('node')} tidak ada di graf"
                    )
        for trash in entities.get("trash", []):
            u, v = trash.get("edge", (None, None))
            if not graph.has_edge(u, v):
                errors.append(f"sampah {trash['id']}: edge ({u}, {v}) tidak ada di graf")
        for flood in entities.get("flood", []):
            for u, v in flood.get("submerged_edges", []):
                if not graph.has_edge(u, v):
                    errors.append(f"banjir {flood['id']}: edge ({u}, {v}) tidak ada di graf")

        known_ids = set(self.get_entity_ids())
        for idx, event in enumerate(plan.get("events", []), 1):
            entity_id = event.get("entity_id")
            if entity_id and entity_id not in known_ids:
                errors.append(
                    f"event #{idx}: entity_id {entity_id} tidak terdaftar di entities"
                )
            etype = event.get("type")
            if etype in self.NODE_BLOCK_TYPES:
                if event.get("target_node") not in graph.nodes:
                    errors.append(
                        f"event #{idx}: target_node {event.get('target_node')} tidak valid"
                    )
            if etype in self.EDGE_BLOCK_TYPES or etype in self.WEIGHT_TYPES:
                u, v = event.get("target_edge", (None, None))
                if not graph.has_edge(u, v):
                    errors.append(
                        f"event #{idx}: target_edge ({u}, {v}) tidak ada di graf"
                    )
            if etype in self.WEIGHT_TYPES and "new_weight" not in event:
                errors.append(f"event #{idx}: DYNAMIC_EDGE_WEIGHT tanpa new_weight")

        if errors:
            raise ValueError("Validasi skenario gagal:\n  " + "\n  ".join(errors))
        return True
