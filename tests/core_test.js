#!/usr/bin/env node
// Core of index.html in node: Utah is unchanged, and the precomputed default tables match the computed ones.
//
//   node tests/core_test.js [--base REF] [--legacy REF]
//
// 1. The old Core (index.html at --base, default de1e5cf, before the states were split) on the legacy
//    data/data.json and data/payments.json, against the new Core on data/index.json, data/ut.json and
//    data/ut-payments.json in the Utah view, for about 2,000 generated states: normState, stateParams,
//    tableModel (items, sum, peers, rows) and paymentsModel, after mapping ids (agency 359 -> "UT-359",
//    vendor index -> vendor id, payee name and description index -> text). The legacy files are read from
//    the working tree, or from --legacy REF (the last commit that has them) when they are gone.
// 2. The precomputed default table of every scope (data/index.json home) against the table computed from
//    the rows once every state is loaded: spend and spend per year within $0.01, counts and last year exact.
//    For Utah, also exactly equal to the old Core.
// 3. Store and URL rules: needs (pre mode, missing states), older URL forms (numeric agency ids, a county
//    without a state), agg with string ids, files from another build refused.
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const BASE = opt('--base', 'de1e5cf');
const LEGACY = opt('--legacy', null);

const git = (ref, file) => execFileSync('git', ['show', ref + ':' + file], { cwd: ROOT, maxBuffer: 1 << 30 }).toString('utf8');
function loadCore(src) {
  const a = src.indexOf('const Core = (function () {');
  const b = src.indexOf('\n})();\n', a);
  if (a < 0 || b < 0) throw new Error('Core not found in index.html');
  return new Function(src.slice(a, b + 6) + '\nreturn Core;')();
}
const readData = f => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', f), 'utf8'));
function readLegacy(f) {
  if (!LEGACY && fs.existsSync(path.join(ROOT, 'data', f))) return readData(f);
  return JSON.parse(git(LEGACY || BASE, 'data/' + f));
}

const OldCore = loadCore(git(BASE, 'index.html'));
const Core = loadCore(fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8'));

let checks = 0, failures = 0;
const fail = (what, a, b) => {
  failures++;
  if (failures <= 25) console.log('FAIL ' + what + (a !== undefined ? '\n  old/expected: ' + JSON.stringify(a).slice(0, 400) + '\n  new/actual:   ' + JSON.stringify(b).slice(0, 400) : ''));
};
const ok = (cond, what, a, b) => { checks++; if (!cond) fail(what, a, b); };
const same = (a, b, what) => { checks++; const x = JSON.stringify(a), y = JSON.stringify(b); if (x !== y) fail(what, a, b); };

// ---- Data ----
const t0 = Date.now();
const D = readLegacy('data.json');
const LP = readLegacy('payments.json');
const ix0 = OldCore.buildIndex(D);
OldCore.setPayments(ix0, LP);
const I = readData('index.json');
const STATES = I.meta.states_order;
const stateFile = s => readData(path.basename(I.meta.states[s].files.rows));
const payFile = s => readData(path.basename(I.meta.states[s].files.payments));
// Full store: every state and every state's payments
const store = Core.buildStore(readData('index.json'));
for (const s of STATES) Core.addState(store, s, stateFile(s));
for (const s of STATES) Core.addPayments(store, s, payFile(s));
// Utah only, loaded after nothing else (other vendor and payee name offsets than the full store)
const storeUT = Core.buildStore(readData('index.json'));
Core.addState(storeUT, 'UT', stateFile('UT'));
Core.addPayments(storeUT, 'UT', payFile('UT'));
console.log('loaded in ' + ((Date.now() - t0) / 1000).toFixed(1) + ' s');

// ---- Id mapping: everything to comparable values ----
const oldAg = a => (a == null ? a : 'UT-' + a);
function mapper(ix, old) {
  const ag = a => (old ? oldAg(a) : a);
  const ven = vi => ix.D.vendors[vi].id;
  const alias = i => (i < 0 ? null : ix.D.aliases[i]);
  const key = (g, k) => (g === 'vendor' ? ven(k) : g === 'agency' ? ag(k) : k);
  const set = (xs, f) => [...xs].map(f).sort();
  const aggo = (g, o) => ({ key: key(g, o.key), spend: o.spend, n: o.n, ag: set(o.ag, ag), ve: set(o.ve, ven), yr: o.yr, last: o.last });
  const row = r => [ag(r[0]), ven(r[1]), r[2], r[3], r[4], alias(r[5])];
  const pay = p => [ag(p[0]), p[1], ven(p[2]), p[3], p[4], ix.P.descriptions[p[5]], alias(p[6]), p[7]];
  const state = s => { const o = Object.assign({}, s, { agency: ag(s.agency) }); delete o.state; delete o.scope; return o; };
  const params = ps => ps.filter(([k]) => k !== 'state').map(([k, v]) => [k, k === 'agency' && old ? oldAg(v) : v]);
  return { ag, ven, aggo, row, pay, state, params };
}
const M0 = mapper(ix0, true);

// ---- 1. Generated states ----
const cats = D.categories.map(c => c.id);
const vendorSpend = new Map();
for (const r of D.rows) vendorSpend.set(r[1], (vendorSpend.get(r[1]) || 0) + Math.abs(r[4]));
const topVendors = [...vendorSpend].sort((a, b) => b[1] - a[1] || a[0] - b[0]).slice(0, 50).map(([vi]) => D.vendors[vi].id);
const agencies = D.agencies.map(a => a.id);
const counties = [...new Set(D.agencies.map(a => a.county).filter(Boolean))].sort();
const sizes = ['', ...OldCore.SIZES.map(z => z.id)];
const years = D.meta.years;
const G = OldCore.GROUPS;
let seed = 12345;
const rnd = n => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed % n; };
const pick = xs => xs[rnd(xs.length)];

