// 백엔드 country_risk.py의 COUNTRIES 키와 1:1 대응하는 위경도 좌표.
// 국가 대표 좌표(대체로 수도) — GlobalRiskMap에서 마커 위치로 사용.
// COUNTRIES에 새 국가가 추가되면 여기도 같이 추가해야 함.
export const COUNTRY_COORDS: Record<string, [number, number]> = {
  DRC:            [-4.4419, 15.2663],   // 킨샤사
  Uganda:         [0.3476, 32.5825],    // 캄팔라
  'Saudi Arabia': [24.7136, 46.6753],   // 리야드
  Thailand:       [13.7563, 100.5018],  // 방콕
  'South Korea':  [37.5665, 126.9780],  // 서울
  Japan:          [35.6762, 139.6503],  // 도쿄
  'Hong Kong':    [22.3193, 114.1694],
  Brazil:         [-15.7939, -47.8828], // 브라질리아
  USA:            [39.8283, -98.5795],  // 국토 중심(대표점)
};
