import type { BaikalDict, ContentPage, SystemDict } from '../types';

/**
 * 아이기론 대표 시스템 — 엔진 → YGGDRASIL → BAIKAL MOB (한국어).
 *
 * ★ 2026-10-19 캡틴 지시 ★ "엔진=>온톨로지=>바이칼몹 시스템을 아이기론을 대표하는 시스템으로
 * 명명하고 기록해 · 각 엔진 이름을 영어이름/한국이름으로 고객이 쉽게 알 수 있도록 ·
 * 문장은 회사 보고체 형태로 중요하게."
 *
 * 문체: 보고체(~함·~임) · 개조식. 사실·정직 표시는 그대로 — 이름은 내부 코드명이고,
 * 상태는 운영 서버가 실제로 기록한 값만 표시한다.
 */

export const systemsKo: SystemDict[] = [
  {
    code: 'HUGINN', name: '후긴', role: '감시',
    myth: '오딘의 까마귀 — 온 세상을 날며 본 것을 보고함',
    summary: '178개국·52개 언어 현지 보도와 각국 공식 자료를 매시간 수집하고 이상 신호를 탐지함',
  },
  {
    code: 'MIMIR', name: '미미르', role: '추출',
    myth: '지혜의 샘 — 원문에서 의미를 길어 올림',
    summary: '보도 본문·보고서 PDF 표를 질병·국가·확진·사망의 구조화 신호로 변환함',
  },
  {
    code: 'FORSETI', name: '포르세티', role: '판정',
    myth: '심판의 신 — 무엇을 위로 올릴지 가름',
    summary: '국가 위험지수를 산출하고 등급·일일 상한을 적용해 사람에게 보낼 경보만 선별함',
  },
  {
    code: 'SKULD', name: '스쿨드', role: '예측·시뮬레이션',
    myth: '미래를 맡은 노른 — 앞으로 될 것',
    summary: '위험도를 예측으로 기록하고 확산·국내 유입·개입 시나리오를 산출함',
  },
  {
    code: 'HEIMDALL', name: '헤임달', role: '유전체',
    myth: '다리를 지키는 감시자',
    summary: '공개 시퀀스 계통을 추적하고 방어적 유전체 스크리닝을 수행함 — 결과는 판정이 아닌 검토 우선순위임',
  },
  {
    code: 'VALHALLA', name: '발할라', role: '대응제',
    myth: '전투를 준비하는 전당',
    summary: '공개 자료로 비축 커버리지 격차·생산 주권 격차·임상 파이프라인을 집계함',
  },
  {
    code: 'VAR', name: '바르', role: '검증',
    myth: '맹세의 여신 — 약속을 지켜보고 어기면 벌함',
    summary: '예측 봉인·공식 선언 대조 채점·선행성 원장으로 자체 수치를 검증함',
  },
];

