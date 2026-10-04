#!/usr/bin/env python3

#!/usr/bin/env python3
"""
ToolRegistry: patrón Registry (+ Decorator para el registro).

Uso:
    from .tool_registry import registry

    @registry.register
    def fetch_flight_info(date: Date, origin: str, destination: str):
        '''Fetch flight information ...'''

    registry.get_tools()         # -> list[Tool]
    registry.get_tools_schema()  # -> list[dict] listo para el LLM
    registry.execute("fetch_flight_info", date=..., origin=..., destination=...)
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Iterator,
    get_args,
    get_origin,
    get_type_hints,
)

_PRIMITIVES: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    tuple: "array",
    dict: "object",
}


def _json_type(annotation: Any) -> dict[str, Any]:
    """Convierte una anotación de tipo en un fragmento de JSON Schema."""
    if annotation is inspect.Parameter.empty or isinstance(
        annotation, str
    ):
        return {"type": "string"}
    origin = get_origin(annotation)
    if origin in (list, tuple):
        args = get_args(annotation)
        schema: dict[str, Any] = {"type": "array"}
        if args:
            schema["items"] = _json_type(args[0])
        return schema
    if origin is dict:
        return {"type": "object"}
    return {"type": _PRIMITIVES.get(annotation, "object")}


@dataclass(frozen=True)
class Tool:
    """Representa una tool registrada."""

    name: str
    description: str
    func: Callable[..., Any]
    parameters: dict[str, Any] = field(default_factory=dict)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)

    def to_schema(self) -> dict[str, Any]:
        """Formato estilo function-calling (OpenAI / Anthropic / LiteLLM)."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @classmethod
    def from_function(
        cls,
        func: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
    ) -> "Tool":
        sig = inspect.signature(func)
        try:
            hints = get_type_hints(func)
        except (
            Exception
        ):  # anotaciones no resolubles (imports faltantes, etc.)
            hints = {}

        properties: dict[str, Any] = {}
        required: list[str] = []
        for pname, param in sig.parameters.items():
            if pname in ("self", "cls"):
                continue
            properties[pname] = _json_type(
                hints.get(pname, param.annotation)
            )
            if param.default is inspect.Parameter.empty:
                required.append(pname)

        return cls(
            name=name or func.__name__,
            description=(
                description or inspect.getdoc(func) or ""
            ).strip(),
            func=func,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        )


class ToolRegistry:
    """Registro central de tools disponibles para el agente."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    # ---------- Registro ----------
    def add(self, tool: Tool, *, overwrite: bool = False) -> Tool:
        if tool.name in self._tools and not overwrite:
            raise ValueError(f"La tool '{tool.name}' ya está registrada.")
        self._tools[tool.name] = tool
        return tool

    def register(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        overwrite: bool = False,
    ):
        """Decorador. Funciona como @register y como @register(name=...)."""

        def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
            self.add(
                Tool.from_function(f, name, description),
                overwrite=overwrite,
            )
            return f  # la función original queda intacta y sigue siendo invocable

        return decorator(func) if func is not None else decorator

    def unregister(self, name: str) -> None:
        if name not in self._tools:
            raise KeyError(f"La tool '{name}' no existe.")
        del self._tools[name]

    # ---------- Consulta ----------
    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(
                f"La tool '{name}' no existe. Disponibles: {self.names()}"
            ) from None

    def get_tools(self) -> list[Tool]:
        """Devuelve las tools existentes."""
        return list(self._tools.values())

    def get_tools_schema(self) -> list[dict[str, Any]]:
        """Devuelve las tools en formato de function-calling para el LLM."""
        return [t.to_schema() for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)

    # ---------- Ejecución ----------
    def execute(self, name: str, **kwargs: Any) -> Any:
        return self.get(name)(**kwargs)

    # ---------- Dunder ----------
    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self) -> Iterator[Tool]:
        return iter(self._tools.values())

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={self.names()})"


# Instancia compartida por el módulo (los módulos de Python son singletons)
registry = ToolRegistry()
