import type { Dictionary } from '../types';
import { pagesKo } from './pages.ko';
import { extraKo } from './extra.ko';

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
  extra: extraKo,

  briefings: {
    archiveTitle: '지난 브리핑',
    count: '{n}건',
    quietDay: '조용한 날',
    openBrief: '읽기',
    empty: '보관된 브리핑 없음',
    error: '브리핑 불러오기 실패 · 시스템은 계속 가동 중',
    backToList: '브리핑 목록',
    summary: '요약',
    segments: '구성',
    ticker: '한 줄 속보',
    disclosure: '고지',
    notFound: '해당 날짜 브리핑 없음',
    langNoticeTitle: '언어 안내',
    langNoticeMismatch:
      '요청 언어와 다른 언어로 생성된 브리핑 · 비은폐 위해 원본 그대로 표시',
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
    live: '실가동',
    record: '공개 예측 원장',
    korea: '대한민국 관점',
    security: '보안 · 데이터 거버넌스',
    press: '미디어 키트',
    pilot: '도입 방식',
    developers: '개발자 · API',
    diseases: '질병별 감시',
    solNgo: '국제기구 · 인도지원',
    solReinsurance: '재보험 · 보험',
    solGovernment: '정부 · 공공보건',
    engines: '엔진 카탈로그',
    techSpec2: '기술 스펙 Ⅱ · 분석과 대응',
    techSpec1: '기술 스펙 Ⅰ · 감시와 수집',
    trust: '검증·데이터',
    company: '회사',
    platform: '플랫폼',
    technology: '기술',
    programs: '스페셜 프로그램',
    methodology: '방법론',
    transparency: '검증 체계',
    dataSources: '데이터 소스',
    solutions: '활용 분야',
    briefings: '일일 브리핑',
    about: '회사 소개',
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
      '아이기론 = 조기감지 정확도 검증 트랙레코드 미보유 · 본 사이트 전 수치 = 시스템 규모 실측값, 예측 성능 주장 아님',
  },

  home: {
    metaTitle: 'AEGIRON — 감염병 조기경보 · 예측 · 확산 시뮬레이션',
    metaDescription:
      '178개국 현지어 보도와 각국 공식 감시 자료에서 감염병 이상 신호를 판정하고, 경보마다 개입 시나리오를 산출하며, 모든 예측을 이후의 공식 선언과 대조해 스스로 채점하는 감염병 인텔리전스 시스템.',

    heroLiveOk: '데이터 소스 {ok}/{total} 정상 수집 중',
    heroLiveUnknown: '수집 상태 현재 확인 불가',
    heroTitle: '경보를 넘어,\n[[예측]]과 [[시뮬레이션]]까지',
    heroLead:
      '178개국 현지어 보도·각국 공식 감시 자료 이상 신호 판정 · 경보 시점 개입 강도별 확산 시나리오 동시 산출 · 전 예측 이후 공식 선언 자동 대조 자가 채점·생성 시점 봉인',
    heroPrimaryCta: '라이브 대시보드',
    heroSecondaryCta: '기술 구조',
    heroNoLogin: '가입·로그인 없이 즉시 접속',

    stats: [
      { value: '114', label: '알고리즘 모듈', note: '감지 · 유전체 · 예측 · 대응 · 검증' },
      { value: '123', label: 'API 엔드포인트', note: '수집 · 분석 · 시뮬레이션 · 채점' },
      { value: '2,145', label: '자동 시험', note: '전부 통과해야 운영에 반영' },
      { value: '178', label: '감시 대상 국가', note: '52개 언어 현지 보도 · 매시 수집' },
    ],
    statsAsOf: '2026-10-18 저장소·운영 로그 기준 실측',
    introVideoLabel: '아이기론 소개 영상',
    photo: {
      src: '/media/photos/earth-eastern-hemisphere.jpg',
      alt: '지구 동반구 — 아프리카·유럽·아시아(위성 합성 영상)',
      caption: '지구 동반구(Blue Marble) · 위성 관측 합성 영상',
      credit: 'NASA · 퍼블릭 도메인',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Blue_Marble_Eastern_Hemisphere.jpg',
      position: 'center 45%',
    },

    galleryTitle: '신호가 생기는 곳',
    galleryLead:
      '아이기론 감시 대상 = 연구실 밖 세계 · 실험실·현장 대응·국제 항공망·하수·병상 — 감염병 신호 발생 현장 · 하단 전부 공개 자료(퍼블릭 도메인·자유 라이선스) · 아이기론 시설 아닌 감시 대상 사진',
    gallery: [
      {
        src: '/media/photos/emergency-operations-center.jpg',
        alt: '여러 화면이 걸린 긴급운영센터(EOC) 내부',
        caption: '긴급운영센터(EOC) · 경보 → 사람 → 대응 연결 지점',
        credit: '中華民國總統府 · CC BY 2.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Central_Emergency_Operation_Center_2024-10-31.jpg',
      },
      {
        src: '/media/photos/ebola-field-response.jpg',
        alt: '에볼라 대응 현장의 방호복을 입은 의료진',
        caption: '에볼라 대응 현장(2014 서아프리카) · 현지어 보도 번역 이전 — 신호 최초 발생 현장',
        credit: 'Sgt. 1st Class Nathan Hoskins, U.S. Army · 퍼블릭 도메인',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:United_Assistance_141105-A-CH600-043.jpg',
      },
      {
        src: '/media/photos/world-air-routes.jpg',
        alt: '전 세계 항공 노선을 그린 세계 지도',
        caption: '국제 항공망 · 확산 디지털 트윈 159개국 연결 1,671개 나라쌍 실제 모습',
        credit: 'aomd88 · CC BY 1.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:EK_emirates_2011_routes_world_map.jpg',
      },
      {
        src: '/media/photos/dna-sequencer.jpg',
        alt: '유전체 시퀀싱 장비',
        caption: '유전체 시퀀서 · 변이 신호 = 확진자 수보다 서열에서 선행 노출',
        credit: 'Scotted400 · CC BY 4.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Revolocity_DNA_sequencer.jpg',
      },
      {
        src: '/media/photos/wastewater-plant.jpg',
        alt: '하수 처리장 항공 사진',
        caption: '하수 처리장 · 하수 감시 = 증상 발현 전 단계 병원체 신호 관측',
        credit: 'Sdkb · CC BY-SA 4.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Blue_Plains_Advanced_Wastewater_Treatment_Plant_aerial_view,_2025.jpg',
      },
      {
        src: '/media/photos/sars-cov-2-niaid.jpg',
        alt: 'SARS-CoV-2 바이러스 입자 전자현미경 사진(채색)',
        caption: 'SARS-CoV-2 바이러스 입자(채색) · 미국 NIAID 공개 자료',
        credit: 'NIAID · CC BY 2.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Novel_Coronavirus_SARS-CoV-2_(49597020648).jpg',
      },
      {
        src: '/media/photos/hospital-icu.jpg',
        alt: '중환자실 병상',
        caption: '중환자실 병상 · 개입 시나리오 추정 "병상 초과 일수" 발생 현장',
        credit: 'Ismael Olea · CC BY 4.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:20250808_Intensive_care_unit_bed.jpg',
      },
      {
        src: '/media/photos/data-center.jpg',
        alt: '데이터센터 서버실',
        caption: '데이터센터 · 114개 모듈 매시간 연산 수행 현장',
        credit: 'BalticServers.com · CC BY-SA 3.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:BalticServers_data_center.jpg',
      },
      {
        src: '/media/photos/arctic-permafrost.jpg',
        alt: '영구동토가 녹아 생긴 북극의 융해 연못',
        caption: '영구동토 해빙(북극) · 극지 영토 감시 대상 — 새 발병 여건 발생 지점',
        credit: 'NPS Climate Change Response · 퍼블릭 도메인',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Permafrost_Thaw_(14413865677).jpg',
      },
    ],

    engineTitle: '엔진 구성',
    engineLead:
      '114개 모듈 중 감지·유전체·예측·대응·검증 축 16개 선별 · 엔진별 실제 가동 방식(매시·매일·경보 시·요청 시) 병기 — 상시 가동·호출 가동 구분 · 전체 114개 모듈 = 엔진 카탈로그 정리',
    engineModes: {
      hourly: '매시 자동',
      daily: '매일 자동',
      onAlert: '경보 시 자동',
      onRequest: '요청 시 실행',
    },
    engineCaveatLabel: '한계',
    engineGroups: [
      {
        key: 'detect',
        label: '감지',
        engines: [
          {
            id: 'local_news',
            name: '현지어 보도 감시',
            body: '국가·언어별 뉴스 집계 감염병 어휘 밀도 측정 · 판정 애매 피드 언어모델 재분류 · 대상 = 영어 보도 이전 현지 첫 보도',
            mode: 'hourly',
          },
          {
            id: 'gai',
            name: '6계층 이상도 지수',
            body: '공식·비공식·행동·환경·동물·설명불가 6개 층 신호 — 각 기준선 대비 이상도 환산 × 출처 신뢰도 → 단일 지수 · 기준 = 절대량 아닌 해당 지표 평소 수준',
            mode: 'hourly',
          },
          {
            id: 'negative_space',
            name: '보고 침묵 감시',
            body: '활발하던 보고 채널의 기준선 절반 이하 급감 별도 관측 · 표적 = 보고 체계 붕괴의 확산 선행 사례(2014년 기니 에볼라) · 판정 기준 선언 지표만 대상',
            mode: 'hourly',
          },
          {
            id: 'unexplained',
            name: '설명 불가 집단 발병',
            body: '보도 추출 집단 발병 중 기존 질병 패턴 불일치 건 별도 집계 · 2019년 12월 우한 원인불명 폐렴 유형',
            mode: 'hourly',
          },
        ],
      },
      {
        key: 'environment',
        label: '환경 · 극지 영토',
        engines: [
          {
            id: 'polar_signals',
            name: '극지 영토 감시',
            body: '북극·남극·27개 빙하 산맥 지역 기준선·추세 관찰 · 영구동토 해빙 노출 병원체·극지 조류인플루엔자 등 기후 변화 발 새 발병 여건 영토 단위 관측',
            mode: 'daily',
            caveat: '경보 아닌 관찰 대상 · 극지 신호 ≠ 발병',
          },
          {
            id: 'disaster_watch',
            name: '재난 감시창',
            body: '홍수·지진·태풍 후 수인성·매개체 감염병 고위험 기간 — 해당 국가 감시 문턱 하향 · 표적 = 재난~발병 간 시간',
            mode: 'hourly',
          },
          {
            id: 'comtrade_signals',
            name: '의료물자 무역 감시',
            body: 'UN Comtrade 기반 마스크·방호장비·진단키트 국가별 수입 급증 감지 · 공식 발표 선행 대비 행동 신호',
            mode: 'daily',
            caveat: '무역 신고 약 2개월 지연 — 실시간 지표 아님',
          },
        ],
      },
      {
        key: 'genomics',
        label: '유전체',
        engines: [
          {
            id: 'genomic_variants',
            name: '계통 구성비 추적',
            body: 'Nextstrain 공개 시퀀스 재분석 — 우세 계통 구성비 변화·신규 계통 출현 판독 · 확진자 수 선행 전파력·면역회피 변화 단서 · 갱신 정지 빌드 신호 미사용',
            mode: 'hourly',
          },
          {
            id: 'evo2_naturalness',
            name: '서열 순서의 자연성 실측',
            body: '유전체 파운데이션 모델 Evo2 — 서열 앞부분 입력 → 다음 염기 예측 → 실제 서열 일치율 측정 · 표적 = 조성 통계 미노출 이어붙임·재조합 구간',
            mode: 'onRequest',
            caveat: 'Evo2 진핵 숙주 바이러스 학습 제외 — 코로나·독감·에볼라 서열 미적용',
          },
          {
            id: 'msa_homology',
            name: '상동성 기반 키메라 탐지',
            body: '단백질 서열 공개 상동성 데이터베이스 검색 — 질의 전체 커버 자연 단백질 존재 여부 확인 · 학습 모델 아닌 검색 — Evo2 미적용 병원체에도 사용 가능',
            mode: 'onRequest',
          },
        ],
      },
      {
        key: 'simulate',
        label: '예측 · 시뮬레이션',
        engines: [
          {
            id: 'forecast_engine',
            name: '7·14일 추세 예보',
            body: '지표별 시계열 선형회귀·지수평활 앙상블 7일·14일 외삽 → 일일 브리핑 반영',
            mode: 'daily',
            caveat: '측정 발병 수 아닌 신호 시계열 외삽',
          },
          {
            id: 'digital_twin',
            name: '국가 간 확산 시뮬레이션',
            body: '메타개체군 SEIR 모델 — 노드 159개국 · 간선 = 항공 연결 1,671개 나라쌍 + 육로 국경 314개 · 기간 내 미도달 국가와 경로 미상 국가 구분 보고',
            mode: 'onRequest',
            caveat: '항공망 = 2014년 노선 데이터 · 육로 통행량 = 인구 기반 추정',
          },
          {
            id: 'global_inflow',
            name: '국내 유입 시점 추정',
            body: '발원 도시 국제선 여객량·비행시간·초기 지수성장률 기반 국내 첫 유입 일수·입국 관문별 위험 추정',
            mode: 'onRequest',
            caveat: '모델 추정값 · 관측 유입일 아님',
          },
        ],
      },
      {
        key: 'respond',
        label: '대응',
        engines: [
          {
            id: 'alert_intervention',
            name: '경보별 개입 시나리오',
            body: '신규 critical·high 경보별 질병 파라미터 SEIR 방어 시뮬레이션 — 무대응 vs 개입 시나리오 차이 경보 동봉 · "무엇이 오는가" → "어떤 조치가 무엇을 바꾸는가"',
            mode: 'onAlert',
            caveat: '예보 아닌 문헌 파라미터 기반 모델 시나리오 · 질병 미특정 경보 숫자 미생성',
          },
          {
            id: 'defense',
            name: '시간가변 개입 비교',
            body: '격리·거리두기·백신 접종 시작 시점·강도 조정 — 실효 재생산수·병상 초과 일수 변화 비교',
            mode: 'onRequest',
          },
        ],
      },
      {
        key: 'verify',
        label: '자기검증',
        engines: [
          {
            id: 'prediction_resolver',
            name: '예측 자동 채점',
            body: '기록 예측 × 이후 공식 선언 매일 대조 → 적중·실패·판정 보류 구분 · 조회수 급증·확진자 갱신 정답 미사용 — 자기 신호 자기 채점 순환 차단',
            mode: 'daily',
          },
          {
            id: 'lead_time_ledger',
            name: '선행성 원장',
            body: '신호 최초 관측 시각 공식 선언 이전 기록 · 선언 후 역산 선행일수 실측 불인정',
            mode: 'hourly',
          },
          {
            id: 'prediction_timestamp',
            name: '예측 봉인',
            body: '예측 기록 SHA-256 해시 OpenTimestamps 경유 비트코인 블록체인 고정 · 사후 수정 예측 아님 제3자 직접 검증 가능',
            mode: 'onRequest',
          },
          {
            id: 'source_health',
            name: '조용한 실패 감시',
            body: '소스별 실제 값 유입 여부·값 생성 방식 무결성 매 주기 개별 집계 · 수집 실행·값 결측 소스 정상 집계 제외',
            mode: 'hourly',
          },
        ],
      },
    ],

    engineCatalogueCta: '엔진 카탈로그에서 114개 모듈의 역할을 전부 보기',

    diffEyebrow: 'WHAT MAKES US DIFFERENT',
    diffTitle: '다른 조기경보와 무엇이 다른가',
    diffLead:
      '감염병 조기경보 = 신규 영역 아님 · 선행 서비스 존재(블루닷·EIOS·메타바이오타) · 아이기론 차별점 = 탐지를 넘어 검증·대응·주권까지 단일 시스템 통합 · 과장 없이 구조만 기재',
    diffItems: [
      {
        title: '탐지에서 끝나지 않는다',
        body: '대부분 조기경보 = "어디서 무슨 일"에서 종료 · 아이기론 = 확산 시뮬레이션·개입 시나리오·대응제 준비태세 결합 → "그래서 무엇을 어느 강도로"까지 응답',
      },
      {
        title: '우리 숫자를 우리가 채점한다',
        body: '전 예측 생성 시점 봉인 · 공식 선언 매일 자동 대조 → 적중·실패 자가 기록 · 트랙레코드 = 주장 아닌 검증 가능 기록 축적 구조 — 희소',
      },
      {
        title: '감시 공백 지역을 처음부터 포함',
        body: '상업성 저하로 타 서비스 사각인 178개국·52개 언어 동일 기준 감시 · 아프리카·중앙아시아·태평양 도서국·극지 영토까지 감시 범위 포함',
      },
      {
        title: '국가 바이오안보 축',
        body: '방어적 유전체 스크리닝(HEIMDALL)·대응제 커버리지·생산 주권 분석(VALHALLA) = 상업 조기경보 서비스 부재의 국가 단위 축',
      },
      {
        title: '전부 공개',
        body: '시스템·방법론·데이터·한계 초기 전면 공개 · 보호할 고객 계약 보유 대형 서비스의 구조적 모방 난이 선택 · 실사 직접 검증 가능 신뢰 근거',
      },
    ],
    futureTitle: '어디로 가는가',
    futureLead: '현 시점 = 시작점 · 운영 축적 비례 강화 설계',
    futureItems: [
      {
        title: '독자 추출 모델',
        body: '현재 외부 API 신호 추출 · 추출 경로 단일 지점 전환 — 자체 모델(NVIDIA NIM 기반) 교체 배선 완료 · 민감 데이터 해외 API 미반출 구조 지향',
      },
      {
        title: '데이터 해자',
        body: '"실제 발병으로 이어진 신호" 매일 학습셋 조립 · 운영 지속 비례 학습셋 확대 — 휴리스틱 → 실측 학습 모델 교체 가능',
      },
      {
        title: '봉인된 트랙레코드',
        body: '봉인 예측 축적 → "선행 인지" 제3자 블록체인 검증 가능 실적 · 시간 경과 비례 증명력 증가 자산',
      },
      {
        title: '현장 연결',
        body: '다음 단계 = 실제 감시망·현장 조직 연결 — 신호 원천 근접 · 글로벌 조기경보 인프라 확장 경로',
      },
    ],

    specialEyebrow: 'SPECIAL PROGRAMS',
    specialTitle: '경쟁사에 없는 두 축 — HEIMDALL · VALHALLA',
    specialLead: '감시 계층 대부분 공개 운영 · 성격 상이 2개 내부 R&D 프로그램 = 국가 바이오안보 축 · 능력 과장 없이 수행·비수행 범위만 기재',
    specialCards: [
      { code: 'HEIMDALL', name: '방어적 유전체 스크리닝', body: '서열의 자연 진화 통계 이탈 탐지·플래그 · 설계·합성 기능 없음 · 판정 아닌 검토 우선순위만 산출' },
      { code: 'VALHALLA', name: '대응제 준비태세', body: '분자 예측 모사 없음 · 공개 자료 기반 비축 커버리지 격차·생산 주권 격차 집계 · 국가 비축량 등 비공개 정보 미취급' },
    ],
    specialCta: '스페셜 프로그램 보기',

    openTitle: '검증 가능성을 위한 공개',
    openLead:
      '감염병 감시 최빈 실패 = 틀린 예측 아닌 검증 불가 예측 · 판단 근거 시스템·방법론·데이터·한계 초기 전면 개방',
    openItems: [
      {
        title: '실시간 시스템',
        body: '운영 중 수집·경보 데이터 대시보드 원본 표시 · 시뮬레이션 콘솔 가정값·모델 값 화면 명시',
        href: '/dashboard',
        linkLabel: '대시보드 열기',
      },
      {
        title: '방법론',
        body: '신호 수집 → 이상 판정 → 예측 생성 과정 4개 층 분해 설명 · 층별 준거 표준 병기',
        href: '/methodology',
        linkLabel: '방법론 보기',
      },
      {
        title: '데이터 소스',
        body: '운영 수집 소스 전수 나열 · 소스별 관측 사각·현재 정상 여부 병기',
        href: '/data-sources',
        linkLabel: '소스 목록 보기',
      },
      {
        title: '검증과 한계',
        body: '미검증 항목·알려진 한계·데이터 공백 기재 · 시스템 자가 수치 점검 방식 설명',
        href: '/transparency',
        linkLabel: '검증 현황 보기',
      },
    ],

    honestTitle: '자체 수치 자가 선검증',
    honestLead:
      '조기경보 신뢰 = 주장 크기 아닌 검증 경로 · 미확보 항목·공백 보완 가동 장치 동시 공개',
    honestPoints: [
      '조기감지 성능 = **검증 가능 기록 전용 증명** · "며칠 선행 감지"류 서술 대신 봉인 예측 기록 대체',
      '전 예측 **생성 시점 봉인** · 이후 공식 선언 매일 자동 대조 채점 · 트랙레코드 = 주장 아닌 본 기록 축적',
      '시나리오 수치 = **모델 가정 하 추정** 표기 · 역사상 최대 발병 자동 대조 — 설명 범위 초과 시 경고 병기',
      '데이터 공백 비은폐 · 결측 국가·기간·정지 소스 시스템 자가 보고',
    ],
    honestClose:
      '발병 누락 시 "모델 누락"과 "데이터 부재 미관측" 구분 보고 · 혼재 시 원인 진단 역전',
    honestCta: '검증 현황 전체 보기',

    pipelineTitle: '신호가 경보가 되기까지',
    pipelineLead: '5단계 처리 · 각 단계 버림의 선택 = 취함의 선택만큼 중요',
    pipelineSteps: [
      {
        step: '01',
        title: '수집',
        body: 'WHO 지역사무소·각국 보건당국 공식 자료·178개국 현지어 보도·학술 매체·하수 감시·유전체 계통 자료 매시간 수집',
      },
      {
        step: '02',
        title: '추출',
        body: 'PDF 표·기사 본문 → 질병·국가·확진·사망 구조화 · 미판독 항목 추측 미채움·공란 유지',
      },
      {
        step: '03',
        title: '판정',
        body: '이상도 = 절대량 아닌 지표별 평소 수준 대비 계산 · 동일 5건도 국가별 의미 상이',
      },
      {
        step: '04',
        title: '예측',
        body: '전파 모델 기반 확산 경로·유입 위험 추정 · 전 값에 가정·한계 병기',
      },
      {
        step: '05',
        title: '대응',
        body: '무대응 vs 개입 시나리오 비교 — 조치별·강도별 전파 차단 지점 제시',
      },
    ],

    briefTitle: '오늘의 브리핑',
    briefLead: '매일 자동 생성 · 조용한 날 = 조용함 기재',
    briefCta: '지난 브리핑 보기',
    briefEmpty: '금일 브리핑 미생성',
    briefError: '브리핑 불러오기 실패 · 시스템은 계속 가동 중',

    audienceTitle: '누구를 위한 것인가',
    audienceLead: '동일 신호도 수용자별 필요 형태 상이',
    audiences: [
      {
        title: '재보험 · 보험',
        body: '국가별 노출 지수·포트폴리오 비교 · 절대 확률 아닌 상대 지표 — 응답 상시 명시',
        href: '/solutions/reinsurance',
      },
      {
        title: '정부 · 공공보건',
        body: '유입 경로 추적·개입 시나리오 비교 · 방어 조치별 효과 모델 대조',
        href: '/solutions/government',
      },
      {
        title: '국제기구 · 인도지원',
        body: '감시 취약 지역 조기 신호 · 상업성 저하 타 서비스 사각 국가 포함',
        href: '/solutions/ngo',
      },
    ],

    ctaTitle: '도입 검토 자료 전면 개방',
    ctaBody:
      '데모 예약 없이 시스템 전체 사전 검토 가능 · 파일럿·협력 논의 = 문의 페이지 접수',
    ctaButton: '문의하기',
  },
};