const gen = [];
for (const g of G) gen.push({ g });
for (const g of G) for (const c of cats) gen.push({ g, cat: c });
for (const g of G) gen.push({ g, cat: 'apparatus,ambulance' }, { g, cat: 'scba,ppe,apparatus,ambulance,communications' });
for (const v of topVendors) for (const g of G) gen.push({ g, vendor: v });
for (const a of agencies) for (const g of G) gen.push({ g, agency: String(a) });
for (const y of years) for (const g of G) gen.push({ g, year: String(y) });
for (const [f, t] of [[2022, 2024], [2021, 2021], [2023, 2026], [2026, 2022], [2025, 2026]]) for (const g of G) gen.push({ g, from: String(f), to: String(t) });
for (const c of counties) for (const z of sizes) gen.push({ g: pick(G), county: c, size: z || undefined });
for (const z of sizes.slice(1)) for (const g of G) gen.push({ g, size: z });
for (const g of G) gen.push({ g, np: '1' }, { g, years: '1' }, { g, np: '1', years: '1' }, { g, purch: 'no' }, { g, group: 'Apparatus and vehicles' });
for (const c of ['payroll', 'debt', 'government', 'individuals', 'unclassified', 'no-vendor']) for (const g of G) gen.push({ g, cat: c, np: '1' });
for (const v of ['individuals', 'no-vendor-named']) for (const g of G) gen.push({ g, vendor: v });
for (let i = 0; i < 300; i++) {
  const p = { g: pick(G) };
  if (rnd(2)) p.cat = pick(cats);
  if (rnd(3) === 0) p.vendor = pick(topVendors);
  if (rnd(3) === 0) p.agency = String(pick(agencies));
  if (rnd(4) === 0) p.year = String(pick(years));
  else if (rnd(3) === 0) { p.from = String(pick(years)); p.to = String(pick(years)); }
  if (rnd(4) === 0) p.county = pick(counties);
  if (rnd(4) === 0) p.size = pick(sizes.slice(1));
  if (rnd(5) === 0) p.np = '1';
  if (rnd(5) === 0) p.years = '1';
  if (rnd(6) === 0) p.q = pick(['air', 'fire', 'x']);
  gen.push(p);
}
// Values that do not match the data, and older forms
gen.push({ g: 'vendor', agency: '99999' }, { g: 'agency', vendor: 'no-such-vendor' }, { cat: 'nope,scba' }, { year: '1999' },
  { g: 'nope' }, { g: 'vendor', type: 'x', staff: 'y' }, { g: 'vendor', purch: 'yes' }, { g: 'agency', county: 'Nowhere' },
  { g: 'vendor', vendor: topVendors[0], cat: 'ppe', group: 'Facilities' }, { g: 'none', agency: '631', from: '2023', to: '2024' });
