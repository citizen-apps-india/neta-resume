"""S3-compatible raw evidence storage remains content-addressed and replayable."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pytest
from botocore.exceptions import ClientError

from neta_core.config import Settings
from neta_core.pipeline import S3RawObjectStore


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, Any]] = {}
        self.put_calls = 0

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        key = (kwargs["Bucket"], kwargs["Key"])
        try:
            stored = self.objects[key]
        except KeyError:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}},
                "HeadObject",
            ) from None
        return {"Metadata": dict(stored["Metadata"])}

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self.put_calls += 1
        key = (kwargs["Bucket"], kwargs["Key"])
        self.objects[key] = {
            "Body": bytes(kwargs["Body"]),
            "ContentType": kwargs["ContentType"],
            "Metadata": dict(kwargs["Metadata"]),
        }
        return {}

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        key = (kwargs["Bucket"], kwargs["Key"])
        return {"Body": BytesIO(self.objects[key]["Body"])}


def test_s3_store_writes_once_and_replays_verified_content() -> None:
    client = FakeS3Client()
    store = S3RawObjectStore(
        bucket="neta-evidence",
        prefix="staging/raw",
        client=client,
    )
    payload = b'{"answer": 42}'

    stored = store.put(payload, content_type="application/json; charset=utf-8")
    duplicate = store.put(payload, content_type="application/json; charset=utf-8")

    assert stored == duplicate
    assert stored.object_uri.startswith("s3://neta-evidence/staging/raw/")
    assert stored.provenance_ref.endswith(".json")
    assert client.put_calls == 1
    assert store.read(stored.object_uri) == payload


def test_s3_store_rejects_wrong_bucket_prefix_and_corrupt_content() -> None:
    client = FakeS3Client()
    store = S3RawObjectStore(bucket="neta-evidence", prefix="raw", client=client)
    stored = store.put(b"original", content_type="text/plain")

    with pytest.raises(ValueError, match="does not belong"):
        store.read(stored.object_uri.replace("neta-evidence", "other-bucket"))
    with pytest.raises(ValueError, match="escapes prefix"):
        store.read(stored.object_uri.replace("/raw/", "/other/"))

    bucket_and_key = ("neta-evidence", stored.object_uri.removeprefix("s3://neta-evidence/"))
    client.objects[bucket_and_key]["Body"] = b"corrupt"
    with pytest.raises(OSError, match="hash mismatch"):
        store.read(stored.object_uri)


def test_s3_store_requires_bucket_configuration() -> None:
    with pytest.raises(ValueError, match="bucket cannot be empty"):
        S3RawObjectStore(bucket=" ", client=FakeS3Client())
    with pytest.raises(ValueError, match="NETA_RAW_S3_BUCKET"):
        Settings(_env_file=None, raw_store_backend="s3", raw_s3_bucket="")
