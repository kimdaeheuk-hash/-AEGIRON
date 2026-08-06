import type { Dictionary } from '../types';
import { pagesKo } from './pages.ko';

/**
 * 한국어 사전 — 기준 언어. 문구를 추가할 때는 여기부터 쓰고 en·fr에 옮긴다.
 *
 * ★ 절대 규칙 ★ 정확도·선행일수 주장을 쓰지 않는다.
 * "며칠 먼저 감지", "정확도 N%", "N건 적중"은 **검증된 트랙레코드가 없으므로**
 * 쓸 수 없다(재보험사 실사에서 즉시 드러난다). 대신 실측 가능한 것만 쓴다:
 * 인프라 규모, 공개 범위, 그리고 우리가 모르는 것.
 */
export const ko: Dictionary = {
  pages: pagesKo,

  briefings: {
    archiveTitle: '지난 브리핑',
    count: '{n}건',
    quietDay: '조용한 날',
    openBrief: '읽기',
    empty: '아직 보관된 브리핑이 없습니다.',
    error: '브리핑을 불러오지 못했습니다. 시스템은 계속 가동 중입니다.',
    backToList: '브리핑 목록',
    summary: '요약',
    segments: '꼭지',
    ticker: '한 줄 속보',
    disclosure: '고지',
    notFound: '해당 날짜의 브리핑이 없습니다.',
    langNoticeTitle: '언어 안내',
    langNoticeFrench:
      '브리핑 생성은 아직 한국어와 영어만 지원합니다. 아래 내용은 영어판입니다 — 프랑스어인 척하지 않기 위해 그대로 밝힙니다.',
    langNoticeEnglish:
      '영어 브리핑은 자동 생성이라 병명·지명 일부가 한국어로 남아 있을 수 있습니다.',
  },

  common: {
    siteName: 'AEGIRON',
    siteTagline: '감염병 조기경보 인텔리전스',
    readMore: '자세히 보기',
    backToHome: '홈으로',
    lastUpdated: '마지막 갱신',
    liveNow: '실시간 가동 중',
  },

  nav: {
    platform: '시스템',
    methodology: '방법론',
    transparency: '우리가 모르는 것',
    dataSources: '데이터 소스',
    solutions: '활용',
    briefings: '브리핑',
    about: '회사',
    contact: '문의',
    dashboard: '라이브 대시보드',
    openMenu: '메뉴 열기',
    closeMenu: '메뉴 닫기',
    language: '언어',
  },

  footer: {
    tagline: '감염병이 국제 뉴스가 되기 전에.',
    product: '제품',
    company: '회사',
    legal: '법적 고지',
    privacy: '개인정보처리방침',
    terms: '이용약관',
    rights: 'All rights reserved.',
    location: '대한민국 부산',
    disclaimer:
      '아이기론은 조기감지 정확도에 대한 검증된 트랙레코드를 아직 보유하지 않았습니다. 이 사이트의 모든 수치는 시스템 규모에 대한 실측값이며, 예측 성능에 대한 주장이 아닙니다.',
  },

  home: {
    metaTitle: 'AEGIRON — 감염병 조기경보 시스템 | 지금 작동하는 것을 그대로 공개합니다',
    metaDescription:
      '21개 실시간 데이터 소스로 감염병 신호를 감시하는 조기경보 시스템. 라이브 대시보드·전체 방법론·데이터 소스를 로그인 없이 공개하고, 아직 검증되지 않은 것도 함께 밝힙니다.',

    heroEyebrow: '완전 공개 · 로그인 없음',
    heroTitle: '지금 이 순간 작동하는 것을\n그대로 보여드립니다',
    heroLead:
      '대부분의 감염병 인텔리전스는 영업 미팅 뒤에 있습니다. 아이기론은 실시간 시스템도, 방법론도, 데이터 소스도, 우리가 아직 모르는 것도 전부 공개합니다. 판단은 보시고 하십시오.',
    heroPrimaryCta: '라이브 대시보드 열기',
    heroSecondaryCta: '시스템 구조 보기',
    heroNoLogin: '가입·로그인 없이 바로 열립니다',

    stats: [
      { value: '21', label: '실시간 데이터 소스', note: 'WHO · CDC · 현지어 뉴스 · 기후 · 위성' },
      { value: '106', label: 'API 엔드포인트', note: '수집 · 분석 · 예측 · 시뮬레이션' },
      { value: '217', label: '국가 참조 데이터', note: 'World Bank 기반 취약성 지수' },
      { value: '740', label: '자동 검증 테스트', note: '전부 통과 · 매 변경마다 재실행' },
    ],

    openTitle: '우리가 공개하는 것',
    openLead:
      '감염병 감시에서 가장 흔한 실패는 틀린 예측이 아니라 검증할 수 없는 예측입니다. 그래서 검증에 필요한 것을 전부 열어둡니다.',
    openItems: [
      {
        title: '실시간 시스템',
        body: '지금 돌아가는 대시보드를 그대로 봅니다. 시연용 화면이 아니라 실제로 신호를 받고 있는 운영 시스템입니다.',
        href: '/dashboard',
        linkLabel: '대시보드 열기',
      },
      {
        title: '전체 방법론',
        body: '신호를 어떻게 모으고, 어떤 기준으로 이상을 판정하고, 예측을 어떻게 만드는지 4개 층으로 나누어 설명합니다.',
        href: '/methodology',
        linkLabel: '방법론 보기',
      },
      {
        title: '데이터 소스 전부',
        body: '21개 소스를 하나도 숨기지 않고 나열합니다. 무엇이 잘 들어오고 무엇이 막혀 있는지도 함께 적습니다.',
        href: '/data-sources',
        linkLabel: '소스 목록 보기',
      },
      {
        title: '우리가 모르는 것',
        body: '검증되지 않은 부분, 알려진 한계, 아직 못 채운 데이터 공백. 경쟁사 사이트에는 없는 페이지입니다.',
        href: '/transparency',
        linkLabel: '한계 읽기',
      },
    ],

    honestTitle: '아직 검증되지 않은 것',
    honestLead:
      '이 문단을 홈페이지에 두는 회사는 드뭅니다. 그런데 이걸 먼저 말하지 않으면, 실사에서 대신 드러납니다.',
    honestPoints: [
      '조기감지 정확도에 대한 **검증된 트랙레코드가 없습니다.** "며칠 먼저 감지했다"는 주장을 이 사이트 어디에도 쓰지 않는 이유입니다.',
      '시스템이 본격 가동된 것은 2026년입니다. 그 이전 발병에 대한 성적은 사후 재구성이라 실시간 성능과 같지 않습니다.',
      '예측 모듈의 시나리오 숫자는 **모델 가정 하의 추정**입니다. 실측값도, 보장도 아닙니다.',
      '데이터 수집에 공백이 있습니다. 어느 나라 어느 기간이 비었는지 시스템이 스스로 보고합니다.',
    ],
    honestClose:
      '대신 이렇게 합니다 — 모델이 낸 숫자를 역사상 최대 발병과 자동으로 대조해, 설명 가능한 범위를 넘으면 시스템이 **스스로 경고를 붙여** 내보냅니다. 놓친 발병이 있으면 "모델이 못 잡은 것"과 "데이터가 없어서 못 잡은 것"을 나누어 보고합니다.',
    honestCta: '한계를 전부 읽어보기',

    pipelineTitle: '신호가 경보가 되기까지',
    pipelineLead: '다섯 단계를 거칩니다. 각 단계에서 무엇을 버리는지가 무엇을 취하는지만큼 중요합니다.',
    pipelineSteps: [
      {
        step: '01',
        title: '수집',
        body: 'WHO 상황보고서·CDC 여행경보·179개국 현지어 뉴스·기후·위성·무역 통계를 자동 수집합니다.',
      },
      {
        step: '02',
        title: '추출',
        body: 'PDF 표와 기사 본문에서 질병·국가·확진·사망을 구조화합니다. 못 알아본 항목은 추측하지 않고 비웁니다.',
      },
      {
        step: '03',
        title: '판정',
        body: '국가별 평소 수준과 대비해 이상도를 계산합니다. 절대량이 아니라 그 나라 기준선 대비로 봅니다.',
      },
      {
        step: '04',
        title: '예측',
        body: '전파 모델로 확산 경로와 유입 위험을 추정합니다. 모든 값에 가정과 한계를 함께 붙입니다.',
      },
      {
        step: '05',
        title: '대응',
        body: '무대응 시나리오와 개입 시나리오를 비교해 "그래서 무엇을 하라"까지 답합니다.',
      },
    ],

    briefTitle: '오늘의 브리핑',
    briefLead: '매일 자동 생성됩니다. 조용한 날에는 조용하다고 씁니다.',
    briefCta: '지난 브리핑 보기',
    briefEmpty: '오늘 브리핑이 아직 생성되지 않았습니다.',
    briefError: '브리핑을 불러오지 못했습니다. 시스템은 계속 가동 중입니다.',

    audienceTitle: '누구를 위한 것인가',
    audienceLead: '같은 신호도 보는 사람에 따라 필요한 형태가 다릅니다.',
    audiences: [
      {
        title: '재보험 · 보험',
        body: '국가별 노출 지수와 포트폴리오 비교. 절대 확률이 아니라 상대 지표임을 응답에 항상 명시합니다.',
        href: '/solutions/reinsurance',
      },
      {
        title: '정부 · 공공보건',
        body: '유입 경로 추적과 개입 시나리오 비교. 방어 조치별 효과를 모델로 대조합니다.',
        href: '/solutions/government',
      },
      {
        title: '국제기구 · 인도지원',
        body: '감시가 약한 지역의 조기 신호. 상업성이 낮아 다른 곳이 잘 보지 않는 국가를 포함합니다.',
        href: '/solutions/ngo',
      },
    ],

    ctaTitle: '먼저 보시고, 그다음에 이야기하시죠',
    ctaBody:
      '데모를 예약하지 않아도 시스템 전체를 볼 수 있습니다. 보신 뒤에 물어보실 게 생기면 그때 연락 주십시오.',
    ctaButton: '문의하기',
  },
};
