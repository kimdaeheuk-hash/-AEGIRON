/**
 * 홈 메인 소개 영상의 출처를 푼다 (2026-10-18 캡틴 지시).
 *
 * ★ 왜 파일을 저장소에 안 넣나 ★
 * 소개 영상은 파일이 크다. git·Vercel 번들은 큰 이진 파일을 담는 곳이 아니다 —
 * 넣으면 배포가 무거워지고 저장소가 부푼다. 그래서 영상은 **영상 호스트에 올리고
 * 주소만** 받는다. 환경변수 NEXT_PUBLIC_INTRO_VIDEO_URL 에 주소를 넣으면 홈이 그걸
 * 읽어 재생기를 띄우고, 비어 있으면 아무것도 안 그린다(깨진 빈 상자를 안 보인다).
 *
 * 받는 주소 세 가지 — 셋 다 알아서 구분한다:
 *   · YouTube  (youtube.com/watch?v=… · youtu.be/… · /shorts/…)  — 미등록 업로드 권장
 *   · Vimeo    (vimeo.com/숫자)
 *   · 직접 파일 (… .mp4 · .webm — 예: Vercel Blob 공개 URL)
 *
 * 포스터(첫 화면 정지 이미지)는 NEXT_PUBLIC_INTRO_VIDEO_POSTER 로 따로 받는다(선택).
 */

export type IntroVideo =
  | { kind: 'youtube' | 'vimeo'; embedUrl: string; poster?: string }
  | { kind: 'file'; src: string; poster?: string }
  | null;

function youtubeId(url: string): string | null {
  // youtu.be/ID · watch?v=ID · /embed/ID · /shorts/ID
  const m =
    url.match(/(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})/);
  return m ? m[1] : null;
}

function vimeoId(url: string): string | null {
  const m = url.match(/vimeo\.com\/(?:video\/)?(\d+)/);
  return m ? m[1] : null;
}

export function introVideo(): IntroVideo {
  const url = process.env.NEXT_PUBLIC_INTRO_VIDEO_URL?.trim();
  if (!url) return null;
  const poster = process.env.NEXT_PUBLIC_INTRO_VIDEO_POSTER?.trim() || undefined;

  const yt = youtubeId(url);
  if (yt) {
    // rel=0: 끝나고 남의 영상을 권하지 않는다. modestbranding: 로고 최소화.
    return { kind: 'youtube', embedUrl: `https://www.youtube-nocookie.com/embed/${yt}?rel=0&modestbranding=1`, poster };
  }
  const vm = vimeoId(url);
  if (vm) {
    return { kind: 'vimeo', embedUrl: `https://player.vimeo.com/video/${vm}?dnt=1`, poster };
  }
  // 그 외에는 직접 재생 가능한 파일 주소로 본다(.mp4/.webm, Vercel Blob 등).
  return { kind: 'file', src: url, poster };
}
