import type { ContentPage, ObservationsDict } from '../types';

/**
 * 관측 데이터 보드(한국어) — 2026-11-15 캡틴 지시:
 * "아이기론에서 받은 모든 정보도 실측이야 — 홈페이지나 대시보드에서 볼 수 있게 해야 해."
 *
 * 문체: 보고체·개조식. 측정값과 해석값(추정·대리)은 칸을 나눠 같은 모양으로 그리지 않는다.
 */
export const observationsPageKo: ContentPage = {
  metaTitle: '관측 데이터 — 아이기론이 실제로 측정하고 있는 값',
  metaDescription:
    '극지·영구동토, 기후, 의료물자 무역, 재난, 여행 경보, 나라별 발생 보도 등 아이기론이 운영 중에 실제로 받아 오는 측정값을 분야별로 공개함.',
  eyebrow: 'OBSERVATIONS',
  title: '관측 데이터',
  lead: '아이기론이 운영 중에 실제로 받아 오는 값을 분야별로 공개함 · 운영 API 실측 · 수 분 간격 갱신',
  blocks: [],
};

export const observationsKo: ObservationsDict = {
  columns: {
    target: '대상',
    measured: '측정값',
    derived: '해석값 (추정·대리)',
    time: '기준 시각',
    note: '비고',
  },
  columnsNote:
    '측정값 = 출처가 직접 잰 값 · 해석값 = 측정값으로 계산한 추정이나 다른 것을 대신 가리키는 대리지표 — 둘을 같은 칸에 섞지 않음',
  unavailable: '지금 운영 서버에서 읽어 오지 못함 — 값을 지어내지 않고 비워 둠',
  empty: '이 분야에 지금 표시할 기록 없음',
  sourceLabel: '출처',
  countLabel: '건',
  caveatKoLabel: '',
  globe: {
    title: '관측 지구본',
    lead: '위 표의 값을 지구본에 찍음 · 점 크기 = 그 나라·지역에서 이번에 받은 기록 수 · 드래그로 회전',
    dragHint: '드래그해서 돌려 보기 · 점을 누르면 내용 표시',
    layers: {
      event: '발생 보도',
      unexplained: '설명 불가 신호',
      disaster: '재난 감시창',
      trade: '의료물자 수입 급증',
      polar: '극지 관찰',
    },
    korea: '대한민국',
    rotateWest: '서쪽',
    rotateEast: '동쪽',
    toKorea: '한국 보기',
    toArctic: '북극 보기',
    toAntarctic: '남극 보기',
    unlocated: '위치를 못 읽어 지구본에 찍지 않은 기록',
    pick: '점을 누르면 그곳의 기록이 여기에 나옴',
    honesty: '점은 보도·관측이 있었던 곳이지 확진 환자 위치가 아님 · 나라 단위 점은 나라 중앙에 찍음',
    card: {
      grade: { high: '높음', elevated: '주의', watch: '관찰' },
      intensity: '관측 강도',
      intensityNote:
        '관측 강도 = 보도 20·설명불가 15·재난 15·무역 10 × log2(1+건수) + CDC 경보 등급 × 8 (최대 100) — 측정값이 아닌 추정, 가중치 미보정 · 발병 확률이 아님',
      counts: '받은 기록',
      travel: 'CDC 여행경보',
      riskScore: '위험지수(모델 추정)',
      dominant: '주요 질병',
      korea: '한국 연결',
      koreaRoutes: '한국 직항 노선',
      koreaPassengers: '인천 여객',
      koreaNone: '유입 보고서에 이 나라의 한국 연결 값 없음',
      koreaUnavailable: '한국 유입 보고서를 읽지 못해 한국행 경로를 그리지 않음',
      arcNote: '빨간 호 = 관측이 있는 나라 중 한국과 항공으로 연결된 곳 → 서울',
      evidence: '근거',
      top: '관측 강도 상위',
    },
  },
  sections: {
    events: {
      title: '나라별 발생 보도',
      lead: '각국 보도·공식 자료에서 AI가 질병·장소·사건 유형을 구조화해 뽑은 기록 · 보도된 사건이지 확진 집계가 아님',
    },
    polar: {
      title: '극지·영구동토 관찰',
      lead: '해빙일수·기온 추세는 기상 관측값 · 해빙 압력·관찰 점수는 그 값으로 계산한 추정 · 경보가 아니라 관찰 등급',
    },
    climate: {
      title: '기후 (매개체 환경)',
      lead: '최근 기온·강수는 관측값 · 매개체 적합도·환경 압력은 발병 위험 측정이 아니라 모델 추정',
    },
    trade: {
      title: '의료물자 수입 급증',
      lead: '수입액은 UN Comtrade 관세 통계 실측 · "발병 대비 행동"이라는 해석은 대리지표 · 신고 지연 약 2개월',
    },
    disaster: {
      title: '재난 후 감시창',
      lead: '재난 발생은 GDACS 실측 · 감시창(질병별 잠복 구간)은 문헌 기반이며 이 시스템 데이터로 보정하지 않음 · 예측 아님',
    },
    travel: {
      title: '여행 건강 경보 (CDC)',
      lead: '미국 CDC가 매긴 공식 1~4단계 등급을 그대로 표시 · 감염병 외 사유가 섞일 수 있음',
    },
    land: {
      title: '산림 화재 (위성)',
      lead: 'NASA FIRMS 위성 화재 탐지 수는 실측 · 벌목·화전으로 읽는 것은 대리지표',
    },
    forest: {
      title: '산림 손실 (위성)',
      lead: 'Global Forest Watch 위성 산림손실 알림 수 · 탐지 지연과 신뢰도 등급이 있음',
    },
    animal: {
      title: '동물 감염병 (WOAH)',
      lead: '세계동물보건기구 공식 RSS에서 읽은 항목 수 · 옛 WAHIS API는 은퇴해 발생 건수는 판정 안 함',
    },
    genomic: {
      title: '유전체 계통 (Nextstrain)',
      lead: '공개 유전체 빌드에서 최근 60일 새로 나타난 계통과 우세 계통',
    },
    social: {
      title: 'SNS 신호 (Mastodon)',
      lead: 'mastodon.social 한 곳의 질병 해시태그 7일 게시량 · 표본이 작아 경보 점수에는 상한을 둠',
    },
    silence: {
      title: '보고 공백 감시',
      lead: '평소 활발하던 보고 채널이 과거 평균의 절반 미만으로 줄었는지 · 보고 체계 붕괴를 의심하는 신호',
    },
    unexplained: {
      title: '설명 불가 신호',
      lead: '알려진 질병 이름에 맞지 않는 보도 · 병원 방문 급증 같은 다른 조건은 데이터가 없어 측정하지 않음',
    },
  },
  country: {
    metaTitle: '{name} — 관측 요약 · 아이기론',
    metaDescription:
      '{name}에 대해 아이기론이 실제로 받은 관측(발생 보도·설명불가 신호·재난·의료물자 수입·CDC 여행경보·한국 연결)과 30일 이력.',
    eyebrow: '나라별 관측',
    back: '← 관측 데이터·지구본으로',
    open: '나라 페이지 열기 →',
    noCard: '지금 이 나라로 묶인 관측이 없음 — 관측이 없다는 것이지 위험이 없다는 판정이 아님',
    summaryTitle: '관측 요약',
    evidenceTitle: '근거 기록',
    travelTitle: 'CDC 여행경보',
    travelNone: '이 나라 이름이 들어간 CDC 여행경보 없음',
    koreaTitle: '한국 연결',
    historyTitle: '30일 관측 이력',
    historyLead:
      '매시 저장한 값 · 값이 바뀔 때만 새 줄이 생김 · "판정 안 함"은 그 시각에 못 읽었다는 뜻(0이 아님) · 이력은 2026-11-15부터',
    historyLayers: { climate: '기후', trade: '의료물자 수입', disaster: '재난 감시창' },
    historyEmpty: '이 기간에 저장된 값 없음',
    historyUnavailable: '이력을 읽지 못함(판정 안 함)',
    historyCols: { observed: '처음 계산', confirmed: '마지막 확인', measured: '측정값(출처)', derived: '해석값(추정)' },
    checklistTitle: '확인할 것',
    checklistLead:
      '받은 관측 종류에 따라 정해 둔 규칙으로 만든 확인 목록임 · 의료·방역 권고가 아니며, 각 항목은 원문 확인이 먼저임',
    checks: {
      travel: 'CDC 여행경보 원문(지역·권고 수준)을 확인하고, 해당 지역 출입국자 안내가 있는지 확인',
      disaster: '재난 후 감시창이 열려 있음 — 창에 든 질병(잠복기 안) 보도가 새로 뜨는지 현지 보도를 확인',
      trade:
        '의료물자 수입이 평소보다 늘었음 — 공식 발표 전 준비 행동일 수 있으나 대리 지표이므로 품목·신고 지연(약 2개월)을 함께 확인',
      event: '발생 보도의 원문 출처와 날짜를 확인 — AI가 구조화한 기록이라 확진 집계가 아님',
      unexplained: '알려진 질병과 맞지 않는 보도가 있음 — 원문을 읽고 같은 사건의 반복 보도인지 확인',
      korea: '한국과 항공으로 연결됨 — 직항 노선·인천 여객 규모를 보고 검역·입국자 안내 필요성을 담당 기관이 판단',
      none: '지금 받은 관측이 없어 확인 목록을 만들지 않음',
    },
    responseTitle: '발병국의 대응 조치',
    responseNote:
      'WHO 질병발생소식(DON)의 "대응" 단락을 정해진 낱말로 읽은 것 · WHO가 그 발표에 적은 조치이며, 실행 정도·범위·효과는 판정하지 않음 · 근거 문장은 WHO 원문(영어) · 매일 21:00 UTC 갱신',
    responseEmpty:
      '최근 400일 WHO 질병발생소식에 이 나라의 대응 기록 없음 — WHO가 발표하지 않았거나 단락에 정해진 낱말이 없는 경우임',
    responseUnavailable: '대응 기록을 읽지 못함(판정 안 함)',
    responseCols: { date: '발표일', disease: '질병', measure: '조치', evidence: '근거(WHO 원문)' },
    responseShared: '여러 나라를 함께 다룬 발표 — 어느 나라의 조치인지는 가르지 않음',
    guidanceTitle: '확산을 막는 표준 대응 — WHO 근거',
    guidanceLead:
      '이 나라에서 관측된 질병별로 WHO가 낸 발병 대응 지침(사례 정의·감시·검사·치료·백신·소통)으로 연결함 · 아이기론이 만든 처방이 아님',
    guidanceToolbox: 'WHO 발병 대응 도구 모음',
    guidanceFactsheet: 'WHO 팩트시트',
    guidanceIndex: '이 질병의 지침 주소를 확인하지 못해 WHO 발병 대응 도구 모음 전체 목록으로 연결함',
  },
};
