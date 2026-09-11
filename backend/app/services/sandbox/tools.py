"""
SIH26117 — Sandboxed Deterministic Engineering Tool Implementations & Whitelist
Defines the explicit whitelist of approved engineering tools with zero eval/exec.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

try:
    from app.services.sandbox.base import ToolNotFoundError, ToolValidationError
    from app.services.sandbox.models import (
        CorrosionRateInput,
        CorrosionRateOutput,
        MinimumWallThicknessInput,
        MinimumWallThicknessOutput,
    )
    from app.services.sandbox.validators import validate_tool_payload
except ImportError:
    from backend.app.services.sandbox.base import ToolNotFoundError, ToolValidationError
    from backend.app.services.sandbox.models import (
        CorrosionRateInput,
        CorrosionRateOutput,
        MinimumWallThicknessInput,
        MinimumWallThicknessOutput,
    )
    from backend.app.services.sandbox.validators import validate_tool_payload

logger = logging.getLogger(__name__)


class DeterministicTool(ABC):
    """
    Abstract interface for all approved deterministic tools running in the sandbox.
    """

    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]

    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute deterministic calculation on validated payload."""
        pass


class MinimumWallThicknessCheck(DeterministicTool):
    """
    Evaluates measured pipe wall thickness against minimum allowable retirement thickness.
    Calculates safety margin and classifies integrity status.
    """

    name = "minimum_wall_thickness_check"
    description = "Deterministic wall thickness verification against retirement limits."
    input_schema = MinimumWallThicknessInput
    output_schema = MinimumWallThicknessOutput

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Validate input schema
        params: MinimumWallThicknessInput = validate_tool_payload(
            self.name, payload, self.input_schema
        )  # type: ignore

        margin = round(params.measured_thickness_mm - params.minimum_required_mm, 3)
        is_acceptable = margin >= 0.0

        if margin >= 0.5:
            status = "PASS"
        elif margin >= 0.0:
            status = "MONITOR"
        else:
            status = "RETIRE"

        output = MinimumWallThicknessOutput(
            component_id=params.component_id,
            measured_thickness_mm=params.measured_thickness_mm,
            minimum_required_mm=params.minimum_required_mm,
            margin_mm=margin,
            status=status,
            is_acceptable=is_acceptable,
        )
        return output.model_dump()


class CorrosionRateCalculation(DeterministicTool):
    """
    Deterministic corrosion-rate and remaining-life calculation using the configured
    engineering formula:
        corrosion_rate = (previous_thickness - current_thickness) / elapsed_time
        remaining_life = (current_thickness - minimum_required) / corrosion_rate
    """

    name = "corrosion_rate_calc"
    description = "Deterministic corrosion rate and equipment remaining life calculation."
    input_schema = CorrosionRateInput
    output_schema = CorrosionRateOutput

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Validate input schema
        params: CorrosionRateInput = validate_tool_payload(
            self.name, payload, self.input_schema
        )  # type: ignore

        metal_loss = round(params.previous_thickness_mm - params.current_thickness_mm, 4)
        corrosion_rate = round(metal_loss / params.elapsed_time_years, 4)

        remaining_life = None
        if params.minimum_required_mm is not None:
            if corrosion_rate > 0:
                remaining_thickness = params.current_thickness_mm - params.minimum_required_mm
                remaining_life = round(remaining_thickness / corrosion_rate, 2)
                remaining_life_status = "CALCULATED"
            elif corrosion_rate == 0:
                remaining_life = None
                remaining_life_status = "STABLE"
            else:
                remaining_life = None
                remaining_life_status = "NEGATIVE_LOSS"
        else:
            remaining_life_status = "NOT_APPLICABLE"

        output = CorrosionRateOutput(
            component_id=params.component_id,
            previous_thickness_mm=params.previous_thickness_mm,
            current_thickness_mm=params.current_thickness_mm,
            elapsed_time_years=params.elapsed_time_years,
            metal_loss_mm=metal_loss,
            corrosion_rate_mm_per_year=corrosion_rate,
            remaining_life_years=remaining_life,
            remaining_life_status=remaining_life_status,
        )
        return output.model_dump()


class ToolWhitelistRegistry:
    """
    Maintains the explicit whitelist of approved sandbox tools.
    Rejects any unregistered tool name with fail-closed security.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, DeterministicTool] = {}
        # Register standard deterministic tools
        self.register(MinimumWallThicknessCheck())
        self.register(CorrosionRateCalculation())

    def register(self, tool: DeterministicTool) -> None:
        """Register an approved deterministic tool."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> DeterministicTool:
        """
        Retrieve approved tool by name.
        Raises ToolNotFoundError if tool is not whitelisted.
        """
        tool = self._tools.get(name)
        if not tool:
            raise ToolNotFoundError(
                f"Tool '{name}' is not in the approved sandbox whitelist. Allowed: {list(self._tools.keys())}"
            )
        return tool

    def is_whitelisted(self, name: str) -> bool:
        """Check if tool name is registered."""
        return name in self._tools

    def list_tools(self) -> List[str]:
        """Return list of whitelisted tool names."""
        return sorted(list(self._tools.keys()))
