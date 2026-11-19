<script>
  import { onMount } from 'svelte';
  import { startRegistration, browserSupportsWebAuthn } from '@simplewebauthn/browser';
  import { api, describe, clearCachedData } from '../lib/api.js';
  import { date } from '../lib/format.js';

  let { onsignedout } = $props();
  let passkeys = $state([]);
  let error = $state('');
  let notice = $state('');
  let busy = $state(false);
  let removing = $state(null);
  const canPasskey = browserSupportsWebAuthn();

  async function load() {
    try { passkeys = await api('/api/auth/passkeys'); } catch (err) { error = describe(err); }
  }
  onMount(load);

  async function addPasskey() {
    busy = true; error = ''; notice = '';
    try {
      const options = await api('/api/auth/passkeys/register/options', { method: 'POST' });
      const credential = await startRegistration({ optionsJSON: options });
      const name = /Android/i.test(navigator.userAgent) ? 'Android phone' : 'This device';
      await api('/api/auth/passkeys/register/verify', { method: 'POST', body: credential, query: { name } });
      notice = 'Passkey added. Next time, sign in with your fingerprint or screen lock.';
      await load();
    } catch (err) {
      error = err?.name === 'NotAllowedError' ? 'Passkey setup cancelled.' : err?.name === 'InvalidStateError' ? 'This device already has a passkey here.' : describe(err);
    } finally { busy = false; }
  }

  async function removePasskey(id) {
    try { await api(`/api/auth/passkeys/${encodeURIComponent(id)}`, { method: 'DELETE' }); removing = null; await load(); }
    catch (err) { error = describe(err); }
  }

  async function exportData() {
    error = '';
    try {
      const data = await api('/api/export');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const a = Object.assign(document.createElement('a'), {
        href: URL.createObjectURL(blob),
        download: `personal-chef-export-${new Date().toISOString().slice(0, 10)}.json`,
      });
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    } catch (err) { error = describe(err); }
  }

  async function signOut() {
    try { await api('/api/auth/logout', { method: 'POST' }); } catch {}
    await clearCachedData();
    onsignedout();
  }
</script>

<main class="page stack">
  <header class="stack-sm">
    <p class="eyebrow">Settings</p>
    <h1>Settings</h1>
  </header>

  {#if error}<div class="notice error" role="alert">{error}</div>{/if}
  {#if notice}<div class="notice ok" role="status">{notice}</div>{/if}

  <section class="card stack">
    <h2>Passkeys</h2>
    <p class="small muted">Sign in with your fingerprint or screen lock instead of the password. The password still works as a backup.</p>
    <div class="list">
      {#each passkeys as k (k.id)}
        <div class="list-item">
          <div><strong>{k.name}</strong><br /><span class="small muted">Added {date(k.created_at)}{k.last_used_at ? ` · last used ${date(k.last_used_at)}` : ''}</span></div>
          {#if removing === k.id}
            <div class="row"><button class="btn small danger" onclick={() => removePasskey(k.id)}>Remove</button><button class="btn small ghost" onclick={() => (removing = null)}>Keep</button></div>
          {:else}
            <button class="btn small ghost" onclick={() => (removing = k.id)}>Remove</button>
          {/if}
        </div>
      {/each}
    </div>
    {#if canPasskey}
      <button class="btn primary" onclick={addPasskey} disabled={busy}>Add a passkey on this device</button>
    {:else}
      <p class="small muted">This browser doesn't support passkeys.</p>
    {/if}
  </section>

  <section class="card stack">
    <h2>Your data</h2>
    <p class="small muted">Everything you've entered, as one JSON file you can keep or move elsewhere. Sessions and passkeys aren't included.</p>
    <button class="btn" onclick={exportData}>Export all data</button>
  </section>

  <section class="card stack">
    <h2>Session</h2>
    <button class="btn danger" onclick={signOut}>Sign out</button>
  </section>

  <p class="small muted" style="text-align:center">Personal Chef · foundation release</p>
</main>
