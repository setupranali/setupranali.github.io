"""
ERD (Entity Relationship Diagram) Manager

Manages visual ERD canvas state:
- Table nodes (position, visibility, collapsed state)
- Relationship edges (joins between tables)
- Graph persistence and retrieval

Supports:
- Multiple ERD models per workspace
- Cardinality (1-1, 1-N, N-N)
- Join types (inner, left, right, full)
- Active/inactive relationships
- Type validation for joins
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Cardinality(str, Enum):
    """Relationship cardinality."""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:N"


class JoinType(str, Enum):
    """SQL join type."""
    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"
    CROSS = "cross"


@dataclass
class Position:
    """Canvas position for a node."""
    x: float = 0
    y: float = 0
    
    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}
    
    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        return cls(x=data.get("x", 0), y=data.get("y", 0))


@dataclass
class TableNode:
    """
    A table node on the ERD canvas.
    
    Attributes:
        id: Unique node identifier
        schema_name: Database schema
        table_name: Table name
        position: Canvas position (x, y)
        columns: List of column names to display
        is_collapsed: Whether to show only table name
        is_visible: Whether to render on canvas
        color: Optional highlight color
        alias: Optional display alias
        metadata: Additional node metadata
    """
    id: str
    schema_name: str
    table_name: str
    position: Position = field(default_factory=Position)
    columns: List[str] = field(default_factory=list)
    is_collapsed: bool = False
    is_visible: bool = True
    color: Optional[str] = None
    alias: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def full_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "schemaName": self.schema_name,
            "tableName": self.table_name,
            "fullName": self.full_name,
            "position": self.position.to_dict(),
            "columns": self.columns,
            "isCollapsed": self.is_collapsed,
            "isVisible": self.is_visible,
            "color": self.color,
            "alias": self.alias,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TableNode":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            schema_name=data.get("schemaName", data.get("schema_name", "")),
            table_name=data.get("tableName", data.get("table_name", "")),
            position=Position.from_dict(data.get("position", {})),
            columns=data.get("columns", []),
            is_collapsed=data.get("isCollapsed", data.get("is_collapsed", False)),
            is_visible=data.get("isVisible", data.get("is_visible", True)),
            color=data.get("color"),
            alias=data.get("alias"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RelationshipEdge:
    """
    A relationship (join) between two tables.
    
    Attributes:
        id: Unique edge identifier
        source_node_id: Source table node ID
        source_column: Source column name
        target_node_id: Target table node ID
        target_column: Target column name
        cardinality: Relationship cardinality
        join_type: SQL join type
        is_active: Whether relationship is active for query generation
        name: Optional relationship name
        description: Optional description
        metadata: Additional edge metadata
    """
    id: str
    source_node_id: str
    source_column: str
    target_node_id: str
    target_column: str
    cardinality: Cardinality = Cardinality.MANY_TO_ONE
    join_type: JoinType = JoinType.LEFT
    is_active: bool = True
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sourceNodeId": self.source_node_id,
            "sourceColumn": self.source_column,
            "targetNodeId": self.target_node_id,
            "targetColumn": self.target_column,
            "cardinality": self.cardinality.value,
            "joinType": self.join_type.value,
            "isActive": self.is_active,
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RelationshipEdge":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source_node_id=data.get("sourceNodeId", data.get("source_node_id", "")),
            source_column=data.get("sourceColumn", data.get("source_column", "")),
            target_node_id=data.get("targetNodeId", data.get("target_node_id", "")),
            target_column=data.get("targetColumn", data.get("target_column", "")),
            cardinality=Cardinality(data.get("cardinality", "N:1")),
            join_type=JoinType(data.get("joinType", data.get("join_type", "left"))),
            is_active=data.get("isActive", data.get("is_active", True)),
            name=data.get("name"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ERDModel:
    """
    Complete ERD model containing nodes and edges.
    
    Attributes:
        id: Unique model identifier
        name: Model name
        description: Model description
        source_id: Associated data source ID
        nodes: Table nodes
        edges: Relationship edges
        created_at: Creation timestamp
        updated_at: Last update timestamp
        version: Schema version for migrations
        metadata: Additional model metadata
    """
    id: str
    name: str
    source_id: str
    nodes: List[TableNode] = field(default_factory=list)
    edges: List[RelationshipEdge] = field(default_factory=list)
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sourceId": self.source_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ERDModel":
        created_at = data.get("createdAt") or data.get("created_at")
        updated_at = data.get("updatedAt") or data.get("updated_at")
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Untitled"),
            description=data.get("description"),
            source_id=data.get("sourceId", data.get("source_id", "")),
            nodes=[TableNode.from_dict(n) for n in data.get("nodes", [])],
            edges=[RelationshipEdge.from_dict(e) for e in data.get("edges", [])],
            created_at=datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at,
            updated_at=datetime.fromisoformat(updated_at) if isinstance(updated_at, str) else updated_at,
            version=data.get("version", 1),
            metadata=data.get("metadata", {}),
        )
    
    def get_node(self, node_id: str) -> Optional[TableNode]:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_node_by_table(self, schema_name: str, table_name: str) -> Optional[TableNode]:
        """Get node by table reference."""
        for node in self.nodes:
            if node.schema_name == schema_name and node.table_name == table_name:
                return node
        return None
    
    def get_edges_for_node(self, node_id: str) -> List[RelationshipEdge]:
        """Get all edges connected to a node."""
        return [
            e for e in self.edges 
            if e.source_node_id == node_id or e.target_node_id == node_id
        ]
    
    def add_node(self, node: TableNode) -> None:
        """Add a node, avoiding duplicates."""
        existing = self.get_node(node.id)
        if not existing:
            self.nodes.append(node)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node and its edges."""
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.edges = [
            e for e in self.edges 
            if e.source_node_id != node_id and e.target_node_id != node_id
        ]
        self.updated_at = datetime.now(timezone.utc)
    
    def add_edge(self, edge: RelationshipEdge) -> None:
        """Add an edge."""
        existing = next((e for e in self.edges if e.id == edge.id), None)
        if not existing:
            self.edges.append(edge)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge."""
        self.edges = [e for e in self.edges if e.id != edge_id]
        self.updated_at = datetime.now(timezone.utc)
    
    def validate(self) -> List[str]:
        """
        Validate the ERD model.
        
        Returns:
            List of validation error messages
        """
        errors = []
        node_ids = {n.id for n in self.nodes}
        
        for edge in self.edges:
            if edge.source_node_id not in node_ids:
                errors.append(f"Edge {edge.id}: source node {edge.source_node_id} not found")
            if edge.target_node_id not in node_ids:
                errors.append(f"Edge {edge.id}: target node {edge.target_node_id} not found")
        
        return errors


class ERDManager:
    """
    Manages ERD model persistence.
    
    Uses SQLite for storage with JSON serialization.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize ERD manager.
        
        Args:
            db_path: Path to SQLite database. Defaults to app/db/erd.db
        """
        if db_path is None:
            db_dir = Path(__file__).parent.parent / "db"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "erd.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS erd_models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    description TEXT,
                    data TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_erd_source_id 
                ON erd_models(source_id)
            """)
            conn.commit()
    
    def create(self, model: ERDModel) -> ERDModel:
        """
        Create a new ERD model.
        
        Args:
            model: ERDModel to create
        
        Returns:
            Created ERDModel with generated ID
        """
        if not model.id:
            model.id = str(uuid.uuid4())
        
        model.created_at = datetime.now(timezone.utc)
        model.updated_at = model.created_at
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO erd_models (id, name, source_id, description, data, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model.id,
                model.name,
                model.source_id,
                model.description,
                json.dumps(model.to_dict()),
                model.version,
                model.created_at.isoformat(),
                model.updated_at.isoformat(),
            ))
            conn.commit()
        
        logger.info(f"Created ERD model: {model.id}")
        return model
    
    def get(self, model_id: str) -> Optional[ERDModel]:
        """
        Get ERD model by ID.
        
        Args:
            model_id: Model ID
        
        Returns:
            ERDModel if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT data FROM erd_models WHERE id = ?",
                (model_id,)
            ).fetchone()
        
        if row:
            return ERDModel.from_dict(json.loads(row["data"]))
        return None
    
    def update(self, model: ERDModel) -> ERDModel:
        """
        Update an existing ERD model.
        
        Args:
            model: ERDModel with updates
        
        Returns:
            Updated ERDModel
        """
        model.updated_at = datetime.now(timezone.utc)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE erd_models 
                SET name = ?, description = ?, data = ?, version = ?, updated_at = ?
                WHERE id = ?
            """, (
                model.name,
                model.description,
                json.dumps(model.to_dict()),
                model.version,
                model.updated_at.isoformat(),
                model.id,
            ))
            conn.commit()
        
        logger.info(f"Updated ERD model: {model.id}")
        return model
    
    def delete(self, model_id: str) -> bool:
        """
        Delete an ERD model.
        
        Args:
            model_id: Model ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM erd_models WHERE id = ?",
                (model_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
        
        if deleted:
            logger.info(f"Deleted ERD model: {model_id}")
        return deleted
    
    def list_by_source(self, source_id: str) -> List[ERDModel]:
        """
        List all ERD models for a source.
        
        Args:
            source_id: Source ID to filter by
        
        Returns:
            List of ERDModels
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT data FROM erd_models WHERE source_id = ? ORDER BY updated_at DESC",
                (source_id,)
            ).fetchall()
        
        return [ERDModel.from_dict(json.loads(row["data"])) for row in rows]
    
    def list_all(self) -> List[ERDModel]:
        """
        List all ERD models.
        
        Returns:
            List of all ERDModels
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT data FROM erd_models ORDER BY updated_at DESC"
            ).fetchall()
        
        return [ERDModel.from_dict(json.loads(row["data"])) for row in rows]
    
    def duplicate(self, model_id: str, new_name: str) -> Optional[ERDModel]:
        """
        Duplicate an ERD model with a new name.
        
        Args:
            model_id: Source model ID
            new_name: Name for the duplicate
        
        Returns:
            New ERDModel if original found, None otherwise
        """
        original = self.get(model_id)
        if not original:
            return None
        
        duplicate = ERDModel(
            id=str(uuid.uuid4()),
            name=new_name,
            source_id=original.source_id,
            description=f"Copy of {original.name}",
            nodes=[TableNode.from_dict(n.to_dict()) for n in original.nodes],
            edges=[RelationshipEdge.from_dict(e.to_dict()) for e in original.edges],
            metadata=original.metadata.copy(),
        )
        
        return self.create(duplicate)


def validate_join_types(
    source_type: str,
    target_type: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate that two column types can be joined.
    
    Args:
        source_type: Normalized type of source column
        target_type: Normalized type of target column
    
    Returns:
        (is_valid, error_message)
    """
    # Compatible type groups
    numeric_types = {"integer", "bigint", "float", "double", "decimal"}
    string_types = {"string"}
    datetime_types = {"date", "datetime", "timestamp"}
    
    def get_type_group(t: str) -> str:
        t_lower = t.lower()
        if t_lower in numeric_types:
            return "numeric"
        if t_lower in string_types:
            return "string"
        if t_lower in datetime_types:
            return "datetime"
        return "other"
    
    source_group = get_type_group(source_type)
    target_group = get_type_group(target_type)
    
    # Same type is always valid
    if source_type.lower() == target_type.lower():
        return True, None
    
    # Same group is usually valid
    if source_group == target_group:
        return True, None
    
    # Cross-group joins are warnings, not errors
    if source_group != target_group:
        return True, f"Warning: Joining {source_type} with {target_type} may cause implicit conversion"
    
    return True, None

