import io
import socket
import stat
import zipfile

import pytest
from aqb_api.security import redact, safe_artifact_path
from aqb_eval.adapters import UnsafeEndpointError, validate_endpoint, validate_stable_endpoint
from aqb_eval.uploads import UnsafeUploadError, parse_trace_upload


def zip_bytes(entries: dict[str, bytes], *, symlink: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            if symlink == name:
                info = zipfile.ZipInfo(name)
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, content)
            else:
                archive.writestr(name, content)
    return buffer.getvalue()


def test_zip_traversal_symlink_and_unsupported_files_are_rejected() -> None:
    with pytest.raises(UnsafeUploadError, match="unsafe path"):
        parse_trace_upload("bad.zip", zip_bytes({"../bundle.json": b"{}"}))
    with pytest.raises(UnsafeUploadError, match="links"):
        parse_trace_upload("bad.zip", zip_bytes({"bundle.json": b"target"}, symlink="bundle.json"))
    with pytest.raises(UnsafeUploadError, match="unsupported"):
        parse_trace_upload("bad.zip", zip_bytes({"script.py": b"print(1)"}))


def test_zip_bomb_ratio_is_rejected() -> None:
    content = b"0" * 300_000
    with pytest.raises(UnsafeUploadError, match="compression ratio"):
        parse_trace_upload("bomb.zip", zip_bytes({"bundle.json": content}))


@pytest.mark.asyncio
async def test_ssrf_blocks_private_addresses(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(UnsafeEndpointError, match="allowlist"):
        await validate_endpoint("https://agent.example.test/run", ())
    assert await validate_endpoint("http://localhost/run", ("localhost",)) == ("127.0.0.1",)


@pytest.mark.asyncio
async def test_dns_rebinding_change_is_rejected(monkeypatch) -> None:
    responses = iter(
        [
            [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
            [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.4.4", 443))],
        ]
    )
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: next(responses))
    with pytest.raises(UnsafeEndpointError):
        await validate_stable_endpoint("https://agent.example.test/run", ())


def test_redaction_and_artifact_path(tmp_path) -> None:
    assert "sk-proj" not in redact("token=sk-proj-abcdefghijklmnop")
    target = safe_artifact_path(tmp_path, "../../trace", ".json")
    assert target.parent == tmp_path.resolve()
