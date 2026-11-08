'use client';

import type { ReactNode } from 'react';
import { Theme } from '@astryxdesign/core/theme';
import { neutralTheme } from '@astryxdesign/theme-neutral/built';

/**
 * Astryx 테마 범위.
 *
 * Astryx 컴포넌트로 만드는 새 화면을 이 컴포넌트로 감싼다. 기존 화면은
 * 감싸지 않는다 — Theme 은 글꼴·제목 색을 자기 범위 안에서 다시 정하므로,
 * 앱 전체를 감싸면 지금 디자인이 바뀐다.
 *
 * 사이트가 어두운 화면이라 기본 모드는 dark 다.
 */
export function AstryxProvider({
  children,
  mode = 'dark',
}: {
  children: ReactNode;
  mode?: 'light' | 'dark' | 'system';
}) {
  return (
    <Theme theme={neutralTheme} mode={mode}>
      {children}
    </Theme>
  );
}
