"""
Callback-based data validation and monitoring hooks.

Enforces type checking, schema consistency, and data integrity on tool returns
and agent task outputs across both CrewAI and Google ADK.
"""

from typing import Any, Callable, Type
from pydantic import BaseModel, ValidationError


class ToolReturnValidator:
    """Validates that tool outputs conform to expected types and schema rules."""

    @staticmethod
    def validate_type(
        tool_name: str,
        result: Any,
        expected_type: Type | tuple[Type, ...],
    ) -> Any:
        """Verify that a tool's return value matches expected Python types."""
        if not isinstance(result, expected_type):
            expected_name = (
                tuple(t.__name__ for t in expected_type)
                if isinstance(expected_type, tuple)
                else expected_type.__name__
            )
            actual_name = type(result).__name__
            raise TypeError(
                f"Tool '{tool_name}' return type mismatch: "
                f"expected {expected_name}, got {actual_name}."
            )
        return result

    @staticmethod
    def validate_pydantic_schema(
        tool_name: str,
        data: dict[str, Any] | Any,
        schema_cls: Type[BaseModel],
    ) -> BaseModel:
        """Validate that a tool's returned dictionary adheres to a Pydantic schema."""
        if isinstance(data, schema_cls):
            return data
        if not isinstance(data, dict):
            raise TypeError(
                f"Tool '{tool_name}' returned non-dict data for schema {schema_cls.__name__}: {type(data)}"
            )
        try:
            return schema_cls.model_validate(data)
        except ValidationError as err:
            raise ValueError(
                f"Tool '{tool_name}' output failed schema validation for {schema_cls.__name__}: {err}"
            ) from err


class DataValidationCallback:
    """Callback hook callable during agent task completion or tool execution."""

    def __init__(
        self,
        *,
        on_success: Callable[[str, Any], None] | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ):
        self._on_success = on_success
        self._on_error = on_error
        self.validation_history: list[dict[str, Any]] = []

    def handle_tool_return(
        self,
        tool_name: str,
        raw_output: Any,
        expected_type: Type | tuple[Type, ...],
    ) -> Any:
        """Check return type, record history, and notify listener."""
        try:
            validated = ToolReturnValidator.validate_type(
                tool_name=tool_name,
                result=raw_output,
                expected_type=expected_type,
            )
            self.validation_history.append({
                "target": tool_name,
                "status": "valid",
                "type": type(raw_output).__name__,
            })
            if self._on_success:
                self._on_success(tool_name, validated)
            return validated
        except Exception as exc:
            self.validation_history.append({
                "target": tool_name,
                "status": "invalid",
                "error": str(exc),
            })
            if self._on_error:
                self._on_error(tool_name, exc)
            raise

    def crewai_task_callback(self, task_output: Any) -> None:
        """CrewAI task callback for intermediate output validation."""
        output_value = getattr(task_output, "pydantic", None) or getattr(task_output, "raw", str(task_output))
        if output_value is None:
            raise ValueError("Task produced an empty output.")
        self.validation_history.append({
            "target": "crewai_task",
            "status": "valid",
            "has_pydantic": hasattr(task_output, "pydantic") and task_output.pydantic is not None,
        })
        if self._on_success:
            self._on_success("crewai_task", output_value)

    def adk_after_tool_callback(self, tool_name: str, tool_output: Any) -> Any:
        """Google ADK tool completion callback."""
        return self.handle_tool_return(tool_name, tool_output, (dict, list, str, int, float, bool))

