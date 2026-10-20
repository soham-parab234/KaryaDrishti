import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../services/apiClient';
import type { ApiHealthResponse } from '../services/apiClient';

export interface BackendStatusState {
  isConnected: boolean;
  isChecking: boolean;
  version: string | null;
  appName: string | null;
  database: string | null;
  latencyMs: number | null;
  error: string | null;
  checkConnection: () => Promise<void>;
}

export function useBackendStatus(): BackendStatusState {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isChecking, setIsChecking] = useState<boolean>(true);
  const [version, setVersion] = useState<string | null>(null);
  const [appName, setAppName] = useState<string | null>(null);
  const [database, setDatabase] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkConnection = useCallback(async () => {
    setIsChecking(true);
    const start = performance.now();
    try {
      const health: ApiHealthResponse = await apiClient.checkHealth();
      const end = performance.now();
      setIsConnected(true);
      setVersion(health.version);
      setAppName(health.app_name);
      setDatabase(health.database);
      setLatencyMs(Math.round(end - start));
      setError(null);
    } catch (err: unknown) {
      setIsConnected(false);
      setVersion(null);
      setAppName(null);
      setDatabase(null);
      setLatencyMs(null);
      setError(err instanceof Error ? err.message : 'Backend unreachable');
    } finally {
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const start = performance.now();
    apiClient
      .checkHealth()
      .then((health) => {
        if (!isMounted) return;
        const end = performance.now();
        setIsConnected(true);
        setVersion(health.version);
        setAppName(health.app_name);
        setDatabase(health.database);
        setLatencyMs(Math.round(end - start));
        setError(null);
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        setIsConnected(false);
        setVersion(null);
        setAppName(null);
        setDatabase(null);
        setLatencyMs(null);
        setError(err instanceof Error ? err.message : 'Backend unreachable');
      })
      .finally(() => {
        if (isMounted) setIsChecking(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return {
    isConnected,
    isChecking,
    version,
    appName,
    database,
    latencyMs,
    error,
    checkConnection,
  };
}
