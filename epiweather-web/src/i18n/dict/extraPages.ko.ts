import type { ExtraDict } from '../types';

/**
 * 실가동·검증·국가사업 페이지 본문(한국어).
 *
 * ★ 수치는 실측만 ★ 엔드포인트 123개 중 인증 필요 37개(main.py 실측), 질병 파라미터는
 * disease_params.DISEASE_PARAMS 의 문헌값. 고객·인증·계약 실적처럼 없는 것은 쓰지 않는다.
 */
export const extraPagesKo: ExtraDict['pages'] = {
  live: {
    metaTitle: '실가동 — 아이기론 실시간 운영 현황',
    metaDescription: '운영 대시보드 화면과 실시간 운영 수치 — 수집 현황, 감시 대상 국가, 경보 후보.',
    eyebrow: 'LIVE OPERATIONS',
    title: '지금 이 순간에도, 아이기론은 세계를 감시하고 있습니다',
    lead: '소개 자료가 아닌 실제 운영 현황 · 운영 서버 수치 수 분 간격 갱신 · 가동 중인 대시보드 화면 그대로',
    blocks: [],
    cta: {
      title: '같은 화면 직접 확인',
      body: '로그인 없이 운영 대시보드 접속 · 실시간 갱신',
      label: '라이브 대시보드 열기',
      href: '/dashboard',
    },
  },

  record: {
    metaTitle: '공개 예측 원장 — 봉인된 예측과 채점 결과',
    metaDescription: '생성 시점 그대로의 예측 공개 — 블록체인 시점 증명, 공식 선언 자동 채점, 선행성 원장.',
    eyebrow: 'TRACK RECORD',
    title: '공개 예측 원장',
    lead: '예측 생성 즉시 봉인 · 공식 선언과 매일 자동 대조 채점 · 적중·실패·판정 보류 전부 원장에 보존',
    blocks: [],
    cta: {
      title: '채점 기준 확인',
      body: '정답으로 인정하는 자료와 인정하지 않는 자료 — 검증 체계 페이지 정리',
      label: '검증 체계 보기',
      href: 'transparency',
    },
  },

  korea: {
    metaTitle: '대한민국을 위한 아이기론 — 유입 대비국의 조기경보',
    metaDescription: '해외 발병 국내 유입 시점·관문별 위험, 법정감염병 감시, 대응제 생산 주권, 국가 조달 감시, 데이터 주권.',
    eyebrow: 'FOR KOREA',
    title: '대한민국을 위한 아이기론',
    lead: '신종 감염병에서 한국은 발생국이 아닌 유입 대비국 · 핵심 질문은 "언제, 어느 관문으로, 무엇으로 막는가" · 이 질문 중심 설계',
    photo: {
      src: '/media/live/model-global-inflow.jpg',
      alt: '아이기론 대시보드의 글로벌 유입 감지 화면 — 발원지에서 한국까지의 항공망 지도',
      caption: '운영 대시보드 글로벌 유입 감지 화면(캡처) — 발원지에서 한국 도착 시점·관문 추정 · 수치는 선택 가정 기반 모델 시나리오',
      credit: 'AEGIRON 운영 화면',
      sourceUrl: '/dashboard',
    },
    blocks: [
      {
        title: '해외 발병 → 국내 유입',
        kicker: 'INBOUND',
        tone: 'indigo',
        body: '발원 도시 국제선 여객량·비행시간·초기 성장률 기반 국내 첫 유입 일수 추정 · 인천·김해·김포 등 관문별 위험 분리 · 국내 이동망 위 지역별 도착 시점까지 연속 계산',
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
          { title: '법정감염병 질병별 급증', body: '질병관리청 주간 신고 질병별 분리 분석 — 총합에 묻히는 개별 급증 포착', meta: 'kdca_anomaly' },
          { title: '국내 검색 신호', body: '네이버 데이터랩 — 독감·코로나·에볼라 등 국내 관심도 변화', meta: 'naver_trends' },
          { title: '한국어 일일 브리핑', body: '국내외 상황 한국어 브리핑 매일 자동 생성', meta: 'daily_brief' },
        ],
      },
      {
        title: '대응제 생산 주권 (VALHALLA)',
        kicker: 'SOVEREIGNTY',
        tone: 'forest',
        body: '위협별 대응 수단 존재 여부와 국내 생산 가능 여부를 공개 자료로 집계 · 해외 단일 공급원 품목 = 위기 시 비축 재보충 불가 병목',
        points: [
          '국제 비상 비축·규제 승인 제품 기반 위협별 커버리지',
          'WHO 사전적격성 목록 기반 품목별 생산 가능 공급원 수',
          'ClinicalTrials.gov 기반 개발 단계(임상 단계) 구분',
        ],
      },
      {
        title: '국가 조달 감시',
        kicker: 'PROCUREMENT',
        tone: 'amber',
        body: '나라장터 입찰공고 매일 추적 — 바이오안보·감염병 대응 구매 동향 · 정부 대비 행동의 선행 신호',
      },
      {
        title: '데이터 주권',
        kicker: 'DATA SOVEREIGNTY',
        tone: 'violet',
        body: '신호 추출 경로 단일 지점 전환 설계 — 자체 호스팅 모델 운영 가능 · 민감 데이터 해외 API 미반출 구조 · 상세: 보안·데이터 거버넌스',
      },
    ],
    cta: {
      title: '공공기관 도입 절차',
      body: '사전 검토 → 범위 설계 → 파일럿 운영 → 공동 채점',
      label: '도입 방식 보기',
      href: 'pilot',
    },
  },

  security: {
    metaTitle: '보안과 데이터 거버넌스',
    metaDescription: '접근 통제, 고위험 프로그램 감사, 개인정보 원칙, 데이터 주권 경로, 비밀 관리, 운영 무결성.',
    eyebrow: 'SECURITY & GOVERNANCE',
    title: '보안과 데이터 거버넌스',
    lead: '변경 권한 · 민감 기능 통제 · 데이터 이동 경로 — 코드 구현 그대로 공개',
    blocks: [
      {
        title: '접근 통제',
        kicker: 'ACCESS CONTROL',
        tone: 'indigo',
        specs: [
          { label: '전체 API', value: '엔드포인트 123개' },
          { label: '인증 필요', value: '37개 — 상태 변경 · 고비용 · 고위험 기능' },
          { label: '인증 방식', value: 'X-API-Key 헤더 · 다중 키(라벨별) · 상수 시간 비교' },
          { label: '키 미설정 시', value: '쓰기 API 전체 비활성(열린 상태 방치 없음)' },
        ],
        note: '읽기 API — 공개 자료 가공 결과로 공개 · 데이터 변경·비용 발생 호출 — 전부 키 필수',
      },
      {
        title: '고위험 프로그램 통제',
        kicker: 'HEIMDALL · VALHALLA',
        tone: 'violet',
        points: [
          '사내 최고 보안등급 프로그램(HEIMDALL 등) 인증 필수 · 전 호출 키 라벨별 감사 로그 기록',
          'HEIMDALL — **방어적 탐지 전용** · 서열 설계·합성·최적화·회피 기능 없음',
          '결과의 대외 공개·재배포 — 담당 승인 대상, 응답에 명시',
        ],
      },
      {
        title: '개인정보 원칙',
        kicker: 'PRIVACY',
        tone: 'teal',
        points: [
          '수집 대상 — 보건당국 보고·언론 보도·공개 통계 등 공개 자료 · 개인 환자 정보 미취급',
          '웹사이트·대시보드 — 로그인·광고·방문 추적 도구 없음',
        ],
      },
      {
        title: '데이터 주권',
        kicker: 'SOVEREIGNTY',
        tone: 'forest',
        body: '신호 추출 모델 계층 — 단일 지점 제공자 전환 설계 · 자체 호스팅(온프레미스 포함) 모델 전환 가능 · 국가 기관의 민감 데이터 외부 API 미전송 운영 구성 가능',
      },
      {
        title: '비밀 관리와 운영 무결성',
        kicker: 'INTEGRITY',
        tone: 'sky',
        items: [
          { title: '비밀 관리', body: 'API 키·자격증명 운영 환경 변수 전용 · 저장소·문서 기록 금지' },
          { title: '배포 관문', body: '자동 시험 2,145건 전부 통과 코드만 운영 반영' },
          { title: '조용한 실패 감시', body: '소스 건강·품질 불변식 — 매 주기 수집·계산 무결성 점검' },
          { title: '변조 방지', body: '예측 기록 해시 봉인 · 비트코인 블록체인 시점 고정' },
        ],
      },
    ],
    cta: {
      title: '보안 심사 자료 요청',
      body: '기관 보안 검토용 구성·통제 설명 자료 제공',
      label: '문의하기',
      href: 'contact',
    },
  },

  press: {
    metaTitle: '미디어 키트',
    metaDescription: '아이기론 한 줄·한 문단 소개문, 핵심 사실, 소개 영상, 이미지 사용 안내.',
    eyebrow: 'PRESS',
    title: '미디어 키트',
    lead: '기사·발표·보고서용 소개 자료 · 전 수치 실측값 · 정확도·선행일수 주장 미포함',
    blocks: [
      {
        title: '한 줄 소개',
        kicker: 'ONE-LINER',
        tone: 'teal',
        body: '아이기론(AEGIRON) — 178개국·52개 언어 현지 보도와 각국 공식 감시 자료를 매시간 분석해 감염병 이상 신호를 판정하고 확산·대응 시나리오까지 산출하는 대한민국 부산의 글로벌 감염병 조기경보 시스템',
      },
      {
        title: '한 문단 소개',
        kicker: 'BOILERPLATE',
        tone: 'indigo',
        body: '감염병이 국제 뉴스가 되기 전 신호 포착을 목표로 하는 조기경보 시스템. 23종 데이터 소스·114개 알고리즘 모듈로 국가별 이상도 판정, 경보 시점에 159개국 확산 시뮬레이션·개입 시나리오 동시 산출. 전 예측 생성 시점 블록체인 봉인 및 공식 선언 자동 대조 채점, 시스템·방법론·데이터·한계 전면 공개. 방어적 유전체 스크리닝(HEIMDALL)·대응제 준비태세(VALHALLA) 두 R&D 프로그램으로 국가 바이오안보 축 담당.',
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
        note: '2026-10-18 실측 기준 · 인용 시 날짜 병기',
      },
      {
        title: '영상과 이미지',
        kicker: 'ASSETS',
        tone: 'forest',
        items: [
          { title: '소개 영상', body: '홈 첫 화면 아이기론 소개 영상(YouTube) 링크 사용 가능', meta: 'youtu.be/2Uzl-5JgLjs' },
          { title: '운영 화면', body: '실가동 페이지 대시보드 캡처 — 출처(AEGIRON) 표기 후 사용 가능', meta: '/live' },
          { title: '공개 사진', body: '사이트 현장 사진 — 각 저작자의 퍼블릭 도메인·자유 라이선스 자료 · 사진별 출처·라이선스 준수', meta: '사진별 출처 표기' },
        ],
      },
    ],
    cta: {
      title: '취재·인터뷰 문의',
      body: '추가 자료·인터뷰 요청 접수',
      label: '문의하기',
      href: 'contact',
    },
  },

  pilot: {
    metaTitle: '도입 방식 — 검토에서 파일럿까지',
    metaDescription: '아이기론 도입 5단계 — 공개 시스템 검토, 범위 설계, 파일럿 운영, 공동 채점, 확장.',
    eyebrow: 'HOW TO ENGAGE',
    title: '도입 방식',
    lead: '데모 예약 없이 시스템 전체 사전 검토 가능 · 고객 데이터 없이 파일럿 착수',
    blocks: [
      {
        title: '도입 5단계',
        kicker: 'PROCESS',
        tone: 'indigo',
        items: [
          { title: '01 · 사전 검토', body: '공개 대시보드·방법론·데이터 소스·예측 원장 확인 — 계약 불필요', meta: '기관 단독 진행' },
          { title: '02 · 범위 설계', body: '관심 국가·질병, 알림 채널(텔레그램·이메일), 산출물 형식, 평가 기준 공동 확정', meta: '공동 설계' },
          { title: '03 · 파일럿 운영', body: '합의 기간 동안 맞춤 경보·브리핑·국가 위험 보고서 실무 적용', meta: '합의된 기간' },
          { title: '04 · 공동 채점', body: '파일럿 기간 경보·예측을 봉인 기록 그대로 공식 선언과 대조 평가', meta: '사후 수정 불가 기록' },
          { title: '05 · 확장', body: '평가 결과 기반 범위·API 연동·운영 형태 확대', meta: '평가 기반' },
        ],
      },
      {
        title: '제공 산출물',
        kicker: 'DELIVERABLES',
        tone: 'teal',
        points: [
          '맞춤 경보 — 관심 범위의 Critical·High 경보 실시간 전달',
          '국가 위험 보고서 — 신호 근거·취약성·확산 잠재력',
          '개입 시나리오 — 경보별 무대응 대비 개입 효과(모델 시나리오 표기)',
          '일일 브리핑 · API 접근',
        ],
      },
      {
        title: '도입 준비 사항',
        kicker: 'REQUIREMENTS',
        tone: 'forest',
        points: [
          '관심 국가·질병 및 업무 목적',
          '담당 연락처 · 알림 수신 채널',
          '고객 데이터 불필요 — 공개 자료만으로 착수',
        ],
        note: '기간·조건은 범위에 따라 협의',
      },
    ],
    cta: {
      title: '사전 검토부터 시작',
      body: '검토 후 질문·파일럿 제안 접수',
      label: '문의하기',
      href: 'contact',
    },
  },

  developers: {
    metaTitle: '개발자 · API',
    metaDescription: '아이기론 REST API — 엔드포인트 123개, JSON 응답, X-API-Key 인증, OpenAPI 문서. 기관 시스템 연동 안내.',
    eyebrow: 'DEVELOPERS',
    title: '개발자 · API',
    lead: '대시보드 전 수치의 단일 출처 = REST API · 경보·위험지수·브리핑 기관 시스템 직접 연동 가능',
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
        title: '주요 엔드포인트',
        kicker: 'QUICK START',
        tone: 'teal',
        items: [
          { title: '국가 위험 순위', body: '국가별 최종 위험도(원시 위험 × 취약성) 전체 순위', meta: 'GET /api/risk-index' },
          { title: '경보', body: '등급·일일 상한 적용 현재 경보 후보', meta: 'GET /api/alerts' },
          { title: '일일 브리핑', body: '언어별 일일 상황 브리핑', meta: 'GET /api/daily-brief?lang=ko' },
          { title: '예측 원장', body: '봉인된 예측 목록·채점표', meta: 'GET /api/predictions · /scorecard' },
          { title: '시점 증명', body: '예측별 블록체인 시점 증명 상태', meta: 'GET /api/predictions/{id}/timestamp-proof' },
          { title: '운영 상태', body: '소스 건강·데이터 규모·스케줄러 상태', meta: 'GET /api/status' },
        ],
      },
    ],
    cta: {
      title: '연동 키 발급',
      body: '쓰기·고위험 기능 연동용 기관별 API 키 발급',
      label: '문의하기',
      href: 'contact',
    },
  },

  diseases: {
    metaTitle: '질병별 감시',
    metaDescription: '주요 감염병별 감시 신호와 시뮬레이션 파라미터 — 조류인플루엔자 H5N1, 에볼라, 마버그, 엠폭스, 콜레라, 홍역, 메르스, 니파.',
    eyebrow: 'DISEASES',
    title: '질병별 감시',
    lead: '질병마다 먼저 움직이는 신호가 상이 · 주요 감염병별 감시 신호와 확산 시뮬레이션 문헌 파라미터 정리',
    blocks: [],
    cta: {
      title: '질병별 최신 신호',
      body: '대시보드·일일 브리핑에서 실시간 확인',
      label: '라이브 대시보드 열기',
      href: '/dashboard',
    },
  },
};
