'use client';
import { useState, useEffect } from 'react';
import { fetchDashboard, dashboardWsUrl, DashboardData } from './api';

// WebSocket(/ws/dashboard)을 우선 시도하고, 연결이 안 되거나 끊기면 기존
// 30초 폴링으로 자동 폴백한다 — 폴링은 삭제하지 않고 안전망으로 유지.
export function useDashboard(intervalMs = 30_000) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [live, setLive] = useState(false); // true면 WebSocket 실시간 수신 중

  useEffect(() => {
    let alive = true;
    let liveNow = false; // 이펙트 내부 흐름제어용 — React state는 비동기라 클로저에서 못 씀
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

    const url = dashboardWsUrl();
    if (url) {
      try {
        ws = new WebSocket(url);
        ws.onopen = () => {
          liveNow = true;
          if (alive) setLive(true);
          stopPolling();
        };
        ws.onmessage = (ev) => {
          try {
            applyData(JSON.parse(ev.data) as DashboardData);
          } catch {
            // 파싱 안 되는 메시지는 무시 (다음 브로드캐스트를 기다림)
          }
        };
        ws.onerror = () => {
          liveNow = false;
          if (alive) setLive(false);
          startPolling();
        };
        ws.onclose = () => {
          liveNow = false;
          if (alive) setLive(false);
          startPolling();
        };
      } catch {
        startPolling();
      }
    } else {
      startPolling();
    }

    // WS가 몇 초 내로 안 열리면 첫 화면 대기시간을 늘리지 않도록 폴링으로 즉시 전환
    const fallbackTimer = setTimeout(() => {
      if (alive && !liveNow) startPolling();
    }, 4000);

    return () => {
      alive = false;
      clearTimeout(fallbackTimer);
      stopPolling();
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;
        ws.close();
      }
    };
  }, [intervalMs]);

  return { data, loading, error, lastUpdated, live };
}
