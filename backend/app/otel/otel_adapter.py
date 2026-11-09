"""Framework detection and OpenTelemetry semantic attribute extraction adapter."""

import json
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.otel.otel_models import OTELSpan, OTELTrace
from app.otel.otel_parser import parse_timestamp_to_seconds


class DetectedFramework(StrEnum):
    """Auto-detected AI agent orchestrator framework."""

    LANGGRAPH = "LANGGRAPH"
    CREWAI = "CREWAI"
    AUTOGEN = "AUTOGEN"
    OPENAI_AGENTS = "OPENAI_AGENTS"
    LLAMAINDEX = "LLAMAINDEX"
    GENERIC_OTEL = "GENERIC_OTEL"


class FrameworkDetector:
    """Detects agent framework origin from OTEL resource attributes and span patterns."""

    @classmethod
    def detect(cls, trace: OTELTrace) -> DetectedFramework:
        """Inspect trace resource attributes, span names, and metadata to classify framework."""
        res_attrs = trace.resource.attributes if trace.resource else {}

        # 1. Check explicit framework tags in resource attributes
        combined_res_text = " ".join(str(v).lower() for v in res_attrs.values())
        if "langgraph" in combined_res_text or "langchain" in combined_res_text:
            return DetectedFramework.LANGGRAPH
        if "crewai" in combined_res_text or "crew" in combined_res_text:
            return DetectedFramework.CREWAI
        if "autogen" in combined_res_text:
            return DetectedFramework.AUTOGEN
        if "llama_index" in combined_res_text or "llamaindex" in combined_res_text:
            return DetectedFramework.LLAMAINDEX
        if "openai" in combined_res_text and (
            "agent" in combined_res_text or "assistants" in combined_res_text
        ):
            return DetectedFramework.OPENAI_AGENTS

        # 2. Inspect span names, attributes, and instrumentation conventions
        for span in trace.spans:
            s_name = span.name.lower()
            s_attrs = span.attributes or {}
            attr_keys = {k.lower() for k in s_attrs}
            attr_vals = " ".join(str(v).lower() for v in s_attrs.values())

            # LangGraph patterns
            if (
                s_name.startswith("langgraph")
                or "langgraph.node" in attr_keys
                or "langgraph.step" in attr_keys
                or "runnable" in s_name
                or any("langgraph" in k for k in attr_keys)
            ):
                return DetectedFramework.LANGGRAPH

            # CrewAI patterns
            if (
                s_name.startswith("crewai")
                or "crewai.agent" in attr_keys
                or "crewai.task" in attr_keys
                or "crew" in s_name
                or "crew_name" in attr_keys
            ):
                return DetectedFramework.CREWAI

            # AutoGen patterns
            if (
                s_name.startswith("autogen")
                or "autogen.agent" in attr_keys
                or "sender" in attr_keys
                and "recipient" in attr_keys
                or "conversable_agent" in attr_vals
            ):
                return DetectedFramework.AUTOGEN

            # LlamaIndex patterns
            if (
                s_name.startswith("llamaindex")
                or "llama_index" in s_name
                or any(k.startswith("llama_index.") for k in attr_keys)
                or "query_engine" in s_name
                or "retriever" in s_name
            ):
                return DetectedFramework.LLAMAINDEX

            # OpenAI Agents / Assistants patterns
            if (
                "openai.agent" in attr_keys
                or "openai.assistant_id" in attr_keys
                or "thread.run" in s_name
                or "assistant.run" in s_name
                or "openai.run_id" in attr_keys
            ):
                return DetectedFramework.OPENAI_AGENTS

        return DetectedFramework.GENERIC_OTEL


def extract_model_name(span: OTELSpan, default: str = "gpt-4o") -> str:
    """Extract LLM model identifier from span attributes."""
    attrs = span.attributes or {}
    candidates = [
        attrs.get("llm.model"),
        attrs.get("gen_ai.request.model"),
        attrs.get("gen_ai.response.model"),
        attrs.get("model_name"),
        attrs.get("model"),
        attrs.get("openinference.model.name"),
    ]
    for c in candidates:
        if c and isinstance(c, str) and c.strip():
            return c.strip()
    return default


def extract_input_state(span: OTELSpan) -> dict[str, Any]:
    """Extract prompt or input state dictionary from span attributes."""
    attrs = span.attributes or {}
    candidates = [
        attrs.get("gen_ai.prompt"),
        attrs.get("gen_ai.content.prompt"),
        attrs.get("llm.prompts"),
        attrs.get("prompt"),
        attrs.get("input"),
        attrs.get("inputs"),
        attrs.get("input.value"),
        attrs.get("query"),
        attrs.get("user_query"),
    ]
    for c in candidates:
        if c is not None:
            if isinstance(c, dict):
                return c
            if isinstance(c, str):
                try:
                    parsed = json.loads(c)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass
                return {"prompt": c}
            if isinstance(c, list):
                return {"prompts": c}
    return {"raw_input": span.name}


def extract_output_state(span: OTELSpan) -> dict[str, Any]:
    """Extract response or completion output state dictionary from span attributes."""
    attrs = span.attributes or {}
    candidates = [
        attrs.get("gen_ai.response"),
        attrs.get("gen_ai.content.completion"),
        attrs.get("llm.completions"),
        attrs.get("output"),
        attrs.get("response"),
        attrs.get("result"),
        attrs.get("output.value"),
    ]
    for c in candidates:
        if c is not None:
            if isinstance(c, dict):
                return c
            if isinstance(c, str):
                try:
                    parsed = json.loads(c)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass
                return {"response": c}
            if isinstance(c, list):
                return {"responses": c}
    return {"raw_output": f"Step '{span.name}' completed."}


def extract_token_counts(span: OTELSpan) -> tuple[int, int]:
    """Extract prompt_tokens and completion_tokens from span attributes."""
    attrs = span.attributes or {}
    p_tokens = (
        attrs.get("gen_ai.usage.prompt_tokens")
        or attrs.get("llm.usage.prompt_tokens")
        or attrs.get("prompt_tokens")
        or attrs.get("gen_ai.prompt_tokens")
        or 0
    )
    c_tokens = (
        attrs.get("gen_ai.usage.completion_tokens")
        or attrs.get("llm.usage.completion_tokens")
        or attrs.get("completion_tokens")
        or attrs.get("gen_ai.completion_tokens")
        or 0
    )
    try:
        p_int = max(0, int(p_tokens))
    except (ValueError, TypeError):
        p_int = 0
    try:
        c_int = max(0, int(c_tokens))
    except (ValueError, TypeError):
        c_int = 0
    return p_int, c_int


def extract_cost_usd(span: OTELSpan) -> Decimal:
    """Extract USD cost from span attributes."""
    attrs = span.attributes or {}
    cost_val = (
        attrs.get("gen_ai.usage.cost")
        or attrs.get("cost")
        or attrs.get("usd_cost")
        or attrs.get("total_cost")
        or 0.0
    )
    try:
        return Decimal(str(cost_val))
    except Exception:
        return Decimal("0.0000")


def extract_span_latency_ms(span: OTELSpan) -> int:
    """Calculate span duration in milliseconds."""
    t_start = parse_timestamp_to_seconds(span.start_time)
    t_end = parse_timestamp_to_seconds(span.end_time)
    if t_start is not None and t_end is not None and t_end >= t_start:
        return max(0, int((t_end - t_start) * 1000))
    return 0
