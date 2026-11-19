import { writable } from 'svelte/store';

export const route = writable(location.pathname);

export function go(path) {
  if (path === location.pathname) return;
  history.pushState({}, '', path);
  route.set(path);
  window.scrollTo(0, 0);
}

window.addEventListener('popstate', () => route.set(location.pathname));
