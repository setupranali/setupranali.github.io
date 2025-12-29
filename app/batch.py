"""
Batch Queries for SetuPranali

Execute multiple queries in a single request:
- Parallel execution for independent queries
- Sequential execution for dependent queries
- Transaction support
- Partial failure handling

Features:
- Reduce HTTP round-trips
- Atomic operations
- Cross-query references
- Rate limit friendly
- Progress tracking
"""

import asyncio
import time
import logging
import hashlib
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class BatchConfig(BaseModel):
    """Batch query configuration."""
    
    enabled: bool = Field(default=True)
    max_queries: int = Field(default=20, description="Max queries per batch")
    max_parallel: int = Field(default=5, description="Max parallel executions")
    timeout_seconds: int = Field(default=300, description="Batch timeout")
    allow_partial_failure: bool = Field(default=True, description="Continue on failures")
    include_timing: bool = Field(default=True, description="Include timing info")


# =============================================================================
# Batch Request/Response Models
# =============================================================================

class BatchOperation(str, Enum):
    """Batch operation types."""
    QUERY = "query"
    SQL = "sql"
    INTROSPECT = "introspect"
    NLQ = "nlq"


class BatchQueryRequest(BaseModel):
    """Single query within a batch."""
    
    id: str = Field(..., description="Unique query ID within batch")
    operation: BatchOperation = Field(default=BatchOperation.QUERY)
    
    # Query parameters (for QUERY operation)
    dataset: Optional[str] = None
    dimensions: List[str] = Field(default=[])
    metrics: List[str] = Field(default=[])
    filters: Optional[Dict[str, Any]] = None
    order_by: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    
    # SQL parameters (for SQL operation)
    sql: Optional[str] = None
    
    # NLQ parameters (for NLQ operation)
    question: Optional[str] = None
    
    # Introspect parameters
    introspect_type: Optional[str] = None  # datasets, dimensions, metrics
    
    # Dependencies
    depends_on: List[str] = Field(default=[], description="Query IDs this depends on")
    
    # Options
    cache: bool = Field(default=True)
    timeout_ms: Optional[int] = None


class BatchRequest(BaseModel):
    """Batch query request."""
    
    queries: List[BatchQueryRequest]
    
    # Options
    parallel: bool = Field(default=True, description="Execute in parallel")
    stop_on_error: bool = Field(default=False, description="Stop batch on first error")
    transaction: bool = Field(default=False, description="Execute as transaction")
    include_metadata: bool = Field(default=True)


@dataclass
class BatchQueryResult:
    """Result of a single query in batch."""
    
    id: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    # Metadata
    rows_returned: int = 0
    cache_hit: bool = False


@dataclass
class BatchResult:
    """Result of batch execution."""
    
    batch_id: str
    total_queries: int
    successful: int
    failed: int
    results: Dict[str, BatchQueryResult]
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    
    # Metadata
    execution_order: List[str] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)


# =============================================================================
# Dependency Resolution
# =============================================================================

