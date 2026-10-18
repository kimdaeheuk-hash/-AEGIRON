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
    empty: '아직 보관된 브리핑이 없습니다.',
    error: '브리핑을 불러오지 못했습니다. 시스템은 계속 가동 중입니다.',
    backToList: '브리핑 목록',
    summary: '요약',
    segments: '구성',
    ticker: '한 줄 속보',
    disclosure: '고지',
    notFound: '해당 날짜의 브리핑이 없습니다.',
    langNoticeTitle: '언어 안내',
    langNoticeMismatch:
      '이 브리핑은 요청한 언어와 다른 언어로 생성되었습니다. 다른 언어인 것을 감추지 않기 위해 그대로 표시합니다.',
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
      '아이기론은 조기감지 정확도에 대한 검증된 트랙레코드를 아직 보유하지 않았습니다. 이 사이트의 모든 수치는 시스템 규모에 대한 실측값이며, 예측 성능에 대한 주장이 아닙니다.',
  },

  home: {
    metaTitle: 'AEGIRON — 감염병 조기경보 · 예측 · 확산 시뮬레이션',
    metaDescription:
      '178개국 현지어 보도와 각국 공식 감시 자료에서 감염병 이상 신호를 판정하고, 경보마다 개입 시나리오를 산출하며, 모든 예측을 이후의 공식 선언과 대조해 스스로 채점하는 감염병 인텔리전스 시스템.',

    heroLiveOk: '데이터 소스 {ok}/{total} 정상 수집 중',
    heroLiveUnknown: '수집 상태를 지금 확인하지 못했습니다',
    heroTitle: '경보를 넘어,\n[[예측]]과 [[시뮬레이션]]까지',
    heroLead:
      '아이기론은 178개국 현지어 보도와 각국 공식 감시 자료에서 이상 신호를 판정하고, 경보가 서는 시점에 개입 강도별 확산 시나리오를 함께 산출합니다. 모든 예측은 이후의 공식 선언과 자동 대조해 스스로 채점하고 생성 시점에 봉인합니다.',
    heroPrimaryCta: '라이브 대시보드',
    heroSecondaryCta: '기술 구조',
    heroNoLogin: '가입·로그인 없이 바로 열립니다',

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
      caption: '지구 동반구(Blue Marble). 위성 관측을 합성한 영상입니다.',
      credit: 'NASA · 퍼블릭 도메인',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Blue_Marble_Eastern_Hemisphere.jpg',
      position: 'center 45%',
    },

    galleryTitle: '신호가 생기는 곳',
    galleryLead:
      '아이기론이 감시하는 세계는 연구실 안이 아니라 밖에 있습니다. 실험실·현장 대응·국제 항공망·하수·병상 — 감염병의 신호가 실제로 생기는 자리입니다. 아래는 전부 공개 자료(퍼블릭 도메인·자유 라이선스)이며, 아이기론의 시설이 아니라 감시 대상을 보여 주는 사진입니다.',
    gallery: [
      {
        src: '/media/photos/emergency-operations-center.jpg',
        alt: '여러 화면이 걸린 긴급운영센터(EOC) 내부',
        caption: '긴급운영센터(EOC). 경보가 사람에게 닿아 대응으로 이어지는 자리입니다.',
        credit: '中華民國總統府 · CC BY 2.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Central_Emergency_Operation_Center_2024-10-31.jpg',
      },
      {
        src: '/media/photos/ebola-field-response.jpg',
        alt: '에볼라 대응 현장의 방호복을 입은 의료진',
        caption: '에볼라 대응 현장(2014 서아프리카). 현지어 보도가 번역되기 전, 신호는 이런 현장에서 먼저 생깁니다.',
        credit: 'Sgt. 1st Class Nathan Hoskins, U.S. Army · 퍼블릭 도메인',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:United_Assistance_141105-A-CH600-043.jpg',
      },
      {
        src: '/media/photos/world-air-routes.jpg',
        alt: '전 세계 항공 노선을 그린 세계 지도',
        caption: '국제 항공망. 확산 디지털 트윈이 159개국을 잇는 1,671개 나라쌍의 실제 모습입니다.',
        credit: 'aomd88 · CC BY 1.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:EK_emirates_2011_routes_world_map.jpg',
      },
      {
        src: '/media/photos/dna-sequencer.jpg',
        alt: '유전체 시퀀싱 장비',
        caption: '유전체 시퀀서. 변이의 신호는 확진자 수보다 서열에서 먼저 드러납니다.',
        credit: 'Scotted400 · CC BY 4.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Revolocity_DNA_sequencer.jpg',
      },
      {
        src: '/media/photos/wastewater-plant.jpg',
        alt: '하수 처리장 항공 사진',
        caption: '하수 처리장. 하수 감시는 증상이 나타나기 전 단계의 병원체 신호를 봅니다.',
        credit: 'Sdkb · CC BY-SA 4.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Blue_Plains_Advanced_Wastewater_Treatment_Plant_aerial_view,_2025.jpg',
      },
      {
        src: '/media/photos/sars-cov-2-niaid.jpg',
        alt: 'SARS-CoV-2 바이러스 입자 전자현미경 사진(채색)',
        caption: 'SARS-CoV-2 바이러스 입자(채색). 미국 NIAID 공개 자료입니다.',
        credit: 'NIAID · CC BY 2.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Novel_Coronavirus_SARS-CoV-2_(49597020648).jpg',
      },
      {
        src: '/media/photos/hospital-icu.jpg',
        alt: '중환자실 병상',
        caption: '중환자실 병상. 개입 시나리오가 추정하는 "병상 초과 일수"가 실제로 걸리는 곳입니다.',
        credit: 'Ismael Olea · CC BY 4.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:20250808_Intensive_care_unit_bed.jpg',
      },
      {
        src: '/media/photos/data-center.jpg',
        alt: '데이터센터 서버실',
        caption: '데이터센터. 114개 모듈이 매시간 도는 연산이 이런 곳에서 이뤄집니다.',
        credit: 'BalticServers.com · CC BY-SA 3.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:BalticServers_data_center.jpg',
      },
      {
        src: '/media/photos/arctic-permafrost.jpg',
        alt: '영구동토가 녹아 생긴 북극의 융해 연못',
        caption: '영구동토 해빙(북극). 극지 영토 감시가 보는 새 발병 여건의 자리입니다.',
        credit: 'NPS Climate Change Response · 퍼블릭 도메인',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Permafrost_Thaw_(14413865677).jpg',
      },
    ],

    engineTitle: '엔진 구성',
    engineLead:
      '114개 모듈 가운데 감지·유전체·예측·대응·검증의 축을 이루는 열여섯 개를 골랐습니다. 엔진마다 실제 가동 방식(매시·매일·경보 시·요청 시)을 함께 적어, 상시 도는 엔진과 부를 때 도는 엔진을 구분해 보여 드립니다. 전체 114개 모듈은 엔진 카탈로그에 정리돼 있습니다.',
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
            body: '국가·언어별 뉴스 집계에서 감염병 어휘의 밀도를 재고, 판정이 애매한 피드는 언어모델로 다시 분류합니다. 영어 보도가 나오기 전의 현지 첫 보도가 대상입니다.',
            mode: 'hourly',
          },
          {
            id: 'gai',
            name: '6계층 이상도 지수',
            body: '공식·비공식·행동·환경·동물·설명불가 여섯 층의 신호를 각자의 기준선 대비 이상도로 환산하고, 출처 신뢰도를 곱해 하나의 지수로 합칩니다. 절대량이 아니라 그 지표의 평소 수준이 기준입니다.',
            mode: 'hourly',
          },
          {
            id: 'negative_space',
            name: '보고 침묵 감시',
            body: '평소 활발하던 보고 채널이 기준선의 절반 아래로 떨어지는 것을 따로 봅니다. 2014년 기니 에볼라처럼 보고 체계의 붕괴가 확산보다 먼저 오는 경우를 겨냥하며, 판정 기준이 선언된 지표만 대상으로 합니다.',
            mode: 'hourly',
          },
          {
            id: 'unexplained',
            name: '설명 불가 집단 발병',
            body: '보도에서 추출한 집단 발병 가운데 알려진 질병 패턴과 맞지 않는 것을 별도로 셉니다. 2019년 12월 우한의 원인불명 폐렴이 이 유형입니다.',
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
            body: '북극·남극과 27개 빙하 산맥 지역을 기준선·추세와 함께 관찰합니다. 영구동토가 녹으며 드러나는 병원체와 극지 조류인플루엔자처럼, 기후 변화가 여는 새 발병 여건을 영토 단위로 봅니다.',
            mode: 'daily',
            caveat: '경보가 아니라 관찰 대상입니다. 극지 신호가 곧 발병을 뜻하지는 않습니다.',
          },
          {
            id: 'disaster_watch',
            name: '재난 감시창',
            body: '홍수·지진·태풍 뒤 수인성·매개체 감염병 위험이 높아지는 기간 동안 해당 국가를 더 낮은 문턱으로 봅니다. 재난과 발병 사이의 시간을 겨냥합니다.',
            mode: 'hourly',
          },
          {
            id: 'comtrade_signals',
            name: '의료물자 무역 감시',
            body: '마스크·방호장비·진단키트의 국가별 수입 급증을 UN Comtrade로 감지합니다. 공식 발표보다 먼저 나타나는 대비 행동의 신호입니다.',
            mode: 'daily',
            caveat: '무역 신고는 약 2개월 지연이 있어 실시간 지표가 아닙니다.',
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
            body: 'Nextstrain 공개 시퀀스 재분석에서 우세 계통의 구성비 변화와 신규 계통의 출현을 읽습니다. 확진자 수보다 먼저 움직이는 전파력·면역회피 변화의 단서입니다. 갱신이 멈춘 빌드는 신호로 쓰지 않습니다.',
            mode: 'hourly',
          },
          {
            id: 'evo2_naturalness',
            name: '서열 순서의 자연성 실측',
            body: '유전체 파운데이션 모델 Evo2에 서열의 앞부분만 주고 다음 염기를 예측하게 해, 실제 서열과의 일치율을 잽니다. 조성 통계로는 드러나지 않는 이어붙임·재조합 구간을 겨냥합니다.',
            mode: 'onRequest',
            caveat: 'Evo2는 진핵 숙주 바이러스를 학습에서 제외했으므로 코로나·독감·에볼라 서열에는 적용하지 않습니다.',
          },
          {
            id: 'msa_homology',
            name: '상동성 기반 키메라 탐지',
            body: '단백질 서열을 공개 상동성 데이터베이스에서 검색해, 질의 전체를 덮는 자연 단백질이 존재하는지 확인합니다. 학습된 모델이 아닌 검색이므로 Evo2가 다루지 못하는 병원체에도 쓸 수 있습니다.',
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
            body: '지표별 시계열을 선형회귀와 지수평활의 앙상블로 7일·14일 앞까지 외삽해 일일 브리핑에 싣습니다.',
            mode: 'daily',
            caveat: '측정된 발병 수가 아니라 신호 시계열의 외삽입니다.',
          },
          {
            id: 'digital_twin',
            name: '국가 간 확산 시뮬레이션',
            body: '159개국을 노드로, 1,671개 항공 연결 나라쌍과 314개 육로 국경을 간선으로 하는 메타개체군 SEIR 모델입니다. 기간 안에 도달하지 않은 나라와 경로 자체를 모르는 나라를 구분해 보고합니다.',
            mode: 'onRequest',
            caveat: '항공망은 2014년 노선 데이터이고, 육로 통행량은 인구 기반 추정입니다.',
          },
          {
            id: 'global_inflow',
            name: '국내 유입 시점 추정',
            body: '발원 도시의 국제선 여객량·비행시간·초기 지수성장률로 국내 첫 유입까지의 일수와 입국 관문별 위험을 추정합니다.',
            mode: 'onRequest',
            caveat: '모델 추정값이며 관측된 유입일이 아닙니다.',
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
            body: '새 critical·high 경보마다 질병별 파라미터로 SEIR 방어 시뮬레이션을 돌려, 무대응과 개입 시나리오의 차이를 경보에 함께 싣습니다. 경보가 "무엇이 오는가"에서 끝나지 않고 "어떤 조치가 무엇을 바꾸는가"까지 답하게 하는 단계입니다.',
            mode: 'onAlert',
            caveat: '예보가 아니라 문헌 파라미터에 기댄 모델 시나리오입니다. 질병을 특정하지 못한 경보에는 숫자를 만들지 않습니다.',
          },
          {
            id: 'defense',
            name: '시간가변 개입 비교',
            body: '격리·거리두기·백신 접종의 시작 시점과 강도를 바꿔 가며 실효 재생산수와 병상 초과 일수가 어떻게 달라지는지 비교합니다.',
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
            body: '기록된 예측을 이후의 공식 선언과 매일 대조해 적중·실패·판정 보류로 나눕니다. 조회수 급증이나 확진자 갱신은 정답으로 쓰지 않습니다. 우리 신호로 우리를 채점하는 순환을 막기 위해서입니다.',
            mode: 'daily',
          },
          {
            id: 'lead_time_ledger',
            name: '선행성 원장',
            body: '신호를 처음 본 시각을 공식 선언 이전에 기록합니다. 선언 뒤에 거꾸로 찾아 맞춘 선행일수는 실측으로 인정하지 않습니다.',
            mode: 'hourly',
          },
          {
            id: 'prediction_timestamp',
            name: '예측 봉인',
            body: '예측 기록의 SHA-256 해시를 OpenTimestamps를 통해 비트코인 블록체인에 고정합니다. 나중에 고쳐 쓴 예측이 아니라는 것을 제3자가 직접 확인할 수 있습니다.',
            mode: 'onRequest',
          },
          {
            id: 'source_health',
            name: '조용한 실패 감시',
            body: '소스마다 값이 실제로 들어왔는지, 그 값을 만든 방식이 무너지지 않았는지를 매 주기 따로 셉니다. 수집은 돌았지만 값이 비어 있는 소스를 정상으로 집계하지 않습니다.',
            mode: 'hourly',
          },
        ],
      },
    ],

    engineCatalogueCta: '엔진 카탈로그에서 114개 모듈의 역할을 전부 보기',

    diffEyebrow: 'WHAT MAKES US DIFFERENT',
    diffTitle: '다른 조기경보와 무엇이 다른가',
    diffLead:
      '감염병 조기경보 자체는 새롭지 않습니다. 블루닷·EIOS·메타바이오타 같은 선행 서비스가 이미 있습니다. 아이기론이 다른 지점은, 탐지에서 멈추지 않고 검증·대응·주권까지 한 시스템에 넣었다는 것입니다. 과장 없이 구조로만 적습니다.',
    diffItems: [
      {
        title: '탐지에서 끝나지 않는다',
        body: '대부분의 조기경보는 "어디서 무슨 일이 난다"에서 멈춥니다. 아이기론은 그 뒤에 확산 시뮬레이션·개입 시나리오·대응제 준비태세를 붙여, "그래서 무엇을 어느 강도로"까지 답합니다.',
      },
      {
        title: '우리 숫자를 우리가 채점한다',
        body: '모든 예측을 생성 시점에 봉인하고 공식 선언과 매일 자동 대조해 적중·실패를 스스로 기록합니다. 트랙레코드를 주장이 아니라 검증 가능한 기록으로 쌓는 구조는 흔치 않습니다.',
      },
      {
        title: '감시 공백 지역을 처음부터 포함',
        body: '상업성이 낮아 다른 서비스가 잘 다루지 않는 178개국·52개 언어를 같은 기준으로 봅니다. 아프리카·중앙아시아·태평양 도서국, 그리고 극지 영토까지 감시 범위에 넣었습니다.',
      },
      {
        title: '국가 바이오안보 축',
        body: '방어적 유전체 스크리닝(HEIMDALL)과 대응제 커버리지·생산 주권 분석(VALHALLA)은 상업 조기경보 서비스에는 없는 국가 단위의 축입니다.',
      },
      {
        title: '전부 공개',
        body: '시스템·방법론·데이터·한계를 처음부터 엽니다. 지킬 고객 계약이 있는 큰 서비스가 구조적으로 따라 하기 어려운 선택이며, 실사에서 그대로 검증 가능한 신뢰의 근거가 됩니다.',
      },
    ],
    futureTitle: '어디로 가는가',
    futureLead: '지금은 시작점입니다. 운영이 쌓일수록 강해지도록 설계했습니다.',
    futureItems: [
      {
        title: '독자 추출 모델',
        body: '지금은 외부 API로 신호를 추출하지만, 추출 경로를 한 곳에서 바꿔 자체 모델(NVIDIA NIM 기반)로 전환할 수 있게 배선해 두었습니다. 민감한 데이터가 해외 API로 나가지 않는 구조로 향합니다.',
      },
      {
        title: '데이터 해자',
        body: '"어떤 신호가 실제 발병으로 이어졌는가"를 매일 학습셋으로 조립합니다. 운영이 지속될수록 이 학습셋이 커지고, 휴리스틱을 실측 학습 모델로 교체할 수 있습니다.',
      },
      {
        title: '봉인된 트랙레코드',
        body: '봉인된 예측이 쌓이면, "먼저 알았다"를 제3자가 블록체인으로 검증할 수 있는 실적이 됩니다. 시간이 지날수록 증명력이 커지는 자산입니다.',
      },
      {
        title: '현장 연결',
        body: '실제 감시망·현장 조직과 연결해 신호의 원천에 더 가까이 가는 것이 다음 단계입니다. 글로벌 조기경보 인프라로 확장하는 경로입니다.',
      },
    ],

    specialEyebrow: 'SPECIAL PROGRAMS',
    specialTitle: '경쟁사에 없는 두 축 — HEIMDALL · VALHALLA',
    specialLead: '감시 계층 대부분은 공개로 돕니다. 그런데 성격이 다른 두 내부 R&D 프로그램이 국가 바이오안보 축을 담당합니다. 능력을 과장하지 않는 선에서, 무엇을 하고 무엇을 안 하는지만 적습니다.',
    specialCards: [
      { code: 'HEIMDALL', name: '방어적 유전체 스크리닝', body: '서열이 자연 진화 통계에서 벗어나는지 탐지·플래그합니다. 설계·합성 기능은 없고, 판정이 아니라 검토 우선순위만 냅니다.' },
      { code: 'VALHALLA', name: '대응제 준비태세', body: '분자 예측을 흉내 내지 않고, 공개 자료로 비축 커버리지 격차와 생산 주권 격차를 집계합니다. 국가 비축량 같은 비공개 정보는 다루지 않습니다.' },
    ],
    specialCta: '스페셜 프로그램 보기',

    openTitle: '검증할 수 있도록 공개합니다',
    openLead:
      '감염병 감시에서 가장 흔한 실패는 틀린 예측이 아니라 검증할 수 없는 예측입니다. 그래서 판단의 근거가 되는 시스템·방법론·데이터·한계를 처음부터 열어 둡니다.',
    openItems: [
      {
        title: '실시간 시스템',
        body: '운영 중인 수집·경보 데이터를 대시보드에서 그대로 보여 줍니다. 시뮬레이션 콘솔의 가정값과 모델 값은 화면에서도 그렇게 표기합니다.',
        href: '/dashboard',
        linkLabel: '대시보드 열기',
      },
      {
        title: '방법론',
        body: '신호를 모으고, 이상을 판정하고, 예측을 만드는 과정을 네 개의 층으로 나누어 설명합니다. 각 층이 따르는 표준도 함께 밝힙니다.',
        href: '/methodology',
        linkLabel: '방법론 보기',
      },
      {
        title: '데이터 소스',
        body: '운영 중인 수집 소스를 빠짐없이 나열하고, 각 소스가 무엇을 볼 수 없는지와 지금 정상인지도 함께 적습니다.',
        href: '/data-sources',
        linkLabel: '소스 목록 보기',
      },
      {
        title: '검증과 한계',
        body: '아직 검증되지 않은 것과 알려진 한계, 데이터 공백을 적고, 시스템이 스스로 자기 숫자를 점검하는 방식을 설명합니다.',
        href: '/transparency',
        linkLabel: '검증 현황 보기',
      },
    ],

    honestTitle: '우리 숫자를 우리가 먼저 검증합니다',
    honestLead:
      '조기경보 시스템의 신뢰는 주장의 크기가 아니라 검증 경로에서 나옵니다. 아직 확보하지 못한 것과, 그 공백을 메우기 위해 이미 가동 중인 장치를 함께 밝힙니다.',
    honestPoints: [
      '조기감지 성능은 **검증 가능한 기록으로만 증명합니다.** "며칠 먼저 감지했다" 같은 말 대신, 봉인된 예측 기록이 그 자리를 대신하게 둡니다.',
      '모든 예측을 **생성 시점에 봉인**하고, 이후의 공식 선언과 매일 자동 대조해 채점합니다. 트랙레코드는 주장이 아니라 이 기록으로 쌓입니다.',
      '시나리오 수치는 **모델 가정 하의 추정**으로 표기하고, 역사상 최대 발병과 자동 대조해 설명 범위를 넘으면 경고를 함께 싣습니다.',
      '데이터 공백은 감추지 않습니다. 어느 나라·어느 기간이 비었는지, 어떤 소스가 멈췄는지 시스템이 스스로 보고합니다.',
    ],
    honestClose:
      '발병을 놓쳤을 때는 "모델이 놓친 것"과 "데이터가 없어 볼 수 없던 것"을 나누어 보고합니다. 둘을 섞으면 원인 진단이 정반대로 나오기 때문입니다.',
    honestCta: '검증 현황 전체 보기',

    pipelineTitle: '신호가 경보가 되기까지',
    pipelineLead: '다섯 단계를 거칩니다. 각 단계에서 무엇을 버리는지가 무엇을 취하는지만큼 중요합니다.',
    pipelineSteps: [
      {
        step: '01',
        title: '수집',
        body: 'WHO 지역사무소와 각국 보건당국의 공식 자료, 178개국 현지어 보도, 학술 매체, 하수 감시, 유전체 계통 자료를 매시간 수집합니다.',
      },
      {
        step: '02',
        title: '추출',
        body: 'PDF 표와 기사 본문에서 질병·국가·확진·사망을 구조화합니다. 읽어 내지 못한 항목은 추측으로 채우지 않고 비워 둡니다.',
      },
      {
        step: '03',
        title: '판정',
        body: '절대량이 아니라 각 지표의 평소 수준 대비로 이상도를 계산합니다. 같은 다섯 건도 나라마다 의미가 다르기 때문입니다.',
      },
      {
        step: '04',
        title: '예측',
        body: '전파 모델로 확산 경로와 유입 위험을 추정하고, 모든 값에 가정과 한계를 함께 붙입니다.',
      },
      {
        step: '05',
        title: '대응',
        body: '무대응과 개입 시나리오를 비교해, 어떤 조치가 어느 강도에서 전파를 꺾는지까지 제시합니다.',
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

    ctaTitle: '도입 검토에 필요한 자료는 모두 열려 있습니다',
    ctaBody:
      '데모 예약 없이 시스템 전체를 먼저 검토하실 수 있습니다. 파일럿과 협력 논의는 문의 페이지로 연락해 주십시오.',
    ctaButton: '문의하기',
  },
};