for (const [parts, q] of [[['category', 'scba'], {}], [['vendor', topVendors[1]], {}], [['agency', '1421'], {}], [['vendors'], {}],
  [['agencies'], {}], [['rows'], {}], [['nope'], {}]]) gen.push(Object.assign({}, OldCore.fromPath(parts, q).p));

// The new URL for an older one: numeric agency ids and Utah counties imply Utah; otherwise state=UT is added.
// Every third state with an agency or county keeps the older form, to test that rule.
const newParams = (p, i) => {
  const q = Object.assign({}, p);
  for (const k of Object.keys(q)) if (q[k] === undefined) delete q[k];
  const implied = (q.agency && /^\d+$/.test(q.agency) && agencies.includes(Number(q.agency))) || (q.county && counties.includes(q.county));
  if (!(implied && i % 3 === 0)) q.state = 'UT';
  if (q.agency && i % 3 === 1 && /^\d+$/.test(q.agency) && agencies.includes(Number(q.agency))) q.agency = 'UT-' + q.agency;
  return q;
};

function compareState(st, p, i, label) {
  const p0 = Object.assign({}, p);
  for (const k of Object.keys(p0)) if (p0[k] === undefined) delete p0[k];
  const S0 = OldCore.normState(ix0, p0);
  const p1 = newParams(p0, i);
  const S1 = Core.normState(st, p1);
  const what = label + ' ' + JSON.stringify(p1);
  ok(S1.scope === 'UT', what + ': scope ' + S1.scope);
  const ix1 = Core.view(st, S1.scope);
  const M1 = mapper(ix1, false);
  same(M0.state(S0), M1.state(S1), what + ': normState');
  same(M0.params(OldCore.stateParams(ix0, S0)), M1.params(Core.stateParams(ix1, S1)), what + ': stateParams');
  const m0 = OldCore.tableModel(ix0, S0), m1 = Core.tableModel(ix1, S1);
  ok(m1.pre === false, what + ': computed, not precomputed');
  same([...m0.peers].map(oldAg).sort(), [...m1.peers].sort(), what + ': peers');
  same([m0.onlyPurch, m0.narrowed, m0.year], [m1.onlyPurch, m1.narrowed, m1.year], what + ': flags');
  same(M0.aggo('sum', m0.sum), M1.aggo('sum', m1.sum), what + ': sum');
  same(m0.rows.map(M0.row), m1.rows.map(M1.row), what + ': rows');
  const items = (M, m, S) => (S.g === 'none' ? m.items.map(M.row) : m.items.map(o => M.aggo(S.g, o)));
  same(items(M0, m0, S0), items(M1, m1, S1), what + ': items');
  const pm0 = OldCore.paymentsModel(ix0, S0, OldCore.rowFilter(S0)), pm1 = Core.paymentsModel(ix1, S1, Core.rowFilter(S1));
  same([pm0.n, pm0.total, [...pm0.ag].map(oldAg).sort(), [...pm0.ve].map(M0.ven).sort()],
    [pm1.n, pm1.total, [...pm1.ag].sort(), [...pm1.ve].map(M1.ven).sort()], what + ': payments totals');
  same(pm0.pays.map(M0.pay), pm1.pays.map(M1.pay), what + ': payments');
  // Drill-downs from the first rows lead to the same states
  if (S0.g !== 'none') {
    for (const k of [0, 1]) {
      const o0 = m0.items[k], o1 = m1.items[k];
      if (!o0 || !o1) continue;
      const d0 = OldCore.drill(ix0, S0, o0.key), d1 = Core.drill(ix1, S1, o1.key);
      same(M0.params(OldCore.stateParams(ix0, d0)), M1.params(Core.stateParams(ix1, d1)), what + ': drill ' + k);
    }
  }
}
const t1 = Date.now();
gen.forEach((p, i) => compareState(store, p, i, 'all states loaded'));
gen.filter((p, i) => i % 10 === 0).forEach((p, i) => compareState(storeUT, p, i * 10, 'Utah only'));
console.log(gen.length + ' generated states compared (' + Math.ceil(gen.length / 10) + ' again with Utah only) in ' + ((Date.now() - t1) / 1000).toFixed(1) + ' s');

