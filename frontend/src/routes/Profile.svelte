<script>
  import Targets from '../lib/profile/Targets.svelte';
  import Body from '../lib/profile/Body.svelte';
  import Preferences from '../lib/profile/Preferences.svelte';

  const tabs = [
    { key: 'targets', label: 'Targets' },
    { key: 'body', label: 'Body' },
    { key: 'food', label: 'Food & kitchen' },
  ];
  let tab = $state(sessionStorage.getItem('profileTab') || 'targets');
  $effect(() => { try { sessionStorage.setItem('profileTab', tab); } catch {} });
</script>

<main class="page stack">
  <header class="stack-sm">
    <p class="eyebrow">Profile</p>
    <h1>About you</h1>
  </header>

  <div class="tabs" role="tablist">
    {#each tabs as t}
      <button role="tab" aria-selected={tab === t.key} class:on={tab === t.key} onclick={() => (tab = t.key)}>{t.label}</button>
    {/each}
  </div>

  {#if tab === 'targets'}<Targets />{:else if tab === 'body'}<Body />{:else}<Preferences />{/if}
</main>

<style>
  .tabs { display: flex; gap: 4px; padding: 4px; background: var(--surface-2); border-radius: 999px; }
  .tabs button {
    flex: 1; min-height: 40px; border: 0; border-radius: 999px; background: transparent;
    font-weight: 600; font-size: 0.9rem; color: var(--muted); cursor: pointer;
  }
  .tabs button.on { background: var(--surface); color: var(--ink); box-shadow: var(--shadow); }
</style>
