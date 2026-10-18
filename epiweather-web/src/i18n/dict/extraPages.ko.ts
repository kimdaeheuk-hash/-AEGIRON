import type { ExtraDict } from '../types';

/**
 * 실가동·검증·국가사업 페이지 본문(한국어).
 *
 * ★ 수치는 실측만 ★ 엔드포인트 123개 중 인증 필요 37개(main.py 실측), 질병 파라미터는
 * disease_params.DISEASE_PARAMS 의 문헌값. 고객·인증·계약 실적처럼 없는 것은 쓰지 않는다.
 */
export const extraPagesKo: ExtraDict['pages'] = {
  live: {
    metaTitle: '실가동 — 아이기론이 지금 하고 있는 일',
    metaDescription: '아이기론 운영 화면 캡처와 실시간 운영 수치. 지금 무엇을 수집하고, 어디를 보고 있으며, 무엇을 경보로 올렸는지 그대로 보여 줍니다.',
    eyebrow: 'LIVE OPERATIONS',
    title: '아이기론은 지금 이렇게 돌고 있습니다',
    lead: '설명이 아니라 실제 운영 화면과 운영 수치입니다. 아래 숫자와 목록은 운영 서버에서 몇 분마다 새로 읽어 오고, 사진은 운영 중인 대시보드를 그대로 캡처한 것입니다.',
    blocks: [],
    cta: {
      title: '같은 화면을 지금 직접 여십시오',
      body: '로그인 없이 운영 대시보드가 열립니다. 위 사진과 같은 화면이 실시간으로 갱신됩니다.',
      label: '라이브 대시보드 열기',
      href: '/dashboard',
    },
  },

  record: {
    metaTitle: '공개 예측 원장 — 봉인된 예측과 채점 결과',
    metaDescription: '아이기론이 남긴 예측을 생성 시점 그대로 공개합니다. 블록체인 시점 증명, 공식 선언과의 자동 채점 결과, 선행성 원장까지 실데이터로 보여 줍니다.',
    eyebrow: 'TRACK RECORD',
    title: '공개 예측 원장',
    lead: '조기경보의 신뢰는 주장에서 나오지 않습니다. 아이기론은 예측을 만드는 순간 봉인하고, 이후 나온 공식 선언과 매일 자동으로 대조해 채점합니다. 적중도 실패도 판정 보류도 지우지 않고 그대로 이 원장에 남습니다.',
    blocks: [],
    cta: {
      title: '채점 방식이 궁금하시다면',
      body: '무엇을 정답으로 보고, 무엇을 정답으로 쓰지 않는지는 검증 체계 페이지에 정리돼 있습니다.',
      label: '검증 체계 보기',
      href: 'transparency',
    },
  },

  korea: {
    metaTitle: '대한민국을 위한 아이기론 — 유입 대비국의 조기경보',
    metaDescription: '해외 발병의 국내 유입 시점과 입국 관문별 위험, 국내 법정감염병 감시, 대응제 생산 주권, 국가 조달 감시, 데이터 주권 — 대한민국 관점에서 본 아이기론.',
    eyebrow: 'FOR KOREA',
    title: '대한민국을 위한 아이기론',
    lead: '한국은 대부분의 신종 감염병에서 발생국이 아니라 유입 대비국입니다. 그래서 질문은 "어디서 났나"보다 "언제, 어느 관문으로 들어오고, 우리는 무엇으로 막을 수 있나"입니다. 아이기론은 이 질문에 맞춰 설계됐습니다.',
    photo: {
      src: '/media/live/model-global-inflow.jpg',
      alt: '아이기론 대시보드의 글로벌 유입 감지 화면 — 발원지에서 한국까지의 항공망 지도',
      caption: '운영 대시보드의 글로벌 유입 감지 화면(캡처). 발원지에서 한국 도착 시점과 관문을 추정합니다. 화면의 수치는 선택한 가정에 따른 모델 시나리오입니다.',
      credit: 'AEGIRON 운영 화면',
      sourceUrl: '/dashboard',
    },
    blocks: [
      {
        title: '해외 발병 → 국내 유입',
        kicker: 'INBOUND',
        tone: 'indigo',
        body: '발원 도시의 국제선 여객량·비행시간·초기 성장률로 국내 첫 유입까지의 일수를 추정하고, 인천·김해·김포 등 입국 관문별 위험을 나눠 봅니다. 그 뒤 국내 이동망 위에서 지역별 도착 시점까지 이어서 계산합니다.',
        specs: [
          { label: '국내 첫 유입', value: '발원지별 D+일수 추정(모델 시나리오)' },
          { label: '입국 관문', value: '인천 · 김해(부산) · 김포 등 관문별 유입 비중' },
          { label: '국내 확산', value: '시·도 단위 도착 시점 추정(메타개체군 모델)' },
          { label: '전 세계 맥락', value: '159개국 · 항공 1,671쌍 · 육로 314개 확산 트윈' },
        ],
      },
      {
        title: '국내 감시',
        kicker: 'DOMESTIC',
        tone: 'teal',
        items: [
          { title: '법정감염병 질병별 급증', body: '질병관리청 주간 신고를 질병마다 따로 보고, 총합에 묻히는 개별 질병의 급증을 잡아냅니다.', meta: 'kdca_anomaly' },
          { title: '국내 검색 신호', body: '네이버 데이터랩으로 독감·코로나·에볼라 등 국내 관심도 변화를 봅니다.', meta: 'naver_trends' },
          { title: '한국어 일일 브리핑', body: '매일 국내외 상황을 한국어 브리핑으로 자동 정리합니다.', meta: 'daily_brief' },
        ],
      },
      {
        title: '대응제 생산 주권 (VALHALLA)',
        kicker: 'SOVEREIGNTY',
        tone: 'forest',
        body: '위협마다 막을 수단이 있는지, 그리고 그 수단을 국내에서 만들 수 있는지를 공개 자료로 셉니다. 공급원이 해외 한 곳뿐인 품목은 위기 때 비축을 다시 채울 수 없는 병목입니다.',
        points: [
          '국제 비상 비축·규제 승인 제품으로 위협별 커버리지를 계산합니다.',
          'WHO 사전적격성 목록으로 품목별 생산 가능 공급원 수를 셉니다.',
          'ClinicalTrials.gov로 "아직 개발 중"을 임상 단계까지 나눕니다.',
        ],
      },
      {
        title: '국가 조달 감시',
        kicker: 'PROCUREMENT',
        tone: 'amber',
        body: '나라장터 입찰공고에서 바이오안보·감염병 대응 관련 구매 움직임을 매일 추적합니다. 정부가 지금 무엇을 준비하는지는 공고로 먼저 드러납니다.',
      },
      {
        title: '데이터 주권',
        kicker: 'DATA SOVEREIGNTY',
        tone: 'violet',
        body: '신호 추출 경로를 한 곳에서 바꿔 자체 호스팅 모델로 전환할 수 있게 설계했습니다. 민감한 데이터가 해외 API로 나가지 않는 운영이 가능한 구조입니다. 자세한 내용은 보안·데이터 거버넌스 페이지에 정리했습니다.',
      },
    ],
    cta: {
      title: '공공기관 도입은 이렇게 진행됩니다',
      body: '사전 검토부터 범위 설계, 파일럿 운영, 공동 채점까지의 절차를 정리해 두었습니다.',
      label: '도입 방식 보기',
      href: 'pilot',
    },
  },

  security: {
    metaTitle: '보안과 데이터 거버넌스',
    metaDescription: '아이기론의 접근 통제, 고위험 프로그램 감사, 개인정보 원칙, 데이터 주권 경로, 비밀 관리, 운영 무결성을 설명합니다.',
    eyebrow: 'SECURITY & GOVERNANCE',
    title: '보안과 데이터 거버넌스',
    lead: '감염병 인텔리전스는 공공의 안전과 맞닿아 있습니다. 누가 무엇을 바꿀 수 있는지, 민감한 기능은 어떻게 통제되는지, 데이터는 어디로 가는지를 코드에 구현된 그대로 설명합니다.',
    blocks: [
      {
        title: '접근 통제',
        kicker: 'ACCESS CONTROL',
        tone: 'indigo',
        specs: [
          { label: '전체 API', value: '엔드포인트 123개' },
          { label: '인증 필요', value: '37개 — 상태 변경 · 고비용 · 고위험 기능' },
          { label: '인증 방식', value: 'X-API-Key 헤더 · 다중 키(라벨별) · 상수 시간 비교' },
          { label: '키 미설정 시', value: '쓰기 API 전체 비활성(열린 채로 두지 않음)' },
        ],
        note: '읽기 API는 공개 자료를 가공한 결과라 공개합니다. 데이터를 바꾸거나 비용이 드는 호출은 모두 키가 있어야 합니다.',
      },
      {
        title: '고위험 프로그램 통제',
        kicker: 'HEIMDALL · VALHALLA',
        tone: 'violet',
        points: [
          '사내 최고 보안등급 프로그램(HEIMDALL 등)은 인증 필수이며, 모든 호출이 키 라벨별 감사 로그에 남습니다.',
          'HEIMDALL은 **방어적 탐지 전용**입니다. 서열 설계·합성·최적화·회피 기능은 없습니다.',
          '결과의 대외 공개·재배포는 담당 승인 대상으로 응답에 명시됩니다.',
        ],
      },
      {
        title: '개인정보 원칙',
        kicker: 'PRIVACY',
        tone: 'teal',
        points: [
          '수집 대상은 보건당국 보고·언론 보도·공개 통계 같은 공개 자료입니다. 개인 환자 정보를 다루지 않습니다.',
          '웹사이트와 대시보드는 로그인·광고·방문 추적 도구 없이 운영됩니다.',
        ],
      },
      {
        title: '데이터 주권',
        kicker: 'SOVEREIGNTY',
        tone: 'forest',
        body: '신호 추출을 담당하는 모델 계층은 한 곳에서 제공자를 바꾸도록 설계돼, 자체 호스팅(온프레미스 포함) 모델로 전환할 수 있습니다. 국가 기관이 민감 데이터를 외부 API로 보내지 않고 운영하는 구성이 가능합니다.',
      },
      {
        title: '비밀 관리와 운영 무결성',
        kicker: 'INTEGRITY',
        tone: 'sky',
        items: [
          { title: '비밀 관리', body: 'API 키와 자격증명은 운영 환경 변수로만 두고 저장소·문서에 기록하지 않습니다.' },
          { title: '배포 관문', body: '자동 시험 2,145건을 모두 통과한 코드만 운영에 반영됩니다.' },
          { title: '조용한 실패 감시', body: '소스 건강·품질 불변식이 매 주기 수집과 계산의 무결성을 점검합니다.' },
          { title: '변조 방지', body: '예측 기록은 해시로 봉인해 비트코인 블록체인에 시점을 고정합니다.' },
        ],
      },
    ],
    cta: {
      title: '보안 심사 자료가 필요하십니까',
      body: '기관 보안 검토에 필요한 구성·통제 설명 자료를 요청하실 수 있습니다.',
      label: '문의하기',
      href: 'contact',
    },
  },

  press: {
    metaTitle: '미디어 키트',
    metaDescription: '아이기론을 소개할 때 쓸 수 있는 한 줄·한 문단 소개문, 핵심 사실, 소개 영상, 이미지 사용 안내.',
    eyebrow: 'PRESS',
    title: '미디어 키트',
    lead: '아이기론을 기사·발표·보고서에 소개하실 때 그대로 쓰실 수 있는 자료입니다. 수치는 모두 실측값이며, 정확도나 선행일수 주장은 담지 않았습니다.',
    blocks: [
      {
        title: '한 줄 소개',
        kicker: 'ONE-LINER',
        tone: 'teal',
        body: '아이기론(AEGIRON)은 178개국·52개 언어의 현지 보도와 각국 공식 감시 자료를 매시간 분석해, 감염병 이상 신호를 판정하고 확산·대응 시나리오까지 산출하는 대한민국 부산의 글로벌 감염병 조기경보 시스템입니다.',
      },
      {
        title: '한 문단 소개',
        kicker: 'BOILERPLATE',
        tone: 'indigo',
        body: '아이기론은 감염병이 국제 뉴스가 되기 전에 신호를 잡는 것을 목표로 합니다. 23종의 데이터 소스와 114개 알고리즘 모듈로 국가별 이상도를 판정하고, 경보가 서는 시점에 159개국 확산 시뮬레이션과 개입 시나리오를 함께 산출합니다. 모든 예측은 생성 시점에 블록체인으로 봉인하고 이후의 공식 선언과 자동 대조해 스스로 채점하며, 시스템·방법론·데이터·한계를 처음부터 공개합니다. 방어적 유전체 스크리닝(HEIMDALL)과 대응제 준비태세(VALHALLA) 두 R&D 프로그램이 국가 바이오안보 축을 맡습니다.',
      },
      {
        title: '핵심 사실',
        kicker: 'FACT SHEET',
        tone: 'sky',
        specs: [
          { label: '본사', value: '대한민국 부산' },
          { label: '감시 범위', value: '178개국 · 52개 언어 현지 보도' },
          { label: '데이터 소스', value: '23종 · 매시간 수집' },
          { label: '알고리즘 모듈', value: '114개' },
          { label: '공개 API', value: '엔드포인트 123개' },
          { label: '공개 범위', value: '시스템 · 방법론 · 데이터 소스 · 한계 · 예측 원장' },
        ],
        note: '2026-10-18 실측 기준. 인용 시 날짜를 함께 표기해 주십시오.',
      },
      {
        title: '영상과 이미지',
        kicker: 'ASSETS',
        tone: 'forest',
        items: [
          { title: '소개 영상', body: '홈 첫 화면의 아이기론 소개 영상(YouTube)을 링크로 사용하실 수 있습니다.', meta: 'youtu.be/2Uzl-5JgLjs' },
          { title: '운영 화면', body: '실가동 페이지의 대시보드 캡처는 출처(AEGIRON) 표기 후 사용하실 수 있습니다.', meta: '/live' },
          { title: '공개 사진', body: '사이트의 현장 사진은 각 저작자의 퍼블릭 도메인·자유 라이선스 자료입니다. 각 사진의 출처·라이선스를 따라 주십시오.', meta: '사진별 출처 표기' },
        ],
      },
    ],
    cta: {
      title: '취재·인터뷰 문의',
      body: '추가 자료나 인터뷰가 필요하시면 연락해 주십시오.',
      label: '문의하기',
      href: 'contact',
    },
  },

  pilot: {
    metaTitle: '도입 방식 — 검토에서 파일럿까지',
    metaDescription: '아이기론 도입은 공개 시스템 검토, 범위 설계, 파일럿 운영, 공동 채점, 확장의 다섯 단계로 진행됩니다.',
    eyebrow: 'HOW TO ENGAGE',
    title: '도입 방식',
    lead: '데모를 예약하지 않아도 시스템 전체를 먼저 검토하실 수 있습니다. 그 뒤의 파일럿은 고객 데이터 없이도 시작할 수 있도록 설계했습니다.',
    blocks: [
      {
        title: '다섯 단계',
        kicker: 'PROCESS',
        tone: 'indigo',
        items: [
          { title: '01 · 사전 검토', body: '공개된 대시보드·방법론·데이터 소스·예측 원장을 먼저 확인하십시오. 검토 자체에는 계약이 필요 없습니다.', meta: '기관 단독 진행' },
          { title: '02 · 범위 설계', body: '관심 국가·질병, 알림 채널(텔레그램·이메일), 납품물 형식, 평가 기준을 함께 정합니다.', meta: '공동 설계' },
          { title: '03 · 파일럿 운영', body: '합의한 기간 동안 맞춤 경보·브리핑·국가 위험 보고서를 받으며 실제 업무에 대 봅니다.', meta: '합의된 기간' },
          { title: '04 · 공동 채점', body: '파일럿 기간의 경보와 예측을 봉인 기록 그대로 공식 선언과 대조해 함께 평가합니다.', meta: '사후 수정 불가 기록' },
          { title: '05 · 확장', body: '평가 결과에 따라 범위·연동(API)·운영 형태를 넓힙니다.', meta: '평가 기반' },
        ],
      },
      {
        title: '받으시는 것',
        kicker: 'DELIVERABLES',
        tone: 'teal',
        points: [
          '맞춤 경보 — 관심 범위의 Critical·High 경보 실시간 전달',
          '국가 위험 보고서 — 신호 근거·취약성·확산 잠재력',
          '개입 시나리오 — 경보별 무대응 대비 개입 효과(모델 시나리오로 표기)',
          '일일 브리핑과 API 접근',
        ],
      },
      {
        title: '준비하실 것',
        kicker: 'WHAT YOU NEED',
        tone: 'forest',
        points: [
          '관심 국가·질병과 업무 목적',
          '담당 연락처와 알림 수신 채널',
          '고객 데이터는 필요하지 않습니다 — 공개 자료만으로 시작합니다.',
        ],
        note: '기간과 조건은 범위에 따라 협의합니다.',
      },
    ],
    cta: {
      title: '사전 검토부터 시작하십시오',
      body: '검토 후 질문이나 파일럿 제안이 있으시면 연락해 주십시오.',
      label: '문의하기',
      href: 'contact',
    },
  },

  developers: {
    metaTitle: '개발자 · API',
    metaDescription: '아이기론 REST API — 엔드포인트 123개, JSON 응답, X-API-Key 인증, OpenAPI 문서. 기관 시스템 연동을 위한 안내.',
    eyebrow: 'DEVELOPERS',
    title: '개발자 · API',
    lead: '대시보드가 보여 주는 모든 값은 같은 REST API에서 나옵니다. 기관 시스템에 경보·위험지수·브리핑을 직접 연동할 수 있습니다.',
    blocks: [
      {
        title: '기본 정보',
        kicker: 'BASICS',
        tone: 'sky',
        specs: [
          { label: '기본 주소', value: 'https://epiweather-api-production.up.railway.app' },
          { label: '형식', value: 'REST · JSON' },
          { label: '인증', value: '읽기 공개 · 쓰기/고위험 X-API-Key' },
          { label: '대화형 문서', value: '/docs (OpenAPI)' },
        ],
      },
      {
        title: '자주 쓰는 엔드포인트',
        kicker: 'QUICK START',
        tone: 'teal',
        items: [
          { title: '국가 위험 순위', body: '국가별 최종 위험도(원시 위험 × 취약성) 전체 순위.', meta: 'GET /api/risk-index' },
          { title: '경보', body: '등급·일일 상한을 적용한 현재 경보 후보.', meta: 'GET /api/alerts' },
          { title: '일일 브리핑', body: '언어별 일일 상황 브리핑.', meta: 'GET /api/daily-brief?lang=ko' },
          { title: '예측 원장', body: '봉인된 예측 목록과 채점표.', meta: 'GET /api/predictions · /scorecard' },
          { title: '시점 증명', body: '예측별 블록체인 시점 증명 상태.', meta: 'GET /api/predictions/{id}/timestamp-proof' },
          { title: '운영 상태', body: '소스 건강·데이터 규모·스케줄러 상태.', meta: 'GET /api/status' },
        ],
      },
    ],
    cta: {
      title: '연동 키가 필요하십니까',
      body: '쓰기·고위험 기능 연동에는 기관별 API 키를 발급합니다.',
      label: '문의하기',
      href: 'contact',
    },
  },

  diseases: {
    metaTitle: '질병별 감시',
    metaDescription: '아이기론이 감시하는 주요 감염병 — 조류인플루엔자 H5N1, 에볼라, 마버그, 엠폭스, 콜레라, 홍역, 메르스, 니파. 질병마다 무엇을 보고, 어떤 파라미터로 시뮬레이션하는지.',
    eyebrow: 'DISEASES',
    title: '질병별 감시',
    lead: '같은 경보 체계라도 질병마다 먼저 움직이는 신호가 다릅니다. 주요 감염병별로 아이기론이 무엇을 보고, 확산 시뮬레이션에 어떤 문헌 파라미터를 쓰는지 정리했습니다.',
    blocks: [],
    cta: {
      title: '지금 각 질병의 신호를 보십시오',
      body: '대시보드와 일일 브리핑에서 질병별 최신 신호를 확인할 수 있습니다.',
      label: '라이브 대시보드 열기',
      href: '/dashboard',
    },
  },
};
