import type { IntroVideo as IntroVideoData } from '@/lib/video';

/**
 * 홈 메인 소개 영상.
 *
 * 영상 주소가 없으면(환경변수 미설정) 아무것도 그리지 않는다 — 실제 방문자에게
 * 빈 상자를 보이지 않기 위해서다. 주소가 생기면 그 자리에 16:9 재생기가 뜬다.
 *
 * - YouTube·Vimeo: iframe. loading="lazy" 로 첫 화면 로딩을 늦추지 않는다.
 * - 직접 파일: <video controls>. preload="none" + poster 로 바이트를 미리 안 받는다.
 */
export function IntroVideo({ video, label }: { video: IntroVideoData; label: string }) {
  if (!video) return null;

  return (
    <figure style={{ margin: 0 }}>
      <figcaption
        style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.12em',
          textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 12,
        }}
      >
        {label}
      </figcaption>
      <div
        style={{
          position: 'relative', width: '100%', aspectRatio: '16 / 9',
          borderRadius: 16, overflow: 'hidden', border: '1px solid var(--line2)',
          background: '#000',
        }}
      >
        {video.kind === 'file' ? (
          <video
            controls
            preload="none"
            poster={video.poster}
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
          >
            <source src={video.src} />
          </video>
        ) : (
          <iframe
            src={video.embedUrl}
            title={label}
            loading="lazy"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', border: 0 }}
          />
        )}
      </div>
    </figure>
  );
}
