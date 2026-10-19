import type { PagesDict } from '../types';

/**
 * 한국어 하위 페이지 콘텐츠.
 *
 * ★ 여기 적힌 수치는 2026-10-19 실측값이다 ★
 * 운영 수집 소스 23종(소스 건강 점검 기준) · 현지어 뉴스 피드 179개(178개국 · 52개 언어,
 * local_news.LOCAL_FEEDS 의 gl/hl 실측) · 알고리즘 모듈 118개(엔진 116 + YGGDRASIL·BAIKAL) · 엔드포인트 128개 ·
 * 자동 시험 2,263건 · 확산 모델 159개국 / 항공 연결 1,671쌍 / 육로 국경 314개.
 * 수치를 바꾸기 전에 다시 센다. 추정치를 사실처럼 쓰지 않는다.
 *
 * ★ 2026-10-18 오후 캡틴 지시 ★ "문장들에서 아이기론이 불리한 부분을 빼라."
 * 스스로를 깎는 문장(“아직 없다”, “불안정하다”, “탈락시켰다”)은 뺐다. 다만 사실이 아닌
 * 것을 새로 주장하지는 않는다 — 정확도·선행일수 주장은 여전히 쓰지 않고, 모델이 낸 숫자는
 * '모델 시나리오'라는 이름을 그대로 단다. 그것은 약점 고백이 아니라 산출물의 정체다.
 */
