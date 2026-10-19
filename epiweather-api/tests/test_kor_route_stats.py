"""한국 국제선 국가별 운송 실적 자동 내려받기 (2026-10-19, ⑦).

개발 환경에서 data.go.kr 에 못 붙어 실제 경로·열 이름을 보지 못했다. 이 시험은 '모를 때 지어내지
않는다'를 고정한다: ① 첨부파일 ID 경로·상세 키 경로 둘 다 ② HTML 응답을 CSV 로 읽지 않음
③ 열 이름이 바뀌면 고르지 않고 머리글을 사유에 남김 ④ 국내선·한국 자신은 빼고, 못 붙인 국가명은 남김
⑤ 인천 자료 실패는 실패(기존 스냅샷 유지는 reference_snapshots) ⑥ 발할라 스냅샷 보고에 섞이지 않음.
"""
from __future__ import annotations

import json

import pytest

from algorithms import kor_route_stats as krs

# 실제 인천 파일(2026-07-07 등록본)의 머리글 그대로 — 캡틴이 받아 준 파일로 확인(2026-10-19).
HEADER = ("년도,월,항공사(ICAO),항공사(IATA),항공사명,국제_국내,노선,국가,공항,도착_출발,정기_부정기,"
          "여객_화물,운항(편),유임승객(명),무임승객(명),환승객(명),직화물(kg),환적화물(kg),우편물(kg),수하물(kg)")
CSV = HEADER + "\n" + "\n".join([
    "2026년,01월,KAL,KE,대한항공,국제,일본,일본,NRT,도착,정기,여객,21 ,4108 ,16 ,681 ,0 ,0 ,0 ,0 ",
    "2026년,02월,KAL,KE,대한항공,국제,일본,일본,NRT,출발,정기,여객,20 ,3788 ,14 ,1862 ,0 ,0 ,0 ,0 ",
    "2026년,01월,HVN,VN,베트남항공,국제,동남아,베트남,HAN,도착,정기,여객,3 ,552 ,0 ,11 ,0 ,0 ,0 ,0 ",
    "2026년,01월,UAL,UA,유나이티드항공,국제,미주,하와이,HNL,도착,정기,여객,2 ,400 ,0 ,0 ,0 ,0 ,0 ,0 ",
    "2026년,01월,UAL,UA,유나이티드항공,국제,미주,미국,SFO,도착,정기,여객,4 ,600 ,0 ,100 ,0 ,0 ,0 ,0 ",
    "2026년,01월,XXX,XX,가상항공,국제,기타,아틀란티스,ZZZ,도착,정기,여객,1 ,10 ,0 ,0 ,0 ,0 ,0 ,0 ",
    "2026년,01월,AAR,OZ,아시아나항공,국내,한국,한국,CJU,도착,부정기,여객,1 ,251 ,0 ,0 ,0 ,0 ,0 ,0 ",
]) + "\n"


class Resp:
    def __init__(self, status=200, text="", content=None, js=None):
        self.status_code, self.text = status, text
        self.content = content if content is not None else text.encode()
        self._js = js

    def json(self):
        if self._js is None:
            raise ValueError("not json")
        return self._js


class FakeSession:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, params=None, **kw):
        self.calls.append((url, params))
        for key, resp in self.routes.items():
            if key in url:
                return resp
        return Resp(404)


def test_atch_file_id_route_and_real_incheon_format():
    page = '<title>인천국제공항공사_항공사별 노선별 운송실적</title> fn(\'FILE_000000003123456\')'
    s = FakeSession({"fileData.do": Resp(text=page),
                     "fileDownload.do": Resp(content=CSV.encode("utf-8-sig"))})
    raw, route = krs.download_csv(15062056, s)
    assert route["route"] == "atchFileId" and route["atch_file_id"] == "FILE_000000003123456"
    agg = krs.aggregate(krs.decode(raw))
    # 여객 = 유임 + 무임 + 환승 (총여객 열은 없다). 일본 = (4108+16+681) + (3788+14+1862)
    assert agg["by_country"]["JPN"] == {"passengers": 10469, "flights": 41, "name": "일본"}
    assert agg["by_country"]["USA"]["passengers"] == 1100, "하와이는 미국으로 합친다(이 자료 전용 표)"
    assert "KOR" not in agg["by_country"] and agg["skipped_domestic"] == 1
    assert agg["unmapped"] == {"아틀란티스": 10}, "못 붙인 국가명을 버리지 않고 남긴다"
    assert agg["period"] == ["2026년 01월", "2026년 02월"]


