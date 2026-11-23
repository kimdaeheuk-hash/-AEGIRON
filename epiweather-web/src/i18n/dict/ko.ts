import type { Dictionary } from '../types';

// 2026-11-22 개편 사전 — 헤임달(변이 추적) → 발할라 → 극지. 지운 페이지 사전은 커밋 83406e4 에 있음.
export const ko: Dictionary = {
  "nav": {
    "polar": "극지 감시",
    "heimdall": "헤임달",
    "valhalla": "발할라",
    "methodology": "방법론",
    "government": "기업·기관",
    "developers": "개발자 · API",
    "security": "보안",
    "about": "회사 소개",
    "contact": "문의",
    "product": "제품",
    "company": "회사",
    "dashboard": "운영 화면",
    "openMenu": "메뉴 열기",
    "closeMenu": "메뉴 닫기",
    "language": "언어"
  },
  "footer": {
    "tagline": "변이 추적 → 대응 판정.",
    "product": "제품",
    "company": "회사",
    "legal": "법적 고지",
    "privacy": "개인정보처리방침",
    "terms": "이용약관",
    "rights": "All rights reserved.",
    "location": "대한민국 부산",
    "disclaimer": "아이기론 = 조기감지 정확도 검증 트랙레코드 미보유 · 본 사이트 수치 = 운영 시스템 실측값, 예측 성능 주장 아님"
  },
  "home": {
    "metaTitle": "AEGIRON — 변이 추적 · 대응 판정",
    "metaDescription": "공개 병원체 유전체에서 우세 계통이 바뀌는 순간을 매시 원장에 기록하고(헤임달), 그 위협에 쓸 백신·치료제가 있는지 매일 판정함(발할라). 바이오·진단 기업과 국가 바이오안보 기관용.",
    "eyebrow": "AEGIRON · 바이오 헬스",
    "title": "변이를 추적하고\n대응 가능 여부까지 본다",
    "lead": "공개 병원체 유전체에서 우세 계통이 바뀌는 순간을 매시 원장에 남기고(헤임달 변이 추적), 그 위협에 쓸 백신·치료제가 있는지 매일 판정함(발할라). 서열 스크리닝은 개발 중(검증 진행)임. 바이오·진단 기업과 국가 바이오안보 기관이 첫 고객임.",
    "primaryCta": "운영 화면 보기",
    "secondaryCta": "기업·기관 도입 검토",
    "chainTitle": "세 고리",
    "chainLead": "변이 추적(헤임달)과 대응 판정(발할라)을 앞에 세우고, 극지(감지)는 미래 연구로 둠. 서열 스크리닝은 검증이 끝날 때까지 개발 중으로 표시함. 지금 실제로 도는 것만 적음. 세 고리의 상태 변화는 BAIKAL MOB(상태변화 엔진)이 매시 판정·기록함.",
    "stages": [
      {
        "code": "HEIMDALL",
        "name": "헤임달",
        "role": "변이 추적",
        "body": "공개 유전체 계통(Nextstrain)에서 우세 계통이 바뀌거나 새 계통이 나타나면 그 순간을 원장에 적음. 판정이 아니라 기록·추적.",
        "facts": [
          "SARS-CoV-2 공개 빌드를 매시 확인 · 우세 계통 교체·신규 계통만 원장에 기록",
          "계통·구성비는 Nextstrain 공개 값을 옮긴 것 · 전이 여부는 원장이 직전 주기와 비교해 적은 기록",
          "서열 스크리닝은 개발 중(검증 진행) — 공개 자연 서열로 거짓 양성을 매주 잼 · 민감도는 아직 재지 않음"
        ],
        "href": "heimdall",
        "linkLabel": "변이 원장 보기"
      },
      {
        "code": "VALHALLA",
        "name": "발할라",
        "role": "대응 판정",
        "body": "위협 목록마다 등록된 대응제(비축·승인 제품)가 덮는지, 변이 변화가 그 판정을 흔드는지를 하루 한 행씩 원장에 남김.",
        "facts": [
          "위협×비축×변이 대조 판정을 매일 원장에 기록",
          "공개 자료(WHO 사전적격 백신·승인 제품·임상 등록) 기준 · 국가 비축 재고는 보지 않음",
          "비축 항목을 등록하면 그 값으로 계산 · 미등록이면 예시 데이터임을 표시"
        ],
        "href": "valhalla",
        "linkLabel": "발할라 구획 열기"
      },
      {
        "code": "POLAR",
        "name": "극지 감시",
        "role": "감지",
        "body": "영구동토가 녹는 지역은 오래 묻혀 있던 병원체(탄저 등)가 다시 드러날 수 있는 자리임. 8개 극지 지역의 기상과 현지어 보도를 매시 관찰함.",
        "facts": [
          "8개 지역(시베리아 야말·알래스카·캐나다 북극권·그린란드·스발바르·남극 반도 등) 매시 관찰",
          "기온·해빙일수 = Open-Meteo 기상 관측값 · 평년 대비 편차 = 16년 재분석 기준 계산값",
          "관찰 등급이지 경보 아님 — 못 읽은 시각은 판정 안 함으로 남김"
        ],
        "href": "polar",
        "linkLabel": "극지 추이 보기"
      }
    ],
    "healthTitle": "수집 상태",
    "healthOk": "세 층 소스 중 {ok}/{total} 정상(운영 서버 실측)",
    "healthUnknown": "운영 서버 상태를 읽지 못함(판정 안 함)",
    "notTitle": "하지 않는 것",
    "notPoints": [
      "전 세계 감염병 경보 · 국가 위험 순위 — 개편(2026-11)에서 뺌",
      "발병·판정 정확도 주장 — 아직 검증된 트랙레코드 없음",
      "병원체 서열 설계·합성·최적화 — 방어 전용, 하지 않음"
    ]
  },
  "polar": {
    "title": "극지 추이 (매시 저장분)",
    "lead": "지역별 처음 저장값 → 최근값 · 기온(일최고 평균)·해빙일수는 기상 관측값, Δ(같은 달 10년 평균 대비)는 계산값 · 값이 바뀔 때만 기록이 늘어남",
    "span": "저장 기간 약 {days}일 — 30일이 아직 차지 않았음(2026-11-15부터 저장)",
    "undetermined": "그 시각에 못 읽은 기록 {n}건은 추이에서 뺌(판정 안 함)",
    "cols": {
      "region": "지역",
      "first": "처음 저장값",
      "latest": "최근값",
      "change": "변화",
      "records": "기록 수"
    },
    "empty": "아직 저장된 극지 값 없음",
    "unavailable": "극지 이력을 읽지 못함(판정 안 함)",
    "apiLabel": "원자료 API"
  },
  "variant": {
    "title": "변이 원장 (매시 기록)",
    "lead": "빌드별 최신 우세 계통과 최근 계통 전이 · 계통·구성비·시퀀스 수는 Nextstrain 공개 값 인용, 전이는 원장이 직전 주기와 비교해 적은 기록",
    "stateTitle": "지금 상태",
    "transitionsTitle": "최근 전이 (최대 10건)",
    "cols": {
      "build": "빌드",
      "dominant": "우세 계통",
      "share": "구성비",
      "sequences": "최근 시퀀스 수",
      "observed": "확인 시각",
      "kind": "전이",
      "change": "변화"
    },
    "transitions": {
      "first_seen": "첫 기록",
      "dominant_changed": "우세 교체",
      "new_clade": "신규 계통",
      "none": "변화 없음"
    },
    "empty": "아직 원장 기록 없음",
    "noTransitions": "기록된 전이 없음",
    "unavailable": "변이 원장을 읽지 못함(판정 안 함)",
    "screenerTitle": "서열 스크리닝 — 개발 중(검증 진행)",
    "screenerNote": "2026-11-22 측정: 공개 자연 서열 7종에서 거짓 양성 1,000염기 조각 기준 6.4%, 서열 단위 1/7. 민감도(위험 서열을 잡는가)는 아직 재지 않았음 — 결과는 판정이 아니라 우선순위 참고값임.",
    "growthTitle": "커지고 있는 변이 (성장 신호 · 추정)",
    "growthLead": "최근 4주와 직전 4주의 계통 구성비를 비교한 주당 성장률. 우세가 바뀌기 전에 커지는 계통을 먼저 보려는 신호임. 표본 수·제출 지연에 따라 흔들리는 추정값이며, 표본이 부족하면 판정하지 않음.",
    "growthCols": {
      "clade": "계통",
      "share": "구성비(직전 → 최근)",
      "weekly": "주당 성장률",
      "doubling": "비율 2배까지(일)",
      "count": "시퀀스 수(직전 → 최근)"
    },
    "growthNone": "커지는 계통 없음",
    "growthUnavailable": "성장 신호를 읽지 못함(판정 안 함)"
  },
  "baikal": {
    "title": "BAIKAL MOB",
    "layer": "상태변화 엔진 · 온톨로지 위층",
    "lead": "온톨로지(엔진과 그 연결) 위에서 매시 각 엔진의 상태를 판정하고, 상태가 바뀐 순간만 기록함. 상태는 정상·저하·중단·판정 안 함 네 가지이며, 못 본 것은 정상으로 세지 않음. 상류 엔진이 멈추면 연결을 따라 어느 입력이 낡는지 함께 적음(하류 상태는 바꾸지 않음).",
    "observedAt": "마지막 판정 {t}",
    "stale": "마지막 판정이 {m}분 전 — 수집이 멎었을 수 있음. 아래를 지금 상태로 읽지 말 것",
    "empty": "아직 판정 기록 없음 — 다음 수집 주기(매시 정각) 뒤에 생김",
    "unavailable": "BAIKAL 상태를 읽지 못함(판정 안 함)",
    "cols": {
      "engine": "엔진",
      "status": "상태",
      "since": "언제부터",
      "reason": "근거",
      "observed": "시각",
      "change": "변화"
    },
    "statuses": {
      "ok": "🟢 정상",
      "degraded": "🟡 저하",
      "down": "🔴 중단",
      "undetermined": "⚪ 판정 안 함"
    },
    "observationStart": "관측 시작",
    "impactsTitle": "영향 — 상류 이상이 번지는 곳",
    "noImpacts": "번지는 이상 없음",
    "transitionsTitle": "최근 상태 전이",
    "noTransitions": "기록된 전이 없음",
    "apiLabel": "원자료 API"
  },
  "pages": {
    "polar": {
      "metaTitle": "극지 감시",
      "metaDescription": "8개 극지 지역의 기온·해빙일수·평년 대비 편차를 매시 저장한 추이.",
      "eyebrow": "POLAR · 감지",
      "title": "극지 감시",
      "lead": "영구동토 지역의 기상 이상을 매시 관찰·저장함 · 관찰 등급(경보 아님)",
      "blocks": []
    },
    "about": {
      "metaTitle": "회사 소개",
      "metaDescription": "아이기론 — 병원체 유전체의 변화를 매시 추적하고, 그 변화에 맞설 수단이 이미 존재하는지까지 가려내는 바이오 헬스 기업.",
      "eyebrow": "ABOUT",
      "title": "아이기론",
      "lead": "부산에서 시작한 1인 기술 기업입니다. 병원체 유전체가 어떻게 변해 가는지를 매시 추적하고, 그 변화 앞에서 막아설 수단이 이미 세상에 존재하는지까지 가려내는 일 — 저희는 그 한 가지에 역량을 모읍니다. 바이오·진단 기업과 국가 바이오안보 기관을 첫 동반자로 맞이합니다.",
      "blocks": [
        {
          "title": "왜 하나에 집중하는가",
          "body": "2026년 11월까지 아이기론은 전 세계의 질병 신호를 폭넓게 수집했습니다. 그러나 다루는 범위가 넓어질수록 전문성은 옅어졌고, 외부의 평가도 이를 냉정하게 지적했습니다. 저희는 욕심을 덜어내기로 했습니다. 병원체 변이 추적(헤임달)을 앞에 세우고, 대응 수단의 유무를 가리는 판정(발할라)이 그 뒤를 받치며, 극지 감시는 미래를 위한 연구로 남겼습니다. 넓게 흩어진 백 가지보다, 깊게 파고든 한 가지가 더 멀리 간다고 믿습니다."
        },
        {
          "title": "지키는 원칙",
          "points": [
            "**측정과 추정, 대리 지표를 결코 뒤섞지 않습니다.** 어떤 숫자가 관측에서 나왔고 어떤 숫자가 해석에서 나왔는지, 화면마다 분명히 밝힙니다.",
            "**성공·실패·판정 안 함, 세 가지 상태를 지킵니다.** 보지 못한 것을 0이나 ‘정상’으로 꾸미지 않습니다.",
            "**방어가 목적입니다.** 병원체를 설계하거나 합성하거나 더 위험하게 만드는 기능은 두지 않습니다."
          ]
        }
      ],
      "cta": {
        "title": "도입과 협력을 환영합니다",
        "body": "바이오·진단 기업, 연구 기관, 그리고 국가와 지자체의 바이오안보 기관 — 함께 검증하고자 하는 모든 분을 기다립니다.",
        "label": "문의하기",
        "href": "contact"
      }
    },
    "methodology": {
      "metaTitle": "방법론",
      "metaDescription": "극지 관찰 점수, 헤임달 변이 원장, 발할라 대조 판정의 계산 방식과 한계.",
      "eyebrow": "METHODOLOGY",
      "title": "방법론",
      "lead": "세 고리가 각각 무엇을 재고 무엇을 재지 않는지",
      "blocks": [
        {
          "title": "극지 감시",
          "kicker": "POLAR",
          "tone": "sky",
          "points": [
            "기온(일최고 평균)·해빙일수 = Open-Meteo 관측값",
            "평년 대비 편차 = 같은 달 16년 재분석 평균 대비 **계산값**",
            "현지어(러·영·노) 보도 키워드 비율 = **대리값** · 확진 아님",
            "관찰 점수는 등급이지 경보가 아님 · 기상 자료를 못 받은 시각은 판정 안 함"
          ],
          "note": "한계: 지역 8곳은 대표 지점 하나씩임 · 영구동토 해빙과 병원체 노출의 인과는 가설 수준"
        },
        {
          "title": "헤임달",
          "kicker": "HEIMDALL",
          "tone": "violet",
          "points": [
            "Nextstrain 공개 빌드에서 최근 60일 우세 계통·구성비를 읽음",
            "우세 계통이 바뀐 주기만 원장에 전이로 기록 · 자료가 없으면 기록하지 않음",
            "서열 스크리닝 지표(CAI·CpG·엔트로피·국소 이상)는 **우선순위 신호**이지 판정이 아님",
            "스크리너는 **개발 중(검증 진행)** — 공개 참조 서열로 특이도(자연 서열 거짓 양성 비율)를 주간 측정(GitHub Actions `heimdall-validation`). 2026-11-22: 1,000염기 조각 기준 6.4%, 서열 단위 1/7. 민감도·판정은 측정하지 않음."
          ],
          "note": "한계: 공개 시퀀스 제출 지연·편향을 그대로 받음"
        },
        {
          "title": "발할라",
          "kicker": "VALHALLA",
          "tone": "forest",
          "points": [
            "위협마다 등록 대응제의 대상 병원체·선언 효능으로 덮음 여부를 판정",
            "변이 원장의 플래그가 있으면 판정에 함께 적음",
            "국가 비축 재고·변이별 효능은 공개 자료가 아니라 보지 않음"
          ],
          "note": "한계: 비축 항목이 등록되지 않으면 예시 데이터로 계산하며 그 사실을 응답에 표시"
        }
      ]
    },
    "government": {
      "metaTitle": "정부·국가 바이오안보",
      "metaDescription": "국가 바이오안보 기관을 위한 변이 추적·대응제 판정·극지 감지.",
      "eyebrow": "GOVERNMENT",
      "title": "바이오·진단 기업과 국가 바이오안보 기관용",
      "lead": "병원체 유전체를 읽고(헤임달), 그 위협에 쓸 대응제가 있는지(발할라)까지 한 화면에서 · 첫 고객으로 바이오·진단 기업과 국가 바이오안보 기관을 둠",
      "blocks": [
        {
          "title": "기관이 얻는 것",
          "items": [
            {
              "title": "극지 조기 관찰",
              "body": "영구동토 지역 8곳의 기상 이상을 매시 관찰한 기록",
              "meta": "극지"
            },
            {
              "title": "계통 전이 원장",
              "body": "공개 유전체에서 우세 계통이 바뀐 시점의 원장",
              "meta": "헤임달"
            },
            {
              "title": "대응제 공백 판정",
              "body": "위협별로 등록 대응제가 덮는지 매일 한 행",
              "meta": "발할라"
            }
          ]
        },
        {
          "title": "도입 형태",
          "points": [
            "공개 API로 바로 검토 가능",
            "기관 비축 목록을 등록하면 그 값으로 판정(키 필요)",
            "민감 데이터는 외부 API로 보내지 않는 구성 가능"
          ]
        },
        {
          "title": "정직 고지",
          "accent": true,
          "points": [
            "예측 정확도 트랙레코드 없음",
            "관찰 등급은 경보가 아님 · 대응 결정은 기관의 판단"
          ]
        }
      ],
      "cta": {
        "title": "파일럿 검토",
        "body": "기관 검토용 자료와 시연을 제공함",
        "label": "문의하기",
        "href": "contact"
      }
    },
    "security": {
      "metaTitle": "보안과 데이터 거버넌스",
      "metaDescription": "접근 통제, 고위험 프로그램 통제, 개인정보 원칙, 데이터 주권, 비밀 관리.",
      "eyebrow": "SECURITY & GOVERNANCE",
      "title": "보안과 데이터 거버넌스",
      "lead": "변경 권한 · 민감 기능 통제 · 데이터 이동 경로 — 코드 구현 그대로 공개",
      "blocks": [
        {
          "title": "접근 통제",
          "kicker": "ACCESS CONTROL",
          "tone": "indigo",
          "specs": [
            {
              "label": "전체 API",
              "value": "엔드포인트 13개"
            },
            {
              "label": "인증 필요",
              "value": "5개 — 상태 변경 · 고비용 · 고위험 기능"
            },
            {
              "label": "인증 방식",
              "value": "X-API-Key 헤더 · 다중 키(라벨별) · 상수 시간 비교"
            },
            {
              "label": "키 미설정 시",
              "value": "쓰기 API 전체 비활성(열린 상태 방치 없음)"
            }
          ]
        },
        {
          "title": "고위험 프로그램 통제",
          "kicker": "HEIMDALL · VALHALLA",
          "tone": "violet",
          "points": [
            "서열 스크리닝·비축 등록은 인증 필수 · 전 호출 키 라벨별 사용 기록",
            "HEIMDALL — **방어적 탐지 전용** · 서열 설계·합성·최적화·회피 기능 없음"
          ]
        },
        {
          "title": "개인정보 원칙",
          "kicker": "PRIVACY",
          "tone": "teal",
          "points": [
            "수집 대상 — 공개 기상·유전체·조달 자료 · 개인 환자 정보 미취급",
            "웹사이트·운영 화면 — 로그인·광고·방문 추적 도구 없음"
          ]
        },
        {
          "title": "비밀 관리와 운영 무결성",
          "kicker": "INTEGRITY",
          "tone": "sky",
          "items": [
            {
              "title": "비밀 관리",
              "body": "API 키·자격증명 운영 환경 변수 전용 · 저장소·문서 기록 금지"
            },
            {
              "title": "배포 관문",
              "body": "자동 시험 365건 전부 통과 코드만 운영 반영"
            },
            {
              "title": "조용한 실패 감시",
              "body": "소스 건강 매 주기 기록 · 외부(GitHub Actions)에서 매시 생존 확인"
            }
          ]
        }
      ],
      "cta": {
        "title": "보안 심사 자료 요청",
        "body": "기관 보안 검토용 구성·통제 설명 자료 제공",
        "label": "문의하기",
        "href": "contact"
      }
    },
    "developers": {
      "metaTitle": "개발자 · API",
      "metaDescription": "아이기론 REST API — 엔드포인트 13개, JSON 응답, X-API-Key 인증, OpenAPI 문서.",
      "eyebrow": "DEVELOPERS",
      "title": "개발자 · API",
      "lead": "운영 화면 전 수치의 단일 출처 = REST API",
      "blocks": [
        {
          "title": "기본 정보",
          "kicker": "BASICS",
          "tone": "sky",
          "specs": [
            {
              "label": "기본 주소",
              "value": "https://epiweather-api-production.up.railway.app"
            },
            {
              "label": "형식",
              "value": "REST · JSON"
            },
            {
              "label": "인증",
              "value": "읽기 공개 · 쓰기/고위험 X-API-Key"
            },
            {
              "label": "대화형 문서",
              "value": "/docs (OpenAPI)"
            }
          ]
        },
        {
          "title": "주요 엔드포인트",
          "kicker": "QUICK START",
          "tone": "teal",
          "items": [
            {
              "title": "극지 감시",
              "body": "8개 지역 관찰 점수·기준선·추세",
              "meta": "GET /api/polar-watch"
            },
            {
              "title": "극지 이력",
              "body": "매시 저장한 관측값 시계열",
              "meta": "GET /api/observations/history?layer=polar"
            },
            {
              "title": "변이 원장",
              "body": "공개 유전체 우세 계통 전이",
              "meta": "GET /api/variant-ledger"
            },
            {
              "title": "대조 원장",
              "body": "위협×비축×변이 일일 판정",
              "meta": "GET /api/valhalla/match-ledger"
            },
            {
              "title": "운영 상태",
              "body": "소스 건강·스케줄러·기준 스냅샷",
              "meta": "GET /api/status"
            }
          ]
        }
      ],
      "cta": {
        "title": "연동 키 발급",
        "body": "쓰기·고위험 기능 연동용 기관별 API 키 발급",
        "label": "문의하기",
        "href": "contact"
      }
    },
    "contact": {
      "metaTitle": "문의",
      "metaDescription": "아이기론 연락 방법",
      "eyebrow": "CONTACT",
      "title": "문의",
      "lead": "데모 예약 없이 시스템 전체 검토 가능 · 검토 후 질문·협력 제안 아래 연락처 접수",
      "blocks": [
        {
          "title": "연락처",
          "items": [
            {
              "title": "이메일",
              "body": "kimdaeheuk@gmail.com",
              "meta": "최속 경로"
            },
            {
              "title": "위치",
              "body": "대한민국 부산",
              "meta": "KST (UTC+9)"
            }
          ]
        },
        {
          "title": "특히 환영하는 연락",
          "points": [
            "**오류 지적** — 방법론·수치 오류 제보 · 확인 후 반영",
            "**현장 조직 연결** — 실제 감시망 연결 경로 = 현 최우선 다음 단계",
            "**파일럿 검토** — 재보험·정부·국제기구·현장 조직 전부 환영"
          ]
        }
      ]
    },
    "privacy": {
      "metaTitle": "개인정보처리방침",
      "metaDescription": "아이기론 웹사이트 개인정보 처리 방침",
      "eyebrow": "LEGAL",
      "title": "개인정보처리방침",
      "lead": "방문자 로그인 미요구 · 개인정보 미수집",
      "blocks": [
        {
          "title": "미수집 항목",
          "points": [
            "회원가입·로그인 부재 — 계정 정보 미수집",
            "광고·방문 분석 추적 도구 미사용",
            "대시보드 열람 — 개인 식별 정보 불필요"
          ]
        },
        {
          "title": "외부 서비스",
          "body": "홈 소개 영상 = YouTube 개인정보 보호 강화 모드 삽입 · 재생 시 YouTube 정책 적용 · 글꼴 = Google Fonts·jsDelivr 로드 — 해당 서비스 접속 기록(IP 주소 등) 잔류 가능"
        },
        {
          "title": "문의 시",
          "body": "이메일 연락 내용·주소 = 답변 목적 전용 사용 · 제3자 미제공"
        },
        {
          "title": "변경",
          "body": "방침 변경 시 본 페이지 갱신"
        }
      ]
    },
    "terms": {
      "metaTitle": "이용약관",
      "metaDescription": "아이기론 웹사이트·공개 데이터 이용 조건",
      "eyebrow": "LEGAL",
      "title": "이용약관",
      "lead": "본 사이트·공개 대시보드 이용 적용 조건",
      "blocks": [
        {
          "title": "제공 정보의 성격",
          "accent": true,
          "points": [
            "본 사이트 정보 = **참고용** · 의료·보건·투자 판단 근거 미제공",
            "예측·시나리오 수치 = **모델 가정 하 추정** · 실측값·보장 아님",
            "본 정보 기반 판단 결과 책임 부담 없음"
          ]
        },
        {
          "title": "데이터 출처",
          "body": "본 시스템 = WHO·CDC 등 공개 자료 수집·가공 · 원 자료 저작권·이용 조건 = 각 기관 귀속 · 가공 수치 원문 상이 가능 — 공식 인용 시 원 기관 자료 확인 필수"
        },
        {
          "title": "가용성",
          "body": "공개 대시보드 예고 없는 중단·변경 가능"
        }
      ]
    }
  },
  "api": {
    "tableTitle": "전체 엔드포인트",
    "tableLead": "운영 API 전 엔드포인트 기능별 분류 · 자물쇠 = X-API-Key 필요",
    "authYes": "키 필요",
    "authNo": "공개",
    "tags": {
      "GAI": "극지 감시",
      "후향 검증": "헤임달 · 변이 원장",
      "Stage 0: 합성위협 탐지": "헤임달 · 합성위협 탐지·서열 스크리닝",
      "Stage 8: 바이오방어": "발할라 · 대응제 판정",
      "시스템": "시스템 · 운영 상태",
      "BAIKAL MOB": "BAIKAL MOB · 상태변화 엔진"
    }
  },
  "common": {
    "siteName": "AEGIRON"
  }
};
