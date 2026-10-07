#!/usr/bin/env node
// The page in Chromium, view by view (design plan section 9): checks plus screenshots at 1366x900 (the fixed
// layout, the window) and 390x844 (a phone, the full page).
//
//   PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers NODE_PATH=/opt/node22/lib/node_modules node tests/page/screens.js \
//     [--base REF] [--base-url URL --new-url URL] [--shots DIR] [--only 1,2,...]
//
// Without URLs, the script serves the working tree (the new page) and `git archive REF index.html data favicon.svg
// favicon-32.png` (the page before the states were added; REF defaults to de1e5cf) with python3 -m http.server on
// two free ports, and stops them at the end. Screenshots go to DIR (default: <tmp>/fire-screens).
//
// Checks (every count is read from data/index.json, so a rebuilt data set needs no edit here):
//  1. #/: only data/index.json among data/* requests, under 1,000,000 bytes gzipped; title and header read the site
//     name; the coverage summary is there; one row per purchasing category.
//  2. #/?state=UT reads as the old #/ (summary, table, context, more).
//  3. #/?g=vendor&state=OH loads data/oh.json and shows Ohio's coverage line and a linked note for each Ohio source.
//  4. #/?g=agency sorted by Agency, all rows shown: every totals-only or directory-only agency reads "No vendor data"
//     (none "$0"), every other agency an amount, and the Coverage column shows.
//  5. #/?g=vendor&agency=CA-00555 (CAL FIRE): single payments, and the item lines before the first fiscal year (SCPRS).
//  6. #/?g=vendor&agency=TX-AA401: item lines with Brand, Quantity and Unit price filled; the DIR scope note.
//  7. #/?g=vendor&agency=CA-01005: the summary starts "No vendor data"; the Annual totals table is there.
//  8. #/?g=vendor&agency=ID-01100: "directory only", and the FEMA grants section.
//  9. #/?g=agency&vendor=motorola-solutions: rows from several states, and item lines.
// 10. #/about: the coverage table has a row per state and a total; every source of meta.sources is listed with a link.
// 11. #/?g=vendor&agency=359 becomes agency=UT-359 and reads as the old page.
// 12. #/?county=Salt%20Lake gains state=UT.
// 13. A state and county whose agencies all lack vendor data: the summary starts "No vendor data", no category rows,
//     no $0; the agency grouping lists them all as "No vendor data", its total row too.
// Every view: no console errors, at both sizes; on the phone, no sideways page scroll.
// Timing (logged): #/ until rendered, and a category drill-down from #/ that loads every state.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const net = require('net');
const zlib = require('zlib');
const { spawn, execFileSync } = require('child_process');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const BASE_REF = opt('--base', 'de1e5cf');
const SHOTS = opt('--shots', path.join(os.tmpdir(), 'fire-screens'));
const ONLY = opt('--only', null);
const runs = n => !ONLY || ONLY.split(',').includes(String(n));

