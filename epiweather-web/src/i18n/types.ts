/**
 * 사전 타입 — 모든 로케일이 **같은 모양**을 갖도록 강제한다.
 *
 * 왜 타입으로 묶는가: 번역을 손으로 관리하면 문구를 하나 추가할 때 다른 언어에서
 * 빠뜨리기 쉽고, 그건 배포 후 빈칸으로 드러난다. 여기서 타입을 고정해두면
 * 빠진 번역이 **빌드 단계에서 실패**한다 — 사이트에 빈칸이 나가는 일이 없다.
 */

export type NavDict = {
  /** 묶음 제목 — 회사 · 기술 · 활용 분야 · 검증·데이터 */
  company: string;
  trust: string;
  live: string;
  record: string;
  korea: string;
  security: string;
  press: string;
  pilot: string;
  developers: string;
  diseases: string;
  techSpec1: string;
  techSpec2: string;
  engines: string;
  solGovernment: string;
  solReinsurance: string;
  solNgo: string;
  platform: string;
  technology: string;
  programs: string;
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

/**
 * 엔진이 **언제 도는가.** 상시 가동하는 것과 부를 때만 도는 것을 같은 무게로
 * 적으면 그 자체로 과장이 된다 — 그래서 엔진마다 이 값을 반드시 단다.
 */
export type EngineMode = 'hourly' | 'daily' | 'onAlert' | 'onRequest';

export type EngineDict = {
  /** 백엔드 모듈 파일명 그대로(algorithms/{id}.py) — 실재하는 코드를 가리킨다. */
  id: string;
  name: string;
  body: string;
  mode: EngineMode;
  /** 이 엔진의 숫자를 어디까지 믿어도 되는지. 있으면 반드시 그린다. */
  caveat?: string;
};

export type EngineGroupDict = {
  key: string;
  label: string;
  engines: EngineDict[];
};

export type HomeDict = {
  metaTitle: string;
  metaDescription: string;
  /** '{ok}' '{total}' 자리에 /api/status 의 실측값이 들어간다. */
  heroLiveOk: string;
  /** API 를 못 읽었을 때 — 초록 불을 켜지 않는다. */
  heroLiveUnknown: string;
  /** [[ ]] 로 감싼 낱말은 강조색으로 그린다. 줄바꿈은 \n. */
  heroTitle: string;
  heroLead: string;
  heroPrimaryCta: string;
  heroSecondaryCta: string;
  heroNoLogin: string;
  stats: StatDict[];
  /** 수치는 세는 날 바뀐다 — 언제 센 값인지를 수치 옆에 둔다. */
  statsAsOf: string;

  /** 홈 메인 소개 영상 라벨. 영상 자체는 환경변수(NEXT_PUBLIC_INTRO_VIDEO_URL)로 켜진다. */
  introVideoLabel: string;

  /** 수치 띠 아래 사진 한 장(퍼블릭 도메인, 출처 표기). */
  photo: PhotoDict;

  /** 감시 현장 갤러리 — 전부 퍼블릭/자유 라이선스, 우리 시설이 아님을 캡션에 명시. */
  galleryTitle: string;
  galleryLead: string;
  gallery: PhotoDict[];

  engineTitle: string;
  engineLead: string;
  engineModes: Record<EngineMode, string>;
  engineCaveatLabel: string;
  engineGroups: EngineGroupDict[];
  /** 엔진 카탈로그(전체 114개 모듈)로 보내는 링크 문구. */
  engineCatalogueCta: string;

  /** 경쟁 조기경보와 무엇이 다른가 + 미래성. */
  diffEyebrow: string;
  diffTitle: string;
  diffLead: string;
  diffItems: { title: string; body: string }[];
  futureTitle: string;
  futureLead: string;
  futureItems: { title: string; body: string }[];

  /** 스페셜 프로그램(헤임달·발할라) 강조 띠 — 홈에서 /programs 로 보낸다. */
  specialEyebrow: string;
  specialTitle: string;
  specialLead: string;
  specialCards: { code: string; name: string; body: string }[];
  specialCta: string;

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

/**
 * 실가동·검증·국가사업 페이지 묶음 (2026-10-18 캡틴 지시: "전부 실행해 — 진짜 아이기론이
 * 뭘 하고 있는지 실가동되는 걸 보여줘야 해"). 기존 사전 파일이 이미 커서 따로 둔다.
 */
export type LiveScreen = {
  /** public/media/live/ 아래 파일명 */
  file: string;
  title: string;
  caption: string;
  /** live = 운영 실데이터 화면 · model = 모델 시나리오가 섞인 화면(그렇게 표기) */
  kind: 'live' | 'model';
};

export type DiseaseEntry = {
  slug: string;
  /** disease_params.DISEASE_PARAMS 의 키 — R0·CFR 은 거기서 가져온다 */
  paramKey: string;
  name: string;
  summary: string;
  watch: string[];
};

export type ExtraDict = {
  pages: {
    live: ContentPage;
    record: ContentPage;
    korea: ContentPage;
    security: ContentPage;
    press: ContentPage;
    pilot: ContentPage;
    developers: ContentPage;
    diseases: ContentPage;
  };
  live: {
    countersTitle: string;
    countersLead: string;
    counters: { predictions: string; alerts: string; extracted: string; sentinel: string; declarations: string; sources: string };
    countersNote: string;
    riskTitle: string;
    riskLead: string;
    riskUnavailable: string;
    riskOpen: string;
    screensTitle: string;
    screensLead: string;
    screens: LiveScreen[];
    kindLive: string;
    kindModel: string;
    sourcesTitle: string;
    sourcesLead: string;
    sourceOk: string;
    sourceIssue: string;
    sourceStale: string;
    updated: string;
    unavailable: string;
    alertsTitle: string;
    alertsLead: string;
    alertsEmpty: string;
    seeLive: string;
    seeRecord: string;
  };
  record: {
    scoreTitle: string;
    scoreLead: string;
    scoreLabels: { total: string; resolved: string; hit: string; miss: string; open: string; overdue: string; brier: string; legacy: string };
    scoreNote: string;
    listTitle: string;
    listLead: string;
    colMade: string;
    colTarget: string;
    colClaim: string;
    colStatus: string;
    colProof: string;
    statusHit: string;
    statusMiss: string;
    statusOpen: string;
    statusOther: string;
    proofSealed: string;
    proofNone: string;
    ledgerTitle: string;
    ledgerLead: string;
    ledgerEmpty: string;
    anatomyTitle: string;
    anatomyLead: string;
    anatomyFields: { level: string; score: string; source: string; country: string; disease: string; reason: string; time: string };
    anatomyEmpty: string;
    empty: string;
  };
  apiTags: Record<string, string>;
  api: { colMethod: string; colPath: string; colAuth: string; authYes: string; authNo: string; tableTitle: string; tableLead: string };
  diseases: DiseaseEntry[];
  disease: { r0: string; cfr: string; paramSource: string; paramNote: string; watchTitle: string; back: string; openDashboard: string };
};

export type Dictionary = {
  nav: NavDict;
  footer: FooterDict;
  home: HomeDict;
  pages: PagesDict;
  extra: ExtraDict;
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
/** 묶음 색 — globals.css 의 [data-tone] 과 짝. 엔진 묶음·페이지 구획을 색으로 가른다. */
export type BlockTone = 'teal' | 'indigo' | 'amber' | 'crimson' | 'forest' | 'violet' | 'sky';

export type PageBlock = {
  title: string;
  /** 제목 위 작은 꼬리표(예: "GROUP 01 · 감시"). tone 색으로 그린다. */
  kicker?: string;
  tone?: BlockTone;
  /** 깊은 남청색 띠로 그릴지 — 스페셜 프로그램처럼 무게를 줄 구획. */
  deep?: boolean;
  body?: string;
  /** 사양표 — 왼쪽 항목 · 오른쪽 값. */
  specs?: { label: string; value: string }[];
  /** 카드 목록. 있으면 격자로 렌더링한다. */
  items?: { title: string; body: string; meta?: string }[];
  /** 블록 안 사진(선택). */
  photo?: PhotoDict;
  /** 번호 매긴 목록. **강조** 표기를 지원한다. */
  points?: string[];
  /** 블록 하단 각주 — 한계·출처를 남길 때 쓴다. */
  note?: string;
  /** 강조 카드로 그릴지(정직성 블록 등). */
  accent?: boolean;
};

/**
 * 사진 한 장. 전부 퍼블릭 도메인이지만 저작자·원본 링크를 캡션에 남긴다.
 * src·credit·sourceUrl 은 언어와 무관하고, alt·caption 만 언어별로 쓴다.
 */
export type PhotoDict = {
  src: string;
  alt: string;
  /** 무엇을 찍은 사진인지 — 우리 시설·장비로 오해되지 않게 쓴다. */
  caption: string;
  /** 예: "NASA · 퍼블릭 도메인" */
  credit: string;
  sourceUrl: string;
  /** object-position. 피사체가 가장자리에 있을 때만 지정. */
  position?: string;
};

export type ContentPage = {
  metaTitle: string;
  metaDescription: string;
  eyebrow: string;
  title: string;
  lead: string;
  /** 제목 아래 사진(선택). */
  photo?: PhotoDict;
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
  techSpec1: ContentPage;
  techSpec2: ContentPage;
  engines: ContentPage;
  programs: ContentPage;
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
