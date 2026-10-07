#!/usr/bin/env node
// The page in Chromium: Utah reads as it did before the states were added, and every state renders.
//
//   PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers NODE_PATH=/opt/node22/lib/node_modules node tests/page/compare_utah.js \
//     [--base REF] [--base-url URL --new-url URL] [--shots DIR] [--only utah,first,states,controls]
//
// Without URLs, the script serves the working tree (the new page) and `git archive REF index.html data favicon.svg
// favicon-32.png` (the old page; REF defaults to de1e5cf) with python3 -m http.server on two free ports, and stops
// them at the end.
//
// 1. Utah: for each pair of URLs (the old page's URL, the same view on the new page: state=UT added unless a
//    numeric agency id or a Utah county implies Utah) the innerText of #summary, #tbl-main, #context and #more
//    (with Largest single payments opened), and the main table's CSV, must be equal. Allowed differences: lines
//    of the agency details starting "Coverage" or "Sources", and a Coverage column in the CSV (file names are
//    not compared). The new canonical URL must be the old one with agency=UT-<id>, plus state=UT after g when
//    the URL named Utah or a Utah county.
// 2. #/ requests only data/index.json among data/* files.
// 3. Every state, and all states, render without console errors: the default view, vendor and agency
//    groupings, an agency of each coverage tier, a vendor, and single payments opened.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const net = require('net');
const { spawn, execFileSync } = require('child_process');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const BASE_REF = opt('--base', 'de1e5cf');
const SHOTS = opt('--shots', null);
const ONLY = opt('--only', 'utah,first,states,controls').split(',');   // parts to run

let failures = 0, checks = 0;
const fail = msg => { failures++; console.log('FAIL ' + msg); };
const ok = (cond, msg) => { checks++; if (!cond) fail(msg); };

// ---- Servers ----
const freePort = () => new Promise((res, rej) => { const s = net.createServer(); s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)); }); s.on('error', rej); });
const servers = [];
async function serve(dir) {
  const port = await freePort();
  const p = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1'], { cwd: dir, stdio: 'ignore' });
  servers.push(p);
  const url = 'http://127.0.0.1:' + port + '/';
  for (let i = 0; i < 100; i++) {
    try { const r = await fetch(url + 'index.html'); if (r.ok) return url; } catch (e) { /* not up yet */ }
    await new Promise(r => setTimeout(r, 100));
  }
  throw new Error('server for ' + dir + ' did not start');
}
const stopServers = () => { for (const p of servers) p.kill(); };

// ---- Page helpers ----
const DONE = () => {
  const s = document.getElementById('summary');
  const ex = document.getElementById('explore');
  if (ex && ex.hidden) { const p = document.getElementById('page'); return !!(p && /did not load|went wrong/.test(p.textContent)); }
  return !!(s && s.textContent.trim() && !/^Loading /.test(s.textContent) && document.getElementById('tbl-main').textContent.trim());
};
async function open(ctx, url, log) {
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') log.errors.push(url + ': ' + m.text()); });
  page.on('pageerror', e => log.errors.push(url + ': ' + e.message));
  page.on('request', r => { const u = r.url(); const i = u.indexOf('/data/'); if (i >= 0) log.data.push(u.slice(i + 1)); });
  await page.goto(url);
  await page.waitForFunction(DONE, null, { timeout: 60000 });
  return page;
}
// Open Largest single payments (when the view has them) and wait for them
async function openPayments(page) {
  const btn = await page.$('#tpay');
  if (!btn || !(await btn.isVisible())) return false;
  await btn.click();
  await page.waitForFunction(() => {
    const d = document.getElementById('d-pay');
    return d && d.open && !/Loading payments/.test(d.querySelector('summary').textContent);
  }, null, { timeout: 60000 });
  return true;
}
const texts = page => page.evaluate(() => Object.fromEntries(['summary', 'tbl-main', 'context', 'more'].map(id => [id, document.getElementById(id).innerText])));
async function csv(page) {
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#tcsv')]);
  const f = await dl.path();
  return { name: dl.suggestedFilename(), text: fs.readFileSync(f, 'utf8') };
}
const hashOf = page => page.evaluate(() => location.hash);