let failures = 0, checks = 0;
const fail = msg => { failures++; console.log('FAIL ' + msg); };
const ok = (cond, msg) => { checks++; if (!cond) fail(msg); return !!cond; };

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
// The table (or the About page) is drawn, and no load is pending in the summary or in the sections below the table
const DONE = () => {
  const ex = document.getElementById('explore');
  if (ex && ex.hidden) { const p = document.getElementById('page'); return !!(p && /About|did not load|went wrong/.test(p.textContent)); }
  const s = document.getElementById('summary');
  if (!(s && s.textContent.trim() && !/^Loading /.test(s.textContent) && document.getElementById('tbl-main').textContent.trim())) return false;
  return ![...document.querySelectorAll('#more details > summary')].some(x => /Loading /.test(x.textContent));
};
async function open(ctx, url, log, what) {
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') log.errors.push(what + ': ' + m.text()); });
  page.on('pageerror', e => log.errors.push(what + ': ' + e.message));
  page.on('request', r => { const u = r.url(); const i = u.indexOf('/data/'); if (i >= 0) log.data.push(u.slice(i + 1)); });
  const t = Date.now();
  await page.goto(url);
  await page.waitForFunction(DONE, null, { timeout: 90000 });
  log.ms = Date.now() - t;
  return page;
}
// Open sections below the table and wait for what they load
async function openDetails(page, ids) {
  await page.evaluate(ids => { for (const id of ids) { const d = document.getElementById(id); if (d) d.open = true; } }, ids);
  await page.waitForTimeout(200);
  await page.waitForFunction(DONE, null, { timeout: 90000 });
}
const texts = page => page.evaluate(() => Object.fromEntries(['summary', 'tbl-main', 'context', 'more'].map(id => [id, document.getElementById(id).innerText])));
const hashOf = page => page.evaluate(() => location.hash);
function firstDiff(a, b) {
  const x = a.split('\n'), y = b.split('\n');
  for (let i = 0; i < Math.max(x.length, y.length); i++) if (x[i] !== y[i]) return 'line ' + (i + 1) + ': old ' + JSON.stringify(x[i]) + ', new ' + JSON.stringify(y[i]);
  return '';
}
// Old and new page read the same; the new agency details may add Coverage, Sources and State lines
function sameAsOld(xo, xn, what) {
  for (const id of Object.keys(xo)) {
    let n = xn[id];
    if (id === 'context') n = n.split('\n').filter(l => !/^(Coverage|Sources|State)\b/.test(l) || xo[id].split('\n').includes(l)).join('\n');
    ok(xo[id] === n, what + ': #' + id + ' differs from the old page, ' + firstDiff(xo[id], n));
  }
}
// A table's cells by column label: [{label: text}]
const tableRows = (page, sel) => page.evaluate(sel => {
  const t = document.querySelector(sel);
  if (!t) return null;
  const heads = [...t.querySelectorAll('thead th')].map(th => th.innerText.replace(/[ \s]*[↑↓]$/, '').trim());
  return [...t.querySelectorAll('tbody tr')].map(tr => Object.fromEntries([...tr.children].map((c, i) => [heads[i], c.innerText.replace(/›$/, '').trim()])));
}, sel);
const headsOf = (page, sel) => page.evaluate(sel => [...document.querySelectorAll(sel + ' thead th')].map(th => th.innerText.replace(/[ \s]*[↑↓]$/, '').trim()), sel);
// Show every row of a table (Show all, or Show more until none is left)
async function showAll(page, id) {
  for (let i = 0; i < 20; i++) {
    const b = await page.$('#tb-' + id + ' [data-all]') || await page.$('#tb-' + id + ' [data-more]');
    if (!b) return;
    await b.click();
    await page.waitForTimeout(300);
  }
}

async function shoot(ctxs, url, name, prep, log) {
  for (const [kind, ctx] of Object.entries(ctxs)) {
    const l = { errors: [], data: [] };
    const page = await open(ctx, url, l, name + ' (' + kind + ')');
    if (prep) await prep(page);
    await page.waitForTimeout(300);
    if (kind === 'phone') {
      // Against the device width: a mobile browser widens innerWidth to fit content that overflows
      const vw = page.viewportSize().width;
      const w = await page.evaluate(() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth, window.innerWidth));
      ok(w <= vw, name + ' (phone): the page scrolls sideways (' + w + ' px wide in ' + vw + ')');
    }
    await page.screenshot({ path: path.join(SHOTS, name + '-' + kind + '.png'), fullPage: kind === 'phone' });
    ok(!l.errors.length, name + ' (' + kind + '): console errors ' + JSON.stringify(l.errors));
    log.push(name + ' (' + kind + ') ' + l.ms + ' ms');
    await page.close();
  }
}

