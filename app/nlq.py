"""
SetuPranali - Natural Language Query (NLQ) Module

Translates natural language questions into semantic queries using AI.
Supports OpenAI, Anthropic, and local LLMs.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NLQConfig:
    """Configuration for Natural Language Query engine."""
    provider: str = "openai"  # openai, anthropic, local
    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 500


@dataclass
class NLQResult:
    """Result of natural language query translation."""
    original_question: str
    translated_query: Dict[str, Any]
    explanation: str
    confidence: float
    suggestions: List[str]


def get_system_prompt(dataset_schema: Dict[str, Any]) -> str:
    """Generate system prompt with dataset schema."""
    dimensions = dataset_schema.get("dimensions", [])
    metrics = dataset_schema.get("metrics", [])
    
    dim_list = "\n".join([
        f"  - {d['name']}: {d.get('description', d.get('label', d['name']))} (type: {d.get('type', 'string')})"
        for d in dimensions
    ])
    
    metric_list = "\n".join([
        f"  - {m['name']}: {m.get('description', m.get('label', m['name']))} (aggregation: {m.get('aggregation', 'sum')})"
        for m in metrics
    ])
    
    return f"""You are a semantic query translator for a BI analytics system called SetuPranali.

Your job is to translate natural language questions into structured semantic queries.

Available Dataset: {dataset_schema.get('name', dataset_schema.get('id', 'unknown'))}
Description: {dataset_schema.get('description', 'No description')}

Available Dimensions (groupable fields):
{dim_list}

Available Metrics (aggregatable measures):
{metric_list}

Output a JSON object with this structure:
{{
    "dimensions": ["dimension_name1", "dimension_name2"],
    "metrics": ["metric_name1"],
    "filters": [
        {{"field": "field_name", "operator": "eq|ne|gt|gte|lt|lte|in|like", "value": "value"}}
    ],
    "orderBy": [
        {{"field": "field_name", "direction": "asc|desc"}}
    ],
    "limit": 100,
    "explanation": "Brief explanation of what this query does",
    "confidence": 0.95
}}

Rules:
1. Only use dimensions and metrics that exist in the schema above
2. Use appropriate filter operators
3. If the question is ambiguous, make reasonable assumptions and note them in explanation
4. Set confidence between 0 and 1 based on how well you understood the question
5. Always return valid JSON

