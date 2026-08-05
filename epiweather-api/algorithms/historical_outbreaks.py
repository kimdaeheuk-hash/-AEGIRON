"""과거 공식 발병 선언 레지스트리 — Tier 2 학습셋의 '라벨' 소스.

정직성: 여기 등재된 것은 전부 WHO Disease Outbreak News/PHEIC 등 '공식 기록'이다.
지어낸 게 아니라 실제로 발생·선언된 사건이다. Tier 2는 이 선언일을 라벨(=미래에
확인된 발병)로 쓰고, 그 시점의 '실제 뉴스 신호'(GDELT, nowcast_backfill.py가 수집)를
특징으로 삼는다. GDELT 커버리지가 2017-01부터라 그 이후 사건만 등재한다.

주의: 이건 라벨(사건이 일어났다)이지 특징이 아니다 — 특징을 이 레지스트리에서
'역산'하면 미래정보 누수(look-ahead)다. 특징은 반드시 선언일 이전 뉴스에서만 온다.
"""
from __future__ import annotations

# 각 항목: 실제 공식 발병 선언(공개 기록).
#   event_id       : 내부 식별자
#   name           : 사건명
#   disease        : 질병
#   iso3           : 국가 ISO3(라벨 대상 국가)
#   declaration    : 공식 선언/보고일(YYYY-MM-DD, WHO DON 등 기준)
#   milestone      : nowcast의 선언 마일스톤 키(who_pheic | official_declaration)
#   gdelt_query    : 그 시점 뉴스량을 뽑을 GDELT DOC 질의(질병+국가 맥락)
#   source         : 근거(공식 출처)
OUTBREAKS = [
    {"event_id": "lassa_nga_2018", "name": "라싸열 나이지리아 2018", "disease": "라싸열",
     "iso3": "NGA", "declaration": "2018-01-22", "milestone": "official_declaration",
     "gdelt_query": '"Lassa fever" Nigeria', "source": "WHO DON 2018-03-01"},
    {"event_id": "ebola_cod_equateur_2018", "name": "에볼라 DRC 에콰퇴르 2018", "disease": "에볼라",
     "iso3": "COD", "declaration": "2018-05-08", "milestone": "official_declaration",
     "gdelt_query": '"Ebola" (Congo OR DRC)', "source": "WHO DON 2018-05-10"},
    {"event_id": "nipah_ind_kerala_2018", "name": "니파 인도 케랄라 2018", "disease": "니파바이러스",
     "iso3": "IND", "declaration": "2018-05-19", "milestone": "official_declaration",
     "gdelt_query": '"Nipah" (Kerala OR India)', "source": "WHO DON 2018-08-07"},
    {"event_id": "ebola_cod_kivu_2018", "name": "에볼라 DRC 북키부 2018", "disease": "에볼라",
     "iso3": "COD", "declaration": "2018-08-01", "milestone": "official_declaration",
     "gdelt_query": '"Ebola" (Congo OR DRC OR Kivu)', "source": "WHO DON 2018-08-04"},
    {"event_id": "ebola_cod_pheic_2019", "name": "에볼라 DRC PHEIC 2019", "disease": "에볼라",
     "iso3": "COD", "declaration": "2019-07-17", "milestone": "who_pheic",
     "gdelt_query": '"Ebola" (Congo OR DRC)', "source": "WHO PHEIC 선언 2019-07-17"},
    {"event_id": "measles_wsm_2019", "name": "홍역 사모아 2019", "disease": "홍역",
     "iso3": "WSM", "declaration": "2019-10-16", "milestone": "official_declaration",
     "gdelt_query": '"measles" Samoa', "source": "Samoa 정부/WHO 2019-11"},
    {"event_id": "ebola_cod_equateur_2020", "name": "에볼라 DRC 에콰퇴르 11차 2020", "disease": "에볼라",
     "iso3": "COD", "declaration": "2020-06-01", "milestone": "official_declaration",
     "gdelt_query": '"Ebola" (Congo OR DRC OR Mbandaka)', "source": "WHO DON 2020-06-11"},
    {"event_id": "marburg_gin_2021", "name": "마르부르크 기니 2021", "disease": "마르부르크",
     "iso3": "GIN", "declaration": "2021-08-09", "milestone": "official_declaration",
     "gdelt_query": '"Marburg" Guinea', "source": "WHO DON 2021-08-09"},
    {"event_id": "nipah_ind_kerala_2021", "name": "니파 인도 케랄라 2021", "disease": "니파바이러스",
     "iso3": "IND", "declaration": "2021-09-05", "milestone": "official_declaration",
     "gdelt_query": '"Nipah" (Kerala OR India)', "source": "WHO DON 2021-09"},
    {"event_id": "ebola_sudan_uga_2022", "name": "수단형 에볼라 우간다 2022", "disease": "에볼라",
     "iso3": "UGA", "declaration": "2022-09-20", "milestone": "official_declaration",
     "gdelt_query": '"Ebola" Uganda', "source": "WHO DON 2022-09-21"},
    {"event_id": "marburg_gha_2022", "name": "마르부르크 가나 2022", "disease": "마르부르크",
     "iso3": "GHA", "declaration": "2022-07-17", "milestone": "official_declaration",
     "gdelt_query": '"Marburg" Ghana', "source": "WHO DON 2022-07-17"},
    {"event_id": "marburg_gnq_2023", "name": "마르부르크 적도기니 2023", "disease": "마르부르크",
     "iso3": "GNQ", "declaration": "2023-02-13", "milestone": "official_declaration",
     # GDELT는 괄호를 OR 묶음에만 허용한다 — `(Equatorial Guinea)`는 HTTP 200 +
     # 평문 오류("Parentheses may only be used around OR'd statements")로 되돌아왔고,
     # 예전 코드가 그걸 '자료 없음'으로 삼켜 이 사건이 조용히 비어 있었다.
     "gdelt_query": '"Marburg" "Equatorial Guinea"', "source": "WHO DON 2023-02-13"},
    {"event_id": "marburg_tza_2023", "name": "마르부르크 탄자니아 2023", "disease": "마르부르크",
     "iso3": "TZA", "declaration": "2023-03-21", "milestone": "official_declaration",
     "gdelt_query": '"Marburg" Tanzania', "source": "WHO DON 2023-03-21"},
    {"event_id": "nipah_ind_kerala_2023", "name": "니파 인도 케랄라 2023", "disease": "니파바이러스",
     "iso3": "IND", "declaration": "2023-09-12", "milestone": "official_declaration",
     "gdelt_query": '"Nipah" (Kerala OR India)', "source": "WHO DON 2023-09"},
    {"event_id": "mpox_cod_pheic_2024", "name": "엠폭스 clade Ib PHEIC 2024", "disease": "엠폭스",
     "iso3": "COD", "declaration": "2024-08-14", "milestone": "who_pheic",
     # 원래 `"mpox" OR "monkeypox" (Congo OR DRC)`였는데 두 가지가 틀렸다:
     # ① 결합 오류 — `A OR B (지역)`은 A를 지역 제한 없이 잡아 전 세계 mpox 기사가
     #    콩고 신호로 들어온다. 병명 묶음을 먼저 괄호로 닫아야 한다.
     # ② GDELT는 5글자 미만 구문을 거부한다("The specified phrase is too short") —
     #    `"mpox"`가 4글자라 질의 전체가 통째로 실패했다. 2024년 8월 시점 보도는
     #    개명 직후라 monkeypox 표기가 함께 쓰였으므로 그쪽만 남긴다.
     "gdelt_query": '"monkeypox" (Congo OR DRC)', "source": "WHO PHEIC 2024-08-14"},
    {"event_id": "marburg_rwa_2024", "name": "마르부르크 르완다 2024", "disease": "마르부르크",
     "iso3": "RWA", "declaration": "2024-09-27", "milestone": "official_declaration",
     "gdelt_query": '"Marburg" Rwanda', "source": "WHO DON 2024-09-27"},
]


def event_country_map() -> dict[str, str]:
    """event_id → iso3(라벨 매핑). nowcast_dataset가 병합해 라벨 국가를 넓힌다."""
    return {o["event_id"]: o["iso3"] for o in OUTBREAKS}
