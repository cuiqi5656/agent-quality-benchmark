from __future__ import annotations

import io
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, cast

ALLOWED_ARCHIVE_SUFFIXES = {".json", ".jsonl"}


class UnsafeUploadError(ValueError):
    pass


def _validate_member(member: zipfile.ZipInfo) -> None:
    path = PurePosixPath(member.filename)
    if path.is_absolute() or ".." in path.parts:
        raise UnsafeUploadError("archive contains an unsafe path")
    mode = member.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise UnsafeUploadError("archive links are not allowed")
    if not member.is_dir() and path.suffix.casefold() not in ALLOWED_ARCHIVE_SUFFIXES:
        raise UnsafeUploadError("archive contains an unsupported file type")


def parse_trace_upload(
    filename: str,
    content: bytes,
    *,
    max_upload_bytes: int = 50 * 1024 * 1024,
    max_extracted_bytes: int = 250 * 1024 * 1024,
) -> dict[str, Any]:
    if len(content) > max_upload_bytes:
        raise UnsafeUploadError("upload exceeds the configured size limit")
    suffix = Path(filename).suffix.casefold()
    if suffix == ".json":
        data = json.loads(content)
        if not isinstance(data, dict):
            raise UnsafeUploadError("JSON trace root must be an object")
        return data
    if suffix == ".jsonl":
        trials = [json.loads(line) for line in content.decode("utf-8").splitlines() if line.strip()]
        return {"protocol_version": "aqb.trace.v1", "manifest": {"source": "upload"}, "trials": trials}
    if suffix != ".zip":
        raise UnsafeUploadError("only JSON, JSONL, and ZIP trace files are supported")

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        members = archive.infolist()
        if len(members) > 10_000:
            raise UnsafeUploadError("archive contains too many entries")
        total_size = 0
        for member in members:
            _validate_member(member)
            total_size += member.file_size
            if total_size > max_extracted_bytes:
                raise UnsafeUploadError("archive expands beyond the configured limit")
            if member.compress_size and member.file_size / member.compress_size > 200:
                raise UnsafeUploadError("archive member has an unsafe compression ratio")
        names = {member.filename for member in members}
        if "bundle.json" in names:
            return cast(dict[str, Any], json.loads(archive.read("bundle.json")))
        if "manifest.json" not in names or "trials.jsonl" not in names:
            raise UnsafeUploadError("ZIP trace requires bundle.json or manifest.json plus trials.jsonl")
        manifest = json.loads(archive.read("manifest.json"))
        trials = [json.loads(line) for line in archive.read("trials.jsonl").decode("utf-8").splitlines() if line.strip()]
        return {"protocol_version": "aqb.trace.v1", "manifest": manifest, "trials": trials}


def validate_trace_bundle(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("protocol_version") != "aqb.trace.v1":
        raise UnsafeUploadError("unsupported or missing trace protocol_version")
    if not isinstance(data.get("manifest"), dict) or not isinstance(data.get("trials"), list):
        raise UnsafeUploadError("trace bundle requires manifest and trials")
    return data
