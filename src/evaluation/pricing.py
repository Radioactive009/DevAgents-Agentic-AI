"""
Model Pricing Catalog and Token Cost Calculator.

Catalogs token pricing rates for Groq and Google Gemini models and provides
accurate dollar cost calculation for prompt and completion token usage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ModelPricing:
    """Pricing rates per million tokens and per single token."""
    model: str
    provider: str
    input_cost_per_million: float
    output_cost_per_million: float

    @property
    def input_cost_per_token(self) -> float:
        """Cost in USD per prompt token."""
        return self.input_cost_per_million / 1_000_000.0

    @property
    def output_cost_per_token(self) -> float:
        """Cost in USD per completion token."""
        return self.output_cost_per_million / 1_000_000.0


# Pricing catalog: rates in USD per 1,000,000 tokens
MODEL_PRICING_CATALOG: Dict[str, ModelPricing] = {
    # Groq Models
    "groq/qwen/qwen3.8-27b": ModelPricing(
        model="groq/qwen/qwen3.8-27b",
        provider="groq",
        input_cost_per_million=0.80,   # $0.00000080 / token
        output_cost_per_million=4.00,  # $0.00000400 / token
    ),
    "groq/qwen-2.5-32b": ModelPricing(
        model="groq/qwen-2.5-32b",
        provider="groq",
        input_cost_per_million=0.79,   # $0.00000079 / token
        output_cost_per_million=0.79,  # $0.00000079 / token
    ),
    "qwen-2.5-32b": ModelPricing(
        model="groq/qwen-2.5-32b",
        provider="groq",
        input_cost_per_million=0.79,   # $0.00000079 / token
        output_cost_per_million=0.79,  # $0.00000079 / token
    ),
    "groq/llama-3.3-70b-versatile": ModelPricing(
        model="groq/llama-3.3-70b-versatile",
        provider="groq",
        input_cost_per_million=0.59,   # $0.00000059 / token
        output_cost_per_million=0.79,  # $0.00000079 / token
    ),
    "groq/llama-3.1-8b-instant": ModelPricing(
        model="groq/llama-3.1-8b-instant",
        provider="groq",
        input_cost_per_million=0.05,   # $0.00000005 / token
        output_cost_per_million=0.08,  # $0.00000008 / token
    ),
    # Google Gemini Models
    "gemini/gemini-1.5-flash": ModelPricing(
        model="gemini/gemini-1.5-flash",
        provider="google",
        input_cost_per_million=0.075,  # $0.000000075 / token
        output_cost_per_million=0.30,  # $0.00000030 / token
    ),
    "gemini/gemini-1.5-pro": ModelPricing(
        model="gemini/gemini-1.5-pro",
        provider="google",
        input_cost_per_million=1.25,   # $0.00000125 / token
        output_cost_per_million=5.00,  # $0.00000500 / token
    ),
    "gemini/gemini-2.0-flash": ModelPricing(
        model="gemini/gemini-2.0-flash",
        provider="google",
        input_cost_per_million=0.10,   # $0.00000010 / token
        output_cost_per_million=0.40,  # $0.00000040 / token
    ),
}

# Aliases mapping variant/short names to canonical catalog keys
MODEL_ALIASES: Dict[str, str] = {
    # Groq Qwen
    "groq/qwen/qwen3.8-27b": "groq/qwen/qwen3.8-27b",
    "qwen/qwen3.8-27b": "groq/qwen/qwen3.8-27b",
    "qwen3.8-27b": "groq/qwen/qwen3.8-27b",
    "qwen-27b": "groq/qwen/qwen3.8-27b",
    "groq/qwen-27b": "groq/qwen/qwen3.8-27b",
    # Groq Qwen 2.5 32B
    "groq/qwen-2.5-32b": "groq/qwen-2.5-32b",
    "qwen-2.5-32b": "groq/qwen-2.5-32b",
    "qwen/qwen-2.5-32b": "groq/qwen-2.5-32b",
    "groq/qwen-2.5": "groq/qwen-2.5-32b",
    "qwen-2.5": "groq/qwen-2.5-32b",
    "groq/qwen2.5-32b": "groq/qwen-2.5-32b",
    "qwen2.5-32b": "groq/qwen-2.5-32b",
    # Groq LLaMA 3.3 70B
    "groq/llama-3.3-70b-versatile": "groq/llama-3.3-70b-versatile",
    "llama-3.3-70b-versatile": "groq/llama-3.3-70b-versatile",
    "groq/llama-3.3-70b": "groq/llama-3.3-70b-versatile",
    "llama-3.3-70b": "groq/llama-3.3-70b-versatile",
    "llama-3.3": "groq/llama-3.3-70b-versatile",
    # Groq LLaMA 3.1 8B
    "groq/llama-3.1-8b-instant": "groq/llama-3.1-8b-instant",
    "llama-3.1-8b-instant": "groq/llama-3.1-8b-instant",
    "groq/llama-3.1-8b": "groq/llama-3.1-8b-instant",
    "llama-3.1-8b": "groq/llama-3.1-8b-instant",
    "llama-3.1": "groq/llama-3.1-8b-instant",
    # Gemini 1.5 Flash
    "gemini/gemini-1.5-flash": "gemini/gemini-1.5-flash",
    "gemini-1.5-flash": "gemini/gemini-1.5-flash",
    "models/gemini-1.5-flash": "gemini/gemini-1.5-flash",
    # Gemini 1.5 Pro
    "gemini/gemini-1.5-pro": "gemini/gemini-1.5-pro",
    "gemini-1.5-pro": "gemini/gemini-1.5-pro",
    "models/gemini-1.5-pro": "gemini/gemini-1.5-pro",
    # Gemini 2.0 Flash
    "gemini/gemini-2.0-flash": "gemini/gemini-2.0-flash",
    "gemini-2.0-flash": "gemini/gemini-2.0-flash",
    "gemini-2.0": "gemini/gemini-2.0-flash",
    "models/gemini-2.0-flash": "gemini/gemini-2.0-flash",
}


def normalize_model_name(model_name: str) -> str:
    """
    Normalizes a model name or alias to its canonical catalog identifier.

    Args:
        model_name: The name or alias of the model (case-insensitive, whitespace-stripped).

    Returns:
        The canonical catalog identifier string.

    Raises:
        ValueError: If the model name is unknown/unsupported.
    """
    if not model_name or not isinstance(model_name, str):
        raise ValueError(f"Model name must be a non-empty string, got: {model_name!r}")

    cleaned = model_name.strip().lower()

    # Exact match in aliases
    if cleaned in MODEL_ALIASES:
        return MODEL_ALIASES[cleaned]

    # Prefix/suffix checks if not found directly
    for alias, canonical in MODEL_ALIASES.items():
        if cleaned == alias.lower() or cleaned.endswith("/" + alias.lower()):
            return canonical

    supported = ", ".join(sorted(MODEL_PRICING_CATALOG.keys()))
    raise ValueError(f"Unsupported model: '{model_name}'. Supported models: {supported}")


# Canonical models benchmarked by default in performance suites
CANONICAL_BENCHMARK_MODELS: List[str] = [
    "gemini/gemini-1.5-flash",
    "gemini/gemini-1.5-pro",
    "gemini/gemini-2.0-flash",
    "groq/llama-3.1-8b-instant",
    "groq/llama-3.3-70b-versatile",
    "groq/qwen/qwen3.8-27b",
]


def get_supported_models(canonical_only: bool = True) -> List[str]:
    """
    Returns a sorted list of all canonical supported model names.

    Args:
        canonical_only: If True, returns the 6 canonical benchmark suite models.
                        If False, returns all keys in MODEL_PRICING_CATALOG.
    """
    if canonical_only:
        return sorted(CANONICAL_BENCHMARK_MODELS)
    return sorted(MODEL_PRICING_CATALOG.keys())


def get_model_pricing(model_name: str) -> ModelPricing:
    """
    Retrieves the ModelPricing record for the specified model name or alias.

    Args:
        model_name: The model name or alias.

    Returns:
        ModelPricing instance.

    Raises:
        ValueError: If the model is not supported.
    """
    canonical = normalize_model_name(model_name)
    return MODEL_PRICING_CATALOG[canonical]


def calculate_token_cost(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    Calculates the dollar cost for prompt and completion token counts on a target model.

    Args:
        model_name: Model identifier or alias.
        prompt_tokens: Number of prompt / input tokens (non-negative integer).
        completion_tokens: Number of completion / output tokens (non-negative integer).

    Returns:
        Calculated total cost in USD rounded to 8 decimal places.

    Raises:
        ValueError: If token counts are negative or invalid, or model is unsupported.
    """
    if not isinstance(prompt_tokens, int) or prompt_tokens < 0:
        raise ValueError(
            f"prompt_tokens must be a non-negative integer, got {prompt_tokens!r}"
        )
    if not isinstance(completion_tokens, int) or completion_tokens < 0:
        raise ValueError(
            f"completion_tokens must be a non-negative integer, got {completion_tokens!r}"
        )

    pricing = get_model_pricing(model_name)
    cost = (
        (prompt_tokens * pricing.input_cost_per_million)
        + (completion_tokens * pricing.output_cost_per_million)
    ) / 1_000_000.0

    return round(cost, 8)
