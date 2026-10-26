"""llm -- the only place a model is allowed to touch the project.

`providers` swaps between the Meta Model API and an offline mock.
`spec_gen` turns a prompt into a schema-validated project spec.
"""
from .providers import (MetaProvider, MockProvider, Provider, ProviderError,
                         get_provider)
from .spec_gen import (SYSTEM_PROMPT, build_prompt, fallback_spec, generate_spec,
                       load_spec_schema, validate_spec)

__all__ = [
    "MetaProvider", "MockProvider", "Provider", "ProviderError", "get_provider",
    "SYSTEM_PROMPT", "build_prompt", "fallback_spec", "generate_spec",
    "load_spec_schema", "validate_spec",
]
