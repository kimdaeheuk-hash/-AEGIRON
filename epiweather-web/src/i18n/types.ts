/**
 * 사전 타입 — 모든 로케일이 **같은 모양**을 갖도록 강제한다.
 * 빠진 번역은 빌드 단계에서 실패한다 — 사이트에 빈칸이 나가지 않는다.
 *
 * 2026-11-22 개편: 극지(감지) → 헤임달(식별) → 발할라(대응)만 남겼다. 지운 페이지의
 * 사전은 복원 기준 커밋 83406e4 에 있다.
 */

export type NavDict = {
  polar: string;
  heimdall: string;
  valhalla: string;
  methodology: string;
  government: string;
  developers: string;
  security: string;
  about: string;
  contact: string;
  /** 묶음 제목 */
  product: string;
  company: string;
  dashboard: string;
  openMenu: string;
  closeMenu: string;
  language: string;
};

export type FooterDict = {
  tagline: string;
  product: string;
  company: string;
  legal: string;
  privacy: string;
  terms: string;
  rights: string;
  location: string;
  /** 푸터에도 정직성 한 줄을 남긴다 — 어느 페이지로 들어와도 보이게. */
  disclaimer: string;
};

/** 사슬의 한 고리. */
export type StageDict = {
  code: 'POLAR' | 'HEIMDALL' | 'VALHALLA';
  name: string;
  role: string;
  body: string;
  /** 실제로 지금 무엇을 하는가 — 과장 없이 한 줄씩. */
  facts: string[];
  /** 대시보드 안 구획 앵커 또는 사이트 경로 */
  href: string;
  linkLabel: string;
};

export type HomeDict = {
  metaTitle: string;
  metaDescription: string;
  eyebrow: string;
  title: string;
  lead: string;
  primaryCta: string;
  secondaryCta: string;
  chainTitle: string;
  chainLead: string;
  stages: StageDict[];
  healthTitle: string;
  /** {ok} · {total} 치환 */
  healthOk: string;
  healthUnknown: string;
  notTitle: string;
  notPoints: string[];
};

export type PolarDict = {
  title: string;
  lead: string;
  /** {days} 치환 */
  span: string;
  /** {n} 치환 */
  undetermined: string;
  cols: { region: string; first: string; latest: string; change: string; records: string };
  empty: string;
  unavailable: string;
  apiLabel: string;
};

/** 묶음 색 — globals.css 의 [data-tone] 과 짝. */
export type BlockTone = 'teal' | 'indigo' | 'amber' | 'crimson' | 'forest' | 'violet' | 'sky';

export type PageBlock = {
  title: string;
  /** 제목 위 작은 꼬리표. tone 색으로 그린다. */
  kicker?: string;
  tone?: BlockTone;
  /** 깊은 남청색 띠로 그릴지. */
  deep?: boolean;
  body?: string;
  /** 사양표 — 왼쪽 항목 · 오른쪽 값. */
  specs?: { label: string; value: string }[];
  /** 카드 목록. 있으면 격자로 렌더링한다. */
  items?: { title: string; body: string; meta?: string }[];
  photo?: PhotoDict;
  /** 번호 매긴 목록. **강조** 표기를 지원한다. */
  points?: string[];
  /** 블록 하단 각주 — 한계·출처를 남길 때 쓴다. */
  note?: string;
  /** 강조 카드로 그릴지(정직성 블록 등). */
  accent?: boolean;
};

/** 사진 한 장. src·credit·sourceUrl 은 언어와 무관하고, alt·caption 만 언어별로 쓴다. */
export type PhotoDict = {
  src: string;
  alt: string;
  caption: string;
  credit: string;
  sourceUrl: string;
  position?: string;
};

export type ContentPage = {
  metaTitle: string;
  metaDescription: string;
  eyebrow: string;
  title: string;
  lead: string;
  photo?: PhotoDict;
  blocks: PageBlock[];
  /** 페이지 하단 행동 유도. 생략 가능. */
  cta?: { title: string; body: string; label: string; href: string };
};

export type PagesDict = {
  about: ContentPage;
  methodology: ContentPage;
  government: ContentPage;
  contact: ContentPage;
  security: ContentPage;
  developers: ContentPage;
  polar: ContentPage;
  privacy: ContentPage;
  terms: ContentPage;
};

export type Dictionary = {
  nav: NavDict;
  footer: FooterDict;
  home: HomeDict;
  polar: PolarDict;
  pages: PagesDict;
  api: { tableTitle: string; tableLead: string; authYes: string; authNo: string; tags: Record<string, string> };
  common: { siteName: string };
};
