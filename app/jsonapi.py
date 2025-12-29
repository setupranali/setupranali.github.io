"""
JSON:API Compliance for SetuPranali

Standardized REST response format following JSON:API specification (v1.1):
https://jsonapi.org/format/

Features:
- Compound documents with included resources
- Sparse fieldsets
- Pagination (cursor and offset)
- Sorting
- Filtering
- Error objects
- Links and relationships
- Meta information
"""

import math
import hashlib
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlencode, urlparse, parse_qs

from pydantic import BaseModel, Field
from fastapi import Request


# =============================================================================
# JSON:API Configuration
# =============================================================================

class JSONAPIConfig(BaseModel):
    """JSON:API configuration."""
    
    enabled: bool = Field(default=True)
    version: str = Field(default="1.1")
    base_url: str = Field(default="http://localhost:8080")
    default_page_size: int = Field(default=25)
    max_page_size: int = Field(default=1000)
    include_meta: bool = Field(default=True)
    include_links: bool = Field(default=True)


# =============================================================================
# JSON:API Resource Objects
# =============================================================================

@dataclass
class ResourceIdentifier:
    """JSON:API resource identifier."""
    type: str
    id: str


@dataclass
class Relationship:
    """JSON:API relationship."""
    data: Optional[Union[ResourceIdentifier, List[ResourceIdentifier]]] = None
    links: Optional[Dict[str, str]] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass
class Resource:
    """JSON:API resource object."""
    type: str
    id: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, Relationship] = field(default_factory=dict)
    links: Optional[Dict[str, str]] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass
class ErrorSource:
    """JSON:API error source."""
    pointer: Optional[str] = None
    parameter: Optional[str] = None
    header: Optional[str] = None


@dataclass
class ErrorObject:
    """JSON:API error object."""
    id: Optional[str] = None
    status: Optional[str] = None
    code: Optional[str] = None
    title: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[ErrorSource] = None
    links: Optional[Dict[str, str]] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass
class Link:
    """JSON:API link object."""
    href: str
    rel: Optional[str] = None
    describedby: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    hreflang: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


# =============================================================================
# JSON:API Document
# =============================================================================