export const baikalKo: BaikalDict = {
  flagshipEyebrow: 'FLAGSHIP SYSTEM · 아이기론 대표 시스템',
  flagshipTitle: '엔진 → YGGDRASIL → BAIKAL MOB',
  flagshipLead:
    '아이기론 대표 시스템으로 명명함. 7개 엔진 시스템을 YGGDRASIL 온톨로지로 연결하고, BAIKAL MOB이 생태계 전체의 상태 변화를 매시간 판정·기록·공개함. 시스템이 스스로 어떻게 작동했는지를 변조 불가 기록으로 남기는 구조임.',
  layers: [
    {
      code: 'LAYER 1 · ENGINES',
      name: '7개 엔진 시스템',
      role: '감시 → 검증',
      body: '114개 엔진 모듈을 7개 시스템(HUGINN·MIMIR·FORSETI·SKULD·HEIMDALL·VALHALLA·VAR)으로 편성함. 엔진마다 실제 가동 방식(매시·매일·경보 시·요청 시)을 표기함.',
    },
    {
      code: 'LAYER 2 · ONTOLOGY',
      name: 'YGGDRASIL',
      role: '연결',
      body: '7개 시스템 사이에 실제로 흐르는 데이터 9개를 연결 구조로 정의함. 흐름마다 코드 위치·주기를 명시하고, W3C 표준(JSON-LD)으로 공개함.',
    },
    {
      code: 'LAYER 3 · STATE',
      name: 'BAIKAL MOB',
      role: '상태변화 기록',
      body: '매시간 7개 시스템 상태를 판정·저장함. 상태가 바뀐 순간만 기록하며 삭제하지 않음. 피드백 루프(정답 적재 → 예측 → 채점) 흐름량을 함께 기록함.',
    },
  ],
  statusTitle: '현재 생태계 상태',
  statusLead:
    '운영 서버가 매시간 기록한 최신 스냅숏을 그대로 표시함. 상태는 정상·저하·중단·판정 안 함 네 가지로만 구분하며, 읽을 값이 없으면 정상으로 집계하지 않음.',
  statusLabels: { ok: '정상', degraded: '저하', down: '중단', undetermined: '판정 안 함' },
  evidenceLabels: { measured: '측정값', estimated: '추정값', proxy: '대리 지표' },
  scopeLabel: '판정 범위',
  reasonLabel: '근거',
  reasonOriginalNote: '',
  onRequestLabel: '요청 시 엔진(매시간 상태 없음)',
  observedAt: '관측 시각',
  staleNote: '마지막 관측이 {n}분 전임 — 매시간 주기 정지 가능성이 있어 현재 상태로 표시하지 않음',
  notYet: '첫 매시간 관측 전임 — 다음 수집 주기 이후 표시됨',
  unavailable: '운영 서버에서 상태를 읽지 못함 — 지어낸 값 대신 이 문구를 표시함',
  summaryLine: '정상 {ok}/7 · 저하 {degraded} · 중단 {down} · 판정 안 함 {undetermined}',
  loopTitle: '피드백 루프 — 정답 적재 → 예측 → 채점',
  loopSubject: '피드백 루프',
  loopLead: '아이기론 예측을 이후 공식 선언과 대조해 채점하는 경로임. 세 고리의 흐름량을 매시간 기록함.',
  loopStates: { measuring: '측정 중', awaiting: '측정 대기', empty: '비어 있음', undetermined: '판정 안 함' },
  loopLinks: { ground_truth: '① 정답 적재', predictions: '② 예측 기록', scoring: '③ 채점' },
  loopFields: {
    live: '실시간 적재', other: '백필 등', total: '전체', named: '질병 지목',
    resolved: '판정', unresolved: '미결', earliestDue: '가장 이른 판정 기한',
  },
  loopNote:
    '판정 0건인 동안 상태는 "측정 대기"임 — 적중률 0%가 아니라 아직 측정 불가 상태임. 채점 결과는 원장에 기록만 하며 예측 모델을 자동으로 수정하지 않음.',
  transitionsTitle: '상태 변화 기록',
  transitionsLead: '상태가 바뀐 순간만 남긴 감사 기록임. 첫 관측은 "관측 시작"으로 표기하며 이전 상태를 지어내지 않음.',
  transitionsEmpty: '기록된 상태 변화 없음',
  observationStart: '관측 시작',
  flowsTitle: 'YGGDRASIL — 시스템 간 데이터 흐름',
  flowsLead: '코드에 실제로 존재하는 흐름만 연결함. 그럴듯해 보이는 연결은 추가하지 않음.',
  flows: [
    { id: 'huginn-mimir', from: 'HUGINN', to: 'MIMIR', kind: 'data', label: '원문 제공', cadence: '매일 21:00 UTC' },
    { id: 'huginn-forseti', from: 'HUGINN', to: 'FORSETI', kind: 'data', label: '이상도 신호', cadence: '매시' },
    { id: 'mimir-forseti', from: 'MIMIR', to: 'FORSETI', kind: 'data', label: '구조화 신호', cadence: '매시' },
    { id: 'heimdall-forseti', from: 'HEIMDALL', to: 'FORSETI', kind: 'data', label: '신규 계통 지표', cadence: '매시' },
    { id: 'forseti-skuld', from: 'FORSETI', to: 'SKULD', kind: 'data', label: '위험도 → 예측 기록', cadence: '매시' },
    { id: 'skuld-var', from: 'SKULD', to: 'VAR', kind: 'data', label: '예측 봉인·채점 대상', cadence: '매시' },
    { id: 'mimir-var', from: 'MIMIR', to: 'VAR', kind: 'data', label: '정답 후보(공식 선언 추출)', cadence: '매일 21:00 UTC' },
    { id: 'huginn-var', from: 'HUGINN', to: 'VAR', kind: 'data', label: '정답 적재(WHO 공식 발표)', cadence: '매일 21:00 UTC' },
    { id: 'var-skuld', from: 'VAR', to: 'SKULD', kind: 'feedback', label: '채점 결과(기록 전용)', cadence: '매일 21:00 UTC' },
  ],
  feedbackNote: 'VAR → SKULD 피드백 흐름은 기록 전용임 — 채점 결과가 예측 모델을 자동으로 수정하지 않음.',
  isolatedNote: 'VALHALLA는 경보 계산에 입력되지 않는 독립 축임 — 나가는 흐름이 없으며, 연결된 것처럼 표시하지 않음.',
  systemsTitle: '7개 엔진 시스템 — 영문명 · 한글명 · 역할',
  systemsLead: '114개 엔진 모듈을 7개 시스템으로 편성함. 이름은 내부 코드명이며 실제 기관·기밀등급·능력 주장이 아님.',
  colSystem: '시스템',
  colRole: '역할',
  colEngines: '주요 엔진',
  honestyTitle: '운영 원칙',
  honestyPoints: [
    '상태를 지어내지 않음 — 읽을 값이 없으면 "판정 안 함"으로 표시함',
    '시스템마다 판정 범위를 명시함 — "정상"이 무엇을 관측했다는 뜻인지 함께 공개함',
    '데이터 부재와 고장을 구분함 — 시퀀스 미제출처럼 아직 올 데이터가 없는 경우는 "판정 불가"로 표기함',
    '요청 시에만 가동하는 엔진(확산 트윈·Evo2 등)은 매시간 가동으로 표시하지 않음',
    '읽기 전용 설계 — BAIKAL MOB은 경보·예측 계산을 변경하지 않으며, 고장 시에도 경보는 그대로 작동함',
  ],
  openPage: 'BAIKAL MOB 상세 보기',
};

export const baikalPageKo: ContentPage = {
  metaTitle: 'BAIKAL MOB — 아이기론 대표 시스템',
  metaDescription:
    '7개 엔진 시스템 → YGGDRASIL 온톨로지 → BAIKAL MOB 상태변화 기록. 아이기론 생태계 상태를 매시간 판정·저장·공개.',
  eyebrow: 'FLAGSHIP SYSTEM',
  title: 'BAIKAL MOB — 아이기론 대표 시스템',
  lead:
    '엔진 → YGGDRASIL → BAIKAL MOB 3층 구조를 아이기론 대표 시스템으로 명명함. 7개 엔진 시스템의 상태를 온톨로지로 연결하고, 생태계 전체의 상태 변화를 매시간 기록·공개함. 가장 깊고 오래된 호수가 바닥에 층층이 역사를 쌓듯, 운영 이력을 변조 없이 축적함.',
  blocks: [],
  cta: {
    title: '같은 데이터 직접 확인',
    body: '운영 API /api/baikal · /api/yggdrasil 공개 — 로그인 불필요, JSON-LD 형식 제공',
    label: '개발자 · API',
    href: 'developers',
  },
};
