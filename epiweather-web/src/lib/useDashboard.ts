'use client';
import { useState, useEffect } from 'react';
import { fetchDashboard, dashboardWsUrl, DashboardData } from './api';

// REST 폴링을 기본으로 깔고, WebSocket(/ws/dashboard) 메시지가 오면 live로 전환.
// 예전엔 "WS가 열리면 폴링 중단"이라, 콜드 캐시 재계산으로 첫 메시지가 늦어지면
// 무한로딩이 됐다. 열렸다고 live가 아니다 — 데이터가 와야 확정.
export function useDashboard(intervalMs = 30_000) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [live, setLive] = useState(false); // true면 WebSocket 실시간 수신 중

  useEffect(() => {
    let alive = true;
    let ws: WebSocket | null = null;
    let pollId: ReturnType<typeof setInterval> | null = null;

    function applyData(d: DashboardData) {
      if (!alive) return;
      setData(d);
      setError(null);
      setLastUpdated(new Date());
      setLoading(false);
    }

    async function pollOnce() {
      try {
        applyData(await fetchDashboard());
      } catch (e) {
        if (alive) {
          setError(String(e));
          setLoading(false);
        }
      }
    }

    function startPolling() {
      if (pollId) return;
      pollOnce();
      pollId = setInterval(pollOnce, intervalMs);
    }

    function stopPolling() {
      if (pollId) {
        clearInterval(pollId);
        pollId = null;
      }
    }

    // REST 먼저 — WS 무응답에도 첫 화면 보장.
    startPolling();

    const url = dashboardWsUrl();
    if (url) {
      try {
        ws = new WebSocket(url);
        ws.onmessage = (ev) => {
          try {
            applyData(JSON.parse(ev.data) as DashboardData);
            stopPolling();
            if (alive) setLive(true);
          } catch {
            // 파싱 안 되는 메시지는 무시 (다음 브로드캐스트를 기다림)
          }
        };
        ws.onerror = () => {
          if (alive) setLive(false);
          startPolling();
        };
        ws.onclose = () => {
          if (alive) setLive(false);
          startPolling();
        };
      } catch {
        // WS 생성 실패 — 폴링 유지
      }
    }

    return () => {
      alive = false;
      stopPolling();
      if (ws) {
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;
        ws.close();
      }
    };
  }, [intervalMs]);

  return { data, loading, error, lastUpdated, live };
}
