"""CORS — 실배포 프론트가 브라우저 직접 호출에 막히지 않는다 (2026-11-03).

9번 대시보드가 TypeError: Failed to fetch로 떴는데 서버는 정상 200이었다.
원인: allow_origins에 실배포 주소가 없어 브라우저가 차단. curl/서버측
조회는 CORS를 안 타서 멀쩡해 보이는 게 함정이다. 미들웨어 설정을 직접 본다
(TestClient가 아니라 소켓 불필요).
"""
from __future__ import annotations


def test_cors_allows_production_frontend():
    from fastapi.middleware.cors import CORSMiddleware

    import main as main_mod

    for m in main_mod.app.user_middleware:
        if m.cls is CORSMiddleware:
            origins = m.kwargs.get("allow_origins", [])
            assert "https://epiweather-web.vercel.app" in origins
            assert "http://localhost:3000" in origins
            return
    raise AssertionError("CORSMiddleware 미등록")


def _drive(coro):
    """실제 I/O 없는 코루틴을 이벤트 루프 없이 끝까지 민다.

    asyncio.run()은 루프 생성 때 소켓을 열어 샌드박스에서 막힌다.
    여기 흐름엔 진짜 대기가 없어 send() 한 번이면 끝난다.
    """
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise AssertionError("예상 밖의 비동기 대기")


def test_cors_preflight_behaves_for_production_frontend():
    """행위 확인 — 실제 설정값으로 프리플라이트를 돌려본다.

    소켓 없이 ASGI를 직접 호출한다. 실배포 오리진은 허용 헤더가 붙고,
    낯선 오리진은 안 붙는다.
    """
    from fastapi.middleware.cors import CORSMiddleware

    import main as main_mod

    origins: list[str] = []
    for m in main_mod.app.user_middleware:
        if m.cls is CORSMiddleware:
            origins = list(m.kwargs.get("allow_origins", []))
    assert origins, "CORSMiddleware 미등록"

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b"{}"})

    async def run_preflight(origin: str) -> dict[str, str]:
        messages: list = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        wrapped = CORSMiddleware(app, allow_origins=origins,
                                 allow_methods=["*"], allow_headers=["*"])
        await wrapped({"type": "http", "http_version": "1.1", "method": "OPTIONS",
                       "path": "/api/dashboard", "headers": [
                           (b"origin", origin.encode()),
                           (b"access-control-request-method", b"GET"),
                       ]}, receive, send)
        start = next(m for m in messages if m["type"] == "http.response.start")
        return {k.decode(): v.decode() for k, v in start["headers"]}

    headers = _drive(run_preflight("https://epiweather-web.vercel.app"))
    assert headers.get("access-control-allow-origin") == \
        "https://epiweather-web.vercel.app"
    stranger = _drive(run_preflight("https://evil.example.com"))
    assert "access-control-allow-origin" not in stranger
