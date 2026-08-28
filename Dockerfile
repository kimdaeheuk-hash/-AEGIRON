FROM python:3.11-slim

# ★ 로그를 버퍼에 가두지 않는다 (2026-08-28) ★
# 컨테이너에서 stdout 은 tty 가 아니라 파이프라, 파이썬이 기본으로 약 8KB
# 블록 버퍼링을 건다. collector 의 `log()` 는 `print()` 라 flush 를 안 하므로
# 수집 로그가 8KB 가 찰 때까지 **프로세스 안에 갇힌다.**
#
# 실측(2026-08-28 배포): 같은 프로세스·같은 시각인데 둘이 갈렸다.
#   04:54:59  INFO: Application startup complete.   ← uvicorn(stderr) 즉시 도착
#   04:55:30  이동성(OpenSky) 전멸 — …              ← collector(stdout) **65분 뒤** 도착
# 관측되던 "2~3시간 배치"(16:00 → 19:00 → 21:01 → 00:00 → 03:00)는 Railway 의
# 전송 주기가 아니라 **8KB 가 차는 데 걸리는 시간**이었다.
#
# 이게 왜 중요한가: 2026-08-23 에 `📊 소스 건강` 한 줄을 넣은 이유가
# "curl 이 막힌 아침 점검도 로그만으로 판정할 수 있게" 였다. 그런데 그 줄이
# 1.5~3시간 늦게 도착하고 있었다 — **점검이 매일 낡은 로그를 보고 있었다.**
# `log_error` 는 2026-08-13 사고(에러가 파일에만 남던 것) 때 이미 flush=True 로
# 고쳤는데, 같은 교훈이 `log()` 에는 적용되지 않았다.
#
# 여기서 한 번에 푼다 — main.py 등 다른 print 도 함께 풀린다.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY epiweather-api/requirements.txt epiweather-api/requirements.txt
RUN pip install --no-cache-dir -r epiweather-api/requirements.txt

COPY epiweather-api epiweather-api

CMD uvicorn main:app --app-dir epiweather-api --host 0.0.0.0 --port $PORT
