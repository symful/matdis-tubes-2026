# Parser struktur fishbone (Ishikawa) dari YAML skenario.
# Mendukung dua varian: kategori baku 6M dan kategori lahir dari kasus (non-6M).

FISHBONE_6M = ("MAN", "MACHINE", "METHOD", "MATERIAL", "ENVIRONMENT", "MEASUREMENT")


class FishboneParser:

    def __init__(self, fishbone_dict):
        self.data = fishbone_dict or {}

    def get_tables(self):
        tables = []
        for key, value in self.data.items():
            tables.append(
                {
                    "key": key,
                    "variant": "6m" if key.endswith("_6m") else "non6m",
                    "problem": value.get("problem", ""),
                    "categories": self._categories(value.get("categories", {})),
                }
            )
        return tables

    def _categories(self, raw):
        if isinstance(raw, dict):
            return [{"name": name, "causes": causes} for name, causes in raw.items()]
        return list(raw)

    def validate(self):
        for table in self.get_tables():
            if table["variant"] != "6m":
                continue
            names = [category["name"] for category in table["categories"]]
            if set(names) != set(FISHBONE_6M):
                raise ValueError(
                    f"Varian 6M '{table['key']}' wajib memakai 6 kategori baku, "
                    f"didapat: {names}"
                )
        return True

    def to_markdown(self):
        lines = []
        for table in self.get_tables():
            lines.append(f"### {table['problem']}")
            lines.append("")
            lines.append("| Kategori | Sub-penyebab |")
            lines.append("|---|---|")
            for category in table["categories"]:
                causes = "; ".join(category["causes"])
                lines.append(f"| **{category['name']}** | {causes} |")
            lines.append("")
        return "\n".join(lines)
