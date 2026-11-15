import { proxyAuthed } from '@/lib/server-api';

/**
 * LLM 추론은 Meta 실측 60~120초라 플랫폼 기본 시간 제한에 걸려 504 로 끊겼다(2026-11-15 캡틴: "추론도 엄청 늦게 떠").
 * 두 번째(LLM) 요청이 끝까지 기다릴 수 있게 늘린다. 첫 요청(fast=true)은 1초 안에 끝난다.
 */
export const maxDuration = 300;

export async function POST(req: Request): Promise<Response> {
  return proxyAuthed('/api/ai/infer', req);
}
