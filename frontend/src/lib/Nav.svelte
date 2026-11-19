<script>
  import { route, go } from './router.js';
  // Later stages add Diary, Plan and Pantry here. Only finished sections are shown.
  const items = [
    { path: '/', label: 'Kitchen', icon: 'M4 11h16M6 11v7a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-7M9 7c0-1 1-2 1-3M13 7c0-1 1-2 1-3' },
    { path: '/profile', label: 'Profile', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8c0-3.5 3.1-6 7-6s7 2.5 7 6' },
    { path: '/settings', label: 'Settings', icon: 'M4 7h10M18 7h2M4 17h2M10 17h10M14 5v4M6 15v4' },
  ];
</script>

<nav aria-label="Main">
  {#each items as item}
    <a
      href={item.path}
      class:active={$route === item.path}
      aria-current={$route === item.path ? 'page' : undefined}
      onclick={(e) => { e.preventDefault(); go(item.path); }}
    >
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d={item.icon} /></svg>
      <span>{item.label}</span>
    </a>
  {/each}
</nav>

<style>
  nav {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 10;
    display: flex; justify-content: center; gap: 4px;
    padding: 6px 12px calc(env(safe-area-inset-bottom, 0px) + 6px);
    background: color-mix(in srgb, var(--bg) 88%, transparent);
    backdrop-filter: blur(12px);
    border-top: 1px solid var(--line);
  }
  a {
    flex: 1; max-width: 140px; min-height: 52px;
    display: grid; justify-items: center; align-content: center; gap: 2px;
    color: var(--muted); text-decoration: none; font-size: 0.75rem; font-weight: 600;
    border-radius: 12px;
  }
  a.active { color: var(--accent); }
  svg { fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
</style>
