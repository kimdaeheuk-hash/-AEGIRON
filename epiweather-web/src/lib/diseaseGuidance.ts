/**
 * 확산을 어떻게 막는가 — 질병별 WHO 표준 대응 근거 링크 (2026-11-16, 관측 데이터 활용 계획 ⑦).
 *
 * 캡틴: "어떻게 확산을 막아야 하고". 우리가 처방을 지어내지 않는다 — WHO 가 낸 '발병 대응 도구 모음
 * (Outbreak Toolbox: 사례 정의·감시·검사·치료·백신·소통 지침 묶음)'과 팩트시트로 연결만 한다.
 *
 * ★ 주소 확인 ★ 이 샌드박스는 who.int 에 직접 못 나가서(프록시 거절) 2026-11-16 웹 검색 결과에 실제로 나온
 * 주소만 질병별로 적었다. 검색에서 확인 못 한 질병은 지어낸 주소 대신 도구 모음 전체 목록(INDEX)으로 보낸다.
 */

const TOOLBOX = 'https://www.who.int/emergencies/outbreak-toolkit/disease-outbreak-toolboxes';
const FACT = 'https://www.who.int/news-room/fact-sheets/detail';

export const GUIDANCE_INDEX = TOOLBOX;

type Guide = { key: string; match: RegExp; toolbox?: string; factsheet?: string };

const GUIDES: Guide[] = [
  {
    key: 'ebola',
    match: /에볼라|ebola|bundibugyo|붕디부교|분디부교/i,
    toolbox: `${TOOLBOX}/ebola-virus-disease-outbreak-toolbox`,
    factsheet: `${FACT}/ebola-disease`,
  },
  {
    key: 'marburg',
    match: /마버그|마르부르크|marburg/i,
    toolbox: `${TOOLBOX}/ebola-and-marburg-virus-outbreak-toolbox`,
    factsheet: `${FACT}/marburg-virus-disease`,
  },
  {
    key: 'mpox',
    match: /엠폭스|원숭이두창|mpox|monkeypox/i,
    toolbox: `${TOOLBOX}/mpox-outbreak-toolbox`,
    factsheet: `${FACT}/mpox`,
  },
  { key: 'cholera', match: /콜레라|cholera/i, toolbox: `${TOOLBOX}/cholera-outbreak-toolbox` },
  { key: 'yellow_fever', match: /황열|yellow fever/i, toolbox: `${TOOLBOX}/yellow-fever-outbreak-toolbox` },
  { key: 'plague', match: /페스트|plague/i, toolbox: `${TOOLBOX}/plague-outbreak-toolbox` },
  {
    key: 'avian_flu',
    match: /조류\s*인플루엔자|h5n1|h5n5|h7n9|h9n2|avian influenza|bird flu/i,
    toolbox: `${TOOLBOX}/zoonotic-influenza-a-virus-outbreak-toolbox`,
  },
  { key: 'mers', match: /메르스|mers/i, toolbox: `${TOOLBOX}/mers-outbreak-toolbox` },
  { key: 'nipah', match: /니파|nipah/i, factsheet: `${FACT}/nipah-virus` },
  { key: 'lassa', match: /라사|lassa/i, factsheet: `${FACT}/lassa-fever` },
];

export type GuidanceLink = { disease: string; toolbox: string | null; factsheet: string | null };

/** 질병 이름들 → WHO 근거 링크. 같은 지침은 한 번만. 매칭 안 된 질병은 toolbox/factsheet 모두 null(화면: 전체 목록). */
export function guidanceFor(diseases: (string | null | undefined)[]): GuidanceLink[] {
  const seen = new Set<string>();
  const out: GuidanceLink[] = [];
  for (const raw of diseases) {
    const d = (raw ?? '').trim();
    if (!d) continue;
    const g = GUIDES.find((x) => x.match.test(d));
    const key = g ? g.key : `?${d.toLowerCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ disease: d, toolbox: g?.toolbox ?? null, factsheet: g?.factsheet ?? null });
  }
  return out;
}