(async () => {
  let baseUrl = opt('--base-url', null), newUrl = opt('--new-url', null);
  let tmp = null;
  const I = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'index.json'), 'utf8'));
  const M = I.meta;
  const SITE = M.site || 'Fire Agency Vendor Finances';
  const tiers = new Map(I.agencies.map(a => [a.id, a.coverage]));
  fs.mkdirSync(SHOTS, { recursive: true });
  try {
    if (!baseUrl) {
      tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'screens-base-'));
      const tar = execFileSync('git', ['archive', BASE_REF, 'index.html', 'data/data.json', 'data/payments.json', 'favicon.svg', 'favicon-32.png'], { cwd: ROOT, maxBuffer: 1 << 30 });
      execFileSync('tar', ['-x', '-C', tmp], { input: tar });
      baseUrl = await serve(tmp);
    }
    if (!newUrl) newUrl = await serve(ROOT);
    console.log('new page ' + newUrl + ', old page ' + baseUrl + ' (' + BASE_REF + '), screenshots in ' + SHOTS);
    const browser = await chromium.launch();
    const desk = await browser.newContext({ viewport: { width: 1366, height: 900 }, acceptDownloads: true });
    const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    const ctxs = { desktop: desk, phone };
    const timing = [];
    const shots = [];
    // One view: open on the desktop, run its checks, then screenshots at both sizes (prep opens the same sections)
    async function view(n, hash, name, checkFn, prep) {
      if (!runs(n)) return;
      const log = { errors: [], data: [] };
      const page = await open(desk, newUrl + hash, log, name);
      if (prep) await prep(page);
      try { await checkFn(page, log); } catch (e) { fail(name + ': ' + e.message); }
      ok(!log.errors.length, name + ': console errors ' + JSON.stringify(log.errors));
      await page.close();
      await shoot(ctxs, newUrl + hash, name, prep, shots);
      console.log('  ' + n + '. ' + hash + ' (' + log.ms + ' ms, data: ' + (log.data.join(' ') || 'none') + ')');
    }

    // 1. The first load
    await view(1, '#/', '01-home', async (page, log) => {
      await page.waitForTimeout(1000);                     // nothing else is fetched afterwards either
      ok(log.data.length === 1 && log.data[0] === 'data/index.json', '#/ requested ' + JSON.stringify(log.data));
      const gz = zlib.gzipSync(fs.readFileSync(path.join(ROOT, 'data', 'index.json')), { level: 9 }).length;
      ok(gz < 1000000, 'data/index.json is ' + gz + ' bytes gzipped');
      ok((await page.title()) === SITE, 'title ' + JSON.stringify(await page.title()));
      ok((await page.$eval('#home-link', e => e.textContent.trim())) === SITE, 'header reads the site name');
      const cov = await page.$('#ctx-cov');
      ok(!!cov, '#/ has the coverage summary');
      if (cov) ok(/Coverage/.test(await cov.textContent()), 'coverage summary reads Coverage');
      ok(!!(await page.$('#tbl-cov')), '#/ has the coverage table by state');
      const nPurch = I.categories.filter(c => c.purchasing === 'yes').length;
      const rows = await page.$$eval('#tbl-main tbody tr', r => r.length);
      ok(rows === nPurch, '#/ shows ' + rows + ' category rows, expected ' + nPurch);
      timing.push('#/ rendered in ' + log.ms + ' ms (desktop, data/index.json only)');
    }, p => openDetails(p, ['d-cov']));

    // 2. Utah alone reads as the old page
    await view(2, '#/?state=UT', '02-utah', async page => {
      const lo = { errors: [], data: [] };
      const po = await open(desk, baseUrl + '#/', lo, 'old #/');
      sameAsOld(await texts(po), await texts(page), '#/?state=UT');
      ok(!lo.errors.length, 'old #/: console errors ' + JSON.stringify(lo.errors));
      await po.close();
      ok(!(await page.$('#ctx-cov')), '#/?state=UT has no coverage summary (as before)');
    });

    // 3. Ohio
    await view(3, '#/?g=vendor&state=OH', '03-ohio-vendors', async (page, log) => {
      ok(log.data.includes(M.states.OH.files.rows), 'Ohio view loaded ' + M.states.OH.files.rows + ' (' + log.data.join(' ') + ')');
      const ctx = await page.$eval('#context', e => e.innerText);
      ok(/Coverage in Ohio/.test(ctx), 'Ohio coverage line');
      const own = M.states.OH.sources.filter(id => M.sources[id]);
      for (const id of own) {
        const href = await page.$eval('#d-src li[data-src="' + id + '"] a', a => a.getAttribute('href')).catch(() => null);
        ok(href && href === M.sources[id].url, 'Ohio source ' + id + ' listed with its link (' + href + ')');
      }
      ok((await page.$$eval('#tbl-main tbody tr', r => r.length)) > 0, 'Ohio vendor rows');
    }, p => openDetails(p, ['d-src']));

    // 4. Agencies: no vendor data, never $0
    await view(4, '#/?g=agency', '04-agencies', async page => {
      const heads = await headsOf(page, '#tbl-main');
      ok(heads.includes('Coverage'), 'agency grouping shows the Coverage column (' + heads.join(', ') + ')');
      await page.click('#tbl-main thead button.sort:text-is("Agency")');
      await page.waitForTimeout(300);
      await showAll(page, 'main-agency');
      const rows = await tableRows(page, '#tbl-main table');
      const paidKey = heads.find(h => /^Paid/.test(h));
      ok(rows.length === I.agencies.length, 'all ' + I.agencies.length + ' agencies listed (' + rows.length + ')');
      let nod = 0, bad = [];
      for (const r of rows) {
        const t = r.Coverage;
        if (t === 'Totals only' || t === 'Directory only') {
          nod++;
          if (r[paidKey] !== 'No vendor data') bad.push(r.Agency + ': ' + r[paidKey]);
        } else if (r[paidKey] === 'No vendor data') bad.push(r.Agency + ' (' + t + ') reads No vendor data');
      }
      const exp = I.agencies.filter(a => a.coverage > 2).length;
      ok(nod === exp, nod + ' agencies without vendor data listed, expected ' + exp);
      ok(!bad.length, 'paid cells: ' + bad.slice(0, 5).join('; '));
      const first = rows[0] || {};
      ok(rows.length && rows.every((r, i) => !i || rows[i - 1].Agency.localeCompare(r.Agency, 'en', { sensitivity: 'base', numeric: true }) <= 0), 'sorted by agency (first ' + first.Agency + ')');
    });

    // 5. CAL FIRE: payments and SCPRS purchase orders before the first fiscal year
    await view(5, '#/?g=vendor&agency=CA-00555', '05-cal-fire', async page => {
      ok((await page.$$eval('#tbl-pay tbody tr', r => r.length)) > 0, 'CAL FIRE single payments');
      const early = await page.$('#tbl-items-early');
      ok(!!early, 'CAL FIRE item lines before FY' + M.years[0]);
      const title = await page.$eval('#d-items', d => d.innerText).catch(() => '');
      ok(new RegExp('before FY' + M.years[0]).test(title) && /SCPRS/.test(title), 'the early table is titled before FY' + M.years[0] + ' (SCPRS)');
      ok((await page.$$eval('#tbl-items-early tbody tr', r => r.length)) > 0, 'SCPRS lines shown');
    }, p => openDetails(p, ['d-pay', 'd-items']));

    // 6. A Texas DIR agency: item lines, filled, and the scope note
    await view(6, '#/?g=vendor&agency=TX-AA401', '06-tx-dir-agency', async page => {
      const rows = await tableRows(page, '#tbl-items table');
      ok(rows && rows.length > 0, 'TX-AA401 item lines');
      for (const col of ['Brand', 'Quantity', 'Unit price']) ok(rows && rows.every(r => r[col]), col + ' filled on every item line');
      const note = String(M.sources.tx_dir.note).split(/[;.]/)[0].trim();
      const all = await page.evaluate(() => document.getElementById('tbl-main').innerText + '\n' + document.getElementById('more').innerText);
      ok(all.includes(note), 'DIR scope note "' + note + '"');
    }, p => openDetails(p, ['d-items']));

    // 7. Totals only
    await view(7, '#/?g=vendor&agency=CA-01005', '07-totals-only', async page => {
      const s = await page.$eval('#summary', e => e.innerText);
      ok(/^No vendor data/.test(s), 'CA-01005 summary: ' + s);
      ok((await page.$$eval('#tbl-ag-tot tbody tr', r => r.length)) > 0, 'Annual totals table');
      ok(!(await page.$('#d-pay')), 'no single payments section');
    });

    // 8. Directory only
    await view(8, '#/?g=vendor&agency=ID-01100', '08-directory-only', async page => {
      const s = await page.$eval('#summary', e => e.innerText);
      ok(/directory only/.test(s), 'ID-01100 summary: ' + s);
      ok(!!(await page.$('#d-grants')), 'FEMA grants section');
    }, p => openDetails(p, ['d-facts', 'd-grants']));

    // 9. A vendor across states, with item lines
    await view(9, '#/?g=agency&vendor=motorola-solutions', '09-vendor-all-states', async page => {
      await showAll(page, 'main-agency');
      const rows = await tableRows(page, '#tbl-main table');
      const sts = new Set((rows || []).map(r => r.State));
      ok(sts.size >= 2, 'rows from ' + sts.size + ' states (' + [...sts].join(', ') + ')');
      ok((await page.$$eval('#tbl-items tbody tr', r => r.length)) > 0, 'Motorola Solutions item lines');
    }, p => openDetails(p, ['d-items']));

    // 10. About
    await view(10, '#/about', '10-about', async page => {
      const rows = await tableRows(page, '#tbl-about-states table');
      ok(rows && rows.length === M.states_order.length, 'About coverage table: ' + (rows ? rows.length : 0) + ' states');
      ok(/^Total/.test(await page.$eval('#tbl-about-states tfoot', e => e.innerText).catch(() => '')), 'About coverage table total');
      const missing = [];
      for (const id of Object.keys(M.sources)) {
        const href = await page.$eval('li[data-src="' + id + '"] a', a => a.getAttribute('href')).catch(() => null);
        if (!href || !/^https?:\/\//.test(href)) missing.push(id);
      }
      ok(!missing.length, 'About lists every source with a link; missing: ' + missing.join(', '));
    });

    // 11. An older Utah agency link
    await view(11, '#/?g=vendor&agency=359', '11-utah-agency', async page => {
      ok((await hashOf(page)) === '#/?g=vendor&agency=UT-359', 'canonical URL ' + (await hashOf(page)));
      const lo = { errors: [], data: [] };
      const po = await open(desk, baseUrl + '#/?g=vendor&agency=359', lo, 'old agency=359');
      sameAsOld(await texts(po), await texts(page), '#/?g=vendor&agency=359');
      await po.close();
    });

    // 12. A Utah county implies Utah
    await view(12, '#/?county=Salt%20Lake', '12-utah-county', async page => {
      const h = await hashOf(page);
      ok(/[?&]state=UT(&|$)/.test(h) && /county=Salt(%20|\+)Lake/.test(h), 'county link becomes ' + h);
    });

    // 13. Filters that match only agencies without vendor data (the largest such state and county in data/index.json):
    // the summary says so, the category table is empty, and the agency grouping lists them; never $0
    const ZERO = /(^|[^\d.,])\$0(?![\d.,]*\d)/;
    const byCounty = new Map();
    for (const a of I.agencies) {
      if (a.state === 'UT' || !a.county) continue;
      const k = a.state + '\t' + a.county, o = byCounty.get(k) || { n: 0, data: 0 };
      o.n++; if (a.coverage <= 2) o.data++;
      byCounty.set(k, o);
    }
    const ndc = [...byCounty].filter(([, o]) => !o.data && o.n > 1).sort((x, y) => y[1].n - x[1].n || (x[0] < y[0] ? -1 : 1))[0];
    if (ndc) {
      const [st, county] = ndc[0].split('\t');
      const q = 'state=' + st + '&county=' + encodeURIComponent(county);
      await view(13, '#/?' + q, '13-no-vendor-data-filters', async page => {
        const s = await page.$eval('#summary', e => e.innerText);
        ok(/^No vendor data/.test(s), q + ' summary: ' + s);
        const tm = await page.$eval('#tbl-main', e => e.innerText);
        ok(!ZERO.test(s) && !ZERO.test(tm), q + ': $0 in the summary or table: ' + (tm.match(/.{0,40}\$0.{0,20}/) || [''])[0]);
        ok((await page.$$eval('#tbl-main tbody tr', r => r.length)) === 0, q + ': no category rows');
        const lo = { errors: [], data: [] };
        const pa = await open(desk, newUrl + '#/?g=agency&' + q, lo, 'agencies in ' + county);
        await showAll(pa, 'main-agency');
        const rows = await tableRows(pa, '#tbl-main table');
        const paidKey = (await headsOf(pa, '#tbl-main')).find(h => /^Paid/.test(h));
        ok(rows && rows.length === ndc[1].n && rows.every(r => r[paidKey] === 'No vendor data'), q + ': agency grouping lists ' + ndc[1].n + ' agencies, all No vendor data');
        const foot = await pa.$eval('#tbl-main tfoot', e => e.innerText).catch(() => '');
        ok(/No vendor data/.test(foot), q + ': total row reads No vendor data (' + foot.replace(/\s+/g, ' ') + ')');
        ok(!lo.errors.length, 'agencies in ' + county + ': console errors ' + JSON.stringify(lo.errors));
        await pa.close();
      });
    } else console.log('  13. skipped: every county outside Utah has an agency with vendor data');

    // Timing: a drill-down from #/ that loads every state
    if (runs('timing')) {
      const log = { errors: [], data: [] };
      const page = await open(desk, newUrl + '#/', log, 'drill');
      const t = Date.now();
      await page.click('#tbl-main tbody tr:first-child button.drill');
      await page.waitForFunction(() => /[?&]cat=/.test(location.hash), null, { timeout: 30000 });
      await page.waitForFunction(DONE, null, { timeout: 120000 });
      const ms = Date.now() - t;
      const files = M.states_order.map(st => M.states[st].files.rows);
      ok(files.every(f => log.data.includes(f)), 'the drill-down loaded every state (' + log.data.join(' ') + ')');
      ok(!log.errors.length, 'drill: console errors ' + JSON.stringify(log.errors));
      timing.push('drill-down from #/ to ' + (await hashOf(page)) + ', loading every state: ' + ms + ' ms');
      await page.close();
    }

    console.log(timing.join('\n'));
    console.log('screenshots: ' + shots.join(', '));
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
