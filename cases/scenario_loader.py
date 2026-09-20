from pathlib import Path
from typing import Any, Dict, Union
import yaml
from core.graph_model import SpatialGraphModel


class ScenarioLoader:

    def __init__(self, yaml_file_path: Union[str, Path]):
        with open(yaml_file_path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

    def get_metadata(self) -> Dict[str, Any]:
        return self.data.get("metadata", {})

    def build_graph_model(self) -> SpatialGraphModel:
        model = SpatialGraphModel()

        for node in self.data["topology"]["nodes"]:
            model.add_spatial_node(
                node_id=node["id"],
                label=node.get("label", f"Node_{node['id']}"),
                pos=node.get("pos", [0.0, 0.0]),
            )

        for edge in self.data["topology"]["edges"]:
            model.add_weighted_edge(
                u=edge["from"], v=edge["to"], weight=edge["weight"]
            )

        return model

    def get_execution_plan(self) -> Dict[str, Any]:
        return self.data.get("execution_plan", {})