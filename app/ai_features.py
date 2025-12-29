"""
AI-Powered Features for SetuPranali

Provides intelligent automation:
- Auto-generated descriptions: AI-powered metric/dimension documentation
- Anomaly detection: Automatic alerts on metric anomalies
- Query suggestions: Smart autocomplete for dimensions/metrics

Features:
- LLM integration (OpenAI, Anthropic, local models)
- Statistical anomaly detection
- Context-aware suggestions
- Learning from usage patterns
"""

import os
import re
import math
import logging
import hashlib
import statistics
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
from functools import lru_cache

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class AIProvider(str, Enum):
    """AI provider options."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    NONE = "none"


class AIConfig(BaseModel):
    """AI features configuration."""
    
    enabled: bool = Field(default=True)
    provider: AIProvider = Field(default=AIProvider.NONE)
    
    # API keys
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    
    # Model settings
    model: str = Field(default="gpt-4o-mini")
    max_tokens: int = Field(default=500)
    temperature: float = Field(default=0.3)
    
    # Feature toggles
    auto_descriptions_enabled: bool = Field(default=True)
    anomaly_detection_enabled: bool = Field(default=True)
    query_suggestions_enabled: bool = Field(default=True)
    
    # Anomaly detection
    anomaly_sensitivity: float = Field(default=2.0, description="Standard deviations for anomaly")
    anomaly_min_samples: int = Field(default=10, description="Minimum samples for detection")
    
    # Caching
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")


# =============================================================================
# Auto-Generated Descriptions
# =============================================================================

@dataclass
class DescriptionContext:
    """Context for generating descriptions."""
    
    name: str
    type: str  # dimension, metric, dataset
    data_type: Optional[str] = None
    sample_values: List[Any] = field(default_factory=list)
    sql_expression: Optional[str] = None
    aggregation: Optional[str] = None
    related_fields: List[str] = field(default_factory=list)
    existing_description: Optional[str] = None


class DescriptionGenerator:
    """Generate AI-powered descriptions for metrics and dimensions."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self._cache: Dict[str, Tuple[str, float]] = {}
    
    def generate(self, context: DescriptionContext) -> str:
        """Generate description for a field."""
        if not self.config.auto_descriptions_enabled:
            return context.existing_description or ""
        
        # Check cache
        cache_key = self._cache_key(context)
        if cache_key in self._cache:
            desc, timestamp = self._cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.config.cache_ttl:
                return desc
        
        # Generate description
        if self.config.provider == AIProvider.OPENAI:
            desc = self._generate_openai(context)
        elif self.config.provider == AIProvider.ANTHROPIC:
            desc = self._generate_anthropic(context)
        elif self.config.provider == AIProvider.LOCAL:
            desc = self._generate_local(context)
        else:
            desc = self._generate_heuristic(context)
        
        # Cache result
        self._cache[cache_key] = (desc, datetime.now().timestamp())
        
        return desc
    
    def _cache_key(self, context: DescriptionContext) -> str:
        """Generate cache key for context."""
        key_parts = [context.name, context.type, context.data_type or ""]
        if context.sample_values:
            key_parts.append(str(context.sample_values[:5]))
        return hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:16]
    
    def _generate_openai(self, context: DescriptionContext) -> str:
        """Generate description using OpenAI."""
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.config.openai_api_key)
            
            prompt = self._build_prompt(context)
            
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are a data documentation expert. Generate clear, concise descriptions for data fields. Be specific and business-focused."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return self._generate_heuristic(context)
    
    def _generate_anthropic(self, context: DescriptionContext) -> str:
        """Generate description using Anthropic Claude."""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
            
            prompt = self._build_prompt(context)
            
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=self.config.max_tokens,
                messages=[
                    {"role": "user", "content": f"You are a data documentation expert. Generate a clear, concise description for this data field:\n\n{prompt}"}
                ]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return self._generate_heuristic(context)
    
    def _generate_local(self, context: DescriptionContext) -> str:
        """Generate description using local model."""
        # Placeholder for local LLM integration (Ollama, etc.)
        return self._generate_heuristic(context)
    
    def _generate_heuristic(self, context: DescriptionContext) -> str:
        """Generate description using heuristics (no AI)."""
        name = context.name
        type_str = context.type
        
        # Clean name
        clean_name = name.replace("_", " ").replace("-", " ").title()
        
        # Detect patterns in name
        patterns = {
            r"(id|_id)$": "Unique identifier for",
            r"^(total|sum)_": "Total sum of",
            r"^(avg|average)_": "Average value of",
            r"^(count|cnt)_": "Count of",
            r"^(max|maximum)_": "Maximum value of",
            r"^(min|minimum)_": "Minimum value of",
            r"_at$": "Timestamp when",
            r"_date$": "Date of",
            r"_amount$": "Monetary amount for",
            r"_rate$": "Rate or percentage of",
            r"_ratio$": "Ratio of",
            r"_percent$": "Percentage of",
        }
        
        for pattern, prefix in patterns.items():
            if re.search(pattern, name, re.IGNORECASE):
                base_name = re.sub(pattern, "", name, flags=re.IGNORECASE)
                clean_base = base_name.replace("_", " ").strip()
                return f"{prefix} {clean_base}."
        
        # Type-specific descriptions
        if type_str == "metric":
            if context.aggregation:
                return f"{context.aggregation.upper()} of {clean_name.lower()}."
            return f"Calculated metric representing {clean_name.lower()}."
        elif type_str == "dimension":
            if context.data_type == "date" or "date" in name.lower():
                return f"Date dimension for {clean_name.lower()} analysis."
            elif context.data_type == "string" or any(x in name.lower() for x in ["name", "category", "type", "status"]):
                return f"Categorical dimension for grouping by {clean_name.lower()}."
            return f"Dimension representing {clean_name.lower()}."
        else:
            return f"{clean_name} - auto-generated description."
    
    def _build_prompt(self, context: DescriptionContext) -> str:
        """Build prompt for AI model."""
        parts = [
            f"Field name: {context.name}",
            f"Type: {context.type}",
        ]
        
        if context.data_type:
            parts.append(f"Data type: {context.data_type}")
        
        if context.aggregation:
            parts.append(f"Aggregation: {context.aggregation}")
        
        if context.sql_expression:
            parts.append(f"SQL: {context.sql_expression}")
        
        if context.sample_values:
            samples = ", ".join(str(v) for v in context.sample_values[:5])
            parts.append(f"Sample values: {samples}")
        
        if context.related_fields:
            parts.append(f"Related fields: {', '.join(context.related_fields)}")
        
        parts.append("\nGenerate a 1-2 sentence business-focused description for this field.")
        
        return "\n".join(parts)
    
    def generate_dataset_description(
        self,
        name: str,
        dimensions: List[str],
        metrics: List[str],
        sample_data: Optional[List[Dict]] = None
    ) -> str:
        """Generate description for a dataset."""
        context = DescriptionContext(
            name=name,
            type="dataset",
            related_fields=dimensions + metrics,
            sample_values=sample_data[:3] if sample_data else []
        )
        
        if self.config.provider == AIProvider.NONE:
            return f"Dataset containing {', '.join(metrics[:3])} metrics with dimensions like {', '.join(dimensions[:3])}."
        
        return self.generate(context)


# =============================================================================
# Anomaly Detection
# =============================================================================

class AnomalyType(str, Enum):
    """Types of anomalies."""
    SPIKE = "spike"
    DROP = "drop"
    TREND_CHANGE = "trend_change"
    MISSING_DATA = "missing_data"
    OUTLIER = "outlier"


@dataclass
class Anomaly:
    """Detected anomaly."""
    
    metric: str
    type: AnomalyType
    timestamp: datetime
    value: float
    expected_value: float
    deviation: float  # Standard deviations from mean
    severity: str  # low, medium, high, critical
    description: str
    
    # Context
    dimension_values: Dict[str, Any] = field(default_factory=dict)
    historical_values: List[float] = field(default_factory=list)


@dataclass
class AnomalyAlert:
    """Alert for detected anomaly."""
    
    id: str
    anomaly: Anomaly
    created_at: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class AnomalyDetector:
    """Detect anomalies in metric values."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self._history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self._alerts: List[AnomalyAlert] = []
    
    def add_observation(
        self,
        metric: str,
        value: float,
        timestamp: Optional[datetime] = None,
        dimensions: Optional[Dict[str, Any]] = None
    ) -> Optional[Anomaly]:
        """Add observation and check for anomalies."""
        if not self.config.anomaly_detection_enabled:
            return None
        
        timestamp = timestamp or datetime.now()
        key = self._make_key(metric, dimensions)
        
        # Add to history
        self._history[key].append((timestamp, value))
        
        # Keep only last 1000 observations
        if len(self._history[key]) > 1000:
            self._history[key] = self._history[key][-1000:]
        
        # Check for anomaly
        return self._detect_anomaly(metric, value, timestamp, dimensions)
    
    def _make_key(self, metric: str, dimensions: Optional[Dict[str, Any]]) -> str:
        """Create unique key for metric + dimensions."""
        if not dimensions:
            return metric
        
        dim_str = "|".join(f"{k}={v}" for k, v in sorted(dimensions.items()))
        return f"{metric}|{dim_str}"
    
    def _detect_anomaly(
        self,
        metric: str,
        value: float,
        timestamp: datetime,
        dimensions: Optional[Dict[str, Any]]
    ) -> Optional[Anomaly]:
        """Detect if current value is anomalous."""
        key = self._make_key(metric, dimensions)
        history = self._history[key]
        
        # Need minimum samples
        if len(history) < self.config.anomaly_min_samples:
            return None
        
        # Get historical values (exclude current)
        historical_values = [v for _, v in history[:-1]]
        
        # Calculate statistics
        mean = statistics.mean(historical_values)
        stdev = statistics.stdev(historical_values) if len(historical_values) > 1 else 0
        
        if stdev == 0:
            return None
        
        # Calculate deviation
        deviation = abs(value - mean) / stdev
        
        # Check if anomalous
        if deviation < self.config.anomaly_sensitivity:
            return None
        
        # Determine type
        if value > mean:
            anomaly_type = AnomalyType.SPIKE
        else:
            anomaly_type = AnomalyType.DROP
        
        # Determine severity
        if deviation >= 4:
            severity = "critical"
        elif deviation >= 3:
            severity = "high"
        elif deviation >= 2.5:
            severity = "medium"
        else:
            severity = "low"
        
        # Generate description
        direction = "above" if value > mean else "below"
        description = (
            f"{metric} is {deviation:.1f} standard deviations {direction} normal. "
            f"Current: {value:.2f}, Expected: {mean:.2f}"
        )
        
        anomaly = Anomaly(
            metric=metric,
            type=anomaly_type,
            timestamp=timestamp,
            value=value,
            expected_value=mean,
            deviation=deviation,
            severity=severity,
            description=description,
            dimension_values=dimensions or {},
            historical_values=historical_values[-20:]
        )
        
        # Create alert
        alert = AnomalyAlert(
            id=hashlib.sha256(f"{key}{timestamp}".encode()).hexdigest()[:16],
            anomaly=anomaly,
            created_at=datetime.now()
        )
        self._alerts.append(alert)
        
        # Keep only last 1000 alerts
        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-1000:]
        
        return anomaly
    
    def get_alerts(
        self,
        metric: Optional[str] = None,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AnomalyAlert]:
        """Get anomaly alerts with optional filtering."""
        alerts = self._alerts
        
        if metric:
            alerts = [a for a in alerts if a.anomaly.metric == metric]
        
        if severity:
            alerts = [a for a in alerts if a.anomaly.severity == severity]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        if since:
            alerts = [a for a in alerts if a.created_at >= since]
        
        return alerts[-limit:]
    
    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = user
                alert.acknowledged_at = datetime.now()
                return True
        return False
    
    def detect_trend_change(
        self,
        metric: str,
        values: List[float],
        window: int = 7
    ) -> Optional[Anomaly]:
        """Detect significant trend changes."""
        if len(values) < window * 2:
            return None
        
        # Calculate moving averages
        recent_avg = statistics.mean(values[-window:])
        previous_avg = statistics.mean(values[-window*2:-window])
        
        # Calculate change
        if previous_avg == 0:
            return None
        
        change_pct = (recent_avg - previous_avg) / abs(previous_avg) * 100
        
        if abs(change_pct) < 20:  # Less than 20% change
            return None
        
        return Anomaly(
            metric=metric,
            type=AnomalyType.TREND_CHANGE,
            timestamp=datetime.now(),
            value=recent_avg,
            expected_value=previous_avg,
            deviation=change_pct / 10,  # Normalize
            severity="high" if abs(change_pct) > 50 else "medium",
            description=f"{metric} trend changed by {change_pct:.1f}% compared to previous {window} periods.",
            historical_values=values
        )


# =============================================================================
# Query Suggestions
# =============================================================================

@dataclass
class QuerySuggestion:
    """A query suggestion."""
    
    type: str  # dimension, metric, filter, query
    value: str
    display: str
    description: Optional[str] = None
    score: float = 1.0  # Relevance score
    metadata: Dict[str, Any] = field(default_factory=dict)


class QuerySuggestionEngine:
    """Smart autocomplete for dimensions and metrics."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self._usage_stats: Dict[str, int] = defaultdict(int)
        self._co_occurrence: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._recent_queries: List[Dict[str, Any]] = []
    
    def record_query(self, query: Dict[str, Any]) -> None:
        """Record a query for learning."""
        if not self.config.query_suggestions_enabled:
            return
        
        # Update usage stats
        for dim in query.get("dimensions", []):
            self._usage_stats[f"dim:{dim}"] += 1
        
        for met in query.get("metrics", []):
            self._usage_stats[f"met:{met}"] += 1
        
        # Update co-occurrence
        all_fields = query.get("dimensions", []) + query.get("metrics", [])
        for i, field1 in enumerate(all_fields):
            for field2 in all_fields[i+1:]:
                self._co_occurrence[field1][field2] += 1
                self._co_occurrence[field2][field1] += 1
        
        # Store recent query
        self._recent_queries.append({
            **query,
            "timestamp": datetime.now()
        })
        
        # Keep only last 1000 queries
        if len(self._recent_queries) > 1000:
            self._recent_queries = self._recent_queries[-1000:]
    
    def suggest_dimensions(
        self,
        dataset: str,
        available_dimensions: List[Dict[str, Any]],
        current_dimensions: List[str] = None,
        current_metrics: List[str] = None,
        query_prefix: str = "",
        limit: int = 10
    ) -> List[QuerySuggestion]:
        """Suggest dimensions based on context."""
        current_dimensions = current_dimensions or []
        current_metrics = current_metrics or []
        
        suggestions = []
        
        for dim in available_dimensions:
            name = dim.get("name", "")
            
            # Skip already selected
            if name in current_dimensions:
                continue
            
            # Filter by prefix
            if query_prefix and not name.lower().startswith(query_prefix.lower()):
                continue
            
            # Calculate score
            score = self._calculate_score(
                f"dim:{name}",
                current_dimensions + current_metrics
            )
            
            suggestions.append(QuerySuggestion(
                type="dimension",
                value=name,
                display=dim.get("label", name),
                description=dim.get("description"),
                score=score,
                metadata={"data_type": dim.get("type")}
            ))
        
        # Sort by score
        suggestions.sort(key=lambda x: x.score, reverse=True)
        
        return suggestions[:limit]
    
    def suggest_metrics(
        self,
        dataset: str,
        available_metrics: List[Dict[str, Any]],
        current_dimensions: List[str] = None,
        current_metrics: List[str] = None,
        query_prefix: str = "",
        limit: int = 10
    ) -> List[QuerySuggestion]:
        """Suggest metrics based on context."""
        current_dimensions = current_dimensions or []
        current_metrics = current_metrics or []
        
        suggestions = []
        
        for met in available_metrics:
            name = met.get("name", "")
            
            # Skip already selected
            if name in current_metrics:
                continue
            
            # Filter by prefix
            if query_prefix and not name.lower().startswith(query_prefix.lower()):
                continue
            
            # Calculate score
            score = self._calculate_score(
                f"met:{name}",
                current_dimensions + current_metrics
            )
            
            suggestions.append(QuerySuggestion(
                type="metric",
                value=name,
                display=met.get("label", name),
                description=met.get("description"),
                score=score,
                metadata={"aggregation": met.get("aggregation")}
            ))
        
        # Sort by score
        suggestions.sort(key=lambda x: x.score, reverse=True)
        
        return suggestions[:limit]
    
    def suggest_filters(
        self,
        dataset: str,
        dimension: str,
        sample_values: List[Any],
        query_prefix: str = "",
        limit: int = 10
    ) -> List[QuerySuggestion]:
        """Suggest filter values for a dimension."""
        suggestions = []
        
        for value in sample_values:
            str_value = str(value)
            
            # Filter by prefix
            if query_prefix and not str_value.lower().startswith(query_prefix.lower()):
                continue
            
            suggestions.append(QuerySuggestion(
                type="filter",
                value=str_value,
                display=str_value,
                score=1.0
            ))
        
        return suggestions[:limit]
    
    def suggest_queries(
        self,
        dataset: str,
        available_dimensions: List[str],
        available_metrics: List[str],
        limit: int = 5
    ) -> List[QuerySuggestion]:
        """Suggest complete queries based on patterns."""
        suggestions = []
        
        # Most popular combinations from recent queries
        dataset_queries = [
            q for q in self._recent_queries
            if q.get("dataset") == dataset
        ]
        
        # Count query patterns
        patterns: Dict[str, int] = defaultdict(int)
        for query in dataset_queries:
            dims = tuple(sorted(query.get("dimensions", [])))
            mets = tuple(sorted(query.get("metrics", [])))
            pattern = f"{dims}|{mets}"
            patterns[pattern] += 1
        
        # Generate suggestions from patterns
        for pattern, count in sorted(patterns.items(), key=lambda x: -x[1])[:limit]:
            dims_str, mets_str = pattern.split("|")
            dims = eval(dims_str) if dims_str != "()" else []
            mets = eval(mets_str) if mets_str != "()" else []
            
            if not mets:
                continue
            
            display = f"{', '.join(mets)} by {', '.join(dims)}" if dims else f"{', '.join(mets)}"
            
            suggestions.append(QuerySuggestion(
                type="query",
                value=pattern,
                display=display,
                description=f"Used {count} times",
                score=count / max(len(dataset_queries), 1),
                metadata={
                    "dimensions": list(dims),
                    "metrics": list(mets)
                }
            ))
        
        # Add common patterns if no history
        if not suggestions:
            # Suggest first metric with common dimensions
            if available_metrics and available_dimensions:
                suggestions.append(QuerySuggestion(
                    type="query",
                    value="default",
                    display=f"{available_metrics[0]} by {available_dimensions[0]}",
                    description="Default query",
                    score=0.5,
                    metadata={
                        "dimensions": [available_dimensions[0]],
                        "metrics": [available_metrics[0]]
                    }
                ))
        
        return suggestions
    
    def _calculate_score(self, field: str, context: List[str]) -> float:
        """Calculate relevance score for a field."""
        # Base score from usage
        usage_score = min(self._usage_stats[field] / 100, 1.0)
        
        # Co-occurrence score
        co_score = 0.0
        if context:
            for ctx_field in context:
                co_count = self._co_occurrence.get(field.split(":")[-1], {}).get(ctx_field, 0)
                co_score += co_count
            co_score = min(co_score / (len(context) * 10), 1.0)
        
        # Combined score
        return 0.4 * usage_score + 0.6 * co_score + 0.1  # Base score of 0.1


