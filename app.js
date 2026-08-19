/* Benchmark Explorer — static client.
   Loads data/index.json once (search + charts), then pulls the full card for a
   single benchmark from its shard in data/cards/ on demand. */

(function () {
  'use strict';

  var MAX_HITS = 200;          // results rendered per query
  var UNLABELLED = 'Unlabelled';
  var OTHER = 'Other';
  var FOLD_BELOW = 0.005;      // values under 0.5% of the corpus fold into Other

  var state = {
    index: [],                 // lean rows, one per card
    meta: null,                // groups + labels from build.py
    shards: new Map(),         // bucket -> {slug: card}
    hits: [],
    selected: null,
    query: '',
    tab: 'stats',           // statistics is the landing view
    chartsBuilt: false,
    charts: []
  };

  var el = {
    corpusLine: document.getElementById('corpus-line'),
    q: document.getElementById('q'),
    resultmeta: document.getElementById('resultmeta'),
    results: document.getElementById('results'),
    detail: document.getElementById('detail'),
    footnote: document.getElementById('footnote'),
    tabExplore: document.getElementById('tab-explore'),
    tabStats: document.getElementById('tab-stats'),
    panelExplore: document.getElementById('panel-explore'),
    panelStats: document.getElementById('panel-stats')
  };

  var nf = new Intl.NumberFormat('en-US');

  // ---------------------------------------------------------------- helpers

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* Escape first, then wrap matches — splitting on the raw string keeps the
     offsets valid, so the markup can never be broken by the query. */
  function highlight(text, needle) {
    if (!needle) return esc(text);
    var hay = text.toLowerCase();
    var out = '';
    var at = 0;
    for (;;) {
      var i = hay.indexOf(needle, at);
      if (i === -1) break;
      out += esc(text.slice(at, i)) + '<mark>' + esc(text.slice(i, i + needle.length)) + '</mark>';
      at = i + needle.length;
    }
    return out + esc(text.slice(at));
  }

  function token(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function looksLikeUrl(s) {
    return /^https?:\/\/\S+$/i.test(s);
  }

  // ------------------------------------------------------------------ boot

  Promise.all([
    fetch('data/index.json').then(function (r) { return r.json(); }),
    fetch('data/meta.json').then(function (r) { return r.json(); })
  ]).then(function (res) {
    state.index = res[0];
    state.meta = res[1];

    state.index.forEach(function (row) {
      row._hay = (row.name + ' ' + row.slug + ' ' + (row.snippet || '')).toLowerCase();
      row._name = row.name.toLowerCase();
    });
    // index.json arrives already in ranked order — the build sorts it and the
    // scores themselves are not published. Never re-sort it here.

    el.corpusLine.textContent = nf.format(state.meta.count) + ' benchmark cards · built ' + state.meta.built_at;
    el.footnote.textContent =
      'Counts are over all ' + nf.format(state.meta.count) + ' cards in the corpus. Cards with no ' +
      'value for a field are shown as “' + UNLABELLED + '” rather than dropped. Only publicly ' +
      'available card fields are published here, plus the capability category.';

    readHash();
    search(state.query);
    if (state.selected) select(state.selected);
    showTab(state.tab);
    if (state.tab !== 'stats') el.q.focus();
  }).catch(function (err) {
    el.results.innerHTML = '<div class="empty">Could not load the index.<br>' + esc(String(err)) + '</div>';
  });

  // ---------------------------------------------------------------- search

  /* Ranked substring search. 20k rows x ~250 chars scans in a few ms, so this
     stays a plain filter rather than a search-index dependency. */
  function search(raw) {
    var q = raw.trim().toLowerCase();
    state.query = q;

    if (!q) {
      state.hits = state.index.slice(0, MAX_HITS);
      renderResults(state.index.length, true);
      return;
    }

    var scored = [];
    for (var i = 0; i < state.index.length; i++) {
      var row = state.index[i];
      var score;
      if (row._name === q) score = 0;
      else if (row._name.indexOf(q) === 0) score = 1;
      else if (row.slug.indexOf(q) === 0) score = 2;
      else if (row._name.indexOf(q) !== -1) score = 3;
      else if (row._hay.indexOf(q) !== -1) score = 4;
      else continue;
      scored.push([score, row]);
    }
    // Relevance tier only. Array.sort is stable (ES2019), and `scored` was
    // built by walking state.index in order, so ties keep the ranked order.
    scored.sort(function (a, b) { return a[0] - b[0]; });

    state.hits = scored.slice(0, MAX_HITS).map(function (p) { return p[1]; });
    renderResults(scored.length, false);
  }

  function renderResults(total, browsing) {
    if (!total) {
      el.resultmeta.textContent = 'No benchmarks match “' + state.query + '”.';
      el.results.innerHTML = '<div class="empty">Nothing found. Try a shorter query.</div>';
      return;
    }

    el.resultmeta.textContent = browsing
      ? nf.format(total) + ' benchmarks — showing the top ' + nf.format(state.hits.length)
      : nf.format(total) + (total === 1 ? ' match' : ' matches') +
        (total > state.hits.length ? ' — showing the top ' + nf.format(state.hits.length) : '');

    var html = ['<ol>'];
    for (var i = 0; i < state.hits.length; i++) {
      var r = state.hits[i];
      var chips = [];
      if (r.category) chips.push(r.category);
      if (r.difficulty_level) chips.push(r.difficulty_level);
      if (r.year_of_publish) chips.push(r.year_of_publish);
      if (typeof r.number_of_questions === 'number') chips.push(nf.format(r.number_of_questions) + ' items');

      html.push(
        '<li><button class="hit" data-slug="' + esc(r.slug) + '"' +
        (state.selected === r.slug ? ' aria-current="true"' : '') + '>' +
        '<span class="hit-name">' + highlight(r.name, state.query) + '</span>' +
        (r.snippet ? '<p class="hit-snippet">' + highlight(r.snippet, state.query) + '…</p>' : '') +
        (chips.length ? '<div class="chips">' + chips.map(function (c) {
          return '<span class="chip">' + esc(c) + '</span>';
        }).join('') + '</div>' : '') +
        '</button></li>'
      );
    }
    html.push('</ol>');
    el.results.innerHTML = html.join('');
  }

  // ---------------------------------------------------------------- detail

  function select(slug) {
    var row = null;
    for (var i = 0; i < state.index.length; i++) {
      if (state.index[i].slug === slug) { row = state.index[i]; break; }
    }
    if (!row) {
      state.selected = null;
      el.detail.innerHTML = '<div class="empty">No benchmark with the id “' + esc(slug) + '”.</div>';
      return;
    }

    state.selected = slug;
    writeHash();

    Array.prototype.forEach.call(el.results.querySelectorAll('.hit'), function (b) {
      if (b.dataset.slug === slug) b.setAttribute('aria-current', 'true');
      else b.removeAttribute('aria-current');
    });

    loadShard(row.b).then(function (shard) {
      var card = shard[slug];
      if (!card) {
        el.detail.innerHTML = '<div class="empty">Card not found in shard.</div>';
        return;
      }
      renderDetail(slug, card);
    }).catch(function (err) {
      el.detail.innerHTML = '<div class="empty">Could not load this card.<br>' + esc(String(err)) + '</div>';
    });
  }

  function loadShard(bucket) {
    if (state.shards.has(bucket)) return Promise.resolve(state.shards.get(bucket));
    var name = 'data/cards/' + String(bucket).padStart(3, '0') + '.json';
    var p = fetch(name).then(function (r) {
      if (!r.ok) throw new Error(r.status + ' ' + name);
      return r.json();
    }).then(function (json) {
      state.shards.set(bucket, json);
      return json;
    });
    state.shards.set(bucket, p);        // de-dupe concurrent clicks
    return p;
  }

  // Years are identifiers, not quantities — never thousands-separated.
  var PLAIN_NUMBER = { year_of_publish: 1, year_of_last_update: 1, year: 1 };

  function renderValue(field, value) {
    if (typeof value === 'number') {
      var text = PLAIN_NUMBER[field] ? String(value) : nf.format(value);
      return '<dd class="num">' + esc(text) + '</dd>';
    }
    if (Array.isArray(value)) {
      if (!value.length) return '<dd>—</dd>';
      if (value.every(function (v) { return typeof v === 'string' || typeof v === 'number'; })) {
        return '<dd><div class="taglist">' + value.map(function (v) {
          return '<span class="chip">' + esc(v) + '</span>';
        }).join('') + '</div></dd>';
      }
      return '<dd>' + esc(JSON.stringify(value)) + '</dd>';
    }
    if (value && typeof value === 'object') {
      var rows = Object.keys(value).filter(function (k) {
        var v = value[k];
        return !(v == null || v === '' || (Array.isArray(v) && !v.length));
      }).map(function (k) {
        var v = value[k];
        var text = Array.isArray(v) ? v.join(', ') : String(v);
        return '<li><span>' + esc(k.replace(/_/g, ' ')) + ':</span> ' + esc(text) + '</li>';
      });
      if (!rows.length) return '<dd>—</dd>';
      return '<dd><ul class="sub">' + rows.join('') + '</ul></dd>';
    }
    var s = String(value);
    if (looksLikeUrl(s)) {
      return '<dd><a href="' + esc(s) + '" target="_blank" rel="noopener noreferrer">' + esc(s) + '</a></dd>';
    }
    return '<dd>' + esc(s) + '</dd>';
  }

  function renderDetail(slug, card) {
    var labels = state.meta.labels;
    var html = [
      '<div class="detail-head">',
      '<h2>' + esc(card.name || slug) + '</h2>',
      '<p class="detail-slug">' + esc(slug) + '.json</p>',
      '</div>'
    ];

    state.meta.groups.forEach(function (group) {
      var fields = group.fields.filter(function (f) {
        return f !== 'name' && card[f] !== undefined;
      });
      if (!fields.length) return;
      html.push('<section class="group"><h3>' + esc(group.title) + '</h3><dl class="fields">');
      fields.forEach(function (f) {
        html.push('<dt>' + esc(labels[f] || f) + '</dt>' + renderValue(f, card[f]));
      });
      html.push('</dl></section>');
    });

    el.detail.innerHTML = html.join('');
  }

  // ----------------------------------------------------------------- stats

  /* Counts one field across the corpus. `fold` collapses every value below that
     fraction of the corpus into a single "Other" row — a handful of cards carry
     drifted values (`vision|multimodal`, `text|code`) that would otherwise each
     get a row of their own. */
  function tally(field, fold) {
    var counts = new Map();
    for (var i = 0; i < state.index.length; i++) {
      var v = state.index[i][field];
      var key = (v === undefined || v === null || v === '') ? UNLABELLED : String(v);
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    var rows = Array.from(counts, function (e) { return { label: e[0], count: e[1] }; });

    if (fold) {
      var cut = fold * state.meta.count;
      var tail = rows.filter(function (r) { return r.count < cut && r.label !== UNLABELLED; });
      if (tail.length > 1) {
        rows = rows.filter(function (r) { return tail.indexOf(r) === -1; });
        rows.push({
          label: OTHER,
          folded: tail.length,
          count: tail.reduce(function (sum, r) { return sum + r.count; }, 0)
        });
      }
    }

    // Aggregate rows sink to the bottom; everything else is largest first.
    var sink = [OTHER, UNLABELLED];
    rows.sort(function (a, b) {
      var ra = sink.indexOf(a.label), rb = sink.indexOf(b.label);
      if (ra !== rb) return (ra === -1 ? -1 : ra) - (rb === -1 ? -1 : rb);
      return b.count - a.count;
    });
    return rows;
  }

  /* One sentence per bar chart: how many real values, plus an honest account of
     whatever was folded away or is missing. */
  function summarise(rows, noun) {
    var other = rows.filter(function (r) { return r.label === OTHER; })[0];
    var un = rows.filter(function (r) { return r.label === UNLABELLED; })[0];
    var real = rows.filter(function (r) { return r.label !== OTHER && r.label !== UNLABELLED; });
    var text = real.length + ' ' + noun + ' cover ' +
      nf.format(real.reduce(function (s, r) { return s + r.count; }, 0)) + ' of ' +
      nf.format(state.meta.count) + ' cards.';
    if (other) {
      text += ' Other folds together ' + other.folded + ' drifted values below ' +
        (FOLD_BELOW * 100).toFixed(1) + '% of the corpus (' + nf.format(other.count) + ' cards).';
    }
    if (un) text += ' ' + nf.format(un.count) + ' cards carry no value.';
    return text;
  }

  function baseOptions() {
    return {
      chart: {
        fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
        background: 'transparent',
        toolbar: { show: false },
        animations: { enabled: true, speed: 260 },
        parentHeightOffset: 0
      },
      grid: {
        borderColor: token('--rule'),
        strokeDashArray: 0,
        padding: { top: 0, right: 8, bottom: 0, left: 4 }
      },
      tooltip: { theme: 'none', style: { fontSize: '13px' } },
      legend: { show: false },
      states: { active: { filter: { type: 'none' } } }
    };
  }

  function axisStyle() {
    return { colors: token('--text-muted'), fontSize: '12px' };
  }

  /* Horizontal bars: one series, one hue. Aggregate rows (Other, Unlabelled)
     take the de-emphasis gray so they never read as a value in their own right;
     both always carry a direct label, which is the relief that gray needs. */
  function barChart(mountId, tableId, rows, noteId, noun) {
    var max = rows.reduce(function (m, r) { return Math.max(m, r.count); }, 0);
    var band = 34;

    document.getElementById(noteId).textContent = summarise(rows, noun);
    renderTable(tableId, ['Value', 'Benchmarks', 'Share'], rows.map(function (r) {
      return [r.label, nf.format(r.count), (100 * r.count / state.meta.count).toFixed(1) + '%'];
    }));

    var options = Object.assign(baseOptions(), {
      series: [{ name: 'Benchmarks', data: rows.map(function (r) { return r.count; }) }],
      chart: Object.assign(baseOptions().chart, { type: 'bar', height: rows.length * band + 56 }),
      colors: rows.map(function (r) {
        var aggregate = r.label === OTHER || r.label === UNLABELLED;
        return aggregate ? token('--series-dim') : token('--series-1');
      }),
      plotOptions: {
        bar: {
          horizontal: true,
          distributed: true,
          barHeight: '56%',
          borderRadius: 4,
          borderRadiusApplication: 'end',
          dataLabels: { position: 'top' }
        }
      },
      dataLabels: {
        enabled: true,
        textAnchor: 'start',
        offsetX: 10,
        formatter: function (v) { return nf.format(v); },
        style: { fontSize: '12px', fontWeight: 400, colors: [token('--text-secondary')] }
      },
      xaxis: {
        categories: rows.map(function (r) { return r.label; }),
        max: Math.ceil(max * 1.16),
        labels: { show: false },
        axisBorder: { show: false },
        axisTicks: { show: false }
      },
      yaxis: { labels: { style: axisStyle(), maxWidth: 380 } },
      tooltip: Object.assign(baseOptions().tooltip, {
        y: {
          formatter: function (v) {
            return nf.format(v) + ' benchmarks (' + (100 * v / state.meta.count).toFixed(1) + '%)';
          },
          title: { formatter: function () { return ''; } }
        }
      })
    });

    return mount(mountId, options);
  }

  function yearChart() {
    var counts = new Map();
    var missing = 0;
    for (var i = 0; i < state.index.length; i++) {
      var y = state.index[i].year_of_publish;
      if (typeof y !== 'number') { missing++; continue; }
      counts.set(y, (counts.get(y) || 0) + 1);
    }
    var years = Array.from(counts.keys()).sort(function (a, b) { return a - b; });
    var first = years[0];
    var last = years[years.length - 1];
    var data = [];
    for (var y2 = first; y2 <= last; y2++) data.push([y2, counts.get(y2) || 0]);

    var early = data.filter(function (p) { return p[0] < 1990; })
                    .reduce(function (s, p) { return s + p[1]; }, 0);

    document.getElementById('note-year').textContent =
      nf.format(state.meta.count - missing) + ' cards carry a publication year (' + nf.format(missing) +
      ' do not). The corpus spans ' + first + '–' + last + '; the view opens at 1990, and the ' +
      nf.format(early) + ' earlier cards — mostly psychometric instruments — are reachable by ' +
      'panning left. ' + last + ' is a partial year.';

    renderTable('tbl-year', ['Year', 'Benchmarks'], data.slice().reverse().map(function (p) {
      return [String(p[0]), nf.format(p[1])];
    }));

    var options = Object.assign(baseOptions(), {
      series: [{ name: 'Benchmarks', data: data }],
      chart: Object.assign(baseOptions().chart, {
        type: 'area',
        height: 300,
        zoom: { enabled: true, type: 'x', autoScaleYaxis: true },
        toolbar: {
          show: true,
          offsetY: -4,
          tools: { download: false, selection: true, zoom: true, zoomin: true, zoomout: true, pan: true, reset: true }
        }
      }),
      colors: [token('--series-1')],
      stroke: { curve: 'straight', width: 2, lineCap: 'round' },
      fill: { type: 'solid', opacity: 0.10 },
      dataLabels: { enabled: false },
      markers: { size: 0, strokeWidth: 2, strokeColors: token('--page'), hover: { size: 5 } },
      xaxis: {
        type: 'numeric',
        min: 1990,
        max: last,
        tickAmount: 6,
        decimalsInFloat: 0,
        labels: { style: axisStyle(), formatter: function (v) { return String(Math.round(v)); } },
        axisBorder: { color: token('--baseline') },
        axisTicks: { color: token('--baseline') },
        crosshairs: { show: true, stroke: { color: token('--baseline'), width: 1, dashArray: 0 } },
        tooltip: { enabled: false }
      },
      yaxis: {
        labels: { style: axisStyle(), formatter: function (v) { return nf.format(Math.round(v)); } },
        axisBorder: { show: false }
      },
      tooltip: Object.assign(baseOptions().tooltip, {
        x: { formatter: function (v) { return String(Math.round(v)); } },
        y: { formatter: function (v) { return nf.format(v) + ' benchmarks'; } }
      })
    });

    return mount('chart-year', options);
  }

  /* Capability x modality: where each capability is actually tested, and which
     combinations nothing covers. */
  function heatChart() {
    // Rows are the named capabilities only: the folded tail and any unlabelled
    // cards would each contribute a near-empty row and inflate the gap count.
    var cats = tally('capability_category', FOLD_BELOW)
      .filter(function (r) { return r.label !== UNLABELLED && r.label !== OTHER; })
      .map(function (r) { return r.label; });

    // Same folding as the modality bars, so the two figures agree.
    var mods = tally('category', FOLD_BELOW).map(function (r) { return r.label; });
    var named = mods.filter(function (m) { return m !== OTHER && m !== UNLABELLED; });

    function modalityOf(row) {
      var v = row.category;
      if (v === undefined || v === null || v === '') return null;
      v = String(v);
      return named.indexOf(v) === -1 ? OTHER : v;
    }

    var grid = new Map();          // capability -> modality -> count
    var covered = 0;
    for (var i = 0; i < state.index.length; i++) {
      var row = state.index[i];
      var mod = modalityOf(row);
      if (!mod || cats.indexOf(row.capability_category) === -1) continue;
      covered++;
      var byMod = grid.get(row.capability_category);
      if (!byMod) { byMod = new Map(); grid.set(row.capability_category, byMod); }
      byMod.set(mod, (byMod.get(mod) || 0) + 1);
    }

    function cell(cat, mod) {
      var byMod = grid.get(cat);
      return (byMod && byMod.get(mod)) || 0;
    }

    // The first series renders at the bottom, so reverse to put the largest on top.
    var series = cats.slice().reverse().map(function (cat) {
      return {
        name: cat,
        data: mods.map(function (mod) { return { x: mod, y: cell(cat, mod) }; })
      };
    });

    var empties = 0;
    cats.forEach(function (cat) {
      mods.forEach(function (mod) { if (!cell(cat, mod)) empties++; });
    });

    document.getElementById('note-heat').textContent =
      'Where each capability is currently tested. ' + nf.format(covered) + ' cards across ' +
      cats.length + ' capability categories × ' + mods.length + ' modalities; ' + empties + ' of ' +
      (cats.length * mods.length) + ' cells are empty, and those are the gaps.';

    renderTable('tbl-heat',
      ['Capability category'].concat(mods),
      cats.map(function (cat) {
        return [cat].concat(mods.map(function (mod) { return nf.format(cell(cat, mod)); }));
      }));

    var options = Object.assign(baseOptions(), {
      series: series,
      chart: Object.assign(baseOptions().chart, { type: 'heatmap', height: cats.length * 34 + 84 }),
      dataLabels: { enabled: false },
      stroke: { show: true, width: 2, colors: [token('--page')] },
      plotOptions: {
        heatmap: {
          radius: 3,
          enableShades: false,
          colorScale: {
            ranges: [
              { from: 0, to: 0, color: token('--seq-0'), name: '0' },
              { from: 1, to: 24, color: token('--seq-1'), name: '1–24' },
              { from: 25, to: 99, color: token('--seq-2'), name: '25–99' },
              { from: 100, to: 299, color: token('--seq-3'), name: '100–299' },
              { from: 300, to: 899, color: token('--seq-4'), name: '300–899' },
              { from: 900, to: 9999999, color: token('--seq-6'), name: '900+' }
            ]
          }
        }
      },
      legend: {
        show: true,
        position: 'top',
        horizontalAlign: 'left',
        offsetX: -6,
        fontSize: '12px',
        labels: { colors: token('--text-muted') },
        markers: { size: 6, offsetX: -3, strokeColor: token('--rule'), strokeWidth: 1 },
        itemMargin: { horizontal: 8, vertical: 4 }
      },
      xaxis: {
        type: 'category',
        labels: { style: axisStyle() },
        axisBorder: { show: false },
        axisTicks: { show: false },
        tooltip: { enabled: false }
      },
      yaxis: { labels: { style: axisStyle(), maxWidth: 380 } },
      tooltip: Object.assign(baseOptions().tooltip, {
        y: { formatter: function (v) { return nf.format(v) + ' benchmarks'; } }
      })
    });

    return mount('chart-heat', options);
  }

  function mount(id, options) {
    var node = document.getElementById(id);
    node.innerHTML = '';
    var chart = new ApexCharts(node, options);
    chart.render();
    return chart;
  }

  /* Every chart ships a table twin — the WCAG-clean way to read any value that
     is otherwise carried by colour or by a tooltip. */
  function renderTable(id, head, rows) {
    var html = ['<table><thead><tr>'];
    head.forEach(function (h, i) {
      html.push('<th' + (i ? ' class="num"' : '') + '>' + esc(h) + '</th>');
    });
    html.push('</tr></thead><tbody>');
    rows.forEach(function (r) {
      html.push('<tr>');
      r.forEach(function (c, i) {
        html.push('<td' + (i ? ' class="num"' : '') + '>' + esc(c) + '</td>');
      });
      html.push('</tr>');
    });
    html.push('</tbody></table>');
    document.getElementById(id).innerHTML = html.join('');
  }

  /* Charts are built the first time the tab is shown — ApexCharts measures a
     hidden container as zero-width and would render a collapsed plot. */
  function buildCharts() {
    state.charts.forEach(function (c) { c.destroy(); });
    state.charts = [
      yearChart(),
      barChart('chart-modality', 'tbl-modality', tally('category', FOLD_BELOW),
        'note-modality', 'input modalities'),
      barChart('chart-capability', 'tbl-capability', tally('capability_category', FOLD_BELOW),
        'note-capability', 'capability categories'),
      heatChart()
    ];
    state.chartsBuilt = true;
  }

  // ------------------------------------------------------------ url + tabs

  function readHash() {
    var h = location.hash.replace(/^#/, '');
    if (!h) return;
    var explicitTab = false;
    h.split('&').forEach(function (pair) {
      var i = pair.indexOf('=');
      if (i === -1) return;
      var k = pair.slice(0, i);
      var v = decodeURIComponent(pair.slice(i + 1));
      if (k === 'q') { state.query = v; el.q.value = v; }
      if (k === 'b') { state.selected = v; }
      if (k === 'tab') { state.tab = v; explicitTab = true; }
    });
    // Statistics is the landing view, but a link carrying a query or a card is
    // a link into Explore. An explicit tab= always wins.
    if (!explicitTab && (state.query || state.selected)) state.tab = 'explore';
  }

  function writeHash() {
    var parts = [];
    if (state.tab !== 'stats') parts.push('tab=' + state.tab);
    if (state.query) parts.push('q=' + encodeURIComponent(state.query));
    if (state.selected) parts.push('b=' + encodeURIComponent(state.selected));
    history.replaceState(null, '', parts.length ? '#' + parts.join('&') : location.pathname);
  }

  function showTab(which) {
    var stats = which === 'stats';
    state.tab = stats ? 'stats' : 'explore';
    writeHash();
    el.tabExplore.setAttribute('aria-selected', String(!stats));
    el.tabStats.setAttribute('aria-selected', String(stats));
    el.panelExplore.hidden = stats;
    el.panelStats.hidden = !stats;
    if (stats && !state.chartsBuilt && state.meta) buildCharts();
  }

  // -------------------------------------------------------------- wiring

  var debounce;
  el.q.addEventListener('input', function () {
    clearTimeout(debounce);
    debounce = setTimeout(function () {
      search(el.q.value);
      writeHash();
    }, 90);
  });

  el.q.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { el.q.value = ''; search(''); writeHash(); }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      var firstHit = el.results.querySelector('.hit');
      if (firstHit) firstHit.focus();
    }
  });

  el.results.addEventListener('click', function (e) {
    var btn = e.target.closest('.hit');
    if (btn) select(btn.dataset.slug);
  });

  el.results.addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    var btn = e.target.closest('.hit');
    if (!btn) return;
    e.preventDefault();
    var li = btn.parentElement;
    var next = e.key === 'ArrowDown' ? li.nextElementSibling : li.previousElementSibling;
    if (next) next.querySelector('.hit').focus();
    else if (e.key === 'ArrowUp') el.q.focus();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== el.q) {
      e.preventDefault();
      el.q.focus();
      el.q.select();
    }
  });

  el.tabExplore.addEventListener('click', function () { showTab('explore'); });
  el.tabStats.addEventListener('click', function () { showTab('stats'); });

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-table]');
    if (!btn) return;
    var wrap = document.getElementById(btn.dataset.table);
    var open = wrap.hidden;
    wrap.hidden = !open;
    btn.setAttribute('aria-expanded', String(open));
    btn.textContent = open ? 'Hide table' : 'Show table';
  });
})();
