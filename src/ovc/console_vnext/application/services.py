from __future__ import annotations

from typing import Any, Mapping, Protocol

from .models import ConsoleResource


class ProjectionAdapter(Protocol):
    def project(self, payload: Mapping[str, Any], context: Mapping[str, Any]) -> ConsoleResource: ...


class CapabilityInspectionService:
    def __init__(self, adapter: ProjectionAdapter):
        self._adapter = adapter

    def inspect(self, payload: Mapping[str, Any], context: Mapping[str, Any]) -> ConsoleResource:
        return self._adapter.project(payload, context)


class C1InspectionService(CapabilityInspectionService):
    pass
