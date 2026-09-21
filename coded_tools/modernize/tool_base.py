# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Base CodedTool compatibility wrapper.
Inherits from neuro_san.interfaces.coded_tool.CodedTool when neuro-san is installed,
or falls back to an equivalent base class when running offline/standalone.
"""

from typing import Any, Dict

try:
    from neuro_san.interfaces.coded_tool import CodedTool
except ImportError:
    class CodedTool:
        """Fallback base class when neuro_san host package is not in the environment."""

        def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
            raise NotImplementedError

        async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
            return self.invoke(args, sly_data)