// ---- 2. Precomputed default tables ----
const empty = Core.buildStore(readData('index.json'));
for (const scope of ['ALL'].concat(STATES)) {
  const p = scope === 'ALL' ? {} : { state: scope };
  const n = Core.needs(empty, p);
  ok(n.pre && n.scope === scope && n.missing.length === (scope === 'ALL' ? STATES.length : 1), 'needs ' + scope, null, n);
  const Se = Core.normState(empty, p), ve = Core.view(empty, Se.scope);
  const pre = Core.tableModel(ve, Se);
  ok(pre.pre === true && ve.loaded === false, scope + ': precomputed table used before loading');
  const Sf = Core.normState(store, p), vf = Core.view(store, Sf.scope);
  const comp = Core.tableModel(vf, Sf);
  ok(comp.pre === false, scope + ': computed once loaded');
  ok(pre.items.length === comp.items.length, scope + ': precomputed categories', comp.items.length, pre.items.length);
  const near = (a, b) => Math.abs(a - b) <= 0.01;
  const nearYr = (a, b) => Object.keys(a).length === Object.keys(b).length && Object.keys(a).every(y => near(a[y], b[y]));
  comp.items.forEach((o, k) => {
    const q = pre.items[k] || {};
    const what = scope + ' precomputed ' + o.key;
    ok(q.key === o.key && near(q.spend, o.spend) && q.n === o.n && q.ve.size === o.ve.size && q.ag.size === o.ag.size &&
      q.last === o.last && nearYr(q.yr, o.yr), what,
    [o.key, o.spend, o.n, o.ve.size, o.ag.size, o.last, o.yr], [q.key, q.spend, q.n, q.ve && q.ve.size, q.ag && q.ag.size, q.last, q.yr]);
  });
  ok(near(pre.sum.spend, comp.sum.spend) && pre.sum.n === comp.sum.n && pre.sum.ve.size === comp.sum.ve.size &&
    pre.sum.ag.size === comp.sum.ag.size && nearYr(pre.sum.yr, comp.sum.yr), scope + ' precomputed total',
  [comp.sum.spend, comp.sum.n, comp.sum.ve.size, comp.sum.ag.size, comp.sum.yr], [pre.sum.spend, pre.sum.n, pre.sum.ve.size, pre.sum.ag.size, pre.sum.yr]);
  same([...pre.peers].sort(), [...comp.peers].sort(), scope + ' precomputed peers');
  if (scope === 'UT') {
    // The page shows the precomputed Utah table: it must show what the old Core gave. The build rounds the
    // amounts to cents, so amounts are compared in cents, and shares as the page and its CSV show them.
    const S0 = OldCore.normState(ix0, {});
    const m0 = OldCore.tableModel(ix0, S0);
    const c = v => Math.round(v * 100);
    const yc = yr => Object.fromEntries(Object.entries(yr).map(([y, v]) => [y, c(v)]));
    const sh = (o, m) => [(o.spend / m.sum.spend * 100).toFixed(1), Math.round(o.spend / m.sum.spend * 100 * 1000) / 1000];
    same(m0.items.map(o => [o.key, c(o.spend), o.n, o.ve.size, o.ag.size, o.last, yc(o.yr), sh(o, m0)]),
      pre.items.map(o => [o.key, c(o.spend), o.n, o.ve.size, o.ag.size, o.last, yc(o.yr), sh(o, pre)]), 'UT precomputed = old Core');
    same([c(m0.sum.spend), m0.sum.n, m0.sum.ve.size, m0.sum.ag.size, yc(m0.sum.yr)], [c(pre.sum.spend), pre.sum.n, pre.sum.ve.size, pre.sum.ag.size, yc(pre.sum.yr)], 'UT precomputed total = old Core');
    for (const y of ['1']) {
      const Sy = Core.normState(empty, { state: 'UT', years: y });
      ok(Core.tableModel(Core.view(empty, 'UT'), Sy).pre === true, 'UT years=1 precomputed');
    }
  }
}

