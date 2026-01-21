"""
Analytics API Endpoints

Query analytics and observability endpoints.
"""

from fastapi import APIRouter, Depends
from typing import Optional
from app.core.security import TenantContext, require_api_key
from app.infrastructure.observability.analytics import get_analytics

router = APIRouter(prefix="/v1/analytics", tags=["Analytics"])


@router.get("")
def get_analytics_data(
    hours: int = 24,
    ctx: TenantContext = Depends(require_api_key)
):
    """
    Get query analytics data for the dashboard.
    
    Returns:
    - Query volume over time (hourly)
    - Query latency percentiles
    - Recent queries
    - Overall statistics
    """
    from datetime import datetime as dt
    
    analytics = get_analytics()
    if not analytics:
        # Return empty data if analytics not initialized
        return {
            "query_volume": [],
            "latency": [],
            "recent_queries": [],
            "stats": {
                "total_queries": 0,
                "total_errors": 0,
                "error_rate": 0,
                "avg_duration_ms": 0,
                "cache_hit_rate": 0
            }
        }
    
    # Get hourly stats
    hourly_stats = analytics.get_hourly_stats(hours=hours)
    
    # Format query volume data for chart
    # Ensure data is sorted chronologically (oldest to newest) for the chart
    query_volume = []
    for stat in hourly_stats:
        hour_str = stat["hour"]
        # Parse hour string (format: YYYY-MM-DD-HH)
        try:
            hour_dt = dt.strptime(hour_str, "%Y-%m-%d-%H")
            time_label = hour_dt.strftime("%H:00")
        except:
            time_label = hour_str.split("-")[-1] + ":00"
        
        query_volume.append({
            "time": time_label,
            "queries": stat["count"],
            "errors": stat.get("errors", 0)
        })
    
    # Ensure data is in chronological order (oldest to newest)
    # The chart expects this order to display correctly
    # Sort by parsing the time string to ensure correct order across day boundaries
    def sort_key(item):
        time_str = item["time"]
        hour = int(time_str.split(":")[0])
        return hour
    
    # Since we're already returning in chronological order from get_hourly_stats,
    # we shouldn't need to sort, but let's ensure it's correct
    # query_volume is already in the correct order from get_hourly_stats
    
    # Get overall stats
    stats = analytics.get_stats()
    
    # Get recent queries
    recent_queries = analytics.get_recent_queries(limit=5)
    
    # Calculate latency percentiles from hourly stats
    latency_data = []
    for stat in hourly_stats:
        hour_str = stat["hour"]
        try:
            hour_dt = dt.strptime(hour_str, "%Y-%m-%d-%H")
            time_label = hour_dt.strftime("%H:00")
        except:
            time_label = hour_str.split("-")[-1] + ":00"
        
        # Use average duration for that hour as approximation for percentiles
        avg_dur = stat.get("avg_duration_ms", 0)
        if avg_dur > 0:
            latency_data.append({
                "time": time_label,
                "p50": int(avg_dur * 0.8),
                "p95": int(avg_dur * 1.5),
                "p99": int(avg_dur * 2.0)
            })
        else:
            latency_data.append({
                "time": time_label,
                "p50": 0,
                "p95": 0,
                "p99": 0
            })
    
    return {
        "query_volume": query_volume,
        "latency": latency_data if latency_data else [
            {"time": "00:00", "p50": 0, "p95": 0, "p99": 0}
        ],
        "recent_queries": recent_queries,
        "stats": {
            "total_queries": stats.get("total_queries", 0),
            "total_errors": stats.get("total_errors", 0),
            "error_rate": stats.get("error_rate", 0),
            "avg_duration_ms": int(stats.get("avg_duration_ms", 0)),
            "cache_hit_rate": stats.get("cache_hit_rate", 0)
        }
    }


@router.get("/recent-queries")
def get_recent_queries(
    limit: int = 10,
    dataset: Optional[str] = None,
    tenant_id: Optional[str] = None,
    ctx: TenantContext = Depends(require_api_key)
):
    """
    Get recent query records.
    
    Returns the most recent query executions with details.
    """
    from app.infrastructure.storage.state_storage import get_state_storage
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    analytics = get_analytics()
    if not analytics:
        return {"items": [], "total": 0}
    
    # Limit max results
    limit = min(limit, 100)
    
    # Get recent queries
    if analytics._use_storage and analytics._storage:
        # Get from DuckDB with filters
        try:
            storage = get_state_storage()
            
            # Use tenant_id from context if not provided and user is not admin
            filter_tenant = tenant_id
            if not filter_tenant and ctx.role != "admin":
                filter_tenant = ctx.tenant
            
            records = storage.get_query_records(
                dataset=dataset,
                tenant_id=filter_tenant,
                limit=limit
            )
            
            # Format records
            formatted = []
            for record in records:
                # Parse JSON fields
                dimensions = record.get("dimensions", [])
                metrics = record.get("metrics", [])
                if isinstance(dimensions, str):
                    dimensions = json.loads(dimensions)
                if isinstance(metrics, str):
                    metrics = json.loads(metrics)
                
                formatted.append({
                    "query_id": record.get("query_id"),
                    "dataset": record.get("dataset", "unknown"),
                    "tenant_id": record.get("tenant_id"),
                    "dimensions": dimensions if isinstance(dimensions, list) else [],
                    "metrics": metrics if isinstance(metrics, list) else [],
                    "duration_ms": record.get("duration_ms", 0),
                    "duration": f"{int(record.get('duration_ms', 0))}ms",
                    "rows_returned": record.get("rows_returned", 0),
                    "cache_hit": record.get("cache_hit", False),
                    "success": record.get("success", True),
                    "status": "error" if not record.get("success", True) else ("warning" if record.get("duration_ms", 0) > 1000 else "success"),
                    "error_code": record.get("error_code"),
                    "error_message": record.get("error_message"),
                    "timestamp": record.get("timestamp").isoformat() if record.get("timestamp") else None,
                    "source_ip": record.get("source_ip"),
                })
            
            return {
                "items": formatted,
                "total": len(formatted),
                "limit": limit
            }
        except Exception as e:
            logger.error(f"Failed to get recent queries from DuckDB: {e}", exc_info=True)
            return {"items": [], "total": 0, "error": str(e)}
    
    # Fallback to observability method
    recent_queries = analytics.get_recent_queries(limit=limit)
    return {
        "items": recent_queries,
        "total": len(recent_queries),
        "limit": limit
    }