// CSV without a Coverage column (allowed in the new page)
function dropCoverage(text) {
  const lines = text.replace(/^﻿/, '').split('\r\n');
  const parse = l => { const out = []; let cur = '', q = false; for (let i = 0; i < l.length; i++) { const c = l[i]; if (q) { if (c === '"' && l[i + 1] === '"') { cur += '"'; i++; } else if (c === '"') q = false; else cur += c; } else if (c === '"') q = true; else if (c === ',') { out.push(cur); cur = ''; } else cur += c; } out.push(cur); return out; };
  const head = parse(lines[0]);
  const k = head.indexOf('Coverage');
  if (k < 0) return lines;
  const qq = v => (/[",\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v);
  return lines.map(l => { if (!l) return l; const f = parse(l); f.splice(k, 1); return f.map(qq).join(','); });
}
function firstDiff(a, b) {
  const x = a.split('\n'), y = b.split('\n');
  for (let i = 0; i < Math.max(x.length, y.length); i++) if (x[i] !== y[i]) return 'line ' + (i + 1) + ':\n    old: ' + JSON.stringify(x[i]) + '\n    new: ' + JSON.stringify(y[i]);
  return '';
}
// Canonical URL the new page should show for the old one
function expectedHash(oldHash, newInput) {
  const q = new URLSearchParams(oldHash.replace(/^#\/\?/, ''));
  const out = [];
  const inp = new URLSearchParams(newInput.replace(/^#\/?[^?]*\??/, ''));
  const utah = inp.get('state') === 'UT' || (inp.get('county') && !inp.get('state'));
  for (const [k, v] of q) {
    out.push([k, k === 'agency' && /^\d+$/.test(v) ? 'UT-' + v : v]);
    if (k === 'g' && utah) out.push(['state', 'UT']);
  }
  return '#/?' + new URLSearchParams(out).toString().replace(/%2C/gi, ',');
}

// [old page URL, new page URL]
const withUT = h => [h, h.includes('?') ? h.replace('?', '?state=UT&') : '#/?state=UT'];
const PAIRS = [
  withUT('#/'), withUT('#/?g=vendor'), withUT('#/?g=agency'), withUT('#/?g=year'), withUT('#/?g=none'),
  withUT('#/?cat=scba'), withUT('#/?cat=apparatus,ambulance&g=agency'),
  withUT('#/?vendor=siddons-martin-emergency-group&g=agency'),
  ['#/?g=vendor&agency=359', '#/?g=vendor&agency=359'],
  ['#/agency/1421', '#/agency/1421'],
  ['#/?county=Salt%20Lake', '#/?county=Salt%20Lake'],
  withUT('#/?size=5m-20m'),
  ['#/?g=none&agency=631&from=2023&to=2024', '#/?g=none&agency=631&from=2023&to=2024'],
  withUT('#/?np=1'), withUT('#/?years=1'), withUT('#/?cat=unclassified'), withUT('#/?vendor=individuals'),
  // A few more: a drill-down chain, a year, the Utah agency by its new id, a category with a vendor and payments
  withUT('#/?g=agency&cat=scba&from=2022&to=2024'), withUT('#/?g=vendor&year=2025'),
  ['#/?g=category&agency=359', '#/?g=category&agency=UT-359'],
  withUT('#/?g=none&vendor=siddons-martin-emergency-group&cat=apparatus'),
  ['#/?g=agency&county=Washington&size=1m-5m', '#/?g=agency&county=Washington&size=1m-5m'],
];

const ALLFILES = I => I.meta.states_order.map(st => I.meta.states[st].files.rows);
async function controls(ctx, newUrl, I) {
  const waitUrl = (page, re) => page.waitForFunction(r => new RegExp(r).test(location.hash), re.source, { timeout: 60000 });
  // The filter bar on the default view of all states: agencies by state, no county before a state is chosen
  {
    const log = { errors: [], data: [] };
    const page = await open(ctx, newUrl + '#/', log);
    const groups = await page.$$eval('#f-agency optgroup', g => g.map(x => x.label + ':' + x.children.length));
    ok(groups.length === I.meta.states_order.length && groups.every((g, i) => g === I.meta.states[I.meta.states_order[i]].name + ':' + I.agencies.filter(a => a.state === I.meta.states_order[i]).length),
      '#/ agency select by state: ' + groups.join(', '));
    ok(await page.$eval('#f-county', e => e.disabled), '#/ county select disabled with all states');
    // Search on the precomputed table: loads every state, then draws the table again with the counts of the matching rows
    await page.click('#tq');
    await page.keyboard.type('air', { delay: 30 });
    await page.waitForFunction(() => /q=air/.test(location.hash) && [...document.querySelectorAll('#tbl-main tfoot td')].filter(td => /\d/.test(td.textContent)).length >= 3, null, { timeout: 60000 });
    ok(await page.evaluate(() => document.activeElement && document.activeElement.id === 'tq' && document.activeElement.value === 'air'), '#/ search keeps focus and text after loading');
    ok(ALLFILES(I).every(f => log.data.includes(f)), '#/ search loaded every state: ' + log.data.join(' '));
    // Picking a state: Utah's counties, the URL has state=UT and no years
    await page.selectOption('#f-state', 'UT');
    await waitUrl(page, /state=UT/);
    await page.waitForFunction(DONE);
    ok(!(await page.$eval('#f-county', e => e.disabled)) && (await page.$$eval('#f-county option', o => o.length)) > 2, 'state=UT enables the county select');
    ok(!/from=|to=/.test(await hashOf(page)), 'state=UT keeps the full range: ' + await hashOf(page));
    await page.selectOption('#f-county', 'Salt Lake');
    await waitUrl(page, /county=Salt/);
    // Leaving the state clears the county
    await page.selectOption('#f-state', '');
    await waitUrl(page, /^#\/\?g=category&q=air$/);
    ok(!log.errors.length, '#/ controls: console errors ' + JSON.stringify(log.errors));
    await page.close();
  }
  // Vendor box with more vendors than the list shows (Ohio): suggestions as the user types, then a pick
  {
    const log = { errors: [], data: [] };
    const page = await open(ctx, newUrl + '#/?state=OH', log);
    ok(log.data.join(' ') === 'data/index.json', 'state=OH precomputed: ' + log.data.join(' '));
    await page.click('#f-vendor');
    await page.waitForFunction(f => performance.getEntriesByType('resource').some(e => e.name.endsWith(f)), I.meta.states.OH.files.rows);
    await page.keyboard.type('motorola', { delay: 30 });
    await page.waitForFunction(() => document.querySelectorAll('#vendor-list option').length > 0);
    const n = await page.$$eval('#vendor-list option', o => o.map(x => x.value));
    ok(n.length <= 200 && n.some(v => /^Motorola/i.test(v)), 'Ohio vendor suggestions: ' + n.length + ' ' + n.slice(0, 3).join(', '));
    await page.fill('#f-vendor', 'Motorola Solutions');
    await page.keyboard.press('Enter');
    await waitUrl(page, /vendor=motorola-solutions/);
    await page.waitForFunction(DONE);
    ok(/state=OH/.test(await hashOf(page)), 'vendor pick keeps the state: ' + await hashOf(page));
    // Agency select: only Ohio's agencies, string ids
    const vals = await page.$$eval('#f-agency option', o => o.map(x => x.value).filter(Boolean));
    ok(vals.length === I.agencies.filter(a => a.state === 'OH').length && vals.every(v => v.startsWith('OH-')), 'state=OH agency select: ' + vals.length);
    await page.selectOption('#f-agency', vals[0]);
    await waitUrl(page, new RegExp('agency=' + vals[0]));
    await page.waitForFunction(DONE);
    // Back returns to the vendor view
    await page.goBack();
    await waitUrl(page, /^#\/\?g=category&state=OH&vendor=motorola-solutions$/);
    await page.waitForFunction(DONE);
    ok(!log.errors.length, 'state=OH controls: console errors ' + JSON.stringify(log.errors));
    await page.close();
  }
  // A drill-down from all states into one agency loads only that agency's state; agencies of the same size
  {
    const log = { errors: [], data: [] };
    const page = await open(ctx, newUrl + '#/?g=agency&state=TX', log);
    await page.click('#tbl-main tbody tr.dr button.drill');
    await waitUrl(page, /agency=TX-/);
    await page.waitForFunction(DONE);
    const like = await page.$('[data-like]');
    if (like) {
      await page.click('#d-facts > summary');
      await page.click('[data-like]');
      await waitUrl(page, /size=/);
      ok(/state=TX/.test(await hashOf(page)), 'agencies of the same size keep the state: ' + await hashOf(page));
    }
    ok(!log.errors.length, 'TX drill: console errors ' + JSON.stringify(log.errors));
    await page.close();
  }
  // A state file that does not load: a message with Retry, which loads it
  {
    const log = { errors: [], data: [] };
    const page = await ctx.newPage();
    page.on('pageerror', e => log.errors.push(e.message));
    let block = true;
    await page.route('**/data/id.json', r => (block ? r.abort() : r.continue()));
    await page.goto(newUrl + '#/?g=vendor&state=ID');
    await page.waitForSelector('[data-retry]', { timeout: 60000 });
    ok(/did not load/.test(await page.evaluate(() => document.getElementById('main').innerText)), 'failed load: message');
    block = false;
    await page.click('[data-retry]');
    await page.waitForFunction(DONE, null, { timeout: 60000 });
    ok((await page.$$eval('#tbl-main tbody tr', r => r.length)) > 0, 'Retry loads the state');
    ok(!log.errors.length, 'Retry: page errors ' + JSON.stringify(log.errors));
    await page.close();
  }
  // About
  {
    const log = { errors: [], data: [] };
    const page = await ctx.newPage();
    page.on('console', m => { if (m.type() === 'error') log.errors.push(m.text()); });
    page.on('pageerror', e => log.errors.push(e.message));
    await page.goto(newUrl + '#/about');
    await page.waitForFunction(() => /About/.test((document.querySelector('#page h1') || {}).textContent || ''));
    ok(!log.errors.length, 'About: console errors ' + JSON.stringify(log.errors));
    await page.close();
  }
}

(async () => {
  let baseUrl = opt('--base-url', null), newUrl = opt('--new-url', null);
  let tmp = null;
  try {
    if (!baseUrl) {
      tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'compare-utah-'));
      const tar = execFileSync('git', ['archive', BASE_REF, 'index.html', 'data/data.json', 'data/payments.json', 'favicon.svg', 'favicon-32.png'], { cwd: ROOT, maxBuffer: 1 << 30 });
      execFileSync('tar', ['-x', '-C', tmp], { input: tar });
      baseUrl = await serve(tmp);
    }
    if (!newUrl) newUrl = await serve(ROOT);
    console.log('old page ' + baseUrl + ' (' + BASE_REF + '), new page ' + newUrl);
    const browser = await chromium.launch();
    const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, acceptDownloads: true });

    // ---- 1. Utah ----
    const t1 = Date.now();
    for (const [oh, nh] of ONLY.includes('utah') ? PAIRS : []) {
      const lo = { errors: [], data: [] }, ln = { errors: [], data: [] };
      const po = await open(ctx, baseUrl + oh, lo), pn = await open(ctx, newUrl + nh, ln);
      const what = oh + ' vs ' + nh;
      const ho = await hashOf(po), hn = await hashOf(pn);
      ok(hn === expectedHash(ho, nh), what + ': canonical URL ' + hn + ', expected ' + expectedHash(ho, nh));
      const a = await openPayments(po), b = await openPayments(pn);
      ok(a === b, what + ': single payments section ' + (a ? 'only on the old page' : 'only on the new page'));
      const xo = await texts(po), xn = await texts(pn);
      for (const id of Object.keys(xo)) {
        let n = xn[id];
        if (id === 'context') n = n.split('\n').filter(l => !/^(Coverage|Sources)\b/.test(l) || xo[id].split('\n').includes(l)).join('\n');
        ok(xo[id] === n, what + ': #' + id + ' differs, ' + firstDiff(xo[id], n));
      }
      const co = await csv(po), cn = await csv(pn);
      const lo2 = dropCoverage(co.text), ln2 = dropCoverage(cn.text);
      ok(lo2.join('\n') === ln2.join('\n'), what + ': CSV differs, ' + firstDiff(lo2.join('\n'), ln2.join('\n')));
      ok(!lo.errors.length && !ln.errors.length, what + ': console errors ' + JSON.stringify(lo.errors.concat(ln.errors)));
      console.log('  ' + nh + ' -> ' + hn + ': ' + co.text.split('\r\n').length + ' CSV lines, data ' + ln.data.join(' '));
      await po.close();
      await pn.close();
    }
    console.log(PAIRS.length + ' Utah views compared in ' + ((Date.now() - t1) / 1000).toFixed(1) + ' s');

    // ---- 2. The first load ----
    if (ONLY.includes('first')) {
      const log = { errors: [], data: [] };
      const t = Date.now();
      const page = await open(ctx, newUrl + '#/', log);
      const ms = Date.now() - t;
      await page.waitForTimeout(1000);                       // nothing else is fetched afterwards either
      ok(log.data.length === 1 && log.data[0] === 'data/index.json', '#/ requested ' + JSON.stringify(log.data));
      ok(!log.errors.length, '#/ console errors ' + JSON.stringify(log.errors));
      const rows = await page.$$eval('#tbl-main tbody tr', r => r.length);
      console.log('#/: ' + log.data.join(' ') + ', ' + rows + ' rows, rendered in ' + ms + ' ms');
      if (SHOTS) await page.screenshot({ path: path.join(SHOTS, 'home.png') });
      await page.close();
    }

    // ---- 3. Every state renders ----
    const I = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'index.json'), 'utf8'));
    const urls = [];
    for (const st of I.meta.states_order) {
      urls.push('#/?state=' + st, '#/?g=vendor&state=' + st, '#/?g=agency&state=' + st, '#/?g=none&state=' + st, '#/?g=year&state=' + st + '&np=1');
      for (const tier of [1, 2, 3, 4]) {
        const a = I.agencies.find(x => x.state === st && x.coverage === tier && (tier > 2 || x.lines > 0));
        if (a) urls.push('#/?g=vendor&agency=' + encodeURIComponent(a.id), '#/?g=category&agency=' + encodeURIComponent(a.id) + '&years=1');
      }
      const c = I.agencies.find(x => x.state === st && x.county);
      if (c) urls.push('#/?g=agency&state=' + st + '&county=' + encodeURIComponent(c.county));
    }
    urls.push('#/?g=vendor', '#/?g=agency', '#/?g=year', '#/?cat=scba', '#/?g=vendor&vendor=motorola-solutions', '#/?g=agency&vendor=zoll-medical&years=1');
    const t3 = Date.now();
    const timing = [];
    for (const h of ONLY.includes('states') ? urls : []) {
      const log = { errors: [], data: [] };
      const t = Date.now();
      let page;
      try { page = await open(ctx, newUrl + h, log); } catch (e) { fail(h + ': did not render (' + e.message.split('\n')[0] + ')'); continue; }
      timing.push([h, Date.now() - t]);
      const s = await page.textContent('#summary');
      ok(!/did not load|went wrong/.test(await page.evaluate(() => document.getElementById('main').innerText)), h + ': error message on the page');
      ok(s.trim().length > 0, h + ': empty summary');
      const paid = await openPayments(page);
      if (paid) ok(!/did not load/.test(await page.textContent('#more')), h + ': payments did not load');
      ok(!log.errors.length, h + ': console errors ' + JSON.stringify(log.errors));
      if (SHOTS) await page.screenshot({ path: path.join(SHOTS, h.replace(/[^a-zA-Z0-9]+/g, '_') + '.png') });
      await page.close();
    }
    timing.sort((a, b) => b[1] - a[1]);
    console.log(urls.length + ' state views rendered in ' + ((Date.now() - t3) / 1000).toFixed(1) + ' s; slowest: ' + timing.slice(0, 3).map(([h, ms]) => h + ' ' + ms + ' ms').join(', '));
    // ---- 4. Controls and loading ----
    const t4 = Date.now();
    if (ONLY.includes('controls')) await controls(ctx, newUrl, I);
    console.log('controls checked in ' + ((Date.now() - t4) / 1000).toFixed(1) + ' s');
    await browser.close();
  } catch (e) {
    fail(e.stack || String(e));
  } finally {
    stopServers();
    if (tmp) fs.rmSync(tmp, { recursive: true, force: true });
  }
  console.log(checks + ' checks, ' + failures + ' failed');
  process.exit(failures ? 1 : 0);
})();
