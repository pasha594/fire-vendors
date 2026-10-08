#!/usr/bin/env node
// VCore of index.html (the vendor page) in node, on data/index.json, data/stack.json and the files it loads later.
//
//   node tests/stack_test.js
//
// 1. Every number the page shows before data/stack-tail.json loads (categories of a scope with their counts,
//    totals and ranked vendors; the agencies of a scope with totals, vendor counts and common vendors) is the same
//    after it loads, for all states, each state and some counties.
// 2. Per category, merchants' and others' net amounts add up to the precomputed default table of data/index.json.
// 3. A vendor's page agrees with the category ranking (agencies and amount in each category) and with its lines.
// 4. An agency's stack adds up to its total on the agencies list, and its vendor count matches.
// 5. Single payments and item lines map to vendors that have lines with the same agency.
// 6. Search finds vendors and agencies by name.
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
let failures = 0, checks = 0;
const ok = (cond, msg) => { checks++; if (!cond) { failures++; console.log('FAIL ' + msg); } };
const read = f => JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8'));

const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
const mod = { exports: null };
new Function('module', m[1])(mod);                         // the page part returns at once without a document
const VCore = mod.exports;

const t0 = Date.now();
const I = read('data/index.json');
const store = VCore.buildStore(I, read('data/stack.json'));
const scopes = [['', ''], ...I.meta.states_order.map(s => [s, ''])];
// Some counties: the three of each state with the most agencies with vendor data
for (const s of I.meta.states_order) {
  const n = new Map();
  for (const a of I.agencies) if (a.state === s && a.county && a.coverage <= 2) n.set(a.county, (n.get(a.county) || 0) + 1);
  for (const [c] of [...n].sort((x, y) => y[1] - x[1]).slice(0, 3)) scopes.push([s, c]);
}
const snap = () => scopes.map(([s, c]) => {
  const sc = VCore.scope(store, s, c);
  const C = VCore.categories(store, sc);
  return {
    key: s + '|' + c, agencies: C.agencies, vendors: C.vendors, paid: C.paid, others: C.others,
    cats: [...C.cats.values()].map(x => ({ id: x.sec.id, nV: x.nVendors, nA: x.nAgencies, paid: x.paid, others: x.others, single: x.single,
      list: x.list.map(y => [y.v.id, y.agencies, y.paid, y.stats && y.stats.median, y.states.join(), y.last].join('|')).join(';') })),
    ags: VCore.agenciesModel(store, sc).map(o => [o.a.id, o.paid, o.vendors, o.others, o.common.map(v => v.id).join()]),
  };
});
const before = snap();
VCore.addTail(store, read('data/stack-tail.json'));
const after = snap();
const near = (x, y) => Math.abs(x - y) < 0.01;

// 1. Before and after data/stack-tail.json
before.forEach((b, i) => {
  const a = after[i];
  ok(b.agencies === a.agencies && b.vendors === a.vendors && near(b.paid, a.paid) && near(b.others, a.others),
    b.key + ': totals change when the tail loads ' + JSON.stringify([b.agencies, b.vendors, b.paid, b.others, a.agencies, a.vendors, a.paid, a.others]));
  b.cats.forEach((c, k) => {
    const d = a.cats[k];
    ok(c.nV === d.nV && c.nA === d.nA && near(c.paid, d.paid) && near(c.others, d.others) && c.single === d.single,
      b.key + ' ' + c.id + ': counts change when the tail loads ' + JSON.stringify([c, d].map(x => [x.nV, x.nA, x.paid, x.others, x.single])));
    ok(c.list === d.list, b.key + ' ' + c.id + ': ranked vendors change when the tail loads');
  });
  ok(b.ags.length === a.ags.length && b.ags.every((x, k) => x[0] === a.ags[k][0] && near(x[1], a.ags[k][1]) && x[2] === a.ags[k][2] &&
    near(x[3], a.ags[k][3]) && x[4] === a.ags[k][4]), b.key + ': agencies list changes when the tail loads');
});

