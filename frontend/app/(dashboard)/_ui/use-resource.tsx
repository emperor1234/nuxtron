"use client";

import { useCallback, useEffect, useReducer, useRef, useState, type ReactNode } from "react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { resolveSessionTenant } from "@/app/lib/api-client";
import { ErrorState, LoadingState } from "./kit";

type ResourceState<T> =
  | { status: "loading"; data: T | null; error: null }
  | { status: "ready"; data: T; error: null }
  | { status: "error"; data: T | null; error: unknown };

type ResourceAction<T> =
  | { type: "start" }
  | { type: "success"; data: T }
  | { type: "failure"; error: unknown };

function reducer<T>(state: ResourceState<T>, action: ResourceAction<T>): ResourceState<T> {
  switch (action.type) {
    case "start":
      return { status: "loading", data: state.data, error: null };
    case "success":
      return { status: "ready", data: action.data, error: null };
    default:
      return { status: "error", data: state.data, error: action.error };
  }
}

/** Active workspace for the signed-in session. Stable across renders. */
export function useTenant(): string {
  const [tenant] = useState(resolveSessionTenant);
  return tenant;
}

/**
 * Loads data for a page and exposes loading / error / ready states. Reloads
 * when `deps` change. The latest request wins, so a slow earlier response can
 * never overwrite a newer one.
 */
export function useResource<T>(load: (tenant: string) => Promise<T>, deps: readonly unknown[] = []) {
  const tenant = useTenant();
  const [state, dispatch] = useReducer(reducer<T>, { status: "loading", data: null, error: null });
  const latest = useRef(0);
  const loader = useRef(load);
  useEffect(() => {
    loader.current = load;
  });

  const run = useCallback(async () => {
    const ticket = ++latest.current;
    dispatch({ type: "start" });
    try {
      const data = await loader.current(tenant);
      if (ticket === latest.current) dispatch({ type: "success", data });
    } catch (error) {
      if (ticket === latest.current) dispatch({ type: "failure", error });
    }
  }, [tenant]);

  useEffect(() => {
    // Fetch on mount and whenever the caller's inputs change.
    void run();
    return () => {
      latest.current += 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, ...deps]);

  return { ...state, tenant, reload: run };
}

/** Convenience wrapper: GET a path for the current tenant. */
export function useGet<T>(path: string | null, deps: readonly unknown[] = []) {
  return useResource<T | null>(
    async (tenant) => (path ? await apiGet<T>(path, tenant) : null),
    [path, ...deps],
  );
}

/**
 * Runs a write request and tracks its outcome so forms can show progress and
 * the real server error. Never reports success unless the backend did.
 */
export function useMutation<TBody, TResult = unknown>(
  path: string | ((body: TBody) => string),
  method: "POST" | "PUT" | "PATCH" | "DELETE" = "POST",
) {
  const tenant = useTenant();
  const [state, setState] = useReducer(
    (_: { pending: boolean; error: unknown }, next: { pending: boolean; error: unknown }) => next,
    { pending: false, error: null },
  );

  const run = useCallback(
    async (body: TBody): Promise<TResult | null> => {
      setState({ pending: true, error: null });
      try {
        const target = typeof path === "function" ? path(body) : path;
        const result = await apiSend<TResult>(target, method, method === "DELETE" ? undefined : body, tenant);
        setState({ pending: false, error: null });
        return result;
      } catch (error) {
        setState({ pending: false, error });
        return null;
      }
    },
    [path, method, tenant],
  );

  return { run, pending: state.pending, error: state.error };
}

/**
 * Renders the right state for a resource: skeleton while loading, a real error
 * with retry on failure, an empty state when `isEmpty` says so, otherwise the
 * page content. Pages never need hand-rolled spinners.
 */
export function ResourceView<T>({
  resource,
  isEmpty,
  empty,
  children,
}: {
  resource: { status: "loading" | "ready" | "error"; data: T | null; error: unknown; reload: () => void };
  isEmpty?: (data: T) => boolean;
  empty?: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (resource.status === "loading" && resource.data === null) return <LoadingState />;
  if (resource.status === "error" && resource.data === null) {
    return <ErrorState error={resource.error} onRetry={resource.reload} />;
  }
  const data = resource.data as T;
  if (isEmpty?.(data)) return <>{empty}</>;
  return <>{children(data)}</>;
}
