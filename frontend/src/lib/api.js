// Every API call goes through here: same-origin cookies, the anti-forgery header, readable errors,
// and a "waking up" signal when Render's free instance is cold-starting.
import { writable } from 'svelte/store';

export const waking = writable(false);
export const signedOut = writable(false);

export class ApiError extends Error {
  constructor(status, message, problems = []) {
    super(message);
    this.status = status;
    this.problems = problems;
  }
}

export async function api(path, { method = 'GET', body, query } = {}) {
  const url = query ? `${path}?${new URLSearchParams(query)}` : path;
  const slow = setTimeout(() => waking.set(true), 2500);
  let res;
  try {
    res = await fetch(url, {
      method,
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'personal-chef',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'No connection. Check your signal and try again.');
  } finally {
    clearTimeout(slow);
    waking.set(false);
  }
  const data = res.headers.get('content-type')?.includes('json') ? await res.json() : null;
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith('/api/auth/')) signedOut.set(true);
    throw new ApiError(res.status, data?.detail || `Request failed (${res.status}).`, data?.problems || []);
  }
  return data;
}

export function describe(err) {
  if (!(err instanceof ApiError)) return 'Something went wrong.';
  if (err.problems?.length) {
    return err.problems.map((p) => (p.field ? `${p.field.replaceAll('.', ' › ')}: ${p.problem}` : p.problem)).join('\n');
  }
  return err.message;
}

export async function clearCachedData() {
  if ('caches' in window) await caches.delete('chef-data');
}
