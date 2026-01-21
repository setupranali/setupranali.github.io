import yaml
from pathlib import Path

# Catalog file is at ubi-connector/catalog.yaml
# From app/domain/sources/catalog.py, we need to go up 4 levels: sources -> domain -> app -> ubi-connector
CATALOG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "catalog.yaml"

def load_catalog() -> dict:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_dataset(catalog: dict, dataset_id: str) -> dict:
    """
    Get dataset by ID from catalog.
    Supports both dict format (id: config) and list format ([{id: ..., ...}]).
    """
    datasets = catalog.get("datasets", {})
    
    # Handle dict format (id: config)
    if isinstance(datasets, dict):
        if dataset_id in datasets:
            dataset = datasets[dataset_id]
            if isinstance(dataset, dict):
                dataset["id"] = dataset_id  # Ensure id is set
                return dataset
        raise KeyError(f"Dataset not found: {dataset_id}")
    
    # Handle list format
    for d in datasets:
        if d.get("id") == dataset_id:
            return d
    raise KeyError(f"Dataset not found: {dataset_id}")