// ---- 3. Store and URL rules ----
const nd = p => { const n = Core.needs(empty, p); return [n.scope, n.missing.join(','), n.pre]; };
same(nd({}), ['ALL', STATES.join(','), true], 'needs #/');
same(nd({ state: 'ut' }), ['UT', 'UT', true], 'needs state=ut');
same(nd({ g: 'vendor' }), ['ALL', STATES.join(','), false], 'needs g=vendor');
same(nd({ g: 'category', years: '1', from: '2021', to: '2027' }), ['ALL', STATES.join(','), true], 'needs full range');
same(nd({ to: '2026' }), ['ALL', STATES.join(','), false], 'needs to=2026');
same(nd({ state: 'UT', from: '2021', to: '2026' }), ['UT', 'UT', true], 'needs UT full range');
same(nd({ agency: '359', g: 'vendor' }), ['UT', 'UT', false], 'needs agency=359');
same(nd({ agency: 'TX-AA401' }), ['TX', 'TX', false], 'needs agency=TX-AA401');
same(nd({ county: 'Salt Lake' }), ['UT', 'UT', false], 'needs county=Salt Lake');
same(nd({ q: 'air' }), ['ALL', STATES.join(','), false], 'needs q');
same(nd({ state: 'XX' }), ['ALL', STATES.join(','), true], 'needs bad state');
same(Core.needs(store, { state: 'OH', g: 'vendor' }).missing, [], 'needs when loaded');

