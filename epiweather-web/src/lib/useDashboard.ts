'use client';
import { useState, useEffect } from 'react';
import { fetchDashboard, DashboardData } from './api';

export function useDashboard(intervalMs = 30_000) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        const d = await fetchDashboard();
        if (alive) {
          setData(d);
          setError(null);
          setLastUpdated(new Date());
        }
      } catch (e) {
        if (alive) setError(String(e));
      } finally {
        if (alive) setLoading(false);
      }
    }

    load();
    const id = setInterval(load, intervalMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [intervalMs]);

  return { data, loading, error, lastUpdated };
}
