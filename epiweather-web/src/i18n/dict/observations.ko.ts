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
};