export const pagesKo: PagesDict = {
  // ── 플랫폼 ────────────────────────────────────────────────
  platform: {
    metaTitle: '플랫폼 — 전 세계를 하나의 감시망으로',
    metaDescription:
      '178개국·52개 언어 현지 보도와 각국 공식 감시 자료 매시간 수집 · 수집·추출·판정·예측·대응 5단계 처리 글로벌 감염병 인텔리전스 플랫폼',
    eyebrow: 'PLATFORM',
    title: '전 세계를 하나의 감시망으로',
    lead: '국경 없는 감염병 · 178개국 현지 보도·각국 보건당국 공식 자료·환경·무역·유전체 신호 단일 체계 통합 · 매시간 국가별 이상 계산 · 신호 → 경보·대응 시나리오 5단계',
    blocks: [
      {
        title: '플랫폼 개요',
        kicker: 'AT A GLANCE',
        tone: 'teal',
        specs: [
          { label: '감시 범위', value: '178개국 · 52개 언어 현지 보도 (피드 179개)' },
          { label: '실시간 수집 소스', value: '23종 · 매시간 자동 수집' },
          { label: '확산 모델 범위', value: '159개국 · 항공 연결 1,671쌍 · 육로 국경 314개' },
          { label: '알고리즘 모듈', value: '118개 (엔진 116 · 온톨로지 YGGDRASIL · 상태변화 BAIKAL MOB)' },
          { label: '공개 API', value: '엔드포인트 128개' },
          { label: '품질 관리', value: '자동 시험 2,263건 — 전부 통과 시에만 운영 반영' },
        ],
        note: '2026-10-19 저장소·운영 기록 기준 실측값',
      },
      {
        title: '01 · 수집',
        kicker: 'STAGE 01',
        tone: 'teal',
        body: '운영 수집 소스 23종 · 매시간 신호 수신 · 국제기구 공식 보고~178개국 현지어 보도 단일 신호 형식 정규화 · 출처별 신뢰도 부여 → 이후 전 계산의 가중치',
        items: [
          { title: '공식 보고', body: 'WHO 아프리카·미주 지역사무소 · 한국 질병관리청 · 일본 감염증 주보 · 홍콩 위생방호센터 · 브라질 InfoDengue — 기관 부여 등급 그대로 반영' },
          { title: '현지어 보도', body: '국제 언론 번역 이전 단계의 현지 첫 보도 · 감시 공백 지역까지 동일 기준 적용' },
          { title: '환경·선행 신호', body: '하수 감시(미국 CDC NWSS) · 재난 감시창(GDACS) · 극지 관찰 · 의료물자 무역 통계 — 발병 여건·대비 행동 변화 선제 포착' },
        ],
      },
      {
        title: '02 · 추출',
        kicker: 'STAGE 02',
        tone: 'sky',
        body: 'PDF 표·기사 본문 → 질병·국가·확진·사망 구조화 · 원칙: 확인된 값만 숫자화',
        points: [
          '표 헤더로 의미 확인된 열만 사용 · 위치 기반 추정 채움 없음 — 숫자의 조용한 어긋남 차단',
          '"최근 7일 신규"·"누적", "의심"·"확진" 별도 항목 분리 집계',
          '"합계" 행 국가 집계 제외 — 추이 분석 순도 유지',
          '추출 숫자 원문 텍스트 교차검증 · 출처 위치 동시 기록',
        ],
      },
      {
        title: '03 · 판정',
        kicker: 'STAGE 03',
        tone: 'crimson',
        body: '이상도 = 절대량이 아닌 **해당 국가·해당 지표의 평소 수준 대비** · 동일 5건도 상시 보고 다수 국가와 조용한 국가에서 의미 상이',
        points: [
          '국가·지표별 기준선 대비 편차 + 미국 CDC EARS 표준 기반 이상도 산출',
          '오래된 신호 기여도 시간 경과에 따라 감소(반감기 감쇠)',
          '"측정 결과 이상 없음"과 "판단할 데이터 없음" 구분 보고',
          '등급별 일일 경보 상한 — 핵심 경보만 상위 노출',
        ],
      },
      {
        title: '04 · 예측',
        kicker: 'STAGE 04',
        tone: 'indigo',
        body: '전파 모델 기반 확산 규모·국가 간 유입 경로 추정 · 159개국 항공·육로 네트워크 위 질병별 문헌 파라미터 시뮬레이션',
        points: [
          '질병별 실측 R0·치명률 기반 모델 보정',
          '접촉 전파 병원체 — **도달 가능 인구** 별도 설정, 현실적 규모 산출',
          '모델 사망자 추정치 — 해당 질병 역사상 최대 발병과 자동 대조, 범위 초과 시 경고 병기',
        ],
      },
      {
        title: '05 · 대응',
        kicker: 'STAGE 05',
        tone: 'forest',
        body: '"무엇이 온다"를 넘어 대응까지 · 무대응 vs 개입 시나리오 비교 — 조치별·강도별 전파 차단 지점 제시',
        items: [
          { title: '무대응 기준선', body: '무조치 시 경로 = 기준선' },
          { title: '개입 비교', body: '격리·거리두기·백신·치료 수준 조합 — 실효 재생산지수 1 미만 진입 지점 탐색' },
          { title: '예측 봉인', body: '예측·시나리오 생성 시점 해시 봉인 — 시점·내용 제3자 검증 가능' },
        ],
      },
    ],
    cta: {
      title: '5단계 실가동 직접 확인',
      body: '수집~대응 전 과정 실시간 화면 · 로그인 없이 라이브 대시보드 접속',
      label: '라이브 대시보드 열기',
      href: '/dashboard',
    },
  },

  // ── 기술 스펙 Ⅰ ───────────────────────────────────────────
  techSpec1: {
    metaTitle: '기술 스펙 Ⅰ — 감시와 수집',
    metaDescription:
      '178개국·52개 언어 현지어 보도 감시 · 공식 보고서 PDF 자동 추출 · 환경·무역·조달 선행지표 · 6계층 이상도 지수 · 보고 침묵 감시 · 2단 탐지 · 소스 건강 감시 — 감시 계층 사양·엔진 정리',
    eyebrow: 'TECHNOLOGY · I',
    title: '감시와 수집',
    lead: '제1계층 = 지구 전체 매시간 감시망 · 무인 자율 가동 · 현지어 보도·공식 보고서·환경 신호·무역·조달 기록에서 "평소와 다른 것" 탐지 · 사양 요약 → 엔진별 원리',
    photo: {
      src: '/media/photos/iss-city-lights.jpg',
      alt: '국제우주정거장에서 내려다본 밤의 도시 불빛',
      caption: '국제우주정거장에서 본 튀르키예의 밤 · 사람·물자 연결망 = 감염병 확산 경로',
      credit: 'NASA JSC · 퍼블릭 도메인',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:The_city_lights_of_T%C3%BCrkiye_sparkle_below_the_International_Space_Station_(iss074e0225549).jpg',
    },
    blocks: [
      {
        title: '감시 계층 사양 요약',
        kicker: 'SPEC SHEET',
        tone: 'teal',
        specs: [
          { label: '현지어 보도', value: '178개국 · 52개 언어 · 피드 179개 · 매시 수집' },
          { label: '보도 분류', value: '언어모델 제목 분류(실제 발병 보도만 선별) + 키워드 폴백' },
          { label: '공식 보고', value: 'WHO 지역사무소 · 각국 보건당국 6곳 · WHO 공식 문서 저장소(IRIS)' },
          { label: '문서 추출', value: 'PDF 표 구조화(NVIDIA 문서 모델) → 정규화 신호 → 추이' },
          { label: '이상도 지수', value: '6계층 가중합(공식 · 비공식 · 행동 · 환경 · 동물 · 설명불가)' },
          { label: '표준 이상탐지', value: '미국 CDC EARS C1 · C2 · C3 + 국가별 z-점수 기준선' },
          { label: '탐지 구조', value: '센티널(빠른 탐지) → 검증 레이어(교차 확인) 2단 구조' },
          { label: '운영 신뢰성', value: '소스 건강 · 품질 불변식 · 능력 장부 — 매 주기 자가 점검' },
        ],
      },
      {
        title: '현지어 보도 감시',
        kicker: 'ENGINE · local_news',
        tone: 'teal',
        body: '최초 신호 = 국제 언론 번역 이전의 현지어 보도 · 178개국 국가·언어별 뉴스 집계 → 감염병 어휘 밀도 측정 · 언어모델 제목 판독 → 실제 발병·집단감염 보도만 선별 · 저위험국 사전 제외 없음 — 팬데믹 발원지는 예측 불가',
        points: [
          '감지 단위 = 국가 × 언어 × 질병 · 국가별 단일 집계창',
          '아프리카·중앙아시아·태평양 도서국 등 상업 감시 사각지대까지 동일 기준 감시',
          '복수 피드의 동일 사건 — 교차언어 클러스터링으로 단일 사건 통합',
          '주 공급원 장애 시 대체 헤드라인 공급자 자동 전환 — 감시 무중단',
        ],
      },
      {
        title: '공식 보고서 자동 추출',
        kicker: 'ENGINE · who_iris → pdf_table_extract → bulletin_*',
        tone: 'sky',
        body: '국가·질병별 핵심 수치가 PDF 표 안에만 존재하는 문서 다수(WHO 아프리카 주간 상황보고서 등) · WHO 공식 문서 저장소 수집 → 문서 모델 표 복원 → 정규화 신호 적재 → 회차 연결 추이 산출',
        items: [
          { title: '수집', body: 'WHO IRIS 주간 보고서 안정 수집 · 적재 완료 회차 중복 수집 없음', meta: 'who_iris · bulletin_collect' },
          { title: '표 복원', body: 'NVIDIA 문서 모델 기반 PDF 표 행·열 구조 복원', meta: 'pdf_table_extract' },
          { title: '신호화 · 적재', body: '"7일 신규"·"누적"·"의심"·"확진" 분리 정규화 · 경보 엔진 입력 형식 적재', meta: 'bulletin_signals · bulletin_ingest' },
          { title: '추이', body: '회차별 점 신호 → 시계열 · 증가 속도·방향 분석', meta: 'bulletin_trend' },
        ],
      },
      {
        title: '환경 · 무역 · 조달 선행지표',
        kicker: 'ENGINE · disaster_watch · polar_* · comtrade_signals · procurement_watch',
        tone: 'forest',
        body: '의료 시스템 밖의 선행 흔적 · 재난·기후·극지 변화·의료물자 수입·정부 조달 공고 = 발병 자체가 아닌 발병 여건·대비 행동 신호 · 별도 계층 감시',
        items: [
          { title: '재난 감시창', body: '홍수·지진·태풍 후 수인성·매개체 감염병 고위험 기간 — 해당 국가 감시 문턱 하향', meta: 'disaster_watch · GDACS' },
          { title: '극지 · 빙하', body: '영구동토·27개 빙하 산맥 지역 변화 — 기준선·추세 동시 관찰', meta: 'polar_signals · polar_baseline · polar_trend · glacier_regions' },
          { title: '기후 · 산림', body: '기온·강수 이상, 산림 손실·화재 — 스필오버 여건 지표', meta: 'climate_signals · forest_signals · deforestation_signals' },
          { title: '의료물자 무역', body: 'UN Comtrade 기반 마스크·방호장비·진단키트 국가별 수입 급증 감지', meta: 'comtrade_signals' },
          { title: '정부 조달', body: '나라장터 입찰공고 — 바이오안보 관련 구매 동향 추적', meta: 'procurement_watch' },
          { title: '하수 · 동물', body: '미국 하수 처리장 병원체 농도 · 세계동물보건기구(WOAH) 동물 발병 보고', meta: 'CDC NWSS · wahis' },
        ],
      },
      {
        title: '6계층 이상도 지수와 표준 이상탐지',
        kicker: 'ENGINE · gai · ears · anomaly_engine · kdca_anomaly',
        tone: 'crimson',
        body: '공식·비공식·행동·환경·동물·설명불가 6개 층 신호 — 각 층 평소 수준 대비 이상도 환산 × 출처 신뢰도 → 단일 지수(GAI) · 감시역학 표준 미국 CDC EARS C1·C2·C3 결합 — 짧은 기준선 신호도 안정적 탐지',
        points: [
          '신호별 고유 과거 분포 대비 z-점수 환산 · 최신값 기준선 계산 제외',
          '층별 출처 신뢰도 가중치 차등 — 정부 공식 자료 ≠ 소셜 게시물',
          'EARS 가드밴드 — 발병 초기값의 기준선 오염 차단',
          '한국 법정감염병 질병별 개별 급증 탐지 — 총합에 묻히는 개별 질병 변화 포착',
        ],
      },
      {
        title: '보고 침묵 · 설명 불가 · 고위험 병원체',
        kicker: 'ENGINE · negative_space · unexplained · pathogen_sentinel',
        tone: 'violet',
        body: '숫자 증가 외의 위험 · 카운트 기반 탐지 사각지대 3개 유형 — 전담 엔진 감시',
        items: [
          { title: '보고 침묵 감시', body: '활발하던 보고 채널의 기준선 절반 이하 급감 = 신호 · 표적: 보고 체계 붕괴가 확산에 선행하는 사례(2014년 기니 에볼라)', meta: 'negative_space' },
          { title: '설명 불가 집단 발병', body: '기존 질병 패턴 불일치 집단 발병 별도 집계 · 2019년 12월 우한 원인불명 폐렴 유형', meta: 'unexplained' },
          { title: '고위험 병원체 단건 감시', body: '페스트·탄저·두창 등 단건 = 뉴스 병원체 — 누적 대기 없이 단건 보도 즉시 상향', meta: 'pathogen_sentinel' },
        ],
      },
      {
        title: '2단 탐지와 운영 신뢰성',
        kicker: 'ENGINE · sentinel · verification · source_health · quality_health',
        tone: 'sky',
        body: '빠른 탐지·정확한 확인 엔진 분리 · 센티널 — 기준선 2배 초과 움직임 즉시 대기열 등록 · 검증 레이어 — 실시간 검색 교차 확인 · 전체 정상 여부 — 별도 계층 매 주기 감시',
        items: [
          { title: '센티널', body: '누락 방지 우선 · 낮은 문턱의 빠른 탐지층', meta: 'sentinel' },
          { title: '검증 레이어', body: '센티널 항목 실시간 웹 검색 확인 · 확정·기각 기록', meta: 'verification' },
          { title: '소스 건강', body: '수집 실행 여부가 아닌 실제 값 유입 여부 집계', meta: 'source_health' },
          { title: '품질 불변식', body: '소스 정상·계산 붕괴 사례 별도 포착', meta: 'quality_health · capability_ledger' },
        ],
      },
    ],
    cta: {
      title: '분석·대응 계층 — 기술 스펙 Ⅱ',
      body: '국가 위험지수 · 7·14일 예보 · 159개국 확산 시뮬레이션 · 경보별 개입 시나리오 · 유전체 스크리닝 · 예측 자기검증',
      label: '기술 스펙 Ⅱ 보기',
      href: 'technology-advanced',
    },
  },

  // ── 기술 스펙 Ⅱ ───────────────────────────────────────────
  techSpec2: {
    metaTitle: '기술 스펙 Ⅱ — 분석과 대응',
    metaDescription:
      '국가 위험지수 · 경보 피로 방지 · 7·14일 예보 · 나우캐스트 학습 체계 · 159개국 확산 디지털 트윈 · 유입 시점 추정 · 경보별 개입 시나리오 · 유전체 스크리닝 · 예측 채점·봉인 — 분석·대응 계층 사양·엔진 정리',
    eyebrow: 'TECHNOLOGY · II',
    title: '분석과 대응',
    lead: '감시 계층 = "무엇이 다른가" · 분석·대응 계층 = "어디가, 얼마나, 무엇을 해야 하는가" · 국가별 위험 계량 · 확산 시뮬레이션 · 개입 효과 비교 · 전 예측 자기 채점',
    photo: {
      src: '/media/photos/avian-influenza-h5n1.jpg',
      alt: '조류인플루엔자 A(H5N1) 바이러스 입자의 투과전자현미경 사진(채색)',
      caption: '조류인플루엔자 A(H5N1) 바이러스 입자 · 투과전자현미경(채색) · 미국 CDC 공개 자료',
      credit: 'CDC / Cynthia Goldsmith · 퍼블릭 도메인',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Colorized_transmission_electron_micrograph_of_Avian_influenza_A_H5N1_viruses.jpg',
    },
    blocks: [
      {
        title: '분석 · 대응 계층 사양 요약',
        kicker: 'SPEC SHEET',
        tone: 'indigo',
        specs: [
          { label: '국가 위험지수', value: '원시 위험도 × 국가 취약성(의료 인프라 · 인구밀도 · 공항 연결성 · 국경 이동량)' },
          { label: '경보 체계', value: 'Critical 90+ (일 3건) · High 80+ (일 5건) · Medium 70+ · 텔레그램 실시간 알림' },
          { label: '추세 예보', value: '7일 · 14일 — 선형회귀 · 지수평활 앙상블' },
          { label: '확산 디지털 트윈', value: '메타개체군 SEIR · 159개국 · 항공 1,671쌍 · 육로 314개' },
          { label: '질병 파라미터', value: '14종 질병의 문헌 실측 R0 · 치명률' },
          { label: '유전체 스크리닝', value: '조성 통계 · Evo2 순서 자연성 · ColabFold 상동성 커버리지' },
          { label: '자기검증', value: '자동 채점(적중 · Brier · 보정) · 선행성 원장 · 비트코인 체인 봉인' },
        ],
      },
      {
        title: '국가 위험지수와 경보 피로 방지',
        kicker: 'ENGINE · country_risk · alerts · notifier',
        tone: 'crimson',
        body: '국가별 최종 위험도 = 신호 기반 원시 위험도 × 국가 취약성 · 동일 신호도 의료 인프라 취약·국제선 연결 다수 국가에서 위험 증폭 · 등급·일일 상한 필터 — 핵심 경보만 즉시 전달',
        points: [
          '공식 수치(한국·브라질·일본·홍콩) + 보도 추출값 — 출처 신뢰도 가중 합산',
          '취약성 지수 — 세계은행 등 공개 지표 실측값',
          'Critical·High 경보 텔레그램 즉시 전달 · 상한 초과 후보도 삭제 없이 기록 보존',
        ],
      },
      {
        title: '예보와 나우캐스트 학습 체계',
        kicker: 'ENGINE · forecast_engine · nowcast_*',
        tone: 'indigo',
        body: '지표별 시계열 7일·14일 외삽 → 일일 브리핑 반영 · 별도 나우캐스트 체계 — "실제 발병으로 이어진 신호" 학습 · 과거 공식 선언 + 당시 보도량 기반 학습셋 자동 조립 · 미학습 미래 구간 전용 평가 · 재현율·오경보율 균형점 운영 정책별 선택',
        items: [
          { title: '학습셋 자동 조립', body: '공식 선언(라벨) + 당시 보도량(특징) 매일 누적', meta: 'nowcast_dataset · nowcast_backfill' },
          { title: '전향적 평가', body: '학습 데이터가 아닌 당시 미지의 미래 구간으로만 채점', meta: 'nowcast_eval' },
          { title: '운영점 선택', body: '재현율·오경보율 사이 조직별 목표 지점 선택', meta: 'nowcast_threshold' },
        ],
      },
      {
        title: '확산 디지털 트윈과 유입 추정',
        kicker: 'ENGINE · digital_twin · country_borders · global_inflow',
        tone: 'indigo',
        body: '메타개체군 SEIR 모델 — 노드 159개국 · 간선 = 실제 항공 노선 1,671개 국가쌍 + 육로 국경 314개 · 발원국·질병 입력 → 국가별 도달 시점·규모 시뮬레이션 · 경로 미도달 국가와 데이터 부재 국가 구분 보고',
        items: [
          { title: '국가 간 확산', body: '항공 여객 + 육로 이동 동시 반영 · 국가별 도달 순서 산출', meta: 'digital_twin · country_borders' },
          { title: '국내 유입 시점', body: '발원 도시 국제선 여객량·비행시간·초기 성장률 기반 국내 첫 유입 일수·입국 관문별 위험 추정', meta: 'global_inflow · origin_catalog' },
          { title: '지역 단위 세분화', body: '국가 단위 위험 → 행정구역 단위 세분화', meta: 'geo_resolution' },
        ],
      },
      {
        title: '경보별 개입 시나리오',
        kicker: 'ENGINE · alert_intervention · defense · disease_params · decision_tree',
        tone: 'forest',
        body: '신규 Critical·High 경보별 질병 파라미터 기반 SEIR 방어 시뮬레이션 · 무대응 vs 개입 — 사망·병상 초과 일수 차이 경보 동봉 · "무엇이 오는가" → "어떤 조치가 무엇을 바꾸는가"',
        points: [
          '격리·거리두기·백신 접종 시작 시점·강도 조정 — 실효 재생산수 1 미만 조합 탐색',
          '14종 질병 문헌 실측 R0·치명률 보정 · 결과는 "모델 시나리오" 표기',
          '위험 수준별 대응 권고 — 규칙 기반 의사결정 트리 즉시 생성',
        ],
      },
      {
        title: '유전체 스크리닝 (HEIMDALL)',
        kicker: 'ENGINE · genome_signals · evo2_naturalness · msa_homology',
        tone: 'violet',
        body: '서열 3각도 분석 · 조성 통계 = 염기 구성 · Evo2 = 순서 자연성 · 상동성 검색 = 자연계 단백질 기반 서열 전체 설명 가능 여부 · 방어적 탐지 전용 · 결과 = 판정 아닌 정밀 검토 우선순위',
        points: [
          '조성 통계(CAI·CpG) — 자연계 상이 구성 표적 · Evo2 순서 자연성 — 이어붙임·재조합 구간 표적',
          '상동성 검색 = 학습 모델이 아닌 공개 데이터베이스 조회 — Evo2 미적용 병원체에도 그대로 작동',
          'Evo2 진핵 숙주 감염 바이러스 학습 제외 — 적용 범위 선언 후 판정 · 범위 밖은 점수 보고, 플래그 미상향',
        ],
        note: '세부 사양·분류군별 실측 근거 — 스페셜 프로그램(HEIMDALL) 정리',
      },
      {
        title: '자기검증 — 채점과 봉인',
        kicker: 'ENGINE · prediction_resolver · lead_time_ledger · prediction_timestamp',
        tone: 'teal',
        body: '예측의 기록 증명 — 검증 코드 내장 · 기록 예측 × 이후 공식 선언 매일 대조 채점 · 신호 최초 관측 시각 선언 이전 고정 · 전 예측 생성 시점 봉인',
        items: [
          { title: '예측 자동 채점', body: '미해소 예측 매일 공식 선언 대조 → 적중·실패·판정 보류 구분 · 조회수·확진자 갱신 정답 미사용 — 자기 신호 자기 채점 순환 차단', meta: 'prediction_resolver · prediction_scoring' },
          { title: '선행성 원장', body: '신호 최초 관측 시각 공식 선언 이전 기록 · 선언 후 역산 선행일수 실측 불인정', meta: 'lead_time_ledger' },
          { title: '예측 봉인', body: '예측 기록 SHA-256 해시 OpenTimestamps 비트코인 블록체인 고정 · 사후 수정 예측 아님 제3자 직접 검증 가능', meta: 'prediction_timestamp' },
        ],
      },
    ],
    cta: {
      title: '두 계층 — 단일 사슬',
      body: '감지 → 판정 → 예측 → 시뮬레이션 → 처방 → 자기검증 → 봉인 · 실가동 사슬 = 라이브 대시보드',
      label: '라이브 대시보드',
      href: '/dashboard',
    },
  },

  // ── 엔진 카탈로그 ─────────────────────────────────────────
  engines: {
    metaTitle: '엔진 카탈로그 — 116개 모듈 전체 지도',
    metaDescription:
      '116개 알고리즘 모듈 — 감시·추출·판정·예측·유전체·대응제·검증 7개 묶음 전수 나열 · 모듈별 기능·가동 주기(매시/요청 시) 병기',
    eyebrow: 'ENGINE CATALOGUE',
    title: '116개 모듈, 7개 시스템',
    lead: '단일 거대 모델이 아닌 — 각 1개 기능 특화 모듈 116개 결합 시스템 · 전 세계 감시에 필요한 각도의 수 · 핵심 모듈을 7개 시스템(HUGINN 후긴·MIMIR 미미르·FORSETI 포르세티·SKULD 스쿨드·HEIMDALL 헤임달·VALHALLA 발할라·VAR 바르)으로 편성함 · 3층 구조의 기반 계층 — 상세: BAIKAL MOB',
    blocks: [
      {
        title: 'HUGINN · 후긴 — 감시 — 신호 수집·이상 탐지',
        kicker: 'SYSTEM 01 · HUGINN',
        tone: 'teal',
        items: [
          { title: '현지어 보도 감시', body: '178개국·52개 언어 뉴스 집계 → 발병 보도 선별', meta: 'local_news · cerebras/groq 분류 · 매시' },
          { title: '6계층 이상도 지수', body: '6개 층 신호 평소 대비 이상도 합산 → 단일 지수', meta: 'gai · 매시' },
          { title: '보고 침묵 감시', body: '활발하던 채널의 침묵 = 신호', meta: 'negative_space · 매시' },
          { title: '설명 불가 집단 발병', body: '기존 질병 미설명 집단 발병 별도 집계', meta: 'unexplained · 매시' },
          { title: '고위험 병원체 단건', body: '페스트·탄저 등 단건 = 뉴스 병원체 단건 상향', meta: 'pathogen_sentinel · 매시' },
          { title: '표준 이상탐지', body: '미국 CDC EARS C1·C2·C3 + z-점수 기준선 이상 탐지', meta: 'ears · anomaly_engine · kdca_anomaly' },
          { title: '2단 탐지', body: '빠른 센티널 상향 → 검증 레이어 교차 확인', meta: 'sentinel · verification' },
          { title: '재난·극지·기후', body: '발병 여건 변화 환경 신호 = 선행지표', meta: 'disaster_watch · polar_* · climate_signals' },
          { title: '무역·조달·동물', body: '의료물자 수입·정부 조달·동물 발병 추적', meta: 'comtrade_signals · procurement_watch · wahis' },
        ],
      },
      {
        title: 'MIMIR · 미미르 — 추출 — 문장·표 → 숫자',
        kicker: 'SYSTEM 02 · MIMIR',
        tone: 'sky',
        items: [
          { title: 'PDF 표 추출', body: '보건 보고서 표 행·열 구조 복원', meta: 'pdf_table_extract' },
          { title: '보고서 신호화·적재', body: '복원 표 → 정규화 신호 적재·추이 산출', meta: 'bulletin_signals · bulletin_ingest · bulletin_trend' },
          { title: 'NLP 신호 추출', body: '자유문장 보도 → 구조화 JSON 집계화', meta: 'nlp_extract' },
          { title: '국가명 해소', body: '자유문장 위치 → ISO 국가코드', meta: 'country_resolve · geo_resolution' },
          { title: '이벤트 중복제거', body: '복수 출처 동일 사건 통합 — 중복 경보 차단', meta: 'event_dedup' },
          { title: '추출 모델 계층', body: '추출 경로 단일 지점 전환 — 독자 모델 교체 가능', meta: 'aegiron_model · nvidia' },
        ],
      },
      {
        title: 'FORSETI · 포르세티 — 판정 — 경보 상향 여부 선별',
        kicker: 'SYSTEM 03 · FORSETI',
        tone: 'crimson',
        items: [
          { title: '국가 위험지수', body: '원시 위험도 × 국가 취약성 → 최종 위험', meta: 'country_risk · country_indicators' },
          { title: '경보 피로 방지', body: '등급·일일 상한 — 핵심 경보만 잔류', meta: 'alerts' },
          { title: '실시간 알림', body: 'Critical·High 경보 텔레그램 즉시 전달', meta: 'notifier' },
          { title: '신뢰도 엔진', body: '루머·추정 vs 공식 1차 자료 차등 가중', meta: 'trust' },
          { title: '리스크 계량화', body: '보험·금융 비교용 상대 지표 산출', meta: 'risk_quantification' },
        ],
      },
      {
        title: 'SKULD · 스쿨드 — 예측 · 시뮬레이션 — 확산 경로 추정',
        kicker: 'SYSTEM 04 · SKULD',
        tone: 'indigo',
        items: [
          { title: '7·14일 예보', body: '지표 시계열 앙상블 외삽', meta: 'forecast_engine' },
          { title: '확산 디지털 트윈', body: '159개국 항공·육로 네트워크 SEIR 시뮬레이션', meta: 'digital_twin · country_borders' },
          { title: '국내 유입 시점', body: '발원지 → 국내 첫 유입 일수 추정', meta: 'global_inflow · origin_catalog' },
          { title: '나우캐스트 학습', body: '신호→발병 학습셋 조립·전향적 평가', meta: 'nowcast_dataset · nowcast_eval' },
          { title: '지식 그래프', body: '원인-결과 인과 체인 기반 신호 해석', meta: 'knowledge_graph' },
          { title: '유입 주간 보고서', body: '국가 이상도 × 한국 직항 연결 → ISO 주마다 한 장 · 노출 지수는 확률 아님', meta: 'korea_import_report' },
        ],
      },
      {
        title: 'HEIMDALL · 헤임달 — 유전체 — 서열 방어적 판독',
        kicker: 'SYSTEM 05 · HEIMDALL',
        tone: 'violet',
        items: [
          { title: '조성 통계', body: 'CAI·CpG 등 서열 구성 부자연성 탐지', meta: 'genome_signals' },
          { title: '순서 자연성', body: 'Evo2 기반 서열 순서 자연성 실측', meta: 'evo2_naturalness' },
          { title: '상동성 키메라 탐지', body: '자연계 단백질 기반 서열 전체 커버 여부 검색', meta: 'msa_homology' },
          { title: '계통 추적', body: 'Nextstrain 재분석 — 우세 계통 변화 판독', meta: 'genomic_variants' },
        ],
      },
      {
        title: 'VALHALLA · 발할라 — 대응제 — 방어 수단 집계 (VALHALLA)',
        kicker: 'SYSTEM 06 · VALHALLA',
        tone: 'forest',
        items: [
          { title: '커버리지 격차', body: '현 비축·승인 제품 미방어 위협 식별', meta: 'countermeasure_stockpile · approved_products' },
          { title: '생산 주권', body: '"생산 가능 지점 수" — WHO 목록 기반', meta: 'vaccine_supply · countermeasure_pipeline' },
          { title: '준비태세 범위', body: '국내 비축·세계 수단 범위별 분류 응답', meta: 'readiness_scopes · ihr_capacity' },
          { title: '개입 시나리오', body: '경보별 무대응 vs 개입 차이 시뮬레이션', meta: 'alert_intervention · defense' },
          { title: '발할라 감시', body: '대응제 준비태세 일일 누적·추이 산출', meta: 'valhalla_watch' },
        ],
      },
      {
        title: 'VAR · 바르 — 검증 — 자체 수치 자가 점검',
        kicker: 'SYSTEM 07 · VAR',
        tone: 'teal',
        items: [
          { title: '예측 자동 채점', body: '예측 × 공식 선언 대조 → 적중·실패·보류 구분', meta: 'prediction_resolver · prediction_scoring' },
          { title: '선행성 원장', body: '신호 최초 관측 시각 선언 이전 고정', meta: 'lead_time_ledger' },
          { title: '예측 봉인', body: '예측 해시 비트코인 체인 고정', meta: 'prediction_timestamp' },
          { title: '주간 추세 예측', body: '일본 공식 주간 표본감시 다음 주 증감 봉인·자동 채점 · 90일 예측과 별도 채점표', meta: 'weekly_forecast' },
          { title: '소스 건강', body: '실제 값 유입 여부 매 주기 집계', meta: 'source_health' },
          { title: '품질 불변식', body: '소스 정상·계산 붕괴 사례 포착', meta: 'quality_health · capability_ledger' },
          { title: '런칭 준비도', body: '"런칭 가능 여부" — 의견 아닌 측정값 응답', meta: 'launch_readiness' },
        ],
      },
    ],
    cta: {
      title: '엔진 실제 산출값 확인',
      body: '대시보드 = 이 모듈들의 실시간 신호·지표 원본',
      label: '라이브 대시보드 열기',
      href: '/dashboard',
    },
  },

  // ── 스페셜 프로그램 ───────────────────────────────────────
  programs: {
    metaTitle: '스페셜 프로그램 — HEIMDALL · VALHALLA',
    metaDescription:
      '두 내부 R&D 프로그램 · HEIMDALL = 방어적 유전체 스크리닝 · VALHALLA = 대응제 준비태세 · 능력 과장 없는 정직성 경계선 내 운영',
    eyebrow: 'SPECIAL PROGRAMS',
    title: 'HEIMDALL · VALHALLA',
    lead: '감시 계층 대부분 공개 운영 · 성격 상이한 2개 축 — 생물학적 위협 유전체 스크리닝 · 국가 대응제 준비태세 · R&D형 별도 프로그램 · 본 페이지 = 수행·비수행 범위, 능력 과장 없는 기술',
    photo: {
      src: '/media/photos/ebola-virion.jpg',
      alt: '에볼라 바이러스 입자의 투과전자현미경 사진(채색)',
      caption: '에볼라 바이러스 입자 · 투과전자현미경(채색) · 미국 CDC 공개 자료 · 아이기론 실험 자료 아님',
      credit: 'CDC / Cynthia Goldsmith · 퍼블릭 도메인',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Ebola_virus_virion.jpg',
    },
    blocks: [
      {
        title: 'HEIMDALL — 방어적 유전체 스크리닝',
        kicker: 'PROGRAM · HEIMDALL',
        tone: 'violet',
        deep: true,
        body: '명칭 유래 = 북유럽 신화 다리 감시자 · 기능 = 유전체 서열의 자연 진화 통계 이탈 신호 탐지·플래그 · 바이오안보 스크리닝의 방어 기능 · 조성 통계·순서 자연성·상동성 커버리지 동시 분석(기술 스펙 Ⅱ 유전체 계층)',
        points: [
          '**방어적 탐지 전용** · 서열 설계·합성·최적화·스크리닝 회피 방법 미제공',
          '결과 = 판정 아닌 "정밀 검토 우선순위" · 최종 판정 — 전문가·습식 실험 필요',
          '적용 범위 = 세균·고균·진핵 유전체·파지 · 진핵 숙주 감염 바이러스 = 모델 한계로 범위 밖, 응답에 명시',
        ],
        note: '엔드포인트 인증 필수 · 전 접근 감사 로그 기록 · 기밀 = 접근 통제이지 미검증의 검증 위장 아님',
      },
      {
        title: 'VALHALLA — 대응제 준비태세',
        kicker: 'PROGRAM · VALHALLA',
        tone: 'forest',
        deep: true,
        body: '분자 수준 중화 예측 모사 대신 실제 응답 가능 질문에 응답 — "현 비축 미방어 위협(커버리지 격차), 방어 품목 중 국내 생산 불가 품목(생산 주권 격차)" · 국가 바이오안보 기획 핵심 질문 · 전부 공개 자료 계산',
        items: [
          { title: '커버리지 격차', body: '질병별 국제 비상 비축·규제 승인 제품 존재 여부 · 국가 비축량 등 비공개 정보 미취급', meta: 'WHO ICG · openFDA 등 공개 자료' },
          { title: '생산 주권', body: 'WHO 사전적격성 목록 기반 "생산 가능 지점 수" · 단일 공급원 품목 = 병목 노출', meta: '공급 단일점 = 비축 재보충 불가 위험' },
          { title: '개발 단계', body: 'ClinicalTrials.gov 기반 "개발 중" 임상 단계 세분 · "비축 없음" 혼재 상태 구분', meta: '대비 우선순위 구분 기준' },
        ],
      },
      {
        title: '정직성 경계선',
        accent: true,
        body: '양 프로그램 공통 운영 원칙 = 능력 과장 금지 · 코드 주석 경계선 고정 · 응답 동봉',
        points: [
          'HEIMDALL = **판정 아닌 스크리닝 우선순위** 산출',
          'VALHALLA 효능 = 대응제별 **선언(라벨) 효능 집계** · 분자 중화 예측 아님',
          '데이터 부재 시 보수적 "커버리지 불명" 처리',
        ],
        note: '프로그램 코드명·조직 구조 = 아이기론 자체 내부 정의 · 실제 정부기관 소속·공식 기밀등급 아님',
      },
    ],
    cta: {
      title: '유전체·확산 엔진의 실측 근거',
      body: '유전체 판독의 분류군별 실측 결과와 확산 시뮬레이션 네트워크의 한계 — 기술 스펙 Ⅱ에 정리함',
      label: '기술 스펙 Ⅱ 보기',
      href: 'technology-advanced',
    },
  },

  // ── 검증과 한계 ───────────────────────────────────────────
  transparency: {
    metaTitle: '검증과 한계 — 시스템 자가 검증 방식',
    metaDescription:
      '검증의 시스템 내장 방식 · 알려진 한계·데이터 공백 동시 공개 · 숫자의 근거 초과 사용 방지 장치',
    eyebrow: 'VALIDATION & LIMITS',
    title: '검증과 한계',
    lead: '감염병 감시 최대 위험 = 틀린 예측이 아닌, 틀림 여부 확인 불가 예측 · 검증 장치 코드 내장 · 시스템 자가 수치 점검 방식·알려진 한계 동시 공개',
    blocks: [
      {
        title: '시스템 자가 수행 검증',
        kicker: 'SELF-CHECK',
        tone: 'teal',
        body: '한계 문서 전용 기록 시 숫자만 분리되어 화면·보고서 유입 · 검증 장치 코드 내장',
        points: [
          '**역사 대조** — 모델 사망자 추정 × 해당 질병 역사상 최대 발병 자동 비교 · 범위 대폭 초과 시 "대외 자료 사용 금지" 경고 응답 동봉',
          '**실패 원인 분리** — 발병 누락 시 "모델 미탐지"와 "데이터 부재 미탐지" 구분 보고 · 혼재 시 진단 역전',
          '**전향적 평가** — 성능 채점 = 학습 데이터 아닌 "당시 미지의 미래" 전용',
          '**출처 표시** — 병명·국가의 표 외 문맥 추출 시 출처 동시 기록',
        ],
      },
      {
        title: '예측의 기록 증명 방식',
        kicker: 'PROOF',
        tone: 'indigo',
        body: '"선행 인지" 주장 = 증명 경로 존재 시에만 유효 · 전 예측 생성 시점 봉인 · 이후 공식 선언 매일 자동 대조 채점 · 트랙레코드 = 주장 아닌 봉인 기록 축적',
        points: [
          '예측 기록 해시 비트코인 블록체인 고정 — 사후 수정 불가',
          '신호 최초 관측 시각 공식 선언 이전 고정 — 선행성 실시간 전용 인정',
          '조회수 급증·확진자 갱신 정답 미사용 — 자기 신호 자기 채점 순환 차단',
        ],
      },
      {
        title: '알려진 한계',
        kicker: 'KNOWN LIMITS',
        tone: 'amber',
        items: [
          { title: '수집 공백', body: '일부 국가·기간 신호 결측 가능 · 시스템 자가 결측 구간 보고', meta: '공백 비은폐·표시' },
          { title: '경보 임계값', body: '경보 상향 민감도 = 기술 아닌 운영 정책 · 단일 "정답" 임계값 미제시', meta: '조직 선택 운영점' },
          { title: '기계 추출', body: 'PDF 표 추출 오독 가능 — 원문 교차검증 결합 · 미확인 값 별도 표시', meta: '미검증 값 구분 표기' },
          { title: '현지어 처리', body: '자동 번역 대신 언어모델 분류·키워드 매칭 · 번역 중 병명 소실·역전 회피 선택', meta: '정확도 위한 설계 선택' },
        ],
      },
      {
        title: '한계 선공개 이유',
        body: '현 시점 고객 계약 부재 — 한계 선공개 가능 · 실사 직접 검증 가능한 신뢰 근거 · 재보험사·정부 평가위원 1순위 확인 항목 = "자기 한계 정확 인지 여부"',
      },
    ],
    cta: {
      title: '오류 발견 시',
      body: '본 페이지 내용 부정확·누락 한계 제보 접수 · 확인 후 반영',
      label: '문의하기',
      href: 'contact',
    },
  },

  // ── 데이터 소스 ───────────────────────────────────────────
  dataSources: {
    metaTitle: '데이터 소스 — 운영 중인 23종 전부 공개',
    metaDescription:
      '매시간 수집 23종 데이터 소스 성격별 공개 · 소스별 관측 대상·원천 갱신 주기 병기',
    eyebrow: 'DATA SOURCES',
    title: '데이터 소스 23종',
    lead: '판단 근거 공개 = 판단 검증 가능성 · 운영 수집 소스 성격별 전수 기재 · 소스별 관측 대상 명시',
    blocks: [
      {
        title: '공식 보건당국',
        kicker: 'OFFICIAL',
        tone: 'teal',
        body: '최고 신뢰도 · 공식 확인 절차 — 최후행 신호 · 타 신호 대조 기준선 역할',
        items: [
          { title: 'WHO 아프리카 지역사무소', body: '아프리카 지역 발병 공지·상황 보고', meta: '원천 갱신: 수시' },
          { title: 'WHO 미주 지역사무소(PAHO)', body: '미주 지역 역학 경보·업데이트', meta: '원천 갱신: 수시' },
          { title: '한국 질병관리청', body: '국내 법정감염병 주간 신고 집계', meta: '원천 갱신: 주 1회' },
          { title: '일본 감염증 주보(IDWR)', body: '일본 국립감염증연구소 표본감시 주간 집계', meta: '원천 갱신: 주 1회' },
          { title: '홍콩 위생방호센터', body: '감염병 감시 공지·조류인플루엔자 정기 보고', meta: '원천 갱신: 수시' },
          { title: '브라질 InfoDengue', body: '도시 단위 뎅기열 실효 재생산수·경보 단계', meta: '원천 갱신: 주 1회' },
        ],
      },
      {
        title: '학술·전문 매체',
        kicker: 'ACADEMIC',
        tone: 'sky',
        body: '공식 발표 대비 선행 가능 · 단독 경보 등급 미상향 · 타 층 중첩 시 무게 획득',
        items: [
          { title: 'CDC Emerging Infectious Diseases', body: '미국 CDC 신종 감염병 학술지', meta: '원천 갱신: 수시' },
          { title: 'CIDRAP', body: '미네소타대 감염병연구정책센터 질병별 보도', meta: '원천 갱신: 수시' },
          { title: 'PubMed', body: '특정 병원체 관련 논문 수 추이', meta: '원천 갱신: 일 단위' },
          { title: 'medRxiv', body: '동료 평가 전 의학 프리프린트 편수', meta: '원천 갱신: 일 단위' },
        ],
      },
      {
        title: '보도·관심도',
        kicker: 'REPORTING',
        tone: 'crimson',
        body: '최속 신호 · 잡음 다수 — 신뢰도 하향·타 축 대조 사용',
        items: [
          { title: '현지어 보도', body: '178개국·52개 언어 뉴스 집계 피드(179개) · 판정 애매 피드 언어모델 재분류', meta: '원천 갱신: 매시' },
          { title: 'NewsWatch', body: '웹 검색 결과 요약 기반 주요 감염병 보도 동향', meta: '원천 갱신: 매시' },
          { title: '네이버 검색 트렌드', body: '국내 독감·코로나·에볼라 검색 비율', meta: '원천 갱신: 일 단위' },
          { title: 'Mastodon', body: '질병별 해시태그 게시자 수(최근 7일 창)', meta: '원천 갱신: 매시' },
          { title: 'Wikipedia 조회수', body: '에볼라 관련 문서 조회량', meta: '원천 갱신: 일 단위' },
          { title: 'Polymarket', body: '신규 팬데믹 관련 예측시장 가격 · 집단적 판단일 뿐 근거 아님', meta: '원천 갱신: 매시' },
        ],
      },
      {
        title: '환경·동물·대비 행동',
        kicker: 'ENVIRONMENT',
        tone: 'forest',
        body: '발병 자체 아닌 발병 여건·대비 행동 관측 · 타 축 정적 시 선행 가능 신호',
        items: [
          { title: '하수 감시(CDC NWSS)', body: '미국 하수 처리장 병원체 농도 · 증상 발현 전 단계 신호', meta: '원천 갱신: 주 단위' },
          { title: 'WAHIS 동물질병', body: '세계동물보건기구 동물 발병 보고 · 인수공통감염병 동물 단계 신호', meta: '원천 갱신: 수시' },
          { title: '재난 감시창(GDACS)', body: '홍수·지진·태풍 후 감염병 고위험 기간 — 해당 국가 감시 문턱 하향', meta: '원천 갱신: 수시' },
          { title: '극지 관찰', body: '영구동토 해빙·극지 조류인플루엔자 관련 신호 · 경보 아닌 관찰 대상', meta: '원천 갱신: 일 단위' },
          { title: '공급망 신호', body: '해열제·마스크 등 의약품 수요 관련 검색 추이', meta: '원천 갱신: 일 단위' },
        ],
      },
      {
        title: '유전체·대응제',
        kicker: 'GENOMICS',
        tone: 'violet',
        items: [
          { title: 'Nextstrain 계통 추적', body: '공개 시퀀스 재분석 우세 계통 구성비·신규 계통 출현 · 갱신 정지 빌드 미사용', meta: '원천 갱신: 빌드별 상이' },
          { title: 'VALHALLA 대응제 자료', body: 'WHO 사전적격성 목록·ClinicalTrials.gov·국내 조달 공고(나라장터) 등 대응제 준비태세 공개 자료', meta: '원천 갱신: 일·월 단위 혼합' },
        ],
        note: '2026-10-18 운영 소스 건강 점검 기준 · 현재 정상 소스 수 = 홈 가동 배지 실시간 표시',
      },
    ],
    cta: {
      title: '소스별 현재 상태 확인',
      body: '대시보드 — 소스별 최근 수집 상태·해당 신호 산출 지표 원본 확인',
      label: '라이브 대시보드 열기',
      href: '/dashboard',
    },
  },

  // ── 방법론 ────────────────────────────────────────────────
  methodology: {
    metaTitle: '방법론 — 4개 층 구조',
    metaDescription:
      '방법론 4개 층 — 수집층·추출층·분석층·예측층 · 역학·감시역학 검증 방법의 일일 자동 가동 제품화 구조',
    eyebrow: 'METHODOLOGY',
    title: '4개 층으로 나눈 방법론',
    lead: '감염병 역학·감시역학 검증 방법의 일일 자동 가동 제품화 · 층별 준거 표준 명시',
    blocks: [
      {
        title: '1층 · 수집',
        kicker: 'LAYER 01',
        tone: 'teal',
        body: '성격 상이 23종 수집 소스 단일 신호 형식 정규화 · 출처별 신뢰도 차등 — 값+신뢰도 동시 저장, 이후 전 계산 가중치',
      },
      {
        title: '2층 · 추출',
        kicker: 'LAYER 02',
        tone: 'sky',
        body: '비정형 문서(PDF 표·기사 본문) → 구조화 수치 · 문서 블록 단위 해석 → 추출 숫자 원문 텍스트 교차검증 · 원문 미확인 값 미검증 표시',
      },
      {
        title: '3층 · 분석',
        kicker: 'LAYER 03',
        tone: 'crimson',
        body: '감시역학 표준 준거 · 이상 판정 = 국가별 기준선 대비 z-score + CDC EARS 계열 방법 · 성능 지표 = 민감도·특이도·양성예측도·오탐율',
        points: [
          '민감도(POD) = 실제 발병 중 포착 비율',
          '특이도 = 평시의 평시 판정 비율',
          '오탐율(FAR) = 경보 중 헛경보 비율',
          '적정 오탐율 = 기술 문제 아닌 **운영 정책** · 조직별 누락 비용 ÷ 헛경보 비용 결정 — 단일 "정답" 임계값 미제시',
        ],
      },
      {
        title: '4층 · 예측',
        kicker: 'LAYER 04',
        tone: 'indigo',
        body: '표준 SEIR 구획 모형 + 시간가변 개입 → 확산 경로 추정 · 질병별 파라미터 = 문헌 실측값',
        points: [
          '접촉 제한 병원체 — **도달 가능 인구** 설정, 현실적 규모 산출',
          '개입 효과 판정 = 실효 재생산지수 1 미만 진입 여부',
          '전 결과 "모델 시나리오" 명시 · 역사 대조 결과 병기',
        ],
      },
      {
        title: '본 방법론의 위치',
        body: '예측+시뮬레이션 결합 감염병 모델링 = 임페리얼 칼리지 MRC GIDA·노스이스턴 MOBS Lab 등 10년+ 영역 · 아이기론 기여 = **해당 방법의 일일 자동 가동 글로벌 상업 제품 구조화**',
      },
    ],
  },

  // ── 활용 분야 ─────────────────────────────────────────────
  solutionsReinsurance: {
    metaTitle: '재보험 · 보험을 위한 활용',
    metaDescription:
      '국가별 노출 지수·포트폴리오 비교 · 절대 확률 아닌 상대 지표 — 응답 상시 명시',
    eyebrow: 'FOR REINSURANCE',
    title: '재보험 · 보험',
    lead: '팬데믹 리스크 비교 가능 지표 계량 공백 · 아이기론 = 해당 공백 상대 지표 충족 · 확률 아님 구분 응답 강제 표시',
    blocks: [
      {
        title: '제공 항목',
        tone: 'indigo',
        items: [
          { title: '국가별 노출 지수', body: '신호 압력·취약성·확산 잠재력 합성 0~100 지수 · 국가 간 비교·순위용' },
          { title: '포트폴리오 비교', body: '보유 국가 단일 화면 상대 백분위 표시' },
          { title: '개입 반사실', body: '무대응 대비 개입 시나리오 차이 모델 비교' },
          { title: '봉인된 예측 기록', body: '예측 생성 시점 봉인 — 시간 경과 시 검증 가능 기록 자가 축적' },
        ],
      },
      {
        title: '필수 유의 사항',
        accent: true,
        points: [
          '노출 지수 = **절대 확률 아님** · 전 응답 `is_probability: false` 부착',
          '가중치 = 실증 보정값 아닌 정책값 · `weights_calibrated: false` 명시',
          '요율 산정 직접 사용 전 공개 시스템 선검증 가능',
        ],
      },
    ],
    cta: {
      title: '실사부터 착수 가능',
      body: '시스템 전체 공개 · 선검증 후 도입 범위 논의',
      label: '문의하기',
      href: 'contact',
    },
  },

  solutionsGovernment: {
    metaTitle: '정부 · 공공보건을 위한 활용',
    metaDescription:
      '유입 경로 추적·개입 시나리오 비교 · 방어 조치별 효과 모델 대조',
    eyebrow: 'FOR GOVERNMENT',
    title: '정부 · 공공보건',
    lead: '해외 발병 국내 유입 경로 + 실제 전파 통제 조치 동시 분석',
    blocks: [
      {
        title: '제공 항목',
        tone: 'forest',
        items: [
          { title: '유입 경로 추적', body: '항공 연결성·도시 단위 가중치 기반 유입 위험 경로 추정' },
          { title: '개입 시나리오 비교', body: '격리·거리두기·백신·치료 수준 조합 — 실효 재생산지수 1 미만 최소 조합 탐색' },
          { title: '병상 부담 추정', body: '유행 곡선 기반 병상 초과 일수 추정' },
          { title: '일일 브리핑', body: '매일 자동 생성 상황 요약 · 조용한 날 = 조용함 기재' },
        ],
      },
      {
        title: '필수 유의 사항',
        accent: true,
        points: [
          '시나리오 숫자 = **모델 가정 하 추정** · 정책 근거 사용 전 역학 전문가 검토 필요',
          '역사 대조 설명 범위 초과 값 — 시스템 자가 경고 부착',
        ],
      },
    ],
    cta: {
      title: '평가 자료 전면 공개',
      body: '시스템·방법론·한계 선검토 후 파일럿 범위 논의 가능',
      label: '문의하기',
      href: 'contact',
    },
  },

  solutionsNgo: {
    metaTitle: '국제기구 · 인도지원을 위한 활용',
    metaDescription:
      '감시 취약 지역 조기 신호 · 상업성 낮아 타 서비스 사각 국가 포함',
    eyebrow: 'FOR MULTILATERAL & HUMANITARIAN',
    title: '국제기구 · 인도지원',
    lead: '감시 체계 취약 지역 = 신호 지연 지역 · 상업적 유인 부족으로 기존 서비스 사각인 지역 — 아이기론 초기부터 감시 범위 포함',
    blocks: [
      {
        title: '제공 항목',
        tone: 'teal',
        items: [
          { title: '취약 지역 우선 감시', body: '나이지리아·에티오피아·예멘·마다가스카르·파푸아뉴기니 등 감시 공백 큰 국가 포함' },
          { title: '현지어 최초 보도 포착', body: '국제 언론 이전 단계 현지 보도 관측' },
          { title: '설명 불가 사건 탐지', body: '기존 질병 미설명 집단 발병 별도 표시' },
          { title: '수집 공백 보고', body: '결측 지역·기간 시스템 자가 보고 — 그 자체가 현장 필요 정보' },
        ],
      },
      {
        title: '필수 유의 사항',
        accent: true,
        points: [
          '감시 취약 지역 = 데이터 공백도 큼 · 아이기론 공백 비은폐·표시',
          '현지어 처리 = 언어모델 분류·키워드 매칭 · 번역 중 병명 소실 회피 선택',
        ],
      },
    ],
    cta: {
      title: '현장 조직 협력 모색',
      body: '현장 신호 직접 접촉 조직 연결 = 아이기론 최우선 다음 단계',
      label: '문의하기',
      href: 'contact',
    },
  },

  // ── 브리핑 ────────────────────────────────────────────────
  briefings: {
    metaTitle: '일일 브리핑',
    metaDescription:
      '매일 자동 생성 감염병 상황 브리핑 · 조용한 날 = 조용함 기재',
    eyebrow: 'BRIEFINGS',
    title: '일일 브리핑',
    lead: '매일 자동 생성 · 무인 운영 — 특이 사항 없는 날 = 특이 사항 없음 기록',
    blocks: [
      {
        title: '생성 방식',
        body: '당일 수집 신호·국가별 위험도 집계 → 요약 구성 · 형식 매일 가변(속보·심층·현장·데이터·대담) · 브리핑 전 수치 = 당일 시스템 실수신 값',
        note: '브리핑 = 요약, 예측 아님 · 특정 국가 판단 필요 시 대시보드 근거 직접 확인',
      },
    ],
    cta: {
      title: '오늘 시스템 관측 대상',
      body: '대시보드 — 브리핑 근거 신호 원본 확인',
      label: '라이브 대시보드 열기',
      href: '/dashboard',
    },
  },

  // ── 회사 소개 ─────────────────────────────────────────────
  about: {
    metaTitle: '회사 소개 — 아이기론',
    metaDescription:
      '아이기론(AEGIRON) = 감염병의 국제 뉴스화 이전 신호 포착 글로벌 조기경보 시스템 개발사 · 대한민국 부산',
    eyebrow: 'ABOUT',
    title: '아이기론',
    lead:
      '2019년 12월 31일, 중국 우한의 보건당국이 원인 모를 폐렴 환자들이 있다고 알렸습니다. 세계보건기구가 국제 비상사태를 선언한 건 그로부터 한 달 뒤였습니다. 그 한 달 동안 신호가 없었던 게 아닙니다. 다만 그 신호들은 현지 언어로, 국제 감시망이 잘 보지 않는 곳에 있었습니다.\n\n아이기론은 그 간극을 줄이고 싶어서 시작했습니다. 현지어 뉴스, 검색량, 하수, 교역, 동물 질병 신호처럼 공식 발표보다 먼저 움직이는 흔적들을 원문 그대로 모아 매시간 전 세계의 이상 지점을 계산합니다. 그리고 우리가 내놓는 모든 예측은 만든 순간 봉인해, 맞았는지 틀렸는지를 누구나 확인할 수 있게 공개합니다.',
    photo: {
      src: '/media/photos/earth-at-night.jpg',
      alt: '밤의 지구 — 아메리카 대륙의 도시 불빛(위성 합성 영상)',
      caption: '밤의 지구(Black Marble) · 위성 관측 합성 영상',
      credit: 'NASA Earth Observatory · 퍼블릭 도메인',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Black_Marble_Americas.jpg',
      position: 'center 40%',
    },
    blocks: [
      {
        title: '무엇을 만드는가',
        kicker: 'WHAT WE BUILD',
        tone: 'teal',
        body: '178개국 현지어 보도·각국 공식 감시 자료·환경·무역·유전체 신호 단일 지수 통합 → 국가별 이상도 판정 · 경보 시점 확산 시나리오·개입 효과 동시 산출 · 설계 축 = 감지를 넘어 "무엇을, 어느 강도로"까지 응답',
        points: [
          '감지 → 판정 → 예측 → 시뮬레이션 → 처방 → 자기검증 → 봉인 — 전 사슬 단일 시스템 내장',
          '전 예측 이후 공식 선언 자동 대조 채점 · 생성 시점 봉인 — 사후 수정 불가',
          '두 내부 R&D 프로그램 — 방어적 유전체 스크리닝(HEIMDALL)·대응제 준비태세(VALHALLA) — 국가 바이오안보 축 담당',
        ],
      },
      {
        title: '지금 단계',
        kicker: 'WHERE WE ARE',
        tone: 'indigo',
        body: '시스템 실가동 중 · 데이터 소스 매시간 신호 유입 · 라이브 대시보드 현재 로그인 없이 개방 · 첫 파트너 탐색 단계 — 비은폐 기재 · 공개·검증 가능성 = 본 단계 강점',
        points: [
          '118개 모듈·128개 엔드포인트 매시간 가동 · 자동 시험 2,263건 통과 코드만 운영 반영',
          '시스템·방법론·데이터·한계 초기부터 전면 공개 — 실사 직접 검증 가능 상태',
          '전 예측 봉인 축적 — 운영 지속 시 검증 가능 기록 자연 증가',
        ],
      },
      {
        title: '왜 전부 공개하는가',
        kicker: 'WHY OPEN',
        tone: 'forest',
        body: '전면 공개 = 검증 준비 완료 상태 유지 · 대형 경쟁사 구조적 모방 난이 선택 — 경쟁사 = 보호할 고객 계약 보유, 아이기론 = 현 시점 해당 제약 없이 공개 가능 · 공개 자체 = 신뢰 근거',
        note: '검증 현황·알려진 한계 — 별도 페이지 전면 기재',
      },
      {
        title: '어디로 가는가',
        kicker: 'ROADMAP',
        tone: 'violet',
        items: [
          { title: '단기', body: '실제 현장 조직·감시망 연결 — 신호 원천 근접 · 재보험·정부·국제기구·현장 조직 = 첫 파트너 후보' },
          { title: '중기', body: '운영 지속 — 검증 가능 예측 기록 축적 · 봉인 기록 = "당시 실제 예측" 근거' },
          { title: '장기', body: '감시 공백 지역 실사용 글로벌 조기경보 인프라화' },
        ],
      },
    ],
    cta: {
      title: '함께 이야기할 파트너 모집',
      body: '재보험·정부·국제기구·현장 조직 전부 환영 · 데모 예약 없이 시스템 전체 사전 열람 가능',
      label: '문의하기',
      href: 'contact',
    },
  },

  // ── 문의 ──────────────────────────────────────────────────
  contact: {
    metaTitle: '문의',
    metaDescription: '아이기론 연락 방법',
    eyebrow: 'CONTACT',
    title: '문의',
    lead: '데모 예약 없이 시스템 전체 검토 가능 · 검토 후 질문·협력 제안 아래 연락처 접수',
    blocks: [
      {
        title: '연락처',
        items: [
          { title: '이메일', body: 'kimdaeheuk@gmail.com', meta: '최속 경로' },
          { title: '위치', body: '대한민국 부산', meta: 'KST (UTC+9)' },
        ],
      },
      {
        title: '특히 환영하는 연락',
        points: [
          '**오류 지적** — 방법론·수치 오류 제보 · 확인 후 반영',
          '**현장 조직 연결** — 실제 감시망 연결 경로 = 현 최우선 다음 단계',
          '**파일럿 검토** — 재보험·정부·국제기구·현장 조직 전부 환영',
        ],
      },
    ],
  },

  // ── 법적 고지 ─────────────────────────────────────────────
  privacy: {
    metaTitle: '개인정보처리방침',
    metaDescription: '아이기론 웹사이트 개인정보 처리 방침',
    eyebrow: 'LEGAL',
    title: '개인정보처리방침',
    lead: '방문자 로그인 미요구 · 개인정보 미수집',
    blocks: [
      {
        title: '미수집 항목',
        points: [
          '회원가입·로그인 부재 — 계정 정보 미수집',
          '광고·방문 분석 추적 도구 미사용',
          '대시보드 열람 — 개인 식별 정보 불필요',
        ],
      },
      {
        title: '외부 서비스',
        body: '홈 소개 영상 = YouTube 개인정보 보호 강화 모드 삽입 · 재생 시 YouTube 정책 적용 · 글꼴 = Google Fonts·jsDelivr 로드 — 해당 서비스 접속 기록(IP 주소 등) 잔류 가능',
      },
      {
        title: '문의 시',
        body: '이메일 연락 내용·주소 = 답변 목적 전용 사용 · 제3자 미제공',
      },
      {
        title: '변경',
        body: '방침 변경 시 본 페이지 갱신',
      },
    ],
  },

  terms: {
    metaTitle: '이용약관',
    metaDescription: '아이기론 웹사이트·공개 데이터 이용 조건',
    eyebrow: 'LEGAL',
    title: '이용약관',
    lead: '본 사이트·공개 대시보드 이용 적용 조건',
    blocks: [
      {
        title: '제공 정보의 성격',
        accent: true,
        points: [
          '본 사이트 정보 = **참고용** · 의료·보건·투자 판단 근거 미제공',
          '예측·시나리오 수치 = **모델 가정 하 추정** · 실측값·보장 아님',
          '본 정보 기반 판단 결과 책임 부담 없음',
        ],
      },
      {
        title: '데이터 출처',
        body: '본 시스템 = WHO·CDC 등 공개 자료 수집·가공 · 원 자료 저작권·이용 조건 = 각 기관 귀속 · 가공 수치 원문 상이 가능 — 공식 인용 시 원 기관 자료 확인 필수',
      },
      {
        title: '가용성',
        body: '공개 대시보드 예고 없는 중단·변경 가능',
      },
    ],
  },
};