@dataclass
class JSONAPIDocument:
    """JSON:API top-level document."""
    
    # Primary data
    data: Optional[Union[Resource, List[Resource], ResourceIdentifier, List[ResourceIdentifier]]] = None
    
    # Errors (mutually exclusive with data)
    errors: Optional[List[ErrorObject]] = None
    
    # Meta information
    meta: Optional[Dict[str, Any]] = None
    
    # JSON:API object
    jsonapi: Optional[Dict[str, Any]] = None
    
    # Links
    links: Optional[Dict[str, Union[str, Link]]] = None
    
    # Included resources
    included: Optional[List[Resource]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        result = {}
        
        if self.data is not None:
            result["data"] = self._serialize_data(self.data)
        
        if self.errors:
            result["errors"] = [self._serialize_error(e) for e in self.errors]
        
        if self.meta:
            result["meta"] = self.meta
        
        if self.jsonapi:
            result["jsonapi"] = self.jsonapi
        
        if self.links:
            result["links"] = self._serialize_links(self.links)
        
        if self.included:
            result["included"] = [self._serialize_resource(r) for r in self.included]
        
        return result
    
    def _serialize_data(self, data) -> Any:
        """Serialize data field."""
        if isinstance(data, list):
            return [self._serialize_data(item) for item in data]
        elif isinstance(data, Resource):
            return self._serialize_resource(data)
        elif isinstance(data, ResourceIdentifier):
            return {"type": data.type, "id": data.id}
        return data
    
    def _serialize_resource(self, resource: Resource) -> Dict[str, Any]:
        """Serialize resource object."""
        result = {
            "type": resource.type,
            "id": resource.id,
        }
        
        if resource.attributes:
            result["attributes"] = resource.attributes
        
        if resource.relationships:
            result["relationships"] = {
                name: self._serialize_relationship(rel)
                for name, rel in resource.relationships.items()
            }
        
        if resource.links:
            result["links"] = resource.links
        
        if resource.meta:
            result["meta"] = resource.meta
        
        return result
    
    def _serialize_relationship(self, rel: Relationship) -> Dict[str, Any]:
        """Serialize relationship."""
        result = {}
        
        if rel.data is not None:
            if isinstance(rel.data, list):
                result["data"] = [{"type": r.type, "id": r.id} for r in rel.data]
            else:
                result["data"] = {"type": rel.data.type, "id": rel.data.id}
        
        if rel.links:
            result["links"] = rel.links
        
        if rel.meta:
            result["meta"] = rel.meta
        
        return result
    
    def _serialize_error(self, error: ErrorObject) -> Dict[str, Any]:
        """Serialize error object."""
        result = {}
        
        if error.id:
            result["id"] = error.id
        if error.status:
            result["status"] = error.status
        if error.code:
            result["code"] = error.code
        if error.title:
            result["title"] = error.title
        if error.detail:
            result["detail"] = error.detail
        if error.source:
            result["source"] = {
                k: v for k, v in {
                    "pointer": error.source.pointer,
                    "parameter": error.source.parameter,
                    "header": error.source.header,
                }.items() if v
            }
        if error.links:
            result["links"] = error.links
        if error.meta:
            result["meta"] = error.meta
        
        return result
    
    def _serialize_links(self, links: Dict[str, Union[str, Link]]) -> Dict[str, Any]:
        """Serialize links object."""
        result = {}
        for name, link in links.items():
            if isinstance(link, str):
                result[name] = link
            elif isinstance(link, Link):
                result[name] = {
                    "href": link.href,
                    **({"rel": link.rel} if link.rel else {}),
                    **({"title": link.title} if link.title else {}),
                    **({"type": link.type} if link.type else {}),
                    **({"meta": link.meta} if link.meta else {}),
                }
        return result


# =============================================================================
# JSON:API Response Builder
# =============================================================================

class JSONAPIBuilder:
    """Build JSON:API compliant responses."""
    
    def __init__(self, config: JSONAPIConfig):
        self.config = config
    
    def resource(
        self,
        type: str,
        id: str,
        attributes: Dict[str, Any] = None,
        relationships: Dict[str, Any] = None,
        links: Dict[str, str] = None,
        meta: Dict[str, Any] = None,
    ) -> Resource:
        """Create a resource object."""
        rels = {}
        if relationships:
            for name, rel_data in relationships.items():
                if isinstance(rel_data, dict):
                    if "data" in rel_data:
                        data = rel_data["data"]
                        if isinstance(data, list):
                            rels[name] = Relationship(
                                data=[ResourceIdentifier(type=d["type"], id=d["id"]) for d in data]
                            )
                        else:
                            rels[name] = Relationship(
                                data=ResourceIdentifier(type=data["type"], id=data["id"])
                            )
                    else:
                        rels[name] = Relationship(**rel_data)
        
        return Resource(
            type=type,
            id=str(id),
            attributes=attributes or {},
            relationships=rels,
            links=links,
            meta=meta,
        )
    
    def collection(
        self,
        resources: List[Resource],
        total: Optional[int] = None,
        page: int = 1,
        page_size: int = None,
        request: Request = None,
        included: List[Resource] = None,
        meta: Dict[str, Any] = None,
    ) -> JSONAPIDocument:
        """Create a collection document with pagination."""
        page_size = page_size or self.config.default_page_size
        
        # Build meta
        doc_meta = meta or {}
        if total is not None:
            doc_meta["total"] = total
            doc_meta["page"] = page
            doc_meta["pageSize"] = page_size
            doc_meta["totalPages"] = math.ceil(total / page_size)
        
        # Build links
        links = {}
        if self.config.include_links and request:
            base_url = str(request.url).split("?")[0]
            params = dict(request.query_params)
            
            links["self"] = self._build_url(base_url, {**params, "page[number]": page, "page[size]": page_size})
            links["first"] = self._build_url(base_url, {**params, "page[number]": 1, "page[size]": page_size})
            
            if total is not None:
                total_pages = math.ceil(total / page_size)
                links["last"] = self._build_url(base_url, {**params, "page[number]": total_pages, "page[size]": page_size})
                
                if page > 1:
                    links["prev"] = self._build_url(base_url, {**params, "page[number]": page - 1, "page[size]": page_size})
                
                if page < total_pages:
                    links["next"] = self._build_url(base_url, {**params, "page[number]": page + 1, "page[size]": page_size})
        
        return JSONAPIDocument(
            data=resources,
            links=links if links else None,
            meta=doc_meta if doc_meta else None,
            included=included,
            jsonapi={"version": self.config.version} if self.config.include_meta else None,
        )
    
    def single(
        self,
        resource: Resource,
        included: List[Resource] = None,
        links: Dict[str, str] = None,
        meta: Dict[str, Any] = None,
    ) -> JSONAPIDocument:
        """Create a single resource document."""
        return JSONAPIDocument(
            data=resource,
            links=links,
            meta=meta,
            included=included,
            jsonapi={"version": self.config.version} if self.config.include_meta else None,
        )
    
    def error(
        self,
        status: int,
        title: str,
        detail: str = None,
        code: str = None,
        source_pointer: str = None,
        source_parameter: str = None,
        meta: Dict[str, Any] = None,
    ) -> JSONAPIDocument:
        """Create an error document."""
        error = ErrorObject(
            id=hashlib.sha256(str(datetime.now().timestamp()).encode()).hexdigest()[:16],
            status=str(status),
            code=code,
            title=title,
            detail=detail,
            source=ErrorSource(pointer=source_pointer, parameter=source_parameter) if source_pointer or source_parameter else None,
            meta=meta,
        )
        
        return JSONAPIDocument(
            errors=[error],
            jsonapi={"version": self.config.version} if self.config.include_meta else None,
        )
    
    def errors(self, errors: List[ErrorObject]) -> JSONAPIDocument:
        """Create a document with multiple errors."""
        return JSONAPIDocument(
            errors=errors,
            jsonapi={"version": self.config.version} if self.config.include_meta else None,
        )
    
    def _build_url(self, base: str, params: Dict[str, Any]) -> str:
        """Build URL with query parameters."""
        clean_params = {k: v for k, v in params.items() if v is not None}
        if clean_params:
            return f"{base}?{urlencode(clean_params)}"
        return base


# =============================================================================
# Query Result to JSON:API Converter
# =============================================================================

class QueryResultConverter:
    """Convert query results to JSON:API format."""
    
    def __init__(self, builder: JSONAPIBuilder):
        self.builder = builder
    
    def convert_query_result(
        self,
        dataset: str,
        data: List[Dict[str, Any]],
        dimensions: List[str],
        metrics: List[str],
        request: Request = None,
        total: int = None,
        page: int = 1,
        page_size: int = 25,
        cache_hit: bool = False,
        duration_ms: float = None,
    ) -> JSONAPIDocument:
        """Convert query result to JSON:API document."""
        resources = []
        
        for i, row in enumerate(data):
            # Generate stable ID from dimension values
            dim_values = "_".join(str(row.get(d, "")) for d in dimensions)
            row_id = hashlib.sha256(f"{dataset}_{i}_{dim_values}".encode()).hexdigest()[:12]
            
            resource = self.builder.resource(
                type=f"{dataset}_result",
                id=row_id,
                attributes=row,
                meta={"index": i},
            )
            resources.append(resource)
        
        # Add query metadata
        meta = {
            "dataset": dataset,
            "dimensions": dimensions,
            "metrics": metrics,
            "cacheHit": cache_hit,
        }
        if duration_ms is not None:
            meta["durationMs"] = duration_ms
        
        return self.builder.collection(
            resources=resources,
            total=total or len(data),
            page=page,
            page_size=page_size,
            request=request,
            meta=meta,
        )
    
    def convert_dataset(
        self,
        dataset: Dict[str, Any],
        include_dimensions: bool = True,
        include_metrics: bool = True,
    ) -> Resource:
        """Convert dataset to JSON:API resource."""
        relationships = {}
        included = []
        
        if include_dimensions and "dimensions" in dataset:
            dim_refs = []
            for dim in dataset["dimensions"]:
                dim_id = f"{dataset['id']}_dim_{dim['name']}"
                dim_refs.append(ResourceIdentifier(type="dimension", id=dim_id))
                included.append(self.builder.resource(
                    type="dimension",
                    id=dim_id,
                    attributes={
                        "name": dim["name"],
                        "type": dim.get("type", "string"),
                        "description": dim.get("description"),
                    },
                ))
            relationships["dimensions"] = Relationship(data=dim_refs)
        
        if include_metrics and "metrics" in dataset:
            met_refs = []
            for met in dataset["metrics"]:
                met_id = f"{dataset['id']}_met_{met['name']}"
                met_refs.append(ResourceIdentifier(type="metric", id=met_id))
                included.append(self.builder.resource(
                    type="metric",
                    id=met_id,
                    attributes={
                        "name": met["name"],
                        "type": met.get("type", "number"),
                        "aggregation": met.get("aggregation"),
                        "description": met.get("description"),
                    },
                ))
            relationships["metrics"] = Relationship(data=met_refs)
        
        resource = self.builder.resource(
            type="dataset",
            id=dataset["id"],
            attributes={
                "name": dataset.get("name", dataset["id"]),
                "description": dataset.get("description"),
                "tags": dataset.get("tags", []),
            },
            relationships={"dimensions": relationships.get("dimensions"), "metrics": relationships.get("metrics")} if relationships else None,
        )
        
        return resource, included
    
    def convert_error(
        self,
        status: int,
        code: str,
        message: str,
        details: Dict[str, Any] = None,
        suggestion: str = None,
    ) -> JSONAPIDocument:
        """Convert error to JSON:API format."""
        meta = {}
        if details:
            meta["details"] = details
        if suggestion:
            meta["suggestion"] = suggestion
        
        return self.builder.error(
            status=status,
            title=self._get_error_title(status),
            detail=message,
            code=code,
            meta=meta if meta else None,
        )
    
    def _get_error_title(self, status: int) -> str:
        """Get error title from status code."""
        titles = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
        }
        return titles.get(status, "Error")


