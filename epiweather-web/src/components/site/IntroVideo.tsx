'use client';

import { useState } from 'react';
import { DEFAULT_INTRO_POSTER, type IntroVideo as IntroVideoData } from '@/lib/video';

/**
 * 홈 메인 소개 영상 — 파사드(facade) 방식.
 *
 * ★ 2026-10-18 캡틴 지시: "유튜브 동영상 화면에 내 이름 빼" ★
 * 유튜브 임베드는 정지 상태에서 썸네일 위에 업로더(채널) 이름·영상 제목을 얹는다. 그 이름을
 * 안 보이게 하려면, 재생 전까지 유튜브 iframe 자체를 띄우지 않는 게 가장 확실하다. 그래서
 * 첫 화면에는 **우리 퍼블릭 도메인 포스터**와 재생 버튼만 두고, 방문자가 누르는 순간에만
 * iframe(autoplay)을 끼워 넣는다. 유튜브 썸네일(제작자 이름이 박혀 있을 수 있음)은 쓰지 않는다.
 *
 * - 직접 파일(.mp4/.webm): 파사드 없이 <video controls> 로 바로 둔다 — 남의 이름이 뜰 일이 없다.
 */
export function IntroVideo({ video, label }: { video: IntroVideoData; label: string }) {
  const [playing, setPlaying] = useState(false);
  if (!video) return null;

  const poster = video.poster || DEFAULT_INTRO_POSTER;

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
            poster={poster}
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
          >
            <source src={video.src} />
          </video>
        ) : playing ? (
          <iframe
            src={video.embedUrl}
            title={label}
            loading="lazy"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', border: 0 }}
          />
        ) : (
          <button
            type="button"
            onClick={() => setPlaying(true)}
            aria-label={label}
            style={{
              position: 'absolute', inset: 0, width: '100%', height: '100%', padding: 0, border: 0,
              cursor: 'pointer', display: 'grid', placeItems: 'center',
              backgroundImage: `linear-gradient(rgba(6,12,22,.28), rgba(6,12,22,.5)), url(${poster})`,
              backgroundSize: 'cover', backgroundPosition: 'center',
            }}
          >
            <span
              aria-hidden="true"
              style={{
                width: 72, height: 72, borderRadius: 999, display: 'grid', placeItems: 'center',
                background: 'rgba(255,255,255,.92)', boxShadow: '0 10px 30px rgba(0,0,0,.35)',
              }}
            >
              <svg width="26" height="28" viewBox="0 0 26 28" fill="none" aria-hidden="true">
                <path d="M24 12.3a2 2 0 0 1 0 3.4L4 27.3A2 2 0 0 1 1 25.6V2.4A2 2 0 0 1 4 .7l20 11.6Z" fill="#b42318" />
              </svg>
            </span>
          </button>
        )}
      </div>
    </figure>
  );
}