const canon = p => { const S = Core.normState(store, p); return [new URLSearchParams(Core.stateParams(Core.view(store, S.scope), S)).toString(), S.bad]; };
same(canon({ g: 'vendor', agency: '359' }), ['g=vendor&agency=UT-359', []], 'canonical agency=359');
same(canon({ g: 'vendor', agency: 'UT-359' }), ['g=vendor&agency=UT-359', []], 'canonical agency=UT-359');
same(canon({ county: 'Salt Lake' }), ['g=category&state=UT&county=Salt+Lake', []], 'canonical county=Salt Lake');
same(canon({ county: 'Washington' }), ['g=category&state=UT&county=Washington', []], 'canonical county shared with Utah');
const ohOnly = store.st.OH.counties.find(c => store.order.filter(s => store.st[s].counties.includes(c)).length === 1);
same(canon({ county: ohOnly }), ['g=category&state=OH&county=' + encodeURIComponent(ohOnly).replace(/%20/g, '+'), []], 'canonical county of one state');
same(canon({ county: 'Nowhere' }), ['g=category', ['county "Nowhere"']], 'canonical unknown county');
same(canon({ state: 'oh', g: 'vendor' }), ['g=vendor&state=OH', []], 'canonical state=oh');
same(canon({ state: 'UT', to: '2026' }), ['g=category&state=UT', []], 'canonical UT to=2026');
same(canon({ to: '2026' }), ['g=category&to=2026', []], 'canonical ALL to=2026');
same(canon({ state: 'UT', agency: 'OH-01127', g: 'vendor' }), ['g=vendor&state=UT&agency=OH-01127', []], 'canonical agency of another state');
const ohVendor = store.vendors[store.st.OH.vmap.find(gi => !store.st.UT.valias.has(gi))].id;
same(canon({ state: 'UT', vendor: ohVendor })[1], ['vendor "' + ohVendor + '" (no payments in Utah)'], 'vendor of another state');
// Leaving a scope keeps the full range full: Utah (to FY2026) to all states (to FY2027)
{
  const S = Core.normState(store, { state: 'UT', g: 'vendor' });
  const ixu = Core.view(store, 'UT');
  same(Core.stateParams(ixu, Object.assign({}, S, { state: '' })), [['g', 'vendor']], 'UT to all states keeps the full range');
  const S2 = Core.normState(store, { state: 'UT', g: 'vendor', to: '2025' });
  same(Core.stateParams(ixu, Object.assign({}, S2, { state: '' })), [['g', 'vendor'], ['to', '2025']], 'UT to all states keeps a chosen range');
  const Sa = Core.normState(store, { g: 'agency' });
  const ixa = Core.view(store, 'ALL');
  same(Core.stateParams(ixa, Core.drill(ixa, Sa, 'UT-359')), [['g', 'vendor'], ['agency', 'UT-359']], 'drill to a Utah agency from all states');
}
// The scope of an agency in another state than the filter: the agency's state
{
  const S = Core.normState(store, { state: 'OH', agency: '359', g: 'vendor' });
  same([S.scope, S.state, S.agency], ['UT', 'OH', 'UT-359'], 'agency scope over state filter');
}
// Views of other states and all states
for (const scope of ['ALL'].concat(STATES)) {
  const v = Core.view(store, scope);
  ok(v.loaded && v.P && v.P.payments.length > 0, scope + ' view loaded with payments');
  const want = new Set();
  for (const s of Core.scopeStates(store, scope)) for (const gi of store.st[s].vmap) want.add(gi);
  ok(v.vendorPos.size === want.size, scope + ' vendors', want.size, v.vendorPos.size);
  const S = Core.normState(store, scope === 'ALL' ? { g: 'agency' } : { g: 'agency', state: scope });
  const m = Core.tableModel(v, S);
  const nodata = m.items.filter(o => o.nodata).length;
  const want3 = v.D.agencies.filter(a => a.coverage > 2).length;
  ok(nodata === want3 && m.peersData.size + want3 === m.peers.size && m.nodata === 0, scope + ' agencies without vendor data', want3, nodata);
  ok(m.items.filter(o => o.nodata && o.n > 0).length === 0, scope + ' no rows for agencies without vendor data');
}
// A selected agency without vendor data
for (const a of [I.agencies.find(x => x.coverage === 3), I.agencies.find(x => x.coverage === 4), I.agencies.find(x => x.coverage === 1)]) {
  const S = Core.normState(store, { g: 'vendor', agency: a.id });
  const m = Core.tableModel(Core.view(store, S.scope), S);
  ok(m.nodata === (a.coverage > 2 ? a.coverage : 0) && m.peersData.size === (a.coverage > 2 ? 0 : 1), 'selected agency coverage ' + a.coverage, a.coverage, m.nodata);
}
// UT view meta is Utah's meta as data.json had it
{
  const v = Core.view(storeUT, 'UT');
  for (const k of Object.keys(D.meta)) if (k !== 'payments_file') same(D.meta[k], v.meta[k], 'UT meta ' + k);
  same(v.years, ix0.years, 'UT years');
  same([...v.partial], [...ix0.partial], 'UT partial years');
  same(v.counties, ix0.counties, 'UT counties');
  same([...v.latest].filter(([id]) => String(id).startsWith('UT-')).map(([id, l]) => [id, l]),
    [...ix0.latest].map(([id, l]) => [oldAg(id), l]), 'UT annual expenses');
  same(D.vendors.map(x => [x.id, ix0.vcats[ix0.vendorPos.get(x.id)], ix0.vendorText[ix0.vendorPos.get(x.id)], x.category]),
    D.vendors.map(x => { const vi = v.vendorPos.get(x.id); return [x.id, v.vcats[vi], v.vendorText[vi], v.vcategory(vi)]; }), 'UT vendor categories and search text');
  ok(v.vendorPos.size === D.vendors.length, 'UT vendor count', D.vendors.length, v.vendorPos.size);
}
// agg with string ids: agencies counted as themselves, not as NaN
{
  const rows = [['UT-1', 0, 2021, 3, 10, -1], ['UT-2', 0, 2021, 3, 5, -1], ['OH-01127', 1, 2022, 3, -2, -1], ['OH-01127', 1, 2022, 3, 3, -1], ['TX-AA401', 2, 2023, 4, -1, -1]];
  const by = Core.agg(rows, r => r[3]);
  same([[...by.get(3).ag].sort(), [...by.get(3).ve], by.get(3).last, by.get(4).ag.size], [['OH-01127', 'UT-1', 'UT-2'], [0, 1], 2022, 0], 'agg with string ids');
  const tot = Core.emptyAgg(0);
  Core.agg(rows, r => r[1], tot);
  same([tot.spend, tot.n, [...tot.ag].sort(), tot.last], [15, 5, ['OH-01127', 'UT-1', 'UT-2'], 2022], 'agg totals');
}
// Files from another build, or another state, are refused
{
  const s2 = Core.buildStore(readData('index.json'));
  const f = stateFile('ID');
  let err = null;
  try { Core.addState(s2, 'ID', Object.assign({}, f, { built: '1999-01-01' })); } catch (e) { err = e; }
  ok(err && /same build/.test(err.message), 'refuses another build');
  err = null;
  try { Core.addState(s2, 'TX', f); } catch (e) { err = e; }
  ok(!!err, 'refuses another state');
  err = null;
  try { Core.addPayments(s2, 'ID', payFile('ID')); } catch (e) { err = e; }
  ok(!!err, 'refuses payments before rows');
  ok(!Core.isLoaded(s2, 'ID'), 'nothing loaded after a refusal');
}

console.log(checks + ' checks, ' + failures + ' failed (' + ((Date.now() - t0) / 1000).toFixed(1) + ' s)');
process.exit(failures ? 1 : 0);
