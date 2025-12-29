import yaml
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent.parent / "catalog.yaml"

def load_catalog() -> dict:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_dataset(catalog: dict, dataset_id: str) -> dict:
    for d in catalog.get("datasets", []):
        if d["id"] == dataset_id:
            return d
    raise KeyError(f"Dataset not found: {dataset_id}")
