# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
SourceConnector: the interface every connector (local folder, Git, S3,
database, SSH, Confluence, ...) implements. A connector's only job is to
turn its source into a stream of SourceDocument objects and report a new
fingerprint for incremental re-scans - it never touches parsing or the graph.

Credentials are never handled as raw values here: `credential_ref` is the
*name* of an environment variable (for a single secret, e.g. a Git token) or
a *prefix* (for a username+password pair, e.g. "ORACLE_PROD" resolves to
"ORACLE_PROD_USER" and "ORACLE_PROD_PASSWORD"). This keeps secrets out of
Project JSON files, the UI, and logs.
"""

import os
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

try:
    from dotenv import load_dotenv

    load_dotenv()  # no-op if there is no .env file
except ImportError:
    pass


@dataclass
class SourceDocument:
    """One file/object/page fetched from a source, ready for RawMemory ingestion."""

    path: str  # path relative to the source root, e.g. "src/main/ClaimService.java"
    content: str
    kind: str = "file"  # "file" | "sql" | "doc" | "shell" | "cron"
    uri: str = ""  # human-followable link: repo blob URL, DB object name, Confluence page URL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionTestResult:
    ok: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class CredentialError(RuntimeError):
    """Raised when a required credential environment variable is missing."""


def resolve_secret(credential_ref: Optional[str]) -> Optional[str]:
    """Resolves a single-value secret (e.g. a Git/Confluence token) from the env."""
    if not credential_ref:
        return None
    value = os.environ.get(credential_ref)
    if value is None:
        raise CredentialError(
            f"Environment variable '{credential_ref}' is not set. "
            f"Set it (e.g. in a .env file) before using this source."
        )
    return value


def resolve_credential_pair(credential_ref: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Resolves a username+password pair from `<credential_ref>_USER` / `<credential_ref>_PASSWORD`."""
    if not credential_ref:
        return None, None
    user = os.environ.get(f"{credential_ref}_USER")
    password = os.environ.get(f"{credential_ref}_PASSWORD")
    if user is None or password is None:
        raise CredentialError(
            f"Environment variables '{credential_ref}_USER' and '{credential_ref}_PASSWORD' "
            f"must both be set before using this source."
        )
    return user, password


class SourceConnector(ABC):
    """Interface every source type implements."""

    type_name: str = ""

    def __init__(self, source_id: str, config: Dict[str, Any], credential_ref: Optional[str] = None):
        self.source_id = source_id
        self.config = config
        self.credential_ref = credential_ref

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """Cheap reachability/auth check, used by the UI's "Test" button."""
        raise NotImplementedError

    @abstractmethod
    def fetch(self, since_fingerprint: Optional[str] = None) -> Tuple[List[SourceDocument], str]:
        """
        Returns (documents, new_fingerprint). `since_fingerprint` is the value
        this source returned last time; a connector MAY use it to fetch only
        what changed (e.g. `git fetch` + diff since a commit SHA), or ignore
        it and always return everything - both are valid, incrementality is
        an optimization, not a correctness requirement. `new_fingerprint`
        must be stable and comparable (a commit SHA, a max `LAST_DDL_TIME`,
        a hash of file mtimes) so the *next* scan can decide what changed.
        """
        raise NotImplementedError