# =============================================================================
# AI Service
# =============================================================================

class AIService:
    """Unified AI service for SetuPranali."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.description_generator = DescriptionGenerator(config)
        self.anomaly_detector = AnomalyDetector(config)
        self.suggestion_engine = QuerySuggestionEngine(config)
    
    def generate_description(self, context: DescriptionContext) -> str:
        """Generate description for a field."""
        return self.description_generator.generate(context)
    
    def detect_anomaly(
        self,
        metric: str,
        value: float,
        timestamp: Optional[datetime] = None,
        dimensions: Optional[Dict[str, Any]] = None
    ) -> Optional[Anomaly]:
        """Check for anomalies in metric value."""
        return self.anomaly_detector.add_observation(metric, value, timestamp, dimensions)
    
    def get_suggestions(
        self,
        dataset: str,
        available_dimensions: List[Dict[str, Any]],
        available_metrics: List[Dict[str, Any]],
        current_dimensions: List[str] = None,
        current_metrics: List[str] = None,
        query_prefix: str = "",
        suggestion_type: str = "all"
    ) -> Dict[str, List[QuerySuggestion]]:
        """Get query suggestions."""
        result = {}
        
        if suggestion_type in ("all", "dimensions"):
            result["dimensions"] = self.suggestion_engine.suggest_dimensions(
                dataset, available_dimensions, current_dimensions, current_metrics, query_prefix
            )
        
        if suggestion_type in ("all", "metrics"):
            result["metrics"] = self.suggestion_engine.suggest_metrics(
                dataset, available_metrics, current_dimensions, current_metrics, query_prefix
            )
        
        if suggestion_type in ("all", "queries"):
            result["queries"] = self.suggestion_engine.suggest_queries(
                dataset,
                [d.get("name") for d in available_dimensions],
                [m.get("name") for m in available_metrics]
            )
        
        return result
    
    def record_query(self, query: Dict[str, Any]) -> None:
        """Record query for learning."""
        self.suggestion_engine.record_query(query)
    
    def get_alerts(self, **kwargs) -> List[AnomalyAlert]:
        """Get anomaly alerts."""
        return self.anomaly_detector.get_alerts(**kwargs)


# =============================================================================
# Global Instance
# =============================================================================

_ai_service: Optional[AIService] = None


def init_ai(config: Optional[AIConfig] = None) -> AIService:
    """Initialize AI service."""
    global _ai_service
    
    config = config or load_config_from_env()
    _ai_service = AIService(config)
    
    logger.info(f"AI service initialized (provider: {config.provider})")
    return _ai_service


def get_ai_service() -> Optional[AIService]:
    """Get AI service instance."""
    return _ai_service


def load_config_from_env() -> AIConfig:
    """Load AI configuration from environment."""
    provider = os.getenv("AI_PROVIDER", "none")
    
    return AIConfig(
        enabled=os.getenv("AI_ENABLED", "true").lower() == "true",
        provider=AIProvider(provider),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        model=os.getenv("AI_MODEL", "gpt-4o-mini"),
        auto_descriptions_enabled=os.getenv("AI_AUTO_DESCRIPTIONS", "true").lower() == "true",
        anomaly_detection_enabled=os.getenv("AI_ANOMALY_DETECTION", "true").lower() == "true",
        query_suggestions_enabled=os.getenv("AI_QUERY_SUGGESTIONS", "true").lower() == "true",
        anomaly_sensitivity=float(os.getenv("AI_ANOMALY_SENSITIVITY", "2.0")),
    )

