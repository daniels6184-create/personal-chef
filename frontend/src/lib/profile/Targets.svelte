<script>
  import { onMount } from 'svelte';
  import { api, describe } from '../api.js';
  import { n, date, phaseName, statusName, dayKcal } from '../format.js';

  let targets = $state([]);
  let error = $state('');
  let notice = $state('');
  let confirming = $state(null); // { id, action }
  let showForm = $state(false);
  let form = $state(blank());

  function blank(base) {
    const t = base || { phase: 'fat_loss_maintain_muscle', kcal: 3455, protein_g: 175, carbs_g: 475, fat_g: 95, day_types: {} };
    return {
      phase: t.phase, kcal: t.kcal, protein_g: t.protein_g, carbs_g: t.carbs_g, fat_g: t.fat_g,
      rest: t.day_types?.rest?.carbs_g ?? '', long: t.day_types?.long?.carbs_g ?? '',
      rationale: '', effective_from: new Date().toISOString().slice(0, 10),
    };
  }

  const active = $derived(targets.find((t) => t.status === 'active'));
  const proposed = $derived(targets.filter((t) => t.status === 'proposed'));
  const history = $derived(targets.filter((t) => ['superseded', 'rejected'].includes(t.status)));
  const fromMacros = $derived(4 * +form.protein_g + 4 * +form.carbs_g + 9 * +form.fat_g);

  async function load() {
    try { targets = await api('/api/targets'); } catch (err) { error = describe(err); }
  }
  onMount(load);

  async function decide(id, action) {
    error = ''; notice = '';
    try {
      await api(`/api/targets/${id}/${action}`, { method: 'POST', body: { confirm: true } });
      notice = action === 'approve' ? 'New target confirmed. The previous one is kept in history.' : 'Proposal rejected.';
      confirming = null;
      await load();
    } catch (err) { error = describe(err); }
  }

  async function propose(e) {
    e.preventDefault();
    error = ''; notice = '';
    const day_types = {};
    if (form.rest !== '') day_types.rest = { carbs_g: +form.rest, label: 'Rest or very light' };
    if (form.rest !== '' || form.long !== '') day_types.standard = { carbs_g: +form.carbs_g, label: 'Standard training' };
    if (form.long !== '') day_types.long = { carbs_g: +form.long, label: 'Long or hard session' };
    try {
      await api('/api/targets/proposals', { method: 'POST', body: {
        phase: form.phase, kcal: +form.kcal, protein_g: +form.protein_g, carbs_g: +form.carbs_g,
        fat_g: +form.fat_g, day_types, rationale: form.rationale, effective_from: form.effective_from,
      } });
      notice = 'Proposal saved. It changes nothing until you approve it.';
      showForm = false;
      await load();
    } catch (err) { error = describe(err); }
  }
</script>

{#snippet targetCard(t)}
  <div class="card stack-sm">
    <div class="row between">
      <h3>{phaseName[t.phase]}</h3>
      <span class="badge" class:ok={t.status === 'active'} class:warn={t.status === 'proposed'}>{statusName[t.status]}</span>
    </div>
    <p class="num"><strong>{n(t.kcal)} kcal</strong> · {t.protein_g}g protein · {t.carbs_g}g carbs · {t.fat_g}g fat</p>
    {#if Object.keys(t.day_types).length}
      <p class="small muted num">
        {#each ['rest', 'standard', 'long'].filter((k) => t.day_types[k]) as k, i}
          {i ? ' · ' : ''}{k[0].toUpperCase() + k.slice(1)} {n(dayKcal(t, t.day_types[k].carbs_g))} kcal / {t.day_types[k].carbs_g}g carbs
        {/each}
      </p>
    {/if}
    {#if t.rationale}<p class="small muted">{t.rationale}</p>{/if}
    <p class="small muted">
      From {date(t.effective_from)} · source: {t.origin}{t.decided_at ? ` · decided ${date(t.decided_at)}` : ''}
    </p>
    {#if t.status === 'proposed'}
      {#if confirming?.id === t.id}
        <div class="notice">
          {confirming.action === 'approve'
            ? 'This replaces your current confirmed target from now on. Approve?'
            : 'Reject this proposal?'}
        </div>
        <div class="row">
          <button class="btn primary small" onclick={() => decide(t.id, confirming.action)}>Yes, {confirming.action}</button>
          <button class="btn ghost small" onclick={() => (confirming = null)}>Cancel</button>
        </div>
      {:else}
        <div class="row">
          <button class="btn primary small" onclick={() => (confirming = { id: t.id, action: 'approve' })}>Approve</button>
          <button class="btn small" onclick={() => (confirming = { id: t.id, action: 'reject' })}>Reject</button>
        </div>
      {/if}
    {/if}
  </div>
{/snippet}

<div class="stack">
  {#if error}<div class="notice error" role="alert">{error}</div>{/if}
  {#if notice}<div class="notice ok" role="status">{notice}</div>{/if}

  {#if active}
    <p class="eyebrow">Confirmed</p>
    {@render targetCard(active)}
  {/if}

  {#if proposed.length}
    <p class="eyebrow">Awaiting your approval</p>
    {#each proposed as t (t.id)}{@render targetCard(t)}{/each}
  {/if}

  {#if showForm}
    <form class="card stack" onsubmit={propose}>
      <h3>Propose a change</h3>
      <p class="small muted">Saved as a proposal. Your confirmed target stays in force until you approve it.</p>
      <label class="field"><span>Phase</span>
        <select bind:value={form.phase}>
          {#each Object.entries(phaseName) as [k, v]}<option value={k}>{v}</option>{/each}
        </select>
      </label>
      <div class="grid-2">
        <label class="field"><span>kcal</span><input type="number" inputmode="numeric" bind:value={form.kcal} required /></label>
        <label class="field"><span>Protein g</span><input type="number" inputmode="numeric" bind:value={form.protein_g} required /></label>
        <label class="field"><span>Carbs g (standard day)</span><input type="number" inputmode="numeric" bind:value={form.carbs_g} required /></label>
        <label class="field"><span>Fat g</span><input type="number" inputmode="numeric" bind:value={form.fat_g} required /></label>
        <label class="field"><span>Rest-day carbs g</span><input type="number" inputmode="numeric" bind:value={form.rest} /></label>
        <label class="field"><span>Long-day carbs g</span><input type="number" inputmode="numeric" bind:value={form.long} /></label>
      </div>
      <p class="small" class:muted={Math.abs(fromMacros - form.kcal) <= 0.03 * form.kcal}>
        Macros add up to <strong class="num">{n(fromMacros)} kcal</strong>
        {Math.abs(fromMacros - form.kcal) > 0.03 * form.kcal ? ' (more than 3% away from the kcal figure, so this will be refused)' : ''}
      </p>
      <label class="field"><span>Starts</span><input type="date" bind:value={form.effective_from} required /></label>
      <label class="field"><span>Why</span><textarea rows="2" maxlength="500" bind:value={form.rationale} required></textarea></label>
      <div class="row">
        <button class="btn primary">Save proposal</button>
        <button type="button" class="btn ghost" onclick={() => (showForm = false)}>Cancel</button>
      </div>
    </form>
  {:else}
    <button class="btn" onclick={() => { form = blank(active); showForm = true; }}>Propose a change</button>
  {/if}

  {#if history.length}
    <p class="eyebrow">History</p>
    {#each history as t (t.id)}{@render targetCard(t)}{/each}
  {/if}
</div>
