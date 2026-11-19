<script>
  import { onMount } from 'svelte';
  import { api, signedOut, waking } from './lib/api.js';
  import { route, go } from './lib/router.js';
  import Login from './routes/Login.svelte';
  import Kitchen from './routes/Kitchen.svelte';
  import Profile from './routes/Profile.svelte';
  import Settings from './routes/Settings.svelte';
  import Nav from './lib/Nav.svelte';

  let state = $state('loading'); // loading | out | in | locked | offline
  let passkeyAvailable = $state(false);

  async function check() {
    try {
      const s = await api('/api/auth/status');
      passkeyAvailable = s.passkey_available;
      state = s.locked ? 'locked' : s.signed_in ? 'in' : 'out';
    } catch {
      state = 'offline';
    }
  }

  onMount(check);

  $effect(() => {
    if ($signedOut) {
      signedOut.set(false);
      check();
    }
  });

  function signedIn() {
    state = 'in';
    go('/');
  }
</script>

{#if $waking}
  <div class="waking" role="status">Warming up the kitchen… the free server sleeps when idle.</div>
{/if}

{#if state === 'loading'}
  <div class="splash"><span class="mark">Personal Chef</span></div>
{:else if state === 'locked'}
  <main class="page"><div class="notice">The app is locked. Set APP_PASSWORD on the server, then reload.</div></main>
{:else if state === 'offline'}
  <main class="page stack">
    <div class="notice">Can't reach the kitchen right now. Check your connection.</div>
    <button class="btn" onclick={check}>Try again</button>
  </main>
{:else if state === 'out'}
  <Login {passkeyAvailable} onsignedin={signedIn} />
{:else}
  {#if $route === '/profile'}
    <Profile />
  {:else if $route === '/settings'}
    <Settings onsignedout={check} />
  {:else}
    <Kitchen />
  {/if}
  <Nav />
{/if}

<style>
  .splash { min-height: 100dvh; display: grid; place-items: center; }
  .mark { font-family: var(--serif); font-size: 1.6rem; color: var(--muted); }
  .waking {
    position: fixed; z-index: 20; left: 50%; transform: translateX(-50%);
    top: calc(env(safe-area-inset-top, 0px) + 10px);
    background: var(--ink); color: var(--bg);
    padding: 8px 14px; border-radius: 999px; font-size: 0.85rem;
    max-width: calc(100% - 32px); text-align: center;
  }
</style>
