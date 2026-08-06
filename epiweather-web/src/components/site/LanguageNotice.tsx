import type { BriefingsDict } from '@/i18n/types';
import type { Locale } from '@/i18n/config';

/**
 * 브리핑 언어가 방문자의 로케일과 다를 때 그 사실을 알린다.
 *
 * ★ 왜 반드시 필요한가(실측 2026-08-06) ★
 * 백엔드는 한국어와 영어만 생성한다. `lang=fr`를 요청하면 **오류가 아니라 조용히
 * 다른 언어가 돌아온다.** 이걸 그대로 렌더링하면 프랑스어 페이지에 프랑스어가 아닌
 * 글이 아무 설명 없이 실린다 — 방문자는 우리가 프랑스어라고 주장한 걸 읽고 있다고
 * 생각한다. 조용히 틀린 것을 내보내지 않는 것이 이 사이트 전체의 원칙이다.
 *
 * 영어판도 자동 생성이라 병명·지명이 한국어로 남는 경우가 있어 함께 고지한다.
 */
export function LanguageNotice({
  locale,
  actualLang,
  dict,
}: {
  locale: Locale;
  actualLang: string | undefined;
  dict: BriefingsDict;
}) {
  if (!actualLang) return null;

  // 2026-08-06 백엔드 개편으로 ko·en·fr가 모두 정식 생성된다. 그래서 평소에는
  // 아무것도 띄우지 않고, **실제로 다른 언어가 돌아왔을 때만** 알린다.
  // 이 검사를 지우지 않는 이유: 조용히 다른 언어를 내보내는 게 최악의 실패라
  // 안전망은 남겨 둔다.
  const mismatched = actualLang !== locale;
  if (!mismatched) return null;

  const message = dict.langNoticeMismatch;

  return (
    <aside
      style={{
        border: `1px solid ${mismatched ? 'rgba(244,63,94,.32)' : 'var(--line2)'}`,
        background: mismatched ? 'rgba(244,63,94,.05)' : 'var(--panel)',
        borderRadius: 12,
        padding: '15px 18px',
        marginTop: 24,
        maxWidth: 760,
      }}
    >
      <p
        style={{
          fontFamily: 'var(--mono)', fontSize: 10.5, letterSpacing: '.1em',
          textTransform: 'uppercase',
          color: mismatched ? 'var(--accent)' : 'var(--muted2)',
          marginBottom: 8,
        }}
      >
        {dict.langNoticeTitle}
      </p>
      <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.7 }}>{message}</p>
    </aside>
  );
}
