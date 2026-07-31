"""Executable extraction boundary shared by source clients and future orchestrators.

Extraction stops at an immutable raw artifact. Source-specific parsing happens afterward, so a
scheduler can retry, replay, and inspect transport independently from canonical database writes.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, TypeVar, cast
from urllib.parse import urlparse

import boto3
import httpx
from botocore.exceptions import ClientError

from neta_core.config import settings
from neta_core.http import client as http
from neta_core.pipeline.contracts import RawEnvelope, SourceManifest

_CONTENT_TYPE_EXTENSIONS = {
    "application/json": ".json",
    "application/pdf": ".pdf",
    "application/rss+xml": ".xml",
    "application/zip": ".zip",
    "application/xml": ".xml",
    "text/csv": ".csv",
    "text/html": ".html",
    "text/xml": ".xml",
}


@dataclass(frozen=True, slots=True)
class StoredRawObject:
    """Address and legacy provenance reference for one immutable raw object."""

    content_hash: str
    object_uri: str
    provenance_ref: str
    size_bytes: int


class RawObjectStore(Protocol):
    """Storage boundary shared by local and S3-compatible evidence archives."""

    def put(self, payload: bytes, *, content_type: str) -> StoredRawObject:
        """Persist bytes by content hash and return their stable address."""

    def read(self, object_uri: str) -> bytes:
        """Read a previously stored object for deterministic replay."""


@dataclass(slots=True)
class FileRawObjectStore:
    """Content-addressed local store used by the existing ingestion commands and tests."""

    root: Path = field(default_factory=lambda: Path(settings.raw_cache_dir))
    uri_prefix: str = "raw-cache://"

    def put(self, payload: bytes, *, content_type: str) -> StoredRawObject:
        digest, provenance_ref = _object_identity(payload, content_type)
        destination = Path(self.root) / provenance_ref
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            with destination.open("xb") as raw_file:
                raw_file.write(payload)
        except FileExistsError:
            existing_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
            if existing_hash != digest:
                raise OSError(f"raw object hash mismatch at {destination}") from None

        separator = "" if self.uri_prefix.endswith("/") else "/"
        return StoredRawObject(
            content_hash=digest,
            object_uri=f"{self.uri_prefix}{separator}{provenance_ref}",
            provenance_ref=provenance_ref,
            size_bytes=len(payload),
        )

    def read(self, object_uri: str) -> bytes:
        prefix = self.uri_prefix if self.uri_prefix.endswith("/") else f"{self.uri_prefix}/"
        if not object_uri.startswith(prefix):
            raise ValueError(f"object URI {object_uri!r} does not belong to {self.uri_prefix!r}")
        relative_path = object_uri.removeprefix(prefix)
        root = Path(self.root).resolve()
        source = (root / relative_path).resolve()
        if source != root and root not in source.parents:
            raise ValueError("raw object URI escapes the configured store root")
        return source.read_bytes()


class S3Body(Protocol):
    def read(self) -> bytes: ...


class S3Client(Protocol):
    def head_object(self, **kwargs: Any) -> Mapping[str, Any]: ...

    def put_object(self, **kwargs: Any) -> Mapping[str, Any]: ...

    def get_object(self, **kwargs: Any) -> Mapping[str, Any]: ...


@dataclass(slots=True)
class S3RawObjectStore:
    """Content-addressed evidence storage for AWS S3 and compatible object stores."""

    bucket: str
    prefix: str = "raw"
    region_name: str | None = None
    endpoint_url: str | None = None
    client: S3Client | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.bucket = self.bucket.strip()
        self.prefix = self.prefix.strip("/")
        if not self.bucket:
            raise ValueError("S3 raw object bucket cannot be empty")
        if self.client is None:
            self.client = cast(
                S3Client,
                boto3.client(
                    "s3",
                    region_name=self.region_name,
                    endpoint_url=self.endpoint_url,
                ),
            )

    def put(self, payload: bytes, *, content_type: str) -> StoredRawObject:
        digest, provenance_ref = _object_identity(payload, content_type)
        key = self._key(provenance_ref)
        client = self._client()
        try:
            existing = client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchKey", "NotFound"}:
                raise
        else:
            metadata = existing.get("Metadata", {})
            existing_hash = metadata.get("sha256") if isinstance(metadata, Mapping) else None
            if existing_hash is None:
                existing_hash = hashlib.sha256(self._read_key(key)).hexdigest()
            if existing_hash != digest:
                raise OSError(f"raw object hash mismatch at s3://{self.bucket}/{key}")
            return self._stored(digest, provenance_ref, len(payload))

        client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload,
            ContentType=content_type,
            Metadata={"sha256": digest},
        )
        return self._stored(digest, provenance_ref, len(payload))

    def read(self, object_uri: str) -> bytes:
        parsed = urlparse(object_uri)
        if parsed.scheme != "s3" or parsed.netloc != self.bucket:
            raise ValueError(f"object URI {object_uri!r} does not belong to s3://{self.bucket}")
        key = parsed.path.lstrip("/")
        expected_prefix = f"{self.prefix}/" if self.prefix else ""
        if not key.startswith(expected_prefix):
            raise ValueError(f"object URI {object_uri!r} escapes prefix {self.prefix!r}")
        payload = self._read_key(key)
        filename = key.rsplit("/", 1)[-1]
        expected_hash = filename.partition(".")[0]
        if len(expected_hash) != 64 or hashlib.sha256(payload).hexdigest() != expected_hash:
            raise OSError(f"raw object hash mismatch at {object_uri}")
        return payload

    def _client(self) -> S3Client:
        if self.client is None:  # pragma: no cover - guarded by __post_init__
            raise RuntimeError("S3 client is not configured")
        return self.client

    def _key(self, provenance_ref: str) -> str:
        return f"{self.prefix}/{provenance_ref}" if self.prefix else provenance_ref

    def _read_key(self, key: str) -> bytes:
        response = self._client().get_object(Bucket=self.bucket, Key=key)
        body = response.get("Body")
        if body is None or not hasattr(body, "read"):
            raise OSError(f"S3 object body is missing for s3://{self.bucket}/{key}")
        return cast(S3Body, body).read()

    def _stored(
        self,
        digest: str,
        provenance_ref: str,
        size_bytes: int,
    ) -> StoredRawObject:
        key = self._key(provenance_ref)
        return StoredRawObject(
            content_hash=digest,
            object_uri=f"s3://{self.bucket}/{key}",
            provenance_ref=provenance_ref,
            size_bytes=size_bytes,
        )


def configured_raw_object_store() -> RawObjectStore:
    """Build the environment-selected evidence store without exposing it to source clients."""
    if settings.raw_store_backend == "s3":
        return S3RawObjectStore(
            bucket=settings.raw_s3_bucket,
            prefix=settings.raw_s3_prefix,
            region_name=settings.raw_s3_region,
            endpoint_url=settings.raw_s3_endpoint_url,
        )
    return FileRawObjectStore()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _object_identity(payload: bytes, content_type: str) -> tuple[str, str]:
    digest = hashlib.sha256(payload).hexdigest()
    media_type = content_type.partition(";")[0].strip().lower()
    extension = _CONTENT_TYPE_EXTENSIONS.get(media_type, ".bin")
    return digest, f"{digest[:2]}/{digest}{extension}"


@dataclass(frozen=True, slots=True)
class ExtractionContext:
    """Run-scoped dependencies and the exact Git-owned source definition being executed."""

    manifest: SourceManifest
    pipeline_run_id: str
    object_store: RawObjectStore
    clock: Callable[[], datetime] = field(default=_utcnow, repr=False, compare=False)
    artifact_observer: Callable[[RawArtifact], None] | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not self.pipeline_run_id.strip():
            raise ValueError("pipeline_run_id cannot be empty")


@dataclass(frozen=True, slots=True)
class HttpExtractionRequest:
    """One source-native resource to retrieve through the standard HTTP adapter."""

    source_id: str
    native_id: str
    url: str
    default_content_type: str = "application/octet-stream"
    headers: Mapping[str, str] = field(default_factory=dict)
    params: Mapping[str, object] = field(default_factory=dict)
    accepted_status_codes: frozenset[int] = frozenset({200})
    effective_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RawArtifact:
    """Raw bytes plus their immutable envelope and legacy ``source_ref`` pointer."""

    envelope: RawEnvelope
    payload: bytes
    provenance_ref: str | None

    def text(self, default_encoding: str = "utf-8") -> str:
        """Decode text using the captured HTTP charset when one was supplied."""
        encoding = default_encoding
        for parameter in self.envelope.content_type.split(";")[1:]:
            key, separator, value = parameter.strip().partition("=")
            if separator and key.lower() == "charset":
                encoding = value.strip(" \"'") or default_encoding
                break
        try:
            return self.payload.decode(encoding, errors="replace")
        except LookupError:
            return self.payload.decode(default_encoding, errors="replace")


RequestT = TypeVar("RequestT", contravariant=True)


class SourceAdapter(Protocol[RequestT]):
    """Common executable boundary implemented by HTTP, document, bulk, and gated adapters."""

    def extract(self, request: RequestT, *, context: ExtractionContext) -> RawArtifact:
        """Retrieve and persist one raw source resource without converting it."""


class HttpGet(Protocol):
    def __call__(self, url: str, **kwargs: object) -> httpx.Response: ...


@dataclass(slots=True)
class HttpSourceAdapter:
    """Synchronous HTTP extractor for API, crawl, and feed resources."""

    get: HttpGet = http.get

    def extract(
        self,
        request: HttpExtractionRequest,
        *,
        context: ExtractionContext,
    ) -> RawArtifact:
        if request.source_id != context.manifest.id:
            raise ValueError(
                f"request source {request.source_id!r} does not match "
                f"manifest {context.manifest.id!r}"
            )

        kwargs: dict[str, object] = {"headers": dict(request.headers)}
        if request.params:
            kwargs["params"] = dict(request.params)
        response = self.get(request.url, **kwargs)
        if response.status_code not in request.accepted_status_codes:
            response.raise_for_status()
            raise httpx.HTTPStatusError(
                f"unexpected HTTP status {response.status_code}",
                request=response.request,
                response=response,
            )
        content_type = response.headers.get("content-type") or request.default_content_type
        metadata = _http_metadata(response)
        source_uri = (
            str(httpx.URL(request.url, params=dict(request.params)))
            if request.params
            else request.url
        )
        return capture_raw(
            context=context,
            source_id=request.source_id,
            native_id=request.native_id,
            source_uri=source_uri,
            payload=response.content,
            content_type=content_type,
            effective_at=request.effective_at,
            http_metadata=metadata,
        )


def capture_raw(
    *,
    context: ExtractionContext,
    source_id: str,
    native_id: str,
    source_uri: str,
    payload: bytes,
    content_type: str,
    effective_at: datetime | None = None,
    http_metadata: Mapping[str, str] | None = None,
) -> RawArtifact:
    """Persist a payload and build its deterministic, provenance-complete envelope."""
    if source_id != context.manifest.id:
        raise ValueError(
            f"payload source {source_id!r} does not match manifest {context.manifest.id!r}"
        )
    if context.manifest.rights.store_raw:
        stored = context.object_store.put(payload, content_type=content_type)
        content_hash = stored.content_hash
        object_uri = stored.object_uri
        provenance_ref: str | None = stored.provenance_ref
    else:
        content_hash = hashlib.sha256(payload).hexdigest()
        object_uri = f"transient://{source_id}/{content_hash}"
        provenance_ref = None
    fetched_at = context.clock()
    if fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
        raise ValueError("extraction clock must return a timezone-aware datetime")

    envelope = RawEnvelope(
        envelope_id=f"{source_id}:{native_id}:{content_hash}",
        source_id=source_id,
        native_id=native_id,
        source_uri=source_uri,
        fetched_at=fetched_at,
        effective_at=effective_at,
        content_type=content_type,
        content_hash=content_hash,
        object_uri=object_uri,
        license_snapshot=json.dumps(
            context.manifest.rights.model_dump(mode="json", exclude_none=True),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        pipeline_run_id=context.pipeline_run_id,
        http_metadata=dict(http_metadata or {}),
    )
    artifact = RawArtifact(
        envelope=envelope,
        payload=payload,
        provenance_ref=provenance_ref,
    )
    if context.artifact_observer is not None:
        context.artifact_observer(artifact)
    return artifact


def _http_metadata(response: httpx.Response) -> dict[str, str]:
    metadata = {"status_code": str(response.status_code)}
    for header in ("etag", "last-modified", "content-length"):
        value = response.headers.get(header)
        if value:
            metadata[header] = value
    return metadata
