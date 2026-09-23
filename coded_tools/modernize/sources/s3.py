# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
S3Connector: reads objects from an S3 bucket/prefix using boto3. Replaces the
old fake flow in apps/modernizeai_ui/server.py, which only logged "Verifying
IAM credentials... Sync verified" and then silently scanned the local demo
repo instead.

Credentials follow the standard AWS resolution chain (environment variables,
~/.aws/credentials, an instance/task role) unless `credential_ref` names an
env-var prefix for an explicit access key pair.
"""

from typing import List, Optional, Tuple
from urllib.parse import urlsplit

from coded_tools.modernize.parsers.registry import get_default_registry
from coded_tools.modernize.sources.base import (
    ConnectionTestResult,
    SourceConnector,
    SourceDocument,
    resolve_credential_pair,
)

_DOC_EXTENSIONS = (".md", ".txt", ".rst")
_MAX_OBJECT_BYTES = 5 * 1024 * 1024


def _parse_s3_uri(uri: str) -> Tuple[str, str]:
    parts = urlsplit(uri)
    if parts.scheme != "s3" or not parts.netloc:
        raise ValueError(f"Not a valid s3:// URI: '{uri}'")
    return parts.netloc, parts.path.lstrip("/")


class S3Connector(SourceConnector):
    """
    config:
        s3_uri: str (required) - "s3://bucket-name/optional/prefix/"
        region: str (optional, default "us-east-1")
    credential_ref: env var PREFIX resolving to "<PREFIX>_USER" (access key id)
        and "<PREFIX>_PASSWORD" (secret access key). Omit to use the default
        AWS credential chain (env vars, ~/.aws/credentials, an instance role).
    """

    type_name = "s3"

    def _client(self):
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError(
                "The 'boto3' package is required for S3 sources. Install it with: pip install boto3"
            ) from e

        region = self.config.get("region", "us-east-1")
        access_key, secret_key = resolve_credential_pair(self.credential_ref)
        if access_key and secret_key:
            return boto3.client(
                "s3", region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key,
            )
        return boto3.client("s3", region_name=region)

    def test_connection(self) -> ConnectionTestResult:
        s3_uri = self.config.get("s3_uri")
        if not s3_uri:
            return ConnectionTestResult(ok=False, message="'s3_uri' is required for an S3 source.")
        try:
            bucket, prefix = _parse_s3_uri(s3_uri)
        except ValueError as e:
            return ConnectionTestResult(ok=False, message=str(e))
        try:
            client = self._client()
            resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        except Exception as e:  # botocore.exceptions.* / RuntimeError from missing boto3
            return ConnectionTestResult(ok=False, message=f"S3 error: {e}")
        count = resp.get("KeyCount", 0)
        return ConnectionTestResult(ok=True, message=f"Bucket reachable ({'objects found' if count else 'prefix is empty'}).")

    def fetch(self, since_fingerprint: Optional[str] = None) -> Tuple[List[SourceDocument], str]:
        s3_uri = self.config.get("s3_uri")
        if not s3_uri:
            raise ValueError(f"Source '{self.source_id}': 's3_uri' is required for an S3 source.")
        bucket, prefix = _parse_s3_uri(s3_uri)
        client = self._client()

        extensions = set(get_default_registry().supported_extensions()) | set(_DOC_EXTENSIONS)

        documents: List[SourceDocument] = []
        fingerprint_parts: List[str] = []
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                ext = "." + key.rsplit(".", 1)[-1].lower() if "." in key.rsplit("/", 1)[-1] else ""
                if ext not in extensions:
                    continue
                if obj.get("Size", 0) > _MAX_OBJECT_BYTES:
                    continue

                etag = obj.get("ETag", "").strip('"')
                fingerprint_parts.append(f"{key}:{etag}:{obj.get('Size', 0)}")

                body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
                try:
                    content = body.decode("utf-8")
                except UnicodeDecodeError:
                    content = body.decode("utf-8", errors="replace")

                rel_path = key[len(prefix):].lstrip("/") if prefix else key
                documents.append(SourceDocument(
                    path=rel_path,
                    content=content,
                    kind="doc" if ext in _DOC_EXTENSIONS else "file",
                    uri=f"https://{bucket}.s3.amazonaws.com/{key}",
                    metadata={"etag": etag, "size": obj.get("Size", 0)},
                ))

        import hashlib
        fingerprint = hashlib.sha256("\n".join(sorted(fingerprint_parts)).encode("utf-8")).hexdigest()
        return documents, fingerprint
