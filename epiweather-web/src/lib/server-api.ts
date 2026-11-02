/**
 * 서버 전용 백엔드 프록시 헬퍼 — 클라이언트 컴포넌트에서 import 금지.
 *
 * 배경(2026-08-19 발견 → 2026-11-02 해결): X-API-Key를 NEXT_PUBLIC_API_KEY로
 * 브라우저에 박으면 번들에서 키가 그대로 노출되고, 유료 엔드포인트가 무한
 * 호출된다. 인증 필요 호출은 전부 Next 라우트 핸들러(src/app/api/...)를
 * 경유하고, 키는 서버 환경변수 EPIWEATHER_API_KEY에만 둔다. 브라우저는
 * 동일 출처 /api/* 만 부른다.
 */
const BACKEND =
  process.env.EPIWEATHER_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  'http://localhost:8000';
const KEY = process.env.EPIWEATHER_API_KEY ?? '';

export async function proxyAuthed(path: string, req: Request): Promise<Response> {
  if (!KEY) {
    return Response.json({ error: 'server API key not configured' }, { status: 503 });
  }
  const buf = await req.arrayBuffer();
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND}${path}`, {
      method: req.method,
      headers: { 'Content-Type': 'application/json', 'X-API-Key': KEY },
      body: buf.byteLength ? buf : undefined,
      cache: 'no-store',
    });
  } catch (e) {
    return Response.json(
      { error: `backend unreachable: ${e instanceof Error ? e.message : String(e)}` },
      { status: 502 },
    );
  }
  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { 'Content-Type': 'application/json' },
  });
}
