"""Compatibility shims for mismatched Azure SDK preview packages."""

from dataclasses import dataclass
from typing import Any


def _make_dict_model(name: str):
    class _DictModel(dict):
        def __init__(self, values: dict[str, Any] | None = None, **kwargs: Any) -> None:
            payload: dict[str, Any] = {}
            if values:
                payload.update(values)
            payload.update(kwargs)
            super().__init__(payload)

    _DictModel.__name__ = name
    return _DictModel


def patch_azure_projects_models() -> None:
    """Alias renamed classes expected by agent-framework preview dependencies."""
    try:
        from azure.ai.projects import models
    except Exception:
        return

    alias_map = {
        "CodeInterpreterToolAuto": "CodeInterpreterContainerAuto",
        "PromptAgentDefinitionText": "PromptAgentDefinitionTextOptions",
        "ResponseTextFormatConfigurationJsonObject": "TextResponseFormatConfigurationResponseFormatJsonObject",
        "ResponseTextFormatConfigurationJsonSchema": "TextResponseFormatJsonSchema",
        "ResponseTextFormatConfigurationText": "TextResponseFormatConfigurationResponseFormatText",
    }

    for legacy_name, current_name in alias_map.items():
        if hasattr(models, legacy_name):
            continue
        if hasattr(models, current_name):
            setattr(models, legacy_name, getattr(models, current_name))

    if not hasattr(models, "AgentReference"):

        @dataclass
        class AgentReference:
            name: str
            version: str | None = None

        setattr(models, "AgentReference", AgentReference)

    if not hasattr(models, "ItemParam"):
        setattr(models, "ItemParam", _make_dict_model("ItemParam"))

    if not hasattr(models, "ResponsesAssistantMessageItemParam"):
        setattr(
            models,
            "ResponsesAssistantMessageItemParam",
            _make_dict_model("ResponsesAssistantMessageItemParam"),
        )

    if not hasattr(models, "ResponsesUserMessageItemParam"):
        setattr(
            models,
            "ResponsesUserMessageItemParam",
            _make_dict_model("ResponsesUserMessageItemParam"),
        )
