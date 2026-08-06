/**
 * 사전 타입 — 모든 로케일이 **같은 모양**을 갖도록 강제한다.
 *
 * 왜 타입으로 묶는가: 번역을 손으로 관리하면 문구를 하나 추가할 때 다른 언어에서
 * 빠뜨리기 쉽고, 그건 배포 후 빈칸으로 드러난다. 여기서 타입을 고정해두면
 * 빠진 번역이 **빌드 단계에서 실패**한다 — 사이트에 빈칸이 나가는 일이 없다.
 */

export type NavDict = {
  platform: string;
  methodology: string;
  transparency: string;
  dataSources: string;
  solutions: string;
  briefings: string;
  about: string;
  contact: string;
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

export type StatDict = {
  value: string;
  label: string;
  note: string;
};

export type HomeDict = {
  metaTitle: string;
  metaDescription: string;
  heroEyebrow: string;
  heroTitle: string;
  heroLead: string;
  heroPrimaryCta: string;
  heroSecondaryCta: string;
  heroNoLogin: string;
  stats: StatDict[];

  openTitle: string;
  openLead: string;
  openItems: { title: string; body: string; href: string; linkLabel: string }[];

  /** ★ 이 사이트의 핵심 블록 ★ 검증 안 된 것을 우리가 먼저 말한다. */
  honestTitle: string;
  honestLead: string;
  honestPoints: string[];
  honestClose: string;
  honestCta: string;

  pipelineTitle: string;
  pipelineLead: string;
  pipelineSteps: { step: string; title: string; body: string }[];

  briefTitle: string;
  briefLead: string;
  briefCta: string;
  briefEmpty: string;
  briefError: string;

  audienceTitle: string;
  audienceLead: string;
  audiences: { title: string; body: string; href: string }[];

  ctaTitle: string;
  ctaBody: string;
  ctaButton: string;
};

export type Dictionary = {
  nav: NavDict;
  footer: FooterDict;
  home: HomeDict;
  pages: PagesDict;
  briefings: BriefingsDict;
  common: {
    siteName: string;
    siteTagline: string;
    readMore: string;
    backToHome: string;
    lastUpdated: string;
    liveNow: string;
  };
};

/**
 * 일반 콘텐츠 페이지 — 시스템·한계·데이터소스·활용처·회사 등이 전부 이 모양이다.
 *
 * 페이지마다 컴포넌트를 따로 만들면 11개 페이지 × 3개 언어를 손으로 관리하게 되고,
 * 문구를 하나 고칠 때마다 세 군데를 건드려야 한다. 콘텐츠를 데이터로 분리하고
 * 렌더러를 하나만 두면, 언어 추가는 사전 파일 하나로 끝난다.
 */
export type PageBlock = {
  title: string;
  body?: string;
  /** 카드 목록. 있으면 격자로 렌더링한다. */
  items?: { title: string; body: string; meta?: string }[];
  /** 번호 매긴 목록. **강조** 표기를 지원한다. */
  points?: string[];
  /** 블록 하단 각주 — 한계·출처를 남길 때 쓴다. */
  note?: string;
  /** 강조 카드로 그릴지(정직성 블록 등). */
  accent?: boolean;
};

export type ContentPage = {
  metaTitle: string;
  metaDescription: string;
  eyebrow: string;
  title: string;
  lead: string;
  blocks: PageBlock[];
  /** 페이지 하단 행동 유도. 생략 가능. */
  cta?: { title: string; body: string; label: string; href: string };
};

export type BriefingsDict = {
  /** 아카이브 목록 */
  archiveTitle: string;
  count: string;            // "{n}건" — {n} 치환
  quietDay: string;
  openBrief: string;
  empty: string;
  error: string;
  /** 개별 브리핑 */
  backToList: string;
  summary: string;
  segments: string;
  ticker: string;
  disclosure: string;
  notFound: string;
  /** ★ 언어 불일치 고지 ★ 평소엔 안 뜨고, 요청과 다른 언어가 왔을 때만 뜬다. */
  langNoticeTitle: string;
  langNoticeMismatch: string;
};

export type PagesDict = {
  platform: ContentPage;
  transparency: ContentPage;
  dataSources: ContentPage;
  methodology: ContentPage;
  about: ContentPage;
  contact: ContentPage;
  briefings: ContentPage;
  solutionsReinsurance: ContentPage;
  solutionsGovernment: ContentPage;
  solutionsNgo: ContentPage;
  privacy: ContentPage;
  terms: ContentPage;
};
