// End-to-end check of the foundation release on an emulated Android phone (Pixel 7, Chrome).
// Run against a running server:  BASE=http://localhost:8000 PASSWORD=... node e2e/smoke.cjs [shots-dir]
// Uses a virtual WebAuthn authenticator, so passkey sign-up and sign-in are exercised for real.
const { chromium, devices } = require('playwright');
const assert = require('assert');

const BASE = process.env.BASE || 'http://localhost:8000';
const PASSWORD = process.env.PASSWORD;
const SHOTS = process.argv[2];

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ ...devices['Pixel 7'] });
  const page = await ctx.newPage();
  const problems = [];
  // The deliberate wrong-password attempt makes Chrome log a 401; that one is expected.
  page.on('console', (m) => m.type() === 'error' && !m.text().includes('status of 401') && problems.push(m.text()));
  page.on('pageerror', (e) => problems.push(String(e)));
  const shot = async (name) => SHOTS && page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
  const step = (s) => console.log('✓', s);

  // Virtual platform authenticator (like a phone's fingerprint sensor).
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('WebAuthn.enable');
  await cdp.send('WebAuthn.addVirtualAuthenticator', { options: {
    protocol: 'ctap2', transport: 'internal', hasResidentKey: true,
    hasUserVerification: true, isUserVerified: true } });

  // Sign in with the password
  await page.goto(BASE + '/');
  await page.getByLabel('Password').fill('wrong-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('alert').getByText('Wrong password.').waitFor();
  step('wrong password refused');
  await shot('01-login');
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByText("Today's targets").waitFor();
  assert.ok(await page.getByText('3,455').first().isVisible());
  step('signed in; kitchen shows 3,455 kcal');
  await shot('02-kitchen');

  // Profile: targets
  await page.getByRole('link', { name: 'Profile' }).click();
  await page.getByRole('heading', { name: 'About you' }).waitFor();
  await page.getByText('Confirmed', { exact: true }).first().waitFor();
  await page.getByRole('button', { name: 'Propose a change' }).click();
  await page.getByLabel('Phase').selectOption('fat_loss_maintain_muscle');
  await page.getByLabel('kcal').fill('3055');
  await page.getByLabel('Protein g').fill('190');
  await page.getByLabel('Carbs g (standard day)').fill('400');
  await page.getByLabel('Fat g').fill('85');
  await page.getByLabel('Why').fill('E2E proposal');
  await page.getByRole('button', { name: 'Save proposal' }).click();
  await page.getByText('Awaiting your approval').waitFor();
  step('proposal saved without changing the confirmed target');
  await shot('03-targets-proposal');
  await page.getByRole('button', { name: 'Reject' }).click();
  await page.getByRole('button', { name: 'Yes, reject' }).click();
  await page.getByText('Proposal rejected.').waitFor();
  step('proposal rejected via confirm step');

  // Body
  await page.getByRole('tab', { name: 'Body' }).click();
  await page.getByText('79.55 kg').first().waitFor();
  await page.getByRole('button', { name: 'Add' }).click();
  await page.getByLabel('Weight kg').fill('79.8');
  await page.getByLabel('Waist cm').fill('82');
  await page.getByRole('button', { name: 'Save' }).click();
  await page.getByText('79.80 kg · 82.0 cm waist').waitFor();
  step('measurement added');
  await shot('04-body');

  // Food & kitchen: edit a list and a number, save, reload, check it stuck
  await page.getByRole('tab', { name: 'Food & kitchen' }).click();
  await page.getByLabel('Add to Likes').fill('nduja');
  await page.getByLabel('Add to Likes').press('Enter');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await page.getByText('Saved.').waitFor();
  await shot('05-preferences');
  await page.reload();
  await page.getByRole('tab', { name: 'Food & kitchen' }).click();
  await page.getByRole('button', { name: 'Remove nduja' }).waitFor();
  assert.ok(await page.getByText('pork tenderloin').isVisible());
  step('preferences saved and persisted across reload');

  // Settings: passkey, export
  await page.getByRole('link', { name: 'Settings' }).click();
  await page.getByRole('button', { name: 'Add a passkey on this device' }).click();
  await page.getByText('Passkey added.').waitFor();
  step('passkey registered');
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Export all data' }).click(),
  ]);
  const data = JSON.parse(require('fs').readFileSync(await download.path(), 'utf8'));
  assert.equal(data.targets.find((t) => t.status === 'active').kcal, 3455);
  assert.ok(data.profile[0].preferences.taste.likes.includes('nduja'));
  step('export downloaded and contains the edits');
  await shot('06-settings');

  // Sign out, then sign back in with the passkey
  await page.getByRole('button', { name: 'Sign out' }).click();
  await page.getByRole('button', { name: 'Sign in with passkey' }).click();
  await page.getByText("Today's targets").waitFor();
  step('signed in with passkey');

  // PWA basics
  const manifest = await (await page.request.get(BASE + '/manifest.webmanifest')).json();
  assert.equal(manifest.display, 'standalone');
  assert.ok(manifest.icons.some((i) => i.sizes === '512x512' && i.purpose === 'maskable'));
  const swReady = await page.evaluate(async () => !!(await navigator.serviceWorker.ready));
  assert.ok(swReady);
  step('manifest and service worker present');

  // No horizontal scroll at phone width on any page
  for (const path of ['/', '/profile', '/settings']) {
    await page.goto(BASE + path);
    await page.waitForLoadState('networkidle');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    assert.ok(overflow <= 0, `${path} scrolls sideways by ${overflow}px`);
  }
  step('no sideways scrolling at 412px');

  assert.deepEqual(problems, [], 'browser console errors: ' + problems.join(' | '));
  step('no console errors');
  await browser.close();
})().catch((e) => { console.error('✗', e.message); process.exit(1); });
