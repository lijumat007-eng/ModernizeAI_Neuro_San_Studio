# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Maps a Source's `type` string to its SourceConnector implementation.
Database/SSH/Confluence connectors register here in later phases; a missing
optional dependency (e.g. boto3 not installed) only disables that one type.
"""

from typing import Dict, Type

from coded_tools.modernize.sources.base import SourceConnector
from coded_tools.modernize.sources.models import Source

_REGISTRY: Dict[str, Type[SourceConnector]] = {}


def register(connector_cls: Type[SourceConnector]) -> None:
    _REGISTRY[connector_cls.type_name] = connector_cls


def _register_defaults() -> None:
    from coded_tools.modernize.sources.git import GitConnector
    from coded_tools.modernize.sources.local import LocalConnector
    from coded_tools.modernize.sources.s3 import S3Connector

    register(LocalConnector)
    register(GitConnector)
    register(S3Connector)


_register_defaults()


def supported_types() -> list:
    return sorted(_REGISTRY.keys())


def build_connector(source: Source) -> SourceConnector:
    connector_cls = _REGISTRY.get(source.type)
    if connector_cls is None:
        raise ValueError(f"Unknown source type '{source.type}'. Supported: {supported_types()}")
    return connector_cls(source.source_id, source.config, source.credential_ref)
