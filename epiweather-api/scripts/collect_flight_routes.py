"""항공 노선 실측 수집 — 나라쌍별 국제선 노선 수를 뽑아 캐시로 굽는다.

## 왜 만들었나

디지털 트윈의 항공망이 **손으로 적은 11개 노선**뿐이었다. 그래서 아메리카
대륙 전체가 그래프에서 떨어져 나가, 미국·브라질이 1년을 돌려도 "미도달"로
찍혔다. 안 퍼진 게 아니라 **갈 길을 우리가 몰랐던 것**이다.

## 무엇을 쓰나 (둘 다 무료·공개)

* **OurAirports** (퍼블릭 도메인, 지금도 갱신) — 공항 IATA 코드와 ISO 국가코드.
  공항→나라를 **코드로** 잇는다. 국가 *이름* 으로 이으면 "Congo (Kinshasa)"
  같은 표기에서 엉뚱한 나라로 간다(실제로 그랬다).
* **OpenFlights routes.dat** (ODbL) — 어느 항공사가 어느 공항 사이를 나는지.
  67,663개 노선.

## ★ 이 데이터의 한계 ★

**오래됐다.** routes.dat 은 2017년에 마지막으로 갱신됐고 실데이터는 2014년
기준이다. 그래도 쓰는 이유는, 우리가 필요한 게 **"두 나라 사이에 항공편이
있느냐"** 이고 그건 잘 안 변하기 때문이다 — 브라질과 미국 사이 항공편은
2014년에도 있었고 지금도 있다. 반면 개별 노선의 편수·기종은 많이 바뀌었다.

**편수가 없다.** 원본에 주간 편수나 승객 수가 아예 없다. 그래서 나라쌍별
**노선 개수**를 세고, 노선 1개당 하루 몇 명이 오가는지는 계수로 환산한다.
계수는 지어내지 않고 굵은 시장 네 곳에서 역산해 맞췄다(digital_twin.py 참고).

**공항이 닫히면 노선을 잃는다.** 2014년 노선인데 공항 표는 2026년 것이라,
그 사이 문 닫은 공항의 노선은 버려진다(예: 베를린 테겔 TXL, 418개 노선).
같은 나라의 다른 공항이 대개 받쳐주므로 나라 단위에서는 큰 문제가 아니다.

## 쓰는 법

    python scripts/collect_flight_routes.py

원본을 `data/raw/` 에 받아 `algorithms/reference/flight_routes_by_country.json`
을 굽는다. **시뮬레이션은 이 캐시만 읽는다** — 실행 중에 인터넷에 나가지 않는다.

굽는 위치가 `data/` 가 아닌 이유: `epiweather-api/data/` 는 실행 중에 생기는
캐시·DB 스냅샷을 담는 곳이라 저장소에서 폴더째 제외돼 있다. 항공 노선표는
코드와 같이 배포돼야 하므로 코드 옆(`algorithms/reference/`)에 둔다.
원본 파일은 커도 되고 저장소에 안 들어가므로 `data/raw/` 에 그대로 둔다.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import io
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.country_resolve import iso2_to_iso3   # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "algorithms", "reference", "flight_routes_by_country.json")

SOURCES = {
    "ourairports_airports.csv":
        "https://davidmegginson.github.io/ourairports-data/airports.csv",
    "openflights_routes.dat":
        "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat",
}


def fetch(name: str, url: str, force: bool = False) -> str:
    """원본을 data/raw/ 에 받아둔다. 이미 있으면 다시 받지 않는다."""
    os.makedirs(RAW_DIR, exist_ok=True)
    path = os.path.join(RAW_DIR, name)
    if os.path.exists(path) and not force:
        print(f"  이미 있음: {name} ({os.path.getsize(path):,} bytes)")
        return path
    print(f"  내려받는 중: {name} <- {url}")
    with urllib.request.urlopen(url, timeout=180) as resp:
        data = resp.read()
    with open(path, "wb") as fh:
        fh.write(data)
    print(f"  받음: {name} ({len(data):,} bytes)")
    return path


def load_airport_countries(path: str) -> tuple[dict[str, str], set[str]]:
    """IATA 코드 → ISO3. 국가코드를 모르는 건 **버린다**, 추측하지 않는다."""
    iata_to_iso3: dict[str, str] = {}
    unmapped: set[str] = set()
    with io.open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            code = (row.get("iata_code") or "").strip()
            if not code:
                continue
            iso3 = iso2_to_iso3(row.get("iso_country"))
            if iso3:
                iata_to_iso3[code] = iso3
            elif row.get("iso_country"):
                unmapped.add(row["iso_country"])
    return iata_to_iso3, unmapped


def count_country_routes(
    routes_path: str, iata_to_iso3: dict[str, str]
) -> tuple[collections.Counter, dict[str, int]]:
    """나라쌍별 국제선 노선 수. 국내선과 공항을 못 찾은 노선은 세지 않는다."""
    pairs: collections.Counter = collections.Counter()
    stats = {"total": 0, "domestic": 0, "unknown_airport": 0}

    with io.open(routes_path, encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) < 5:
                continue
            stats["total"] += 1
            a = iata_to_iso3.get(row[2].strip())
            b = iata_to_iso3.get(row[4].strip())
            if a is None or b is None:
                stats["unknown_airport"] += 1
                continue
            if a == b:
                stats["domestic"] += 1        # 나라 안 이동은 SEIR 이 이미 다룬다
                continue
            pairs[f"{min(a, b)}|{max(a, b)}"] += 1

    return pairs, stats


def main() -> int:
    force = "--force" in sys.argv
    print("항공 노선 수집 시작")

    paths = {name: fetch(name, url, force) for name, url in SOURCES.items()}

    iata_to_iso3, unmapped = load_airport_countries(paths["ourairports_airports.csv"])
    print(f"  공항 {len(iata_to_iso3):,}개에 국가코드를 붙였다")
    if unmapped:
        print(f"  국가코드를 모르는 지역 {len(unmapped)}개는 뺐다: "
              f"{', '.join(sorted(unmapped)[:12])}…")

    pairs, stats = count_country_routes(paths["openflights_routes.dat"], iata_to_iso3)
    print(f"  노선 {stats['total']:,}개 → 국제 나라쌍 {len(pairs):,}개 "
          f"(국내선 {stats['domestic']:,} · 공항 미상 {stats['unknown_airport']:,} 제외)")

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sources": {
            "airports": "OurAirports (public domain) — 공항 IATA·ISO 국가코드",
            "routes": "OpenFlights routes.dat (ODbL) — 2017-02 갱신, 2014 기준 데이터",
        },
        "caveats": [
            "노선 데이터가 2014년 기준이다. 나라 사이 연결 유무는 잘 안 변하지만 "
            "개별 노선의 편수·기종은 많이 바뀌었다.",
            "원본에 편수·승객 수가 없다. 값은 '노선 개수'이지 사람 수가 아니다.",
            "2014년 이후 문 닫은 공항의 노선은 빠진다(예: 베를린 테겔).",
        ],
        "stats": stats | {"country_pairs": len(pairs),
                          "airports_mapped": len(iata_to_iso3)},
        # 값의 뜻: 그 나라쌍 사이를 잇는 **항공사-공항쌍 노선의 개수**
        "route_counts": dict(sorted(pairs.items())),
    }

    with io.open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, sort_keys=False)

    print(f"  기록: {OUT_PATH} ({os.path.getsize(OUT_PATH):,} bytes)")
    print("가장 굵은 연결:")
    for pair, n in pairs.most_common(8):
        print(f"    {pair}  {n:,}개 노선")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
