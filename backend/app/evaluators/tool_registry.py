"""Deterministic evaluator for tool registry conformance and hallucination detection."""

from app.domain.models import CanonicalTrace
from app.evaluators.base import BaseDeterministicEvaluator, EvaluationFinding, FindingSeverity


class ToolRegistryEvaluator(BaseDeterministicEvaluator):
    """Evaluates whether all tool calls reference valid, registered tools and schemas."""

    def evaluate(self, trace: CanonicalTrace) -> list[EvaluationFinding]:
        """Verify tool calls against the agent's declared tool registry."""
        findings: list[EvaluationFinding] = []

        # Map agent_id to registry
        agent_tool_registries: dict[str, dict[str, dict[str, object]]] = {}
        for agent in trace.agents:
            agent_tool_registries[str(agent.agent_id)] = {
                t.tool_name: t.parameters_schema for t in agent.tool_registry
            }

        # Fallback to union of all registries if step agent_id is unmapped
        all_registered_tools: set[str] = {
            t.tool_name for a in trace.agents for t in a.tool_registry
        }

        for step in trace.steps:
            agent_registry = agent_tool_registries.get(str(step.agent_id), {})

            for tool_call in step.tool_calls:
                tool_name = tool_call.tool_name

                # Check 1: Tool exists in registry
                is_registered = (
                    tool_name in agent_registry
                    if agent_registry
                    else tool_name in all_registered_tools
                )

                if not is_registered or tool_call.is_hallucinated:
                    findings.append(
                        EvaluationFinding(
                            severity=FindingSeverity.HIGH,
                            code="HALLUCINATED_TOOL",
                            message=(
                                f"Step {step.step_index} ({step.node_name}) invoked tool '{tool_name}', "
                                "which is not registered in the agent's tool manifest."
                            ),
                            workflow_id=trace.workflow.workflow_id,
                            affected_steps=[step.step_index],
                            metadata={
                                "tool_name": tool_name,
                                "agent_id": str(step.agent_id),
                                "node_name": step.node_name,
                                "raw_arguments": tool_call.raw_arguments,
                            },
                        )
                    )
                    continue

                # Check 2: Missing tool schema when arguments are provided
                declared_schema = agent_registry.get(tool_name)
                if not declared_schema and tool_call.raw_arguments:
                    findings.append(
                        EvaluationFinding(
                            severity=FindingSeverity.MEDIUM,
                            code="MISSING_TOOL_SCHEMA",
                            message=(
                                f"Tool '{tool_name}' was invoked with arguments in step {step.step_index}, "
                                "but has no parameters schema defined in the tool registry."
                            ),
                            workflow_id=trace.workflow.workflow_id,
                            affected_steps=[step.step_index],
                            metadata={
                                "tool_name": tool_name,
                                "raw_arguments": tool_call.raw_arguments,
                            },
                        )
                    )

        return findings