If you cannot translate the question, return:
{{
    "error": "explanation of why",
    "suggestions": ["alternative question 1", "alternative question 2"]
}}
"""


def translate_with_openai(
    question: str,
    dataset_schema: Dict[str, Any],
    config: NLQConfig
) -> NLQResult:
    """Translate question using OpenAI."""
    try:
        import openai
    except ImportError:
        raise ImportError("openai package required. Install with: pip install openai")
    
    client = openai.OpenAI(
        api_key=config.api_key or os.getenv("OPENAI_API_KEY"),
        base_url=config.base_url
    )
    
    response = client.chat.completions.create(
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        messages=[
            {"role": "system", "content": get_system_prompt(dataset_schema)},
            {"role": "user", "content": question}
        ],
        response_format={"type": "json_object"}
    )
    
    result_text = response.choices[0].message.content
    result = json.loads(result_text)
    
    if "error" in result:
        return NLQResult(
            original_question=question,
            translated_query={},
            explanation=result["error"],
            confidence=0.0,
            suggestions=result.get("suggestions", [])
        )
    
    return NLQResult(
        original_question=question,
        translated_query={
            "dimensions": result.get("dimensions", []),
            "metrics": result.get("metrics", []),
            "filters": result.get("filters", []),
            "orderBy": result.get("orderBy", []),
            "limit": result.get("limit", 100)
        },
        explanation=result.get("explanation", ""),
        confidence=result.get("confidence", 0.8),
        suggestions=[]
    )


def translate_with_anthropic(
    question: str,
    dataset_schema: Dict[str, Any],
    config: NLQConfig
) -> NLQResult:
    """Translate question using Anthropic Claude."""
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package required. Install with: pip install anthropic")
    
    client = anthropic.Anthropic(
        api_key=config.api_key or os.getenv("ANTHROPIC_API_KEY")
    )
    
    response = client.messages.create(
        model=config.model or "claude-3-haiku-20240307",
        max_tokens=config.max_tokens,
        system=get_system_prompt(dataset_schema),
        messages=[
            {"role": "user", "content": question}
        ]
    )
    
    result_text = response.content[0].text
    
    # Extract JSON from response
    import re
    json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
    if json_match:
        result = json.loads(json_match.group())
    else:
        raise ValueError("Could not parse JSON from response")
    
    if "error" in result:
        return NLQResult(
            original_question=question,
            translated_query={},
            explanation=result["error"],
            confidence=0.0,
            suggestions=result.get("suggestions", [])
        )
    
    return NLQResult(
        original_question=question,
        translated_query={
            "dimensions": result.get("dimensions", []),
            "metrics": result.get("metrics", []),
            "filters": result.get("filters", []),
            "orderBy": result.get("orderBy", []),
            "limit": result.get("limit", 100)
        },
        explanation=result.get("explanation", ""),
        confidence=result.get("confidence", 0.8),
        suggestions=[]
    )


def translate_question(
    question: str,
    dataset_schema: Dict[str, Any],
    config: Optional[NLQConfig] = None
) -> NLQResult:
    """
    Translate a natural language question into a semantic query.
    
    Args:
        question: Natural language question (e.g., "What are the top 10 cities by revenue?")
        dataset_schema: Dataset schema with dimensions and metrics
        config: NLQ configuration (provider, model, API key)
        
    Returns:
        NLQResult with translated query
    """
    config = config or NLQConfig()
    
    if config.provider == "openai":
        return translate_with_openai(question, dataset_schema, config)
    elif config.provider == "anthropic":
        return translate_with_anthropic(question, dataset_schema, config)
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")


# =============================================================================
# Simple rule-based fallback (no AI required)
# =============================================================================

def translate_simple(
    question: str,
    dataset_schema: Dict[str, Any]
) -> NLQResult:
    """
    Simple rule-based translation without AI.
    Handles common patterns like:
    - "top N by metric"
    - "total/sum/average of metric"
    - "group by dimension"
    """
    question_lower = question.lower()
    
    dimensions = [d["name"] for d in dataset_schema.get("dimensions", [])]
    metrics = [m["name"] for m in dataset_schema.get("metrics", [])]
    
    result_dims = []
    result_metrics = []
    result_order = []
    result_limit = 100
    
    # Check for "top N" pattern
    import re
    top_match = re.search(r'top\s+(\d+)', question_lower)
    if top_match:
        result_limit = int(top_match.group(1))
    
    # Find mentioned dimensions
    for dim in dimensions:
        if dim.lower() in question_lower or dim.replace("_", " ").lower() in question_lower:
            result_dims.append(dim)
    
    # Find mentioned metrics
    for metric in metrics:
        if metric.lower() in question_lower or metric.replace("_", " ").lower() in question_lower:
            result_metrics.append(metric)
    
    # Check for ordering keywords
    if any(word in question_lower for word in ["top", "highest", "most", "best"]):
        if result_metrics:
            result_order = [{"field": result_metrics[0], "direction": "desc"}]
    elif any(word in question_lower for word in ["bottom", "lowest", "least", "worst"]):
        if result_metrics:
            result_order = [{"field": result_metrics[0], "direction": "asc"}]
    
    # Default: if no specific dimensions/metrics found, use first of each
    if not result_dims and dimensions:
        result_dims = [dimensions[0]]
    if not result_metrics and metrics:
        result_metrics = [metrics[0]]
    
    confidence = 0.5 if (result_dims or result_metrics) else 0.2
    
    return NLQResult(
        original_question=question,
        translated_query={
            "dimensions": result_dims,
            "metrics": result_metrics,
            "filters": [],
            "orderBy": result_order,
            "limit": result_limit
        },
        explanation=f"Interpreted as: Show {', '.join(result_metrics)} by {', '.join(result_dims)}",
        confidence=confidence,
        suggestions=[
            f"Show me {metrics[0]} by {dimensions[0]}" if metrics and dimensions else "",
            f"What are the top 10 {dimensions[0]}s by {metrics[0]}?" if metrics and dimensions else ""
        ]
    )

