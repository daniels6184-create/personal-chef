<script>
  import { onMount } from 'svelte';
  import { api, describe } from '../lib/api.js';
  import { n, greeting, phaseName, dayKcal } from '../lib/format.js';
  import { go } from '../lib/router.js';

  let profile = $state(null);
  let target = $state(null);
  let error = $state('');

  onMount(async () => {
    try {
      [profile, target] = await Promise.all([api('/api/profile'), api('/api/targets/active')]);
    } catch (err) { error = describe(err); }
  });

  const today = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
</script>

<main class="page stack">
  <header class="stack-sm">
    <p class="eyebrow">{today}</p>
    <h1>{greeting()}{profile ? `, ${profile.display_name}` : ''}.</h1>
  </header>

  {#if error}<div class="notice error">{error}</div>{/if}

  {#if target}
    <section class="card stack">
      <div class="row between">
        <h2>Today's targets</h2>
        <span class="badge ok">{phaseName[target.phase]}</span>
      </div>
      <div class="macros">
        <div><span class="v num">{n(target.kcal)}</span><span class="l">kcal</span></div>
        <div><span class="v num">{target.protein_g}g</span><span class="l">protein</span></div>
        <div><span class="v num">{target.carbs_g}g</span><span class="l">carbs</span></div>
        <div><span class="v num">{target.fat_g}g</span><span class="l">fat</span></div>
      </div>
      {#if Object.keys(target.day_types).length}
        <div class="divider"></div>
        <p class="small muted">Carbs move with training; protein and fat stay put. Linking to your Ironman plan comes later, so these are the three day types for now.</p>
        <div class="days">
          {#each ['rest', 'standard', 'long'] as key}
            {#if target.day_types[key]}
              <div class="day">
                <span class="small"><strong>{target.day_types[key].label}</strong></span>
                <span class="small muted num">{n(dayKcal(target, target.day_types[key].carbs_g))} kcal · {target.day_types[key].carbs_g}g carbs</span>
              </div>
            {/if}
          {/each}
        </div>
      {/if}
    </section>
  {/if}

  <section class="card coming stack-sm">
    <p class="eyebrow">Being built</p>
    <h2>Your recipe suggestions will appear here</h2>
    <p class="muted small">
      This is the foundation release: sign-in, your profile and your confirmed targets.
      The food diary arrives next, then the chef with 3–5 meals for every slot.
    </p>
    <div class="row">
      <button class="btn small" onclick={() => go('/profile')}>Check your profile</button>
    </div>
  </section>
</main>

<style>
  .macros { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .macros div { display: grid; gap: 2px; }
  .v { font-family: var(--serif); font-size: 1.45rem; font-weight: 560; }
  .l { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }
  .days { display: grid; gap: 8px; }
  .day { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; padding: 10px 12px; background: var(--bg); border-radius: 12px; }
  .coming { background: var(--accent-soft); border-color: transparent; }
  .coming h2 { color: var(--accent); }
</style>