// 2. Against the default tables of data/index.json
for (const [scope, H] of Object.entries(I.home)) {
  const a = after.find(x => x.key === (scope === 'ALL' ? '' : scope) + '|');
  for (const [c, spend] of H.cats) {
    const x = a.cats.find(y => y.id === I.categories[c].id);
    ok(near(x.paid + x.others, spend), scope + ' ' + I.categories[c].id + ': ' + (x.paid + x.others).toFixed(2) + ' against home ' + spend);
  }
}

// 3. Vendor pages: the top three vendors of every category, all states and Utah
for (const st of ['', 'UT']) {
  const sc = VCore.scope(store, st, '');
  for (const c of VCore.categories(store, sc).cats.values()) {
    for (const x of c.list.slice(0, 3)) {
      const M = VCore.vendorModel(store, sc, x.v.i);
      const bc = M.byCat.find(b => b.pos === c.sec.pos);
      ok(bc && bc.agencies === x.agencies && near(bc.paid, x.paid), (st || 'ALL') + ' ' + c.sec.id + ' ' + x.v.id + ': vendor page ' +
        JSON.stringify(bc && [bc.agencies, bc.paid]) + ' against the ranking ' + JSON.stringify([x.agencies, x.paid]));
      ok(M.nAgencies >= x.agencies && M.list.length === M.nAgencies, x.v.id + ': agencies listed');
      const total = M.list.reduce((t, r) => t + r.paid, 0) + 0;
      ok(M.credits > 0 || near(total, M.paid), x.v.id + ': agency rows add up to ' + total + ', not ' + M.paid);
      ok(M.byState.reduce((t, s) => t + s.agencies, 0) === M.nAgencies, x.v.id + ': agencies by state');
    }
  }
}

// 4. Agency stacks against the agencies list (all states)
const list = VCore.agenciesModel(store, VCore.scope(store, '', ''));
let nStack = 0;
for (const o of list) {
  if (o.ai == null) continue;
  const M = VCore.agencyModel(store, o.ai);
  ok(near(M.paid, o.paid) && M.vendors === o.vendors && near(M.others, o.others), o.a.id + ': stack ' + JSON.stringify([M.paid, M.vendors, M.others]) +
    ' against the agencies list ' + JSON.stringify([o.paid, o.vendors, o.others]));
  const sum = [...M.cats.values()].reduce((t, c) => t + c.paid, 0);
  ok(near(sum, M.paid), o.a.id + ': categories add up');
  nStack++;
}

// 5. Payments and item lines
const pairs = new Set(store.lines.map(r => store.ags[r[0]].id + '|' + r[1]));
for (const st of I.meta.states_order) {
  const f = I.meta.states[st].files;
  const P = VCore.addPayments(store, st, read(f.payments));
  const n = read(f.payments).payments.length;
  ok(P.every(p => pairs.has(p[0] + '|' + p[2])), st + ': a payment names a vendor without lines with its agency');
  ok(P.length >= n * 0.99, st + ': ' + (n - P.length) + ' of ' + n + ' payments without a vendor of the stack files');
  if (f.items) {
    // Item lines before the state's first fiscal year (California SCPRS, FY2013 to FY2015) have no yearly rows
    const first = Math.min(...I.meta.states[st].years);
    const X = VCore.addItems(store, st, read(f.items)).filter(it => it[1] >= first);
    ok(X.every(it => pairs.has(it[0] + '|' + it[3])), st + ': an item line names a vendor without lines with its agency');
  }
}

// 6. Search
const R = VCore.search(store, 'motorola', 5);
ok(R.vendors[0] && R.vendors[0].id === 'motorola-solutions', 'search motorola: ' + R.vendors.map(v => v.id));
const R2 = VCore.search(store, 'american fork', 5);
ok(R2.agencies[0] && R2.agencies[0].id === 'UT-359', 'search american fork: ' + R2.agencies.map(a => a.id));
ok(VCore.search(store, 'zions bank', 5).vendors.length === 0, 'search shows a card issuer as a vendor');

console.log(scopes.length + ' scopes, ' + nStack + ' agency stacks; ' + checks + ' checks, ' + failures + ' failed (' +
  ((Date.now() - t0) / 1000).toFixed(1) + ' s)');
process.exit(failures ? 1 : 0);
