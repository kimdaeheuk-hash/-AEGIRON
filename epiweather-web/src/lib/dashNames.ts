/**
 * 대시보드 시뮬레이션 데이터(lib/algorithms)의 한국어 이름 → 영어·프랑스어 (2026-11-16, ⑪).
 *
 * algorithms.ts 의 값(도시·지역·관문·신호·정책 이름)은 계산과 같이 쓰여 바꾸지 않고, 화면에 낼 때만 옮긴다.
 * 표에 없는 이름은 원문 그대로 둔다.
 */
import type { DashLang } from './dashLang';

const N: Record<string, [string, string]> = {
  // 위협
  '계절 유행': ['seasonal epidemic', 'épidémie saisonnière'],
  '신종 감염병': ['novel infection', 'nouvelle infection'],
  '고위험 신종': ['high-risk novel infection', 'nouvelle infection à haut risque'],
  // 발원지 채널(1단계)
  '검색·SNS': ['Search · social', 'Recherche · réseaux sociaux'],
  'OTC 판매': ['OTC sales', 'Ventes sans ordonnance'],
  '하수 신호': ['Wastewater', 'Eaux usées'],
  '동물 예찰': ['Animal surveillance', 'Surveillance animale'],
  '이동 변화': ['Mobility change', 'Changement de mobilité'],
  '1339 통화': ['1339 hotline calls', 'Appels à la ligne 1339'],
  // 민간 신호(2단계)
  '시민 자가증상': ['Citizen self-reported symptoms', 'Symptômes autodéclarés'],
  '하수 역학': ['Wastewater epidemiology', 'Épidémiologie des eaux usées'],
  '약국 OTC': ['Pharmacy OTC', 'Pharmacies (sans ordonnance)'],
  '민간 진단키트': ['Home test kits', 'Autotests'],
  '민간 검사소': ['Private labs', 'Laboratoires privés'],
  // 발원 도시
  우한: ['Wuhan', 'Wuhan'],
  자카르타: ['Jakarta', 'Jakarta'],
  방콕: ['Bangkok', 'Bangkok'],
  하노이: ['Hanoi', 'Hanoï'],
  다카: ['Dhaka', 'Dacca'],
  킨샤사: ['Kinshasa', 'Kinshasa'],
  라고스: ['Lagos', 'Lagos'],
  멕시코시티: ['Mexico City', 'Mexico'],
  '인수공통·고밀도': ['Zoonotic · dense', 'Zoonotique · dense'],
  '가금·열대': ['Poultry · tropical', 'Volailles · tropical'],
  '관광허브·고여객': ['Tourism hub · high traffic', 'Pôle touristique · fort trafic'],
  '가금·접경': ['Poultry · border', 'Volailles · frontalier'],
  니파위험: ['Nipah risk', 'Risque Nipah'],
  '출혈열·취약': ['Haemorrhagic fever · fragile', 'Fièvre hémorragique · fragile'],
  인수공통: ['Zoonotic', 'Zoonotique'],
  '신종플루 전례': ['2009 flu precedent', 'Précédent grippe 2009'],
  // 국내 지역
  인천: ['Incheon', 'Incheon'],
  서울: ['Seoul', 'Séoul'],
  경기: ['Gyeonggi', 'Gyeonggi'],
  강원: ['Gangwon', 'Gangwon'],
  충남: ['Chungnam', 'Chungnam'],
  충북: ['Chungbuk', 'Chungbuk'],
  대구: ['Daegu', 'Daegu'],
  전북: ['Jeonbuk', 'Jeonbuk'],
  경남: ['Gyeongnam', 'Gyeongnam'],
  전남: ['Jeonnam', 'Jeonnam'],
  부산: ['Busan', 'Busan'],
  제주: ['Jeju', 'Jeju'],
  // 입국 관문
  인천국제공항: ['Incheon Intl Airport', 'Aéroport intl d’Incheon'],
  '김포·기타': ['Gimpo · other', 'Gimpo · autres'],
  'ICN·수도권': ['ICN · capital area', 'ICN · région capitale'],
  'PUS·영남': ['PUS · southeast', 'PUS · sud-est'],
  // 정책 레버(6단계)
  '입국 검역': ['Border quarantine', 'Quarantaine aux frontières'],
  거리두기: ['Distancing', 'Distanciation'],
  '백신 목표': ['Vaccine target', 'Objectif vaccinal'],
  '백신 속도': ['Vaccine pace', 'Rythme vaccinal'],
  치료제: ['Antivirals', 'Antiviraux'],
  취약보호: ['Protect the vulnerable', 'Protection des vulnérables'],
  '유입 차단': ['Block entry', 'Bloquer l’entrée'],
  '접촉 감소': ['Fewer contacts', 'Moins de contacts'],
  커버리지: ['Coverage', 'Couverture'],
  '일일 증가': ['Daily increase', 'Hausse quotidienne'],
  '치명률↓': ['Fatality ↓', 'Létalité ↓'],
  고위험군: ['High-risk groups', 'Groupes à risque'],
  // 위험 단계
  안정: ['Stable', 'Stable'],
  관심: ['Watch', 'Veille'],
  주의: ['Caution', 'Prudence'],
  경계: ['Alert', 'Alerte'],
  심각: ['Severe', 'Grave'],
};

/** 한국어 이름 → 그 언어. 모르면 원문. */
export function nameOf(ko: string, lang: DashLang): string {
  if (lang === 'ko') return ko;
  const v = N[ko];
  return v ? (lang === 'en' ? v[0] : v[1]) : ko;
}
