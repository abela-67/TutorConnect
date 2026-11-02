import { ChangeEvent, useCallback, useEffect, useState } from "react";
import { api, errMsg, fieldErrors, qs } from "./api";
import type { Page, Reference } from "./types";

export interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
  setData: (d: T | null) => void;
}

/** Fetch a GET endpoint; pass null to skip. Re-runs when the path changes or reload() is called. */
export function useFetch<T>(path: string | null): FetchState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(path !== null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (path === null) {
      setData(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get<T>(path)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(errMsg(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [path, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, loading, error, reload, setData };
}

/** Paginated list; the page resets to 1 whenever the filter params change. */
export function usePaged<T>(base: string, params: Record<string, string | number | boolean | null | undefined> = {}) {
  const key = JSON.stringify(params);
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [key]);
  const f = useFetch<Page<T>>(`${base}${qs({ ...params, page })}`);
  return { ...f, page, setPage };
}

let refCache: Promise<Reference> | null = null;
/** Shared lookup lists (subjects, grades, locations, choices). Fetched once per page load. */
export function useReference(): Reference | null {
  const [ref, setRef] = useState<Reference | null>(null);
  useEffect(() => {
    if (!refCache) {
      refCache = api.get<Reference>("/reference/").catch((e) => {
        refCache = null;
        throw e;
      });
    }
    let alive = true;
    refCache.then((r) => alive && setRef(r)).catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);
  return ref;
}
export const invalidateReference = () => {
  refCache = null;
};

/** Run an async action with busy/error/field-error state. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});

  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError(null);
    setFields({});
    try {
      return await fn();
    } catch (e) {
      setError(errMsg(e));
      setFields(fieldErrors(e));
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);

  return { busy, error, fields, run, setError, setFields };
}

type Input = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

export function useForm<T extends Record<string, any>>(initial: T) {
  const [values, setValues] = useState<T>(initial);
  const set = useCallback((k: keyof T, v: any) => setValues((p) => ({ ...p, [k]: v })), []);
  const bind = (k: keyof T) => ({
    value: (values[k] ?? "") as string,
    onChange: (e: ChangeEvent<Input>) => set(k, e.target.value),
  });
  return { values, setValues, set, bind };
}

export const numOrNull = (v: unknown): number | null => (v === "" || v === null || v === undefined ? null : Number(v));
export const idOrNull = numOrNull;
