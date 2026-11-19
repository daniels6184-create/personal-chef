<script>
  import { startAuthentication, browserSupportsWebAuthn } from '@simplewebauthn/browser';
  import { api, describe } from '../lib/api.js';

  let { passkeyAvailable = false, onsignedin } = $props();
  let password = $state('');
  let error = $state('');
  let busy = $state(false);
  const canPasskey = browserSupportsWebAuthn();

  async function withPassword(e) {
    e.preventDefault();
    busy = true; error = '';
    try {
      await api('/api/auth/login', { method: 'POST', body: { password } });
      password = '';
      onsignedin();
    } catch (err) { error = describe(err); } finally { busy = false; }
  }

  async function withPasskey() {
    busy = true; error = '';
    try {
      const options = await api('/api/auth/passkeys/login/options', { method: 'POST' });
      const credential = await startAuthentication({ optionsJSON: options });
      await api('/api/auth/passkeys/login/verify', { method: 'POST', body: credential });
      onsignedin();
    } catch (err) {
      error = err?.name === 'NotAllowedError' ? 'Passkey cancelled.' : describe(err);
    } finally { busy = false; }
  }
</script>

<main class="wrap">
  <div class="brand">
    <p class="eyebrow">Private kitchen</p>
    <h1>Personal Chef</h1>
    <p class="muted">High-protein cooking, planned around your training.</p>
  </div>

  <div class="card stack">
    {#if passkeyAvailable && canPasskey}
      <button class="btn primary block" onclick={withPasskey} disabled={busy}>Sign in with passkey</button>
      <div class="or"><span>or</span></div>
    {/if}
    <form class="stack" onsubmit={withPassword}>
      <label class="field">
        <span>Password</span>
        <input type="password" autocomplete="current-password" bind:value={password} required />
      </label>
      <button class="btn block" class:primary={!(passkeyAvailable && canPasskey)} disabled={busy || !password}>
        Sign in
      </button>
    </form>
    {#if error}<div class="notice error" role="alert">{error}</div>{/if}
  </div>
</main>

<style>
  .wrap {
    min-height: 100dvh; max-width: 420px; margin: 0 auto;
    padding: calc(env(safe-area-inset-top, 0px) + 15vh) 16px 32px;
    display: grid; align-content: start; gap: 28px;
  }
  .brand { display: grid; gap: 8px; }
  h1 { font-size: 2.6rem; }
  .or { display: flex; align-items: center; gap: 12px; color: var(--muted); font-size: 0.8rem; }
  .or::before, .or::after { content: ''; flex: 1; height: 1px; background: var(--line); }
</style>
