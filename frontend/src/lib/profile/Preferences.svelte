<script>
  import { onMount } from 'svelte';
  import { api, describe } from '../api.js';
  import ChipList from '../ChipList.svelte';

  let p = $state(null);
  let error = $state('');
  let saved = $state('');
  let dirty = $state(false);
  let ready = false;

  onMount(async () => {
    try { p = await api('/api/profile'); ready = true; } catch (err) { error = describe(err); }
  });

  $effect(() => { JSON.stringify(p); if (ready) { dirty = true; saved = ''; } });

  // Caps are stored as {"spinach (raw)": 60}; edit them as rows.
  let caps = $derived(p ? Object.entries(p.preferences.limits.ingredient_caps_g_per_portion) : []);
  function setCap(i, key, grams) {
    const entries = [...caps];
    entries[i] = [key, grams];
    p.preferences.limits.ingredient_caps_g_per_portion = Object.fromEntries(entries.filter(([k]) => k.trim()));
  }
  const addCap = () => (p.preferences.limits.ingredient_caps_g_per_portion = { ...p.preferences.limits.ingredient_caps_g_per_portion, 'new ingredient': 50 });
  function removeCap(key) {
    const c = { ...p.preferences.limits.ingredient_caps_g_per_portion }; delete c[key];
    p.preferences.limits.ingredient_caps_g_per_portion = c;
  }

  let exclusionTerms = $derived(p ? p.preferences.other_exclusions.map((e) => e.term) : []);
  function setExclusions(terms) {
    const keep = Object.fromEntries(p.preferences.other_exclusions.map((e) => [e.term, e.reason]));
    p.preferences.other_exclusions = terms.map((t) => ({ term: t, reason: keep[t] ?? '' }));
  }

  async function save() {
    error = '';
    try {
      const body = { display_name: p.display_name, birth_date: p.birth_date, sex: p.sex,
                     height_cm: p.height_cm === '' || p.height_cm == null ? null : String(p.height_cm),
                     preferences: p.preferences };
      p = await api('/api/profile', { method: 'PUT', body });
      ready = false; dirty = false; saved = 'Saved.'; queueMicrotask(() => (ready = true));
    } catch (err) { error = describe(err); }
  }
</script>

