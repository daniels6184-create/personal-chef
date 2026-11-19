<script>
  import { onMount } from 'svelte';
  import { api, describe } from '../api.js';
  import { date } from '../format.js';

  let rows = $state([]);
  let profile = $state(null);
  let error = $state('');
  let editing = $state(null); // null | 'new' | id
  let form = $state({});
  let confirmDelete = $state(null);

  const statusLabel = { verified: 'Measured', stated: 'Your figure', estimated: 'Estimate' };

  async function load() {
    try { [rows, profile] = await Promise.all([api('/api/measurements'), api('/api/profile')]); }
    catch (err) { error = describe(err); }
  }
  onMount(load);

  function start(row) {
    editing = row ? row.id : 'new';
    form = row
      ? { measured_on: row.measured_on, weight_kg: row.weight_kg ?? '', body_fat_pct: row.body_fat_pct ?? '', waist_cm: row.waist_cm ?? '', status: row.status, source: row.source }
      : { measured_on: new Date().toISOString().slice(0, 10), weight_kg: '', body_fat_pct: '', waist_cm: '', status: 'stated', source: '' };
  }

  async function save(e) {
    e.preventDefault();
    error = '';
    const body = { ...form };
    for (const k of ['weight_kg', 'body_fat_pct', 'waist_cm']) body[k] = body[k] === '' || body[k] == null ? null : String(body[k]);
    try {
      if (editing === 'new') await api('/api/measurements', { method: 'POST', body });
      else await api(`/api/measurements/${editing}`, { method: 'PUT', body });
      editing = null;
      await load();
    } catch (err) { error = describe(err); }
  }

  async function remove(id) {
    try { await api(`/api/measurements/${id}`, { method: 'DELETE' }); confirmDelete = null; await load(); }
    catch (err) { error = describe(err); }
  }

  const age = $derived.by(() => {
    if (!profile?.birth_date) return null;
    const b = new Date(profile.birth_date + 'T12:00:00'), t = new Date();
    return t.getFullYear() - b.getFullYear() - (t < new Date(t.getFullYear(), b.getMonth(), b.getDate()) ? 1 : 0);
  });
</script>

<div class="stack">
  {#if error}<div class="notice error" role="alert">{error}</div>{/if}

  {#if profile}
    <div class="card grid-3">
      <div><p class="eyebrow">Height</p><p class="num">{profile.height_cm ? `${Number(profile.height_cm)} cm` : '—'}</p></div>
      <div><p class="eyebrow">Age</p><p class="num">{age ?? '—'}</p></div>
      <div><p class="eyebrow">Latest weight</p><p class="num">{rows.find((r) => r.weight_kg)?.weight_kg ?? '—'} kg</p></div>
    </div>
  {/if}

  <div class="section-title"><h2>Measurements</h2>
    {#if editing === null}<button class="btn small" onclick={() => start(null)}>Add</button>{/if}
  </div>
  <p class="small muted">Scale body fat reads low on lean men; the trend matters more than the number.</p>

  {#if editing !== null}
    <form class="card stack" onsubmit={save}>
      <div class="grid-2">
        <label class="field"><span>Date</span><input type="date" bind:value={form.measured_on} required /></label>
        <label class="field"><span>Weight kg</span><input type="number" step="0.01" inputmode="decimal" bind:value={form.weight_kg} /></label>
        <label class="field"><span>Body fat %</span><input type="number" step="0.1" inputmode="decimal" bind:value={form.body_fat_pct} /></label>
        <label class="field"><span>Waist cm</span><input type="number" step="0.1" inputmode="decimal" bind:value={form.waist_cm} /></label>
      </div>
      <label class="field"><span>Type</span>
        <select bind:value={form.status}>
          <option value="verified">Measured (scale or tape)</option>
          <option value="stated">My own figure</option>
          <option value="estimated">Estimate</option>
        </select>
      </label>
      <label class="field"><span>Note</span><input type="text" maxlength="500" bind:value={form.source} placeholder="e.g. Fitdays scale, fasted, 07:45" /></label>
      <div class="row">
        <button class="btn primary">Save</button>
        <button type="button" class="btn ghost" onclick={() => (editing = null)}>Cancel</button>
      </div>
    </form>
  {/if}

  <div class="card list">
    {#each rows as r (r.id)}
      <div class="list-item">
        <div class="stack-sm" style="gap:2px">
          <strong class="num">
            {[r.weight_kg && `${r.weight_kg} kg`, r.body_fat_pct && `${r.body_fat_pct}%`, r.waist_cm && `${r.waist_cm} cm waist`].filter(Boolean).join(' · ')}
          </strong>
          <span class="small muted">{date(r.measured_on)} · {statusLabel[r.status]}{r.source ? ` · ${r.source}` : ''}</span>
        </div>
        {#if confirmDelete === r.id}
          <div class="row"><button class="btn small danger" onclick={() => remove(r.id)}>Delete</button><button class="btn small ghost" onclick={() => (confirmDelete = null)}>Keep</button></div>
        {:else}
          <div class="row">
            <button class="btn small ghost" onclick={() => start(r)}>Edit</button>
            <button class="btn small ghost" aria-label="Delete" onclick={() => (confirmDelete = r.id)}>✕</button>
          </div>
        {/if}
      </div>
    {:else}
      <p class="muted small">No measurements yet.</p>
    {/each}
  </div>
</div>