def test_uddi_route_when_page_has_no_file_id():
    page = "<title>x</title> publicDataDetailPk=uddi:1234abcd-5678-90ef-aaaa-bbbbccccdddd"
    s = FakeSession({"fileData.do": Resp(text=page),
                     "selectFileDataDownload.do": Resp(js={"atchFileId": "FILE_000000009999999",
                                                           "fileDetailSn": 2}),
                     "fileDownload.do": Resp(content=CSV.encode("utf-8"))})
    raw, route = krs.download_csv(15062056, s)
    assert route["route"] == "uddi→atchFileId"
    assert s.calls[-1][1] == {"atchFileId": "FILE_000000009999999", "fileDetailSn": 2}


def test_html_instead_of_csv_is_a_failure_with_reason():
    s = FakeSession({"fileData.do": Resp(text="FILE_000000003123456"),
                     "fileDownload.do": Resp(text="<!DOCTYPE html><html>로그인이 필요합니다</html>")})
    with pytest.raises(krs.FetchError) as e:
        krs.download_csv(15062056, s)
    assert "HTML" in str(e.value)


def test_page_without_ids_says_so():
    s = FakeSession({"fileData.do": Resp(text="<title>점검 중</title>")})
    with pytest.raises(krs.FetchError) as e:
        krs.download_csv(15062056, s)
    assert "첨부파일 ID·상세 키를 못 찾음" in str(e.value) and "점검 중" in str(e.value)


def test_changed_header_is_not_guessed():
    text = "국가,여객수\n일본,1\n"
    with pytest.raises(krs.FetchError) as e:
        krs.aggregate(text)
    msg = str(e.value)
    assert "없는 열" in msg and "유임승객(명)" in msg and "여객수" in msg, \
        "열 이름이 바뀌면 고르려 들지 않고 없는 열과 머리글을 남긴다"


def test_fetch_snapshot_payload_and_failure(monkeypatch):
    monkeypatch.setattr(krs, "download_csv", lambda pk, session=None: (CSV.encode("utf-8"), {"route": "atchFileId"}))
    snap = krs.fetch_snapshot()
    assert snap["fetched_by"] == "auto" and snap["by_country"]["VNM"]["passengers"] == 563
    assert "인천공항만" in snap["scope_note"]

    def fail(pk, session=None):
        raise krs.FetchError("① 페이지 HTTP 403")
    monkeypatch.setattr(krs, "download_csv", fail)
    with pytest.raises(krs.FetchError) as e:
        krs.fetch_snapshot()
    assert "인천 자료 실패" in str(e.value) and "HTTP 403" in str(e.value)


def test_committed_seed_snapshot_is_valid():
    """캡틴이 받아 준 2026-07-07 등록본으로 만든 첫 스냅샷 — 검증 관문을 통과하고 상위가 상식적이다."""
    from algorithms import reference_snapshots as rs
    payload = json.loads(rs.path_for("kor_route_stats").read_text(encoding="utf-8"))
    assert rs.validate("kor_route_stats", payload)[0]
    assert payload["fetched_by"] == "manual" and payload["period"] == ["2026년 01월", "2026년 06월"]
    assert payload["unmapped"] == {}
    top = sorted(payload["by_country"], key=lambda k: -payload["by_country"][k]["passengers"])[:3]
    assert top == ["JPN", "CHN", "VNM"]


def test_registered_as_snapshot_but_not_in_valhalla_report(tmp_path, monkeypatch):
    from algorithms import reference_snapshots as rs
    monkeypatch.setattr(rs, "REFERENCE_DIR", tmp_path)
    assert rs.SNAPSHOTS["kor_route_stats"]["owner"] == "SKULD"
    names_all = [r["name"] for r in rs.report()["snapshots"]]
    names_valhalla = [r["name"] for r in rs.report(owner="VALHALLA")["snapshots"]]
    assert "kor_route_stats" in names_all and "kor_route_stats" not in names_valhalla
    assert set(names_valhalla) == {"vaccine_supply", "ihr_capacity", "approved_products"}
    payload = {"snapshot_date": "2026-10-19", "by_country": {f"C{i:02d}": {"passengers": 1} for i in range(10)}}
    ok, why = rs.validate("kor_route_stats", payload)
    assert not ok and "하한 30건" in why, "국가가 너무 적으면 매핑이 깨진 것으로 본다"
