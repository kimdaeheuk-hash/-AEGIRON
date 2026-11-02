"""safe_fetch — SSRF·용량 방어. 외부 접속 없이 전부 mock 한다."""
from __future__ import annotations
import socket
from unittest.mock import patch

from algorithms import safe_fetch as sf


def _resp(content=b"%PDF-1.4 fake", declared=None):
    class _R:
        headers = {} if declared is None else {"Content-Length": str(declared)}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=65536):
            yield content
    return _R()


def _global_dns(*a, **k):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("140.211.11.99", 443))]


def test_rejects_non_http_scheme():
    _, reason, status = sf.fetch_pdf_bytes_detailed("ftp://x/y.pdf")
    assert status == 422 and "http(s)" in reason


def test_rejects_userinfo_and_odd_port():
    _, r1, s1 = sf.fetch_pdf_bytes_detailed("https://u:p@example.com/a.pdf")
    _, r2, s2 = sf.fetch_pdf_bytes_detailed("https://example.com:8080/a.pdf")
    assert (s1, s2) == (422, 422)
    assert "userinfo" in r1 and "포트" in r2


def test_rejects_literal_private_ips():
    for host in ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "[::1]"]:
        _, reason, status = sf.fetch_pdf_bytes_detailed(f"https://{host}/a.pdf")
        assert status == 422, host
        assert "사설" in reason, host


def test_rejects_hostname_resolving_private(monkeypatch):
    def _priv(*a, **k):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.9.9.9", 443))]
    monkeypatch.setattr(socket, "getaddrinfo", _priv)
    _, reason, status = sf.fetch_pdf_bytes_detailed("https://evil.example/a.pdf")
    assert status == 422 and "풀림" in reason


def test_rejects_dns_failure(monkeypatch):
    def _boom(*a, **k):
        raise socket.gaierror("nope")
    monkeypatch.setattr(socket, "getaddrinfo", _boom)
    _, reason, status = sf.fetch_pdf_bytes_detailed("https://missing.example/a.pdf")
    assert status == 422 and "DNS" in reason


def test_allowlist_blocks_offlist(monkeypatch):
    monkeypatch.setenv(sf.ALLOWLIST_ENV, "who.int")
    monkeypatch.setattr(socket, "getaddrinfo", _global_dns)
    _, reason, status = sf.fetch_pdf_bytes_detailed("https://evil.example/a.pdf")
    assert status == 422 and "허용목록" in reason


def test_allowlist_permits_suffix(monkeypatch):
    monkeypatch.setenv(sf.ALLOWLIST_ENV, "who.int")
    monkeypatch.setattr(socket, "getaddrinfo", _global_dns)
    with patch("requests.get", return_value=_resp()):
        content, reason, status = sf.fetch_pdf_bytes_detailed("https://afro.who.int/b.pdf")
    assert status == 200 and content.startswith(b"%PDF") and reason is None


def test_declared_length_over_cap_rejected_early(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _global_dns)
    with patch("requests.get", return_value=_resp(declared=999999999)) as m:
        _, reason, status = sf.fetch_pdf_bytes_detailed("https://x.example/b.pdf")
    m.assert_called_once()
    assert status == 422 and "선언 크기" in reason


def test_streaming_aborts_over_cap(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _global_dns)
    big = _resp(b"%PDF" + b"x" * 100)
    with patch("requests.get", return_value=big):
        _, reason, status = sf.fetch_pdf_bytes_detailed("https://x.example/b.pdf", max_bytes=10)
    assert status == 422 and "수신 크기" in reason


def test_non_pdf_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _global_dns)
    with patch("requests.get", return_value=_resp(b"<html>nope")):
        _, reason, status = sf.fetch_pdf_bytes_detailed("https://x.example/b.pdf")
    assert status == 422 and "PDF 파일이 아님" in reason


def test_network_error_is_502(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _global_dns)
    with patch("requests.get", side_effect=RuntimeError("down")):
        _, reason, status = sf.fetch_pdf_bytes_detailed("https://x.example/b.pdf")
    assert status == 502 and "내려받기 실패" in reason


def test_happy_path(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _global_dns)
    with patch("requests.get", return_value=_resp()) as m:
        content, reason, status = sf.fetch_pdf_bytes_detailed("https://x.example/b.pdf")
    assert status == 200 and content.startswith(b"%PDF") and reason is None
    _, kw = m.call_args
    assert kw["stream"] is True  # 스트리밍 수신 강제
