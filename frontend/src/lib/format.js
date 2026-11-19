export const n = (v) => Number(v).toLocaleString('en-GB');

export function date(iso) {
  return new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

export const phaseName = {
  muscle_gain: 'Muscle gain',
  fat_loss_maintain_muscle: 'Lose fat, keep muscle',
  maintenance: 'Maintenance',
};

export const statusName = {
  active: 'Confirmed',
  proposed: 'Awaiting approval',
  superseded: 'Previous',
  rejected: 'Rejected',
};

export function greeting(d = new Date()) {
  const h = d.getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

// kcal for a day type: base kcal shifted by the carb difference (4 kcal/g).
export const dayKcal = (t, carbs) => t.kcal + 4 * (carbs - t.carbs_g);
