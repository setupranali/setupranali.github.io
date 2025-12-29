"""
Row-Level Security (RLS) for SetuPranali

This module implements automatic tenant isolation at the query level.
RLS filters are injected transparently - no BI tool changes required.

HOW IT WORKS:
-------------
1. User authenticates with API key → TenantContext (tenant, role)
2. Dataset has RLS config specifying the tenant column
3. Before query execution, an RLS filter is injected:
   WHERE <rls_column> = '<tenant>'
4. Filter is merged with existing filters using AND
5. Query executes with automatic tenant isolation

SECURITY GUARANTEES:
--------------------
- RLS is applied server-side, not client-side
- BI tools cannot bypass RLS (they don't control filters)
- Only authenticated users can query (401/403 otherwise)
- Admin bypass is optional and controlled per-dataset

CATALOG SCHEMA:
---------------
datasets:
  - id: orders
    rls:
      enabled: true
      column: tenant_id      # Column containing tenant identifier
      mode: equals           # equals | in_list (future)
      allowAdminBypass: true # Admin role sees all data

USAGE:
------
    from app.rls import build_rls_filter, apply_rls_to_filters
    
    # Build RLS filter for this tenant
    rls_filter = build_rls_filter(dataset, tenant_context)
    
    # Merge with existing filters
    merged_filters = apply_rls_to_filters(existing_filters, rls_filter)
"""

from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class RLSConfig:
    """
    Row-Level Security configuration for a dataset.
    
    Parsed from catalog.yaml rls section.
    """
    enabled: bool = False
    column: Optional[str] = None
    mode: str = "equals"  # equals | in_list (future)
    allow_admin_bypass: bool = False


@dataclass
class RLSResult:
    """
    Result of RLS evaluation.
    
    Contains the filter to inject and metadata for auditing.
    """
    applied: bool = False
    filter: Optional[Dict] = None
    column: Optional[str] = None
    bypassed: bool = False
    reason: Optional[str] = None


def get_rls_config(dataset: Dict) -> RLSConfig:
    """
    Extract RLS configuration from dataset definition.
    
    Args:
        dataset: Dataset definition from catalog
    
    Returns:
        RLSConfig with parsed settings
    """
    rls = dataset.get("rls", {})
    
    return RLSConfig(
        enabled=rls.get("enabled", False),
        column=rls.get("column"),
        mode=rls.get("mode", "equals"),
        allow_admin_bypass=rls.get("allowAdminBypass", False)
    )


def validate_rls_config(dataset: Dict, rls_config: RLSConfig) -> Tuple[bool, Optional[str]]:
    """
    Validate that RLS configuration is correct for the dataset.
    
    Checks:
    - If RLS enabled, column must be specified
    - Column must exist in dataset fields
    
    Returns:
        (is_valid, error_message)
    """
    if not rls_config.enabled:
        return True, None
    
    # Check column is specified
    if not rls_config.column:
        return False, "RLS is enabled but no column is specified"
    
    # Check column exists in fields
    field_names = {f["name"] for f in dataset.get("fields", [])}
    
    if rls_config.column not in field_names:
        return False, f"RLS column '{rls_config.column}' not found in dataset fields"
    
    return True, None


def build_rls_filter(
    dataset: Dict,
    tenant: str,
    role: str
) -> RLSResult:
    """
    Build an RLS filter for the given dataset and tenant.
    
    This is the CORE RLS logic:
    1. Check if RLS is enabled
    2. Check if admin bypass applies
    3. Build filter condition
    
    Args:
        dataset: Dataset definition from catalog
        tenant: Authenticated tenant identifier
        role: Authenticated user role
    
    Returns:
        RLSResult with filter to inject and audit info
    """
    rls_config = get_rls_config(dataset)
    
    # RLS not enabled - no filter needed
    if not rls_config.enabled:
        return RLSResult(
            applied=False,
            reason="RLS not enabled for dataset"
        )
    
    # Validate RLS config
    is_valid, error = validate_rls_config(dataset, rls_config)
    if not is_valid:
        raise ValueError(error)
    
    # Check admin bypass
    if rls_config.allow_admin_bypass and role == "admin":
        return RLSResult(
            applied=False,
            bypassed=True,
            column=rls_config.column,
            reason="Admin bypass - user has admin role"
        )
    
    # Build the RLS filter
    # For mode="equals": column = tenant
    if rls_config.mode == "equals":
        rls_filter = {
            "field": rls_config.column,
            "op": "eq",
            "value": tenant
        }
    elif rls_config.mode == "in_list":
        # Future: Support tenant having access to multiple tenant IDs
        # For now, treat as equals
        rls_filter = {
            "field": rls_config.column,
            "op": "eq",
            "value": tenant
        }
    else:
        raise ValueError(f"Unsupported RLS mode: {rls_config.mode}")
    
    return RLSResult(
        applied=True,
        filter=rls_filter,
        column=rls_config.column,
        reason=f"RLS filter: {rls_config.column} = {tenant}"
    )


def apply_rls_to_filters(
    existing_filters: Optional[Dict],
    rls_result: RLSResult
) -> Optional[Dict]:
    """
    Merge RLS filter with existing filters using AND.
    
    The resulting filter is:
        (existing_filters) AND (rls_filter)
    
    This ensures RLS cannot be bypassed by user-provided filters.
    
    Args:
        existing_filters: Filters from the query request (may be None)
        rls_result: RLS evaluation result
    
    Returns:
        Merged filter dict, or None if no filters
    """
    # No RLS filter to apply
    if not rls_result.applied or not rls_result.filter:
        return existing_filters
    
    rls_filter = rls_result.filter
    
    # No existing filters - just return RLS filter
    if not existing_filters:
        return rls_filter
    
    # Merge with AND
    return {
        "and": [existing_filters, rls_filter]
    }


def get_rls_stats(rls_result: RLSResult, tenant: str, role: str) -> Dict[str, Any]:
    """
    Get RLS statistics for audit logging.
    
    Added to QueryResponse.stats for transparency and debugging.
    """
    return {
        "tenant": tenant,
        "role": role,
        "rlsApplied": rls_result.applied,
        "rlsBypassed": rls_result.bypassed,
        "rlsColumn": rls_result.column,
        "rlsReason": rls_result.reason
    }