# =============================================================================
# Request Parser
# =============================================================================

class JSONAPIRequestParser:
    """Parse JSON:API style request parameters."""
    
    def parse_pagination(self, request: Request) -> Dict[str, int]:
        """Parse pagination parameters."""
        params = request.query_params
        
        # Support both page[number] and page styles
        page = int(params.get("page[number]", params.get("page", 1)))
        size = int(params.get("page[size]", params.get("pageSize", params.get("limit", 25))))
        
        return {"page": page, "page_size": size}
    
    def parse_sort(self, request: Request) -> List[Dict[str, str]]:
        """Parse sort parameter."""
        sort_param = request.query_params.get("sort", "")
        if not sort_param:
            return []
        
        result = []
        for field in sort_param.split(","):
            field = field.strip()
            if field.startswith("-"):
                result.append({"field": field[1:], "direction": "desc"})
            else:
                result.append({"field": field, "direction": "asc"})
        
        return result
    
    def parse_filter(self, request: Request) -> Dict[str, Any]:
        """Parse filter parameters."""
        filters = {}
        
        for key, value in request.query_params.items():
            if key.startswith("filter[") and key.endswith("]"):
                field = key[7:-1]
                filters[field] = value
        
        return filters
    
    def parse_fields(self, request: Request) -> Dict[str, List[str]]:
        """Parse sparse fieldsets."""
        fields = {}
        
        for key, value in request.query_params.items():
            if key.startswith("fields[") and key.endswith("]"):
                resource_type = key[7:-1]
                fields[resource_type] = [f.strip() for f in value.split(",")]
        
        return fields
    
    def parse_include(self, request: Request) -> List[str]:
        """Parse include parameter for compound documents."""
        include_param = request.query_params.get("include", "")
        if not include_param:
            return []
        
        return [i.strip() for i in include_param.split(",")]


# =============================================================================
# Global Instances
# =============================================================================

_config: Optional[JSONAPIConfig] = None
_builder: Optional[JSONAPIBuilder] = None
_converter: Optional[QueryResultConverter] = None
_parser: Optional[JSONAPIRequestParser] = None


def init_jsonapi(config: Optional[JSONAPIConfig] = None) -> None:
    """Initialize JSON:API components."""
    global _config, _builder, _converter, _parser
    
    _config = config or JSONAPIConfig()
    _builder = JSONAPIBuilder(_config)
    _converter = QueryResultConverter(_builder)
    _parser = JSONAPIRequestParser()


def get_builder() -> Optional[JSONAPIBuilder]:
    """Get JSON:API builder."""
    return _builder


def get_converter() -> Optional[QueryResultConverter]:
    """Get query result converter."""
    return _converter


def get_parser() -> Optional[JSONAPIRequestParser]:
    """Get request parser."""
    return _parser

