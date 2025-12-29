"""
Fine-Grained Permissions for SetuPranali

Provides comprehensive access control:
- Dataset-level access control
- Column-level (dimension/metric) access control
- Row-level security (RLS)
- Role-based access control (RBAC)
- Policy-based access control
- API key scoping
- Tenant isolation

Features:
- Declarative permission definitions
- Inheritance and cascading
- Deny-by-default security model
- Audit logging
- Performance-optimized evaluation
"""

import os
import re
import logging
import hashlib
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field
from functools import lru_cache

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Permission Types
# =============================================================================

class PermissionAction(str, Enum):
    """Permission actions."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    QUERY = "query"
    EXPORT = "export"
    SHARE = "share"


class PermissionEffect(str, Enum):
    """Permission effect."""
    ALLOW = "allow"
    DENY = "deny"


class ResourceType(str, Enum):
    """Resource types for permissions."""
    DATASET = "dataset"
    DIMENSION = "dimension"
    METRIC = "metric"
    COLUMN = "column"
    SOURCE = "source"
    API_KEY = "api_key"


# =============================================================================
# Permission Models
# =============================================================================

class ColumnPermission(BaseModel):
    """Column-level permission."""
    
    name: str = Field(..., description="Column/dimension/metric name")
    effect: PermissionEffect = Field(default=PermissionEffect.ALLOW)
    actions: List[PermissionAction] = Field(default=[PermissionAction.READ])
    
    # Masking
    mask: Optional[str] = Field(None, description="Mask pattern (e.g., '***' or 'HASH')")
    mask_function: Optional[str] = Field(None, description="Custom masking function")
    
    # Conditions
    condition: Optional[str] = Field(None, description="SQL condition for access")


class DatasetPermission(BaseModel):
    """Dataset-level permission."""
    
    dataset: str = Field(..., description="Dataset ID or pattern (supports wildcards)")
    effect: PermissionEffect = Field(default=PermissionEffect.ALLOW)
    actions: List[PermissionAction] = Field(default=[PermissionAction.QUERY])
    
    # Column restrictions
    allowed_dimensions: Optional[List[str]] = Field(None, description="Allowed dimensions (whitelist)")
    denied_dimensions: Optional[List[str]] = Field(None, description="Denied dimensions (blacklist)")
    allowed_metrics: Optional[List[str]] = Field(None, description="Allowed metrics (whitelist)")
    denied_metrics: Optional[List[str]] = Field(None, description="Denied metrics (blacklist)")
    
    # Column-level permissions
    columns: List[ColumnPermission] = Field(default=[], description="Column-level permissions")
    
    # Row-level security
    rls_filter: Optional[str] = Field(None, description="RLS SQL filter expression")
    rls_field: Optional[str] = Field(None, description="RLS field for tenant isolation")
    
    # Query limits
    max_rows: Optional[int] = Field(None, description="Maximum rows to return")
    max_dimensions: Optional[int] = Field(None, description="Maximum dimensions per query")
    max_metrics: Optional[int] = Field(None, description="Maximum metrics per query")
    
    # Time restrictions
    allowed_time_range: Optional[int] = Field(None, description="Max days of historical data")


class Role(BaseModel):
    """Role definition with permissions."""
    
    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    
    # Permissions
    datasets: List[DatasetPermission] = Field(default=[], description="Dataset permissions")
    
    # Global permissions
    can_create_api_keys: bool = Field(default=False)
    can_manage_sources: bool = Field(default=False)
    can_view_audit_logs: bool = Field(default=False)
    
    # Inheritance
    inherits: List[str] = Field(default=[], description="Roles to inherit from")
    
    # Priority (higher = evaluated first)
    priority: int = Field(default=0)


class Policy(BaseModel):
    """Access policy definition."""
    
    id: str = Field(..., description="Policy ID")
    name: str = Field(..., description="Policy name")
    description: Optional[str] = Field(None)
    enabled: bool = Field(default=True)
    
    # Matching
    principals: List[str] = Field(default=["*"], description="Users/roles/groups this applies to")
    resources: List[str] = Field(default=["*"], description="Resources this applies to")
    actions: List[PermissionAction] = Field(default=[PermissionAction.QUERY])
    
    # Effect
    effect: PermissionEffect = Field(default=PermissionEffect.ALLOW)
    
    # Conditions
    conditions: Dict[str, Any] = Field(default={}, description="Additional conditions")
    
    # Priority
    priority: int = Field(default=0)


class PermissionConfig(BaseModel):
    """Permission configuration."""
    
    enabled: bool = Field(default=True, description="Enable fine-grained permissions")
    default_effect: PermissionEffect = Field(default=PermissionEffect.DENY, description="Default effect")
    
    # Definitions
    roles: List[Role] = Field(default=[], description="Role definitions")
    policies: List[Policy] = Field(default=[], description="Policy definitions")
    
    # Role assignments
    api_key_roles: Dict[str, List[str]] = Field(default={}, description="API key -> roles mapping")
    user_roles: Dict[str, List[str]] = Field(default={}, description="User -> roles mapping")
    tenant_roles: Dict[str, List[str]] = Field(default={}, description="Tenant -> roles mapping")
    
    # Options
    audit_enabled: bool = Field(default=True)
    cache_ttl: int = Field(default=300, description="Permission cache TTL (seconds)")


# =============================================================================
# Permission Context
# =============================================================================

@dataclass
class PermissionContext:
    """Context for permission evaluation."""
    
    # Principal
    api_key: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    
    # Request
    action: PermissionAction = PermissionAction.QUERY
    resource_type: ResourceType = ResourceType.DATASET
    resource_id: Optional[str] = None
    
    # Additional context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Attributes from OAuth/SAML
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionResult:
    """Result of permission evaluation."""
    
    allowed: bool
    effect: PermissionEffect
    reason: str
    
    # Applied restrictions
    allowed_dimensions: Optional[Set[str]] = None
    denied_dimensions: Optional[Set[str]] = None
    allowed_metrics: Optional[Set[str]] = None
    denied_metrics: Optional[Set[str]] = None
    column_masks: Dict[str, str] = field(default_factory=dict)
    rls_filters: List[str] = field(default_factory=list)
    
    # Limits
    max_rows: Optional[int] = None
    max_time_range_days: Optional[int] = None
    
    # Audit
    matched_policies: List[str] = field(default_factory=list)
    matched_roles: List[str] = field(default_factory=list)


# =============================================================================
# Permission Evaluator
# =============================================================================

class PermissionEvaluator:
    """Evaluates permissions for requests."""
    
    def __init__(self, config: PermissionConfig):
        self.config = config
        self._roles_cache: Dict[str, Role] = {}
        self._policies_cache: Dict[str, Policy] = {}
        
        # Index roles and policies
        for role in config.roles:
            self._roles_cache[role.name] = role
        
        for policy in config.policies:
            self._policies_cache[policy.id] = policy
        
        logger.info(f"Permission evaluator initialized with {len(self._roles_cache)} roles, {len(self._policies_cache)} policies")
    
    def _resolve_roles(self, role_names: List[str], resolved: Optional[Set[str]] = None) -> List[Role]:
        """Resolve roles including inherited roles."""
        if resolved is None:
            resolved = set()
        
        roles = []
        for name in role_names:
            if name in resolved:
                continue  # Avoid circular inheritance
            
            role = self._roles_cache.get(name)
            if role:
                resolved.add(name)
                roles.append(role)
                
                # Resolve inherited roles
                if role.inherits:
                    inherited = self._resolve_roles(role.inherits, resolved)
                    roles.extend(inherited)
        
        # Sort by priority (higher first)
        return sorted(roles, key=lambda r: r.priority, reverse=True)
    
    def _get_roles_for_context(self, ctx: PermissionContext) -> List[Role]:
        """Get all applicable roles for a context."""
        role_names = set(ctx.roles)
        
        # Add roles from API key
        if ctx.api_key and ctx.api_key in self.config.api_key_roles:
            role_names.update(self.config.api_key_roles[ctx.api_key])
        
        # Add roles from user
        if ctx.user_id and ctx.user_id in self.config.user_roles:
            role_names.update(self.config.user_roles[ctx.user_id])
        
        # Add roles from tenant
        if ctx.tenant_id and ctx.tenant_id in self.config.tenant_roles:
            role_names.update(self.config.tenant_roles[ctx.tenant_id])
        
        return self._resolve_roles(list(role_names))
    
    def _match_pattern(self, pattern: str, value: str) -> bool:
        """Match a pattern against a value (supports wildcards)."""
        if pattern == "*":
            return True
        
        # Convert glob pattern to regex
        regex = pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
        return bool(re.match(f"^{regex}$", value))
    
    def _evaluate_policies(self, ctx: PermissionContext) -> List[Tuple[Policy, PermissionEffect]]:
        """Evaluate policies for context."""
        matches = []
        
        for policy in self.config.policies:
            if not policy.enabled:
                continue
            
            # Check actions
            if ctx.action not in policy.actions and PermissionAction.ADMIN not in policy.actions:
                continue
            
            # Check principals
            principal_match = False
            for principal in policy.principals:
                if principal == "*":
                    principal_match = True
                    break
                if ctx.user_id and self._match_pattern(principal, ctx.user_id):
                    principal_match = True
                    break
                if ctx.api_key and self._match_pattern(principal, ctx.api_key):
                    principal_match = True
                    break
                if principal in ctx.roles:
                    principal_match = True
                    break
            
            if not principal_match:
                continue
            
            # Check resources
            resource_match = False
            resource_str = f"{ctx.resource_type.value}:{ctx.resource_id}" if ctx.resource_id else "*"
            for resource in policy.resources:
                if self._match_pattern(resource, resource_str):
                    resource_match = True
                    break
                if ctx.resource_id and self._match_pattern(resource, ctx.resource_id):
                    resource_match = True
                    break
            
            if not resource_match:
                continue
            
            # Check conditions
            if policy.conditions:
                if not self._evaluate_conditions(policy.conditions, ctx):
                    continue
            
            matches.append((policy, policy.effect))
        
        # Sort by priority (higher first)
        return sorted(matches, key=lambda x: x[0].priority, reverse=True)
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], ctx: PermissionContext) -> bool:
        """Evaluate policy conditions."""
        for key, value in conditions.items():
            if key == "ip_range":
                # Check IP range
                if ctx.ip_address and not self._ip_in_range(ctx.ip_address, value):
                    return False
            
            elif key == "time_range":
                # Check time range
                hour = ctx.timestamp.hour
                start, end = value.get("start", 0), value.get("end", 24)
                if not (start <= hour < end):
                    return False
            
            elif key == "tenant_id":
                if ctx.tenant_id != value and value != "*":
                    return False
            
            elif key == "attributes":
                # Check attribute conditions
                for attr_key, attr_value in value.items():
                    if ctx.attributes.get(attr_key) != attr_value:
                        return False
        
        return True
    
    def _ip_in_range(self, ip: str, ranges: List[str]) -> bool:
        """Check if IP is in allowed ranges."""
        # Simplified IP range check
        for range_str in ranges:
            if range_str == "*":
                return True
            if "/" in range_str:
                # CIDR notation - simplified check
                network = range_str.split("/")[0]
                if ip.startswith(network.rsplit(".", 1)[0]):
                    return True
            elif ip == range_str:
                return True
        return False
    
    def evaluate_dataset_access(
        self,
        ctx: PermissionContext,
        dataset_id: str
    ) -> PermissionResult:
        """Evaluate access to a dataset."""
        ctx.resource_type = ResourceType.DATASET
        ctx.resource_id = dataset_id
        
        # Get applicable roles
        roles = self._get_roles_for_context(ctx)
        
        # Evaluate policies first
        policy_matches = self._evaluate_policies(ctx)
        
        # Check for explicit deny in policies
        for policy, effect in policy_matches:
            if effect == PermissionEffect.DENY:
                return PermissionResult(
                    allowed=False,
                    effect=PermissionEffect.DENY,
                    reason=f"Denied by policy: {policy.name}",
                    matched_policies=[policy.id]
                )
        
        # Collect permissions from roles
        allowed_dims: Set[str] = set()
        denied_dims: Set[str] = set()
        allowed_mets: Set[str] = set()
        denied_mets: Set[str] = set()
        column_masks: Dict[str, str] = {}
        rls_filters: List[str] = []
        max_rows: Optional[int] = None
        max_time_range: Optional[int] = None
        matched_roles: List[str] = []
        dataset_allowed = False
        
        for role in roles:
            for ds_perm in role.datasets:
                if not self._match_pattern(ds_perm.dataset, dataset_id):
                    continue
                
                matched_roles.append(role.name)
                
                # Check effect
                if ds_perm.effect == PermissionEffect.DENY:
                    return PermissionResult(
                        allowed=False,
                        effect=PermissionEffect.DENY,
                        reason=f"Denied by role: {role.name}",
                        matched_roles=[role.name]
                    )
                
                # Check action
                if ctx.action not in ds_perm.actions:
                    continue
                
                dataset_allowed = True
                
                # Collect dimension restrictions
                if ds_perm.allowed_dimensions:
                    if not allowed_dims:
                        allowed_dims = set(ds_perm.allowed_dimensions)
                    else:
                        allowed_dims &= set(ds_perm.allowed_dimensions)
                
                if ds_perm.denied_dimensions:
                    denied_dims.update(ds_perm.denied_dimensions)
                
                # Collect metric restrictions
                if ds_perm.allowed_metrics:
                    if not allowed_mets:
                        allowed_mets = set(ds_perm.allowed_metrics)
                    else:
                        allowed_mets &= set(ds_perm.allowed_metrics)
                
                if ds_perm.denied_metrics:
                    denied_mets.update(ds_perm.denied_metrics)
                
                # Collect column masks
                for col_perm in ds_perm.columns:
                    if col_perm.mask:
                        column_masks[col_perm.name] = col_perm.mask
                    elif col_perm.mask_function:
                        column_masks[col_perm.name] = f"FUNCTION:{col_perm.mask_function}"
                
                # Collect RLS filters
                if ds_perm.rls_filter:
                    rls_filters.append(ds_perm.rls_filter)
                
                if ds_perm.rls_field and ctx.tenant_id:
                    rls_filters.append(f"{ds_perm.rls_field} = '{ctx.tenant_id}'")
                
                # Collect limits
                if ds_perm.max_rows:
                    if max_rows is None or ds_perm.max_rows < max_rows:
                        max_rows = ds_perm.max_rows
                
                if ds_perm.allowed_time_range:
                    if max_time_range is None or ds_perm.allowed_time_range < max_time_range:
                        max_time_range = ds_perm.allowed_time_range
        
        # Check policy allows
        policy_allowed = any(effect == PermissionEffect.ALLOW for _, effect in policy_matches)
        
        if not dataset_allowed and not policy_allowed:
            # Apply default effect
            if self.config.default_effect == PermissionEffect.DENY:
                return PermissionResult(
                    allowed=False,
                    effect=PermissionEffect.DENY,
                    reason="No matching permission found (default deny)"
                )
        
        return PermissionResult(
            allowed=True,
            effect=PermissionEffect.ALLOW,
            reason="Access granted",
            allowed_dimensions=allowed_dims if allowed_dims else None,
            denied_dimensions=denied_dims if denied_dims else None,
            allowed_metrics=allowed_mets if allowed_mets else None,
            denied_metrics=denied_mets if denied_mets else None,
            column_masks=column_masks,
            rls_filters=rls_filters,
            max_rows=max_rows,
            max_time_range_days=max_time_range,
            matched_policies=[p.id for p, _ in policy_matches if _ == PermissionEffect.ALLOW],
            matched_roles=matched_roles
        )
    
    def filter_columns(
        self,
        result: PermissionResult,
        dimensions: List[str],
        metrics: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Filter dimensions and metrics based on permissions."""
        filtered_dims = dimensions.copy()
        filtered_mets = metrics.copy()
        
        # Apply whitelist
        if result.allowed_dimensions:
            filtered_dims = [d for d in filtered_dims if d in result.allowed_dimensions]
        
        if result.allowed_metrics:
            filtered_mets = [m for m in filtered_mets if m in result.allowed_metrics]
        
        # Apply blacklist
        if result.denied_dimensions:
            filtered_dims = [d for d in filtered_dims if d not in result.denied_dimensions]
        
        if result.denied_metrics:
            filtered_mets = [m for m in filtered_mets if m not in result.denied_metrics]
        
        return filtered_dims, filtered_mets
    
    def apply_column_masks(
        self,
        result: PermissionResult,
        data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply column masking to data."""
        if not result.column_masks:
            return data
        
        masked_data = []
        for row in data:
            masked_row = row.copy()
            for col, mask in result.column_masks.items():
                if col in masked_row:
                    masked_row[col] = self._apply_mask(masked_row[col], mask)
            masked_data.append(masked_row)
        
        return masked_data
    
    def _apply_mask(self, value: Any, mask: str) -> Any:
        """Apply a mask to a value."""
        if value is None:
            return None
        
        str_value = str(value)
        
        if mask == "***":
            return "***"
        elif mask == "HASH":
            return hashlib.sha256(str_value.encode()).hexdigest()[:8]
        elif mask == "PARTIAL":
            # Show first and last character
            if len(str_value) > 2:
                return f"{str_value[0]}{'*' * (len(str_value) - 2)}{str_value[-1]}"
            return "**"
        elif mask == "EMAIL":
            # Mask email
            if "@" in str_value:
                local, domain = str_value.split("@", 1)
                return f"{local[0]}***@{domain}"
            return "***"
        elif mask.startswith("FUNCTION:"):
            # Custom function - would need to be implemented
            return "***"
        else:
            return mask
    
    def build_rls_clause(self, result: PermissionResult) -> Optional[str]:
        """Build SQL WHERE clause from RLS filters."""
        if not result.rls_filters:
            return None
        
        # Combine all filters with AND
        return " AND ".join(f"({f})" for f in result.rls_filters)


# =============================================================================
# Global Instance
# =============================================================================

_permission_evaluator: Optional[PermissionEvaluator] = None


def init_permissions(config: PermissionConfig) -> PermissionEvaluator:
    """Initialize permission evaluator."""
    global _permission_evaluator
    _permission_evaluator = PermissionEvaluator(config)
    return _permission_evaluator


def get_permission_evaluator() -> Optional[PermissionEvaluator]:
    """Get permission evaluator instance."""
    return _permission_evaluator


# =============================================================================
# Pre-defined Roles
# =============================================================================

def analyst_role(datasets: List[str] = ["*"]) -> Role:
    """Create analyst role with read-only query access."""
    return Role(
        name="analyst",
        description="Read-only access to query datasets",
        datasets=[
            DatasetPermission(
                dataset=ds,
                actions=[PermissionAction.QUERY, PermissionAction.READ],
            )
            for ds in datasets
        ],
        priority=10
    )


def admin_role() -> Role:
    """Create admin role with full access."""
    return Role(
        name="admin",
        description="Full administrative access",
        datasets=[
            DatasetPermission(
                dataset="*",
                actions=[PermissionAction.QUERY, PermissionAction.READ, PermissionAction.WRITE, PermissionAction.ADMIN],
            )
        ],
        can_create_api_keys=True,
        can_manage_sources=True,
        can_view_audit_logs=True,
        priority=100
    )


def viewer_role(
    datasets: List[str],
    denied_columns: Optional[List[str]] = None
) -> Role:
    """Create viewer role with limited access."""
    return Role(
        name="viewer",
        description="Limited read access",
        datasets=[
            DatasetPermission(
                dataset=ds,
                actions=[PermissionAction.READ],
                denied_dimensions=denied_columns,
                denied_metrics=denied_columns,
                max_rows=10000,
            )
            for ds in datasets
        ],
        priority=5
    )


def tenant_role(
    tenant_id: str,
    datasets: List[str] = ["*"],
    rls_field: str = "tenant_id"
) -> Role:
    """Create tenant-isolated role."""
    return Role(
        name=f"tenant_{tenant_id}",
        description=f"Tenant-isolated access for {tenant_id}",
        datasets=[
            DatasetPermission(
                dataset=ds,
                actions=[PermissionAction.QUERY, PermissionAction.READ],
                rls_field=rls_field,
            )
            for ds in datasets
        ],
        priority=50
    )


# =============================================================================
# Configuration Helpers
# =============================================================================

def load_permissions_from_yaml(path: str) -> PermissionConfig:
    """Load permission configuration from YAML file."""
    import yaml
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    return PermissionConfig(**data.get("permissions", {}))


def load_permissions_from_env() -> PermissionConfig:
    """Load basic permission configuration from environment."""
    enabled = os.getenv("PERMISSIONS_ENABLED", "true").lower() == "true"
    default_effect = PermissionEffect(os.getenv("PERMISSIONS_DEFAULT_EFFECT", "deny"))
    
    roles = []
    
    # Create admin role if admin API key is set
    admin_key = os.getenv("ADMIN_API_KEY")
    if admin_key:
        roles.append(admin_role())
    
    api_key_roles = {}
    if admin_key:
        api_key_roles[admin_key] = ["admin"]
    
    return PermissionConfig(
        enabled=enabled,
        default_effect=default_effect,
        roles=roles,
        api_key_roles=api_key_roles,
    )