{#if error}<div class="notice error" role="alert">{error}</div>{/if}

{#if p}
  {@const pr = p.preferences}
  <div class="stack">
    <section class="card stack">
      <h2>Protein</h2>
      <ChipList label="Main proteins (preferred)" bind:items={pr.proteins.preferred} />
      <ChipList label="Also fine" bind:items={pr.proteins.acceptable} />
      <ChipList label="Cuts to avoid" bind:items={pr.proteins.excluded_cuts} />
      <label class="field"><span>Beans, lentils and tofu</span>
        <select bind:value={pr.proteins.plant_protein_role}>
          <option value="accompaniment">Alongside meat, not the main protein</option>
          <option value="main_ok">Can be the main protein</option>
        </select>
      </label>
    </section>

    <section class="card stack">
      <h2>Seafood</h2>
      <ChipList label="Never as an ingredient" bind:items={pr.seafood.excluded} />
      <ChipList label="Occasionally" bind:items={pr.seafood.occasional} />
      <ChipList label="Always fine as seasoning" bind:items={pr.seafood.always_allowed_seasonings} />
      <div class="field"><span>Hidden seafood, as seasoning only</span>
        {#each pr.seafood.seasoning_only as s, i}
          <div class="pair">
            <input type="text" maxlength="80" bind:value={s.term} aria-label="Seasoning" />
            <input type="text" maxlength="80" bind:value={s.max_per_portion} aria-label="Limit per portion" />
            <button class="btn small ghost" aria-label={`Remove ${s.term}`} onclick={() => (pr.seafood.seasoning_only = pr.seafood.seasoning_only.filter((_, j) => j !== i))}>✕</button>
          </div>
        {/each}
        <button class="btn small" onclick={() => (pr.seafood.seasoning_only = [...pr.seafood.seasoning_only, { term: '', max_per_portion: '1 tsp' }])}>Add seasoning</button>
      </div>
    </section>

    <section class="card stack">
      <h2>Limits & exclusions</h2>
      <ChipList label="Other foods to exclude" items={exclusionTerms} onchange={setExclusions} />
      <ChipList label="Allergies" bind:items={pr.allergies} placeholder="None declared" />
      <div class="grid-2">
        <label class="field"><span>Gluten meals a day (aim)</span><input type="number" min="0" max="5" bind:value={pr.limits.gluten_meals_per_day_target} /></label>
        <label class="field"><span>Gluten meals a day (max)</span><input type="number" min="0" max="5" bind:value={pr.limits.gluten_meals_per_day_max} /></label>
      </div>
      <div class="field"><span>Ingredient caps per portion</span>
        {#each caps as [key, grams], i (key)}
          <div class="pair">
            <input type="text" value={key} maxlength="80" aria-label="Ingredient" onchange={(e) => setCap(i, e.currentTarget.value, grams)} />
            <input type="number" value={grams} min="1" max="2000" aria-label="Grams" onchange={(e) => setCap(i, key, +e.currentTarget.value)} />
            <button class="btn small ghost" aria-label={`Remove ${key}`} onclick={() => removeCap(key)}>✕</button>
          </div>
        {/each}
        <button class="btn small" onclick={addCap}>Add cap</button>
      </div>
    </section>

    <section class="card stack">
      <h2>Taste</h2>
      <ChipList label="Favourite cuisines" bind:items={pr.taste.favourite_cuisines} />
      <ChipList label="Likes" bind:items={pr.taste.likes} />
      <ChipList label="Dislikes" bind:items={pr.taste.dislikes} />
    </section>

    <section class="card stack">
      <h2>Kitchen</h2>
      <label class="field"><span>Cooking ability</span>
        <select bind:value={pr.cooking.ability}>
          <option value="beginner">Beginner</option><option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option><option value="expert">Expert</option>
        </select>
      </label>
      <div class="grid-3">
        <label class="field"><span>Lunch min</span><input type="number" min="0" bind:value={pr.cooking.lunch_minutes_min} /></label>
        <label class="field"><span>Lunch max</span><input type="number" min="1" bind:value={pr.cooking.lunch_minutes_max} /></label>
        <label class="field"><span>Dinner max</span><input type="number" min="1" bind:value={pr.cooking.dinner_minutes_max} /></label>
        <label class="field"><span>Portions usually</span><input type="number" min="1" bind:value={pr.cooking.portions_usual_min} /></label>
        <label class="field"><span>… up to</span><input type="number" min="1" bind:value={pr.cooking.portions_usual_max} /></label>
        <label class="field"><span>Occasionally</span><input type="number" min="1" bind:value={pr.cooking.portions_occasional_max} /></label>
      </div>
      <label class="row small"><input type="checkbox" bind:checked={pr.cooking.slow_cook_morning_prep} /> Slow-cooker meals prepped in the morning are welcome</label>
      <ChipList label="Equipment" bind:items={pr.cooking.equipment} />
      <ChipList label="Always in the cupboard (never asked about)" bind:items={pr.cooking.assumed_staples} />
    </section>

    <div class="savebar" class:show={dirty || saved}>
      {#if saved}<span class="small">{saved}</span>{:else}<span class="small">Unsaved changes</span>{/if}
      <button class="btn primary small" onclick={save} disabled={!dirty}>Save</button>
    </div>
  </div>
{/if}

<style>
  .pair { display: grid; grid-template-columns: 1fr 7rem auto; gap: 8px; align-items: center; }
  .savebar {
    position: fixed; left: 16px; right: 16px; z-index: 9; max-width: 608px; margin: 0 auto;
    bottom: calc(var(--nav-h) + env(safe-area-inset-bottom, 0px) + 14px);
    display: flex; justify-content: space-between; align-items: center; gap: 12px;
    padding: 8px 8px 8px 16px; border-radius: 999px;
    background: var(--ink); color: var(--bg);
    transform: translateY(160%); transition: transform 0.2s ease;
  }
  .savebar.show { transform: none; }
  input[type='checkbox'] { width: 20px; height: 20px; accent-color: var(--accent); }
</style>
