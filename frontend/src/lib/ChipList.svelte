<script>
  // An editable list of short text items, shown as removable chips.
  let { items = $bindable([]), label, placeholder = 'Add…', onchange } = $props();
  let draft = $state('');

  function add(e) {
    e?.preventDefault();
    const v = draft.trim();
    if (v && v.length <= 80 && !items.some((i) => i.toLowerCase() === v.toLowerCase())) {
      items = [...items, v];
      onchange?.(items);
    }
    draft = '';
  }
  function remove(i) {
    items = items.filter((_, j) => j !== i);
    onchange?.(items);
  }
</script>

<div class="field">
  <span>{label}</span>
  <div class="chips">
    {#each items as item, i}
      <span class="chip">{item}<button type="button" aria-label={`Remove ${item}`} onclick={() => remove(i)}>×</button></span>
    {/each}
  </div>
  <form class="add" onsubmit={add}>
    <input type="text" bind:value={draft} {placeholder} maxlength="80" aria-label={`Add to ${label}`} />
    <button class="btn small" disabled={!draft.trim()}>Add</button>
  </form>
</div>

<style>
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip {
    display: inline-flex; align-items: center; gap: 2px;
    padding: 4px 4px 4px 12px; border-radius: 999px;
    background: var(--surface-2); font-size: 0.875rem;
  }
  .chip button {
    border: 0; background: none; cursor: pointer; color: var(--muted);
    width: 28px; height: 28px; border-radius: 50%; font-size: 1.1rem; line-height: 1;
  }
  .add { display: flex; gap: 8px; }
  .add input { flex: 1; min-width: 0; }
</style>