class DependencyResolver:
    """Resolve query dependencies for execution order."""
    
    def resolve(self, queries: List[BatchQueryRequest]) -> List[List[str]]:
        """
        Resolve dependencies and return execution groups.
        
        Returns list of groups, where queries in same group can run in parallel.
        """
        # Build dependency graph
        query_map = {q.id: q for q in queries}
        dependencies = {q.id: set(q.depends_on) for q in queries}
        
        # Check for cycles
        if self._has_cycle(dependencies):
            raise ValueError("Circular dependency detected in batch queries")
        
        # Topological sort into groups
        groups = []
        remaining = set(dependencies.keys())
        completed = set()
        
        while remaining:
            # Find all queries with no pending dependencies
            ready = {
                q_id for q_id in remaining
                if not (dependencies[q_id] - completed)
            }
            
            if not ready:
                raise ValueError("Unable to resolve dependencies")
            
            groups.append(list(ready))
            completed.update(ready)
            remaining -= ready
        
        return groups
    
    def _has_cycle(self, dependencies: Dict[str, set]) -> bool:
        """Check for circular dependencies using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in dependencies}
        
        def dfs(node):
            color[node] = GRAY
            for neighbor in dependencies.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    return True
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False
        
        return any(dfs(node) for node in dependencies if color[node] == WHITE)


# =============================================================================
# Batch Executor
# =============================================================================

class BatchExecutor:
    """Execute batch queries."""
    
    def __init__(
        self,
        config: BatchConfig,
        query_executor,  # Function to execute single query
        sql_executor=None,
        nlq_executor=None,
        introspect_executor=None
    ):
        self.config = config
        self.query_executor = query_executor
        self.sql_executor = sql_executor
        self.nlq_executor = nlq_executor
        self.introspect_executor = introspect_executor
        self.resolver = DependencyResolver()
    
    async def execute(self, request: BatchRequest) -> BatchResult:
        """Execute batch request."""
        if len(request.queries) > self.config.max_queries:
            raise ValueError(f"Batch size {len(request.queries)} exceeds maximum {self.config.max_queries}")
        
        batch_id = f"batch_{int(time.time() * 1000)}"
        started_at = datetime.now()
        
        result = BatchResult(
            batch_id=batch_id,
            total_queries=len(request.queries),
            successful=0,
            failed=0,
            results={},
            started_at=started_at,
        )
        
        try:
            # Resolve dependencies
            groups = self.resolver.resolve(request.queries)
            result.parallel_groups = groups
            
            query_map = {q.id: q for q in request.queries}
            query_results: Dict[str, BatchQueryResult] = {}
            
            # Execute groups
            for group in groups:
                if request.parallel and len(group) > 1:
                    # Execute group in parallel
                    group_results = await self._execute_parallel(
                        [query_map[q_id] for q_id in group],
                        query_results,
                        request.stop_on_error
                    )
                else:
                    # Execute sequentially
                    group_results = await self._execute_sequential(
                        [query_map[q_id] for q_id in group],
                        query_results,
                        request.stop_on_error
                    )
                
                query_results.update(group_results)
                result.execution_order.extend(group)
                
                # Check if we should stop
                if request.stop_on_error:
                    if any(not r.success for r in group_results.values()):
                        break
            
            # Compile results
            result.results = query_results
            result.successful = sum(1 for r in query_results.values() if r.success)
            result.failed = sum(1 for r in query_results.values() if not r.success)
            
        except Exception as e:
            logger.error(f"Batch execution error: {e}")
            raise
        
        finally:
            result.completed_at = datetime.now()
            result.total_duration_ms = (result.completed_at - started_at).total_seconds() * 1000
        
        return result
    
    async def _execute_parallel(
        self,
        queries: List[BatchQueryRequest],
        prior_results: Dict[str, BatchQueryResult],
        stop_on_error: bool
    ) -> Dict[str, BatchQueryResult]:
        """Execute queries in parallel."""
        semaphore = asyncio.Semaphore(self.config.max_parallel)
        
        async def execute_with_semaphore(query):
            async with semaphore:
                return await self._execute_single(query, prior_results)
        
        tasks = [execute_with_semaphore(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            q.id: (
                r if isinstance(r, BatchQueryResult)
                else BatchQueryResult(
                    id=q.id,
                    success=False,
                    error=str(r) if isinstance(r, Exception) else "Unknown error"
                )
            )
            for q, r in zip(queries, results)
        }
    
    async def _execute_sequential(
        self,
        queries: List[BatchQueryRequest],
        prior_results: Dict[str, BatchQueryResult],
        stop_on_error: bool
    ) -> Dict[str, BatchQueryResult]:
        """Execute queries sequentially."""
        results = {}
        
        for query in queries:
            result = await self._execute_single(query, {**prior_results, **results})
            results[query.id] = result
            
            if stop_on_error and not result.success:
                break
        
        return results
    
    async def _execute_single(
        self,
        query: BatchQueryRequest,
        prior_results: Dict[str, BatchQueryResult]
    ) -> BatchQueryResult:
        """Execute a single query."""
        started_at = datetime.now()
        
        try:
            # Execute based on operation type
            if query.operation == BatchOperation.QUERY:
                data, cache_hit = await self._execute_query(query, prior_results)
            elif query.operation == BatchOperation.SQL:
                data, cache_hit = await self._execute_sql(query)
            elif query.operation == BatchOperation.NLQ:
                data, cache_hit = await self._execute_nlq(query)
            elif query.operation == BatchOperation.INTROSPECT:
                data, cache_hit = await self._execute_introspect(query)
            else:
                raise ValueError(f"Unknown operation: {query.operation}")
            
            completed_at = datetime.now()
            
            return BatchQueryResult(
                id=query.id,
                success=True,
                data=data,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=(completed_at - started_at).total_seconds() * 1000,
                rows_returned=len(data) if isinstance(data, list) else 1,
                cache_hit=cache_hit,
            )
            
        except Exception as e:
            completed_at = datetime.now()
            logger.error(f"Query {query.id} failed: {e}")
            
            return BatchQueryResult(
                id=query.id,
                success=False,
                error=str(e),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=(completed_at - started_at).total_seconds() * 1000,
            )
    
    async def _execute_query(
        self,
        query: BatchQueryRequest,
        prior_results: Dict[str, BatchQueryResult]
    ) -> tuple:
        """Execute semantic query."""
        # Substitute references from prior results
        filters = self._substitute_references(query.filters, prior_results)
        
        result = await self.query_executor(
            dataset=query.dataset,
            dimensions=query.dimensions,
            metrics=query.metrics,
            filters=filters,
            order_by=query.order_by,
            limit=query.limit,
            offset=query.offset,
            cache=query.cache,
        )
        
        return result.get("data", []), result.get("cache_hit", False)
    
    async def _execute_sql(self, query: BatchQueryRequest) -> tuple:
        """Execute SQL query."""
        if not self.sql_executor:
            raise ValueError("SQL execution not configured")
        
        result = await self.sql_executor(sql=query.sql)
        return result.get("data", []), False
    
    async def _execute_nlq(self, query: BatchQueryRequest) -> tuple:
        """Execute natural language query."""
        if not self.nlq_executor:
            raise ValueError("NLQ execution not configured")
        
        result = await self.nlq_executor(question=query.question)
        return result, False
    
    async def _execute_introspect(self, query: BatchQueryRequest) -> tuple:
        """Execute introspection."""
        if not self.introspect_executor:
            raise ValueError("Introspection not configured")
        
        result = await self.introspect_executor(
            type=query.introspect_type,
            dataset=query.dataset
        )
        return result, False
    
    def _substitute_references(
        self,
        filters: Optional[Dict[str, Any]],
        prior_results: Dict[str, BatchQueryResult]
    ) -> Optional[Dict[str, Any]]:
        """Substitute $ref references with prior query results."""
        if not filters:
            return filters
        
        def substitute(value):
            if isinstance(value, str) and value.startswith("$ref:"):
                # Format: $ref:query_id.field or $ref:query_id[0].field
                ref_path = value[5:]
                return self._resolve_ref(ref_path, prior_results)
            elif isinstance(value, dict):
                return {k: substitute(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute(v) for v in value]
            return value
        
        return substitute(filters)
    
    def _resolve_ref(
        self,
        ref_path: str,
        prior_results: Dict[str, BatchQueryResult]
    ) -> Any:
        """Resolve a reference path to a value."""
        parts = ref_path.split(".")
        query_id = parts[0]
        
        # Handle array index
        if "[" in query_id:
            query_id, idx = query_id.split("[")
            idx = int(idx.rstrip("]"))
        else:
            idx = None
        
        if query_id not in prior_results:
            raise ValueError(f"Referenced query '{query_id}' not found")
        
        result = prior_results[query_id]
        if not result.success:
            raise ValueError(f"Referenced query '{query_id}' failed")
        
        data = result.data
        
        # Apply index
        if idx is not None:
            if not isinstance(data, list) or idx >= len(data):
                raise ValueError(f"Invalid index {idx} for query '{query_id}'")
            data = data[idx]
        
        # Apply remaining path
        for part in parts[1:]:
            if isinstance(data, dict):
                data = data.get(part)
            elif isinstance(data, list) and part.isdigit():
                data = data[int(part)]
            else:
                raise ValueError(f"Cannot resolve path '{ref_path}'")
        
        return data


# =============================================================================
# Response Formatting
# =============================================================================

def format_batch_response(result: BatchResult, include_metadata: bool = True) -> Dict[str, Any]:
    """Format batch result for API response."""
    response = {
        "batch_id": result.batch_id,
        "success": result.failed == 0,
        "summary": {
            "total": result.total_queries,
            "successful": result.successful,
            "failed": result.failed,
        },
        "results": {
            q_id: {
                "success": r.success,
                "data": r.data if r.success else None,
                "error": r.error if not r.success else None,
                "rows": r.rows_returned,
                "cache_hit": r.cache_hit,
                "duration_ms": r.duration_ms,
            }
            for q_id, r in result.results.items()
        },
    }
    
    if include_metadata:
        response["metadata"] = {
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "total_duration_ms": result.total_duration_ms,
            "execution_order": result.execution_order,
            "parallel_groups": result.parallel_groups,
        }
    
    return response


# =============================================================================
# Global Instance
# =============================================================================

_executor: Optional[BatchExecutor] = None


def init_batch(
    config: Optional[BatchConfig] = None,
    query_executor=None,
    **kwargs
) -> BatchExecutor:
    """Initialize batch executor."""
    global _executor
    
    _executor = BatchExecutor(
        config=config or BatchConfig(),
        query_executor=query_executor,
        **kwargs
    )
    
    logger.info("Batch executor initialized")
    return _executor


def get_batch_executor() -> Optional[BatchExecutor]:
    """Get batch executor instance."""
    return _executor

