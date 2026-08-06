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
  common: {
    siteName: string;
    siteTagline: string;
    readMore: string;
    backToHome: string;
    lastUpdated: string;
    liveNow: string;
  };
};
