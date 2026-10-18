import Image from 'next/image';
import type { PhotoDict } from '@/i18n/types';

/**
 * 사진 한 장 + 출처 표기.
 *
 * 사진은 전부 퍼블릭 도메인(NASA·CDC)이고, 그래도 저작자와 원본 링크를 사진 바로 아래에
 * 남긴다. 우리 실험실·우리 장비 사진처럼 읽히지 않게, 무엇을 찍은 것인지를 캡션에 쓴다.
 * next/image 가 크기별로 최적화해 내보내므로 1~2MB 원본이 그대로 나가지 않는다.
 */
export function PhotoFigure({
  photo,
  aspect = '21 / 9',
  priority = false,
}: {
  photo: PhotoDict;
  aspect?: string;
  priority?: boolean;
}) {
  return (
    <figure style={{ margin: 0 }}>
      <div
        style={{
          position: 'relative', width: '100%', aspectRatio: aspect,
          borderRadius: 16, overflow: 'hidden', border: '1px solid var(--line)',
          background: 'var(--panel2)',
        }}
      >
        <Image
          src={photo.src}
          alt={photo.alt}
          fill
          priority={priority}
          sizes="(max-width: 1320px) 100vw, 1320px"
          style={{ objectFit: 'cover', objectPosition: photo.position ?? 'center' }}
        />
      </div>
      <figcaption
        style={{
          display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'space-between',
          marginTop: 8, fontSize: 12, lineHeight: 1.6, color: 'var(--muted2)',
        }}
      >
        <span>{photo.caption}</span>
        <a
          href={photo.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}
        >
          {photo.credit}
        </a>
      </figcaption>
    </figure>
  );
}
