/* T 细胞多组学数据库 · 前端逻辑（纯静态，只读 JSON，无后端依赖）
   页面通过 <html data-base="." data-page="..."> 与 #dsh-i18n 注入的文案表工作。 */
(function () {
  'use strict';
  var HTML = document.documentElement;
  var BASE = HTML.dataset.base || '.';
  var PAGE = HTML.dataset.page || 'home';
  var I18N = JSON.parse(document.getElementById('dsh-i18n').textContent);
  var MANIFEST = JSON.parse(document.getElementById('dsh-manifest').textContent);
  var LANG_KEY = 'dsh-lang';
  var MODKEYS = MANIFEST.mod_keys || ['scRNA', 'bulkRNA', 'scATAC', 'bulkATAC', 'scTCR', 'bulkTCR', 'methylation', 'CRISPR-screen'];
  var MODFIELD = { scRNA: 'rna', bulkRNA: 'bulkRNA', scATAC: 'atac', bulkATAC: 'bulkATAC', scTCR: 'tcr', bulkTCR: 'bulkTCR', methylation: 'methyl', 'CRISPR-screen': 'screen' };
  var MODCOLOR = { scRNA: 'g', scATAC: 'g', scTCR: 'g', bulkRNA: 'o', bulkATAC: 'o', bulkTCR: 'o', methylation: 'n', 'CRISPR-screen': 'n' };
  var IGORDER = ['COMPLETE_VERIFIED', 'UNVERIFIED', 'TRUNCATED', 'PARTIAL_BROKEN', 'CORRUPT', 'FAILED_ALL', 'NO_DATA'];
  var THORDER = ['CAR-T', 'CAR-T+内源T(混合)', '内源T', 'TCR-T/工程化T', '非T细胞/对照', '未明确'];
  var lang = new URLSearchParams(location.search).get('lang') || localStorage.getItem(LANG_KEY);
  if (lang !== 'zh' && lang !== 'en') lang = (navigator.language || '').toLowerCase().indexOf('zh') === 0 ? 'zh' : 'en';

  /* ---------------- 通用工具 ---------------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function url(p) { return BASE + '/' + String(p).replace(/^\.?\//, ''); }
  function catUrl(id) { return url((MANIFEST.page_cat && MANIFEST.page_cat[id]) || ('pages/' + id + '.html')); }
  function t(key) { var v = I18N[key]; if (v == null) return key; return v[lang] != null ? v[lang] : (v.zh || key); }
  function tmap(v) { return (v && (v[lang] != null ? v[lang] : v.zh)) || v || ''; }
  function num(n) { return (Number(n) || 0).toLocaleString(lang === 'zh' ? 'zh-CN' : 'en-US'); }
  function gb(bytes) {
    if (!bytes) return '0';
    var g = bytes / 1024 / 1024 / 1024;
    return g >= 1024 ? (g / 1024).toFixed(2) + ' TB' : (g >= 10 ? g.toFixed(1) : g.toFixed(2)) + ' GB';
  }
  function th(x) { return I18NTherapy[x] ? I18NTherapy[x][lang] : x; }
  var I18NTherapy = MANIFEST.th_label || {}, I18NTct = MANIFEST.tct_label || {},
      I18NCat = MANIFEST.cat_label || {}, I18NMod = MANIFEST.mod_label || {}, I18NIg = MANIFEST.ig_label || {};
  function applyLabels(m) {
    I18NTherapy = m.th_label || I18NTherapy; I18NTct = m.tct_label || I18NTct;
    I18NCat = m.cat_label || I18NCat; I18NMod = m.mod_label || I18NMod; I18NIg = m.ig_label || I18NIg;
  }
  function modChips(r) {
    var out = MODKEYS.filter(function (m) { return r[MODFIELD[m]]; });
    if (!out.length) return '<span class="st-unk">' + esc(t('na')) + '</span>';
    return out.map(function (m) { return '<span class="b ' + (MODCOLOR[m] || 'o') + '">' + m + '</span>'; }).join('');
  }
  var IG_ICON = { COMPLETE_VERIFIED: '✅', UNVERIFIED: '◻︎', TRUNCATED: '⚠️', PARTIAL_BROKEN: '⚠️',
    CORRUPT: '❌', FAILED_ALL: '❌', NO_DATA: '❌' };
  var IG_SHORT = { COMPLETE_VERIFIED: { zh: '已验证', en: 'Verified' }, UNVERIFIED: { zh: '未对照', en: 'Unchecked' },
    TRUNCATED: { zh: '截断', en: 'Truncated' }, PARTIAL_BROKEN: { zh: '部分损坏', en: 'Partly broken' },
    CORRUPT: { zh: '损坏', en: 'Corrupt' }, FAILED_ALL: { zh: '全部失败', en: 'All failed' },
    NO_DATA: { zh: '无数据', en: 'No data' } };
  function igLabel(k) { return (IG_ICON[k] || '') + ' ' + ((IG_SHORT[k] || {})[lang] || k); }
  function igCell(r) {
    return '<span class="st-' + r.igc + '">' + esc(igLabel(r.ig)) + '</span>';
  }
  function disChips(r, forceCat) {
    return (r.dis || []).map(function (d) {
      var nm = I18NCat[d] ? I18NCat[d][lang] : d;
      if (forceCat && d === forceCat) return '<span class="b q">' + esc(nm) + '</span>';
      return '<a class="b p" href="' + catUrl(d) + '">' + esc(nm) + '</a>';
    }).join('') || '<span class="st-unk">—</span>';
  }
  function tctChips(r) {
    var arr = (r.tct || []).filter(function (x) { return x && x !== '未标注'; });
    if (!arr.length) return '<span class="st-unk">' + esc(I18NTct['未标注'] ? I18NTct['未标注'][lang] : '—') + '</span>';
    return arr.map(function (x) {
      var nm = I18NTct[x] ? I18NTct[x][lang] : x;
      return '<span class="b">' + esc(nm) + '</span>';
    }).join('');
  }
  function journalCell(r) {
    if (!r.j) return '<span class="st-unk">—</span>';
    var s = esc(r.j) + (r.y ? ' (' + r.y + ')' : '');
    if (r.pmid) s += ' · <a href="https://pubmed.ncbi.nlm.nih.gov/' + encodeURIComponent(r.pmid) + '/" target="_blank" rel="noopener">PMID</a>';
    return s;
  }
  function gseCell(r) {
    return '<a href="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=' + encodeURIComponent(r.acc) +
      '" target="_blank" rel="noopener" title="' + esc(t('geo_link')) + '"><b>' + esc(r.acc) + '</b></a>';
  }

  /* ---------------- 数据加载 ---------------- */
  var cache = {};
  var DS = null;   // 已解析的数据集数组（语言切换时复用，避免重新请求）
  function load(name) {
    if (cache[name]) return cache[name];
    var INLINE = window.DSH_INLINE || {};
    if (INLINE[name]) { cache[name] = Promise.resolve(INLINE[name]); return cache[name]; }
    cache[name] = fetch(url('data/' + name + '.json')).then(function (r) {
      if (!r.ok) throw new Error(name + ': HTTP ' + r.status);
      return r.json();
    });
    return cache[name];
  }

  /* ---------------- 顶栏 ---------------- */
  function applyI18n(scope) {
    (scope || document).querySelectorAll('[data-i18n]').forEach(function (el) {
      var v = I18N[el.dataset.i18n];
      if (v && v[lang] != null) el.textContent = v[lang];
    });
    (scope || document).querySelectorAll('[data-i18n-title]').forEach(function (el) {
      var v = I18N[el.dataset.i18nTitle];
      if (v && v[lang] != null) el.title = v[lang];
    });
    (scope || document).querySelectorAll('[data-i18n-ph]').forEach(function (el) {
      var v = I18N[el.dataset.i18nPh];
      if (v && v[lang] != null) el.placeholder = v[lang];
    });
  }
  function renderTop() {
    applyI18n();
    var ph = document.getElementById('q-global');
    if (ph) ph.placeholder = t('search_ph');
    document.querySelectorAll('nav.main a[data-nav]').forEach(function (a) {
      a.classList.toggle('on', a.dataset.nav === PAGE);
    });
    document.querySelectorAll('.langsw button').forEach(function (b) {
      b.classList.toggle('on', b.dataset.lang === lang);
    });
    var tz = HTML.dataset.titleZh, te = HTML.dataset.titleEn;
    if (tz && te) document.title = lang === 'zh' ? tz : te;
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  }

  function setLang(l) {
    if (l !== 'zh' && l !== 'en') return;
    lang = l;
    localStorage.setItem(LANG_KEY, l);
    try {
      var u = new URL(location.href);
      u.searchParams.set('lang', l);
      history.replaceState(null, '', u);
    } catch (e) { }
    renderTop();
    document.dispatchEvent(new CustomEvent('dsh:lang', { detail: { lang: l } }));
  }

  /* ---------------- 全局搜索 ---------------- */
  function initSearch() {
    var box = document.getElementById('q-global');
    if (!box) return;
    var res = document.getElementById('q-global-res');
    var idx = null, cats = null, sel = -1, items = [];
    Promise.all([load('search-index'), load('categories')]).then(function (a) { idx = a[0]; cats = a[1]; });
    function close() { res.classList.remove('show'); sel = -1; }
    function match(q) {
      var ql = q.toLowerCase(), out = [];
      (cats || []).forEach(function (c) {
        var zh = c.id.toLowerCase(), en = (c.en || '').toLowerCase();
        if (zh.indexOf(ql) >= 0 || en.indexOf(ql) >= 0) {
          out.push({ kind: 'cat', href: catUrl(c.id),
            title: (I18NCat[c.id] ? I18NCat[c.id][lang] : c.id), meta: c.n + ' ' + t('datasets') });
        }
      });
      (idx || []).forEach(function (r) {
        var hay = (r.a + ' ' + r.t + ' ' + r.d + ' ' + r.th + ' ' + r.c + ' ' + r.j + ' ' + r.au + ' ' + r.ct).toLowerCase();
        if (hay.indexOf(ql) >= 0) out.push({ kind: 'ds', href: url('catalog.html') + '#' + r.a, acc: r.a, title: r.t || r.a, meta: r.a + ' · ' + r.mo + (r.y ? ' · ' + r.y : '') });
      });
      return out.slice(0, 24);
    }
    function paint() {
      if (!items.length) { res.innerHTML = '<div class="empty">' + esc(t('search_none')) + '</div>'; res.classList.add('show'); return; }
      res.innerHTML = items.map(function (it, i) {
        return '<a class="it' + (i === sel ? ' sel' : '') + '" href="' + it.href + '">' +
          '<b>' + esc(it.kind === 'cat' ? '◆ ' + it.title : it.acc) + '</b>' +
          '<span class="tt">' + esc(it.kind === 'cat' ? it.meta : it.title) + '</span>' +
          '<span class="mm">' + esc(it.kind === 'cat' ? t('open_category') : it.meta) + '</span></a>';
      }).join('') + '<a class="it all" href="' + url('catalog.html') + '?q=' + encodeURIComponent(box.value.trim()) + '">' +
        esc(t('search_enter')) + ' →</a>';
      res.classList.add('show');
    }
    box.addEventListener('input', function () {
      var q = box.value.trim();
      if (q.length < 1) { close(); return; }
      items = match(q); sel = -1; paint();
    });
    box.addEventListener('focus', function () { if (box.value.trim()) { items = match(box.value.trim()); paint(); } });
    box.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { close(); return; }
      if (e.key === 'Enter') {
        var q = box.value.trim();
        if (sel >= 0 && items[sel]) { location.href = items[sel].href; return; }
        if (q) location.href = url('catalog.html') + '?q=' + encodeURIComponent(q);
        return;
      }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (!items.length) return;
        sel = e.key === 'ArrowDown' ? Math.min(sel + 1, items.length - 1) : Math.max(sel - 1, 0);
        paint();
      }
    });
    document.addEventListener('click', function (e) { if (!res.contains(e.target) && e.target !== box) close(); });
    document.addEventListener('dsh:lang', function () { if (res.classList.contains('show') && box.value.trim()) { items = match(box.value.trim()); paint(); } });
  }

  /* ---------------- 首页：疾病类别卡片 ---------------- */
  function renderHome() {
    var host = document.getElementById('cat-grid');
    if (!host) return;
    load('categories').then(function (cats) {
      var f = HTML.dataset.filter || 'all';
      host.innerHTML = cats.map(function (c) {
        var meta = MANIFEST.cat_meta[c.id] || {};
        var name = I18NCat[c.id] ? I18NCat[c.id][lang] : c.id;
        var desc = meta['desc_' + lang] || (meta.desc_zh || '');
        var mods = MODKEYS.filter(function (m) { return c.mods[m]; })
          .map(function (m) { return '<span class="b ' + (MODCOLOR[m] || 'o') + '">' + m + ' ' + c.mods[m] + '</span>'; }).join('');
        var color = meta.color || '#1a7f5a';
        var ths = Object.keys(c.ths || {}).sort(function (a, b) { return c.ths[b] - c.ths[a]; }).slice(0, 2)
          .map(function (k) { return '<span class="b n">' + esc(I18NTherapy[k] ? I18NTherapy[k][lang] : k) + ' ' + c.ths[k] + '</span>'; }).join('');
        var stat = fil(c, f);
        if (!stat) return '';
        return '<a class="cat" href="' + catUrl(c.id) + '">' +
          '<div class="hd"><div class="tile" style="color:' + color + '">' + svgUse(meta.icon) + '</div>' +
          '<div class="cn"><h3>' + esc(name) + '</h3>' +
          '<div class="en">' + esc(meta['name_' + (lang === 'zh' ? 'en' : 'zh')] || '') + '</div></div></div>' +
          '<p class="cdsc">' + esc(desc) + '</p>' +
          '<div class="nums">' +
          '<span><b>' + num(c.n) + '</b><i>' + t('datasets') + '</i></span>' +
          '<span><b>' + num(c.n_samples) + '</b><i>' + t('samples') + '</i></span>' +
          '<span class="acc"><b>' + num(c.n_matched) + '</b><i>' + t('stat_matched') + '</i></span>' +
          '<span class="acc"><b>' + num(c.n_verified) + '</b><i>' + t('stat_verified') + '</i></span>' +
          '<span><b>' + num(c.n_pub) + '</b><i>' + t('stat_pub') + '</i></span>' +
          '<span><b>' + c.y0 + '–' + c.y1 + '</b><i>' + t('years') + '</i></span>' +
          '</div>' +
          '<div class="tags">' + mods + ths + '</div>' +
          '<div class="go">' + esc(t('open_category')) + ' <span>→</span></div></a>';
      }).join('');
    })['catch'](function (e) { host.innerHTML = '<div class="err">' + esc(e.message) + '</div>'; });
  }
  function svgUse(icon) { return '<svg aria-hidden="true"><use href="#ic-' + icon + '"></use></svg>'; }
  function fil(c, f) {
    if (f === 'verified' && !c.n_verified) return false;
    if (f === 'matched' && !c.n_matched) return false;
    return true;
  }

  /* ---------------- 数据集表格（目录页 / 类别页共用） ---------------- */
  function buildTable(rows, opts) {
    opts = opts || {};
    var forceCat = opts.forceCat || null;
    var F = {}, q0 = opts.q || '', onlyM = false, onlyV = false, sortKey = opts.sort || 'acc', sortDir = 1;
    var host = document.getElementById(opts.hostId);
    host.innerHTML =
      (MANIFEST.dl_stats ? '<div class="dlnote" style="margin:0 0 10px">' + esc(t('dl_tip')) +
        ' <span class="dim">(' + num(MANIFEST.dl_stats.verified) + ' ' + esc(t('dl_verified')) + ' / ' +
        num(MANIFEST.dl_stats.n) + ' ' + esc(t('dl_checked')) + ' · ' + num(MANIFEST.dl_stats.n_files) + ' ' +
        esc(t('files')) + ' · ' + gb(MANIFEST.dl_stats.bytes) + ')</span></div>' : '') +
      '<div class="filters">' +
      '<div class="frow"><input class="q" id="f-q" value="' + esc(q0) + '" placeholder="' + esc(t('search_ph')) +
      '" data-i18n-ph="search_ph">' +
      '<span class="chip" id="f-rst" data-i18n="reset">' + esc(t('reset')) + '</span>' +
      '<span class="chip" id="f-mt" data-i18n="only_matched">' + esc(t('only_matched')) + '</span>' +
      '<span class="chip" id="f-vr" data-i18n="only_verified">' + esc(t('only_verified')) + '</span></div>' +
      chipRow(t('filter'), 'th', THORDER.filter(function (x) { return rows.some(function (r) { return r.th === x; }); }),
        function (x) { return (I18NTherapy[x] ? I18NTherapy[x][lang] : x) + ' (' + rows.filter(function (r) { return r.th === x; }).length + ')'; }) +
      chipRow(t('f_disease'), 'dis', uniq(rows, 'dis'), function (d) { return (I18NCat[d] ? I18NCat[d][lang] : d) + ' (' + rows.filter(function (r) { return r.dis.indexOf(d) >= 0; }).length + ')'; }) +
      (forceCat ? '' : '') +
      chipRow(t('f_tct'), 'tct', uniq(rows, 'tct'), function (x) { return (I18NTct[x] ? I18NTct[x][lang] : x) + ' (' + rows.filter(function (r) { return r.tct.indexOf(x) >= 0; }).length + ')'; }) +
      chipRow(t('f_omics'), 'mo', MODKEYS.filter(function (m) { return rows.some(function (r) { return r[MODFIELD[m]]; }); }),
        function (m) { return m + ' (' + rows.filter(function (r) { return r[MODFIELD[m]]; }).length + ')'; }) +
      chipRow(t('f_integrity'), 'ig', IGORDER.filter(function (k) { return rows.some(function (r) { return r.ig === k; }); }),
        function (k) { return igLabel(k) + ' (' + rows.filter(function (r) { return r.ig === k; }).length + ')'; }) +
      '</div><div id="cnt"></div>' +
      '<div class="tblwrap"><table id="f-tbl"><thead><tr>' +
      '<th class="selcol" data-nosort="1"><input type="checkbox" id="dl-all" title="' + esc(t('col_sel')) + '"></th>' +
      t('cols').map(function (h, i) {
        var keys = ['acc', 'title', 'th', 'dis', 'tct', 'mo', 'journal', 'au', 'ct', 'ns', 'size', 'ig'];
        var ik = ['col_acc','col_title','col_th','col_dis','col_tct','col_mo','col_journal','col_au','col_ct','col_ns','col_size','col_ig'][i];
        return '<th data-sort="' + keys[i] + '" data-i18n="' + ik + '" title="' + esc(lang === 'zh' ? '点击排序' : 'Click to sort') + '">' + esc(h) + '</th>';
      }).join('') +
      '<th></th></tr></thead><tbody></tbody></table></div>' +
      '<div class="legend"><span>' + esc(t('cols')[11]) + '</span>' +
      ['✅', '◻︎', '⚠️', '❌'].map(function (s) { return '<span>' + s + '</span>'; }).join('') + '</div>';

    function chipRow(label, key, vals, fmt) {
      var lk = { th: 'f_therapy', dis: 'f_disease', tct: 'f_tct', mo: 'f_omics', ig: 'f_integrity' }[key];
      return '<div class="frow"><span class="flabel"' + (lk ? ' data-i18n="' + lk + '"' : '') + '>' + esc(label) + '</span>' +
        '<span class="chip" data-k="' + key + '" data-v="__all" data-i18n="all">' + esc(t('all')) + '</span>' +
        vals.map(function (v) { return '<span class="chip" data-k="' + key + '" data-v="' + esc(v) + '">' + esc(fmt(v)) + '</span>'; }).join('') + '</div>';
    }
    function uniq(rows, field) {
      var s = [];
      rows.forEach(function (r) { (r[field] || []).forEach(function (v) { if (v && s.indexOf(v) < 0) s.push(v); }); });
      return s;
    }
    var KEYFN = {
      acc: function (r) { return r.acc; }, title: function (r) { return (r.title || '').toLowerCase(); },
      th: function (r) { return r.th; }, dis: function (r) { return r.dis.join(); },
      tct: function (r) { return r.tct.join(); }, mo: function (r) { return r.nmod; },
      journal: function (r) { return (r.j || '') + (r.y || ''); }, au: function (r) { return r.au || ''; },
      ct: function (r) { return r.ct || ''; }, ns: function (r) { return r.nsrc || 0; },
      size: function (r) { return r.size || 0; }, ig: function (r) { return IGORDER.indexOf(r.ig); }
    };
    function render() {
      var q = document.getElementById('f-q').value.trim().toLowerCase();
      var out = rows.filter(function (r) {
        if (onlyM && !r.mt) return false;
        if (onlyV && r.ig !== 'COMPLETE_VERIFIED') return false;
        for (var k in F) {
          var vals = k === 'mo' ? MODKEYS.filter(function (m) { return r[MODFIELD[m]]; }) : (r[k] || []);
          var hit = false;
          F[k].forEach(function (v) { if (vals.indexOf(v) >= 0) hit = true; });
          if (!hit) return false;
        }
        if (q) {
          var hay = (r.acc + ' ' + (r.title || '') + ' ' + (r.sum || '') + ' ' + r.th + ' ' + r.dis.join(' ') + ' ' +
            r.tct.join(' ') + ' ' + (r.j || '') + ' ' + (r.y || '') + ' ' + (r.au || '') + ' ' + (r.ct || '') + ' ' +
            (r.pmid || '') + ' ' + (r.mo || '')).toLowerCase();
          if (hay.indexOf(q) < 0) return false;
        }
        return true;
      });
      out.sort(function (a, b) {
        var x = KEYFN[sortKey](a), y = KEYFN[sortKey](b);
        if (x < y) return -sortDir; if (x > y) return sortDir; return 0;
      });
      document.querySelector('#f-tbl tbody').innerHTML = out.map(function (r, i) {
        var id = 'r-' + r.acc;
        return '<tr id="' + id + '"><td class="selcol"><input type="checkbox" class="dlchk" data-acc="' +
          esc(r.acc) + '"' + (window.DSH_DOWNLOADS && window.DSH_DOWNLOADS.selected().indexOf(r.acc) >= 0 ? ' checked' : '') + '></td>' +
          '<td class="num">' + gseCell(r) + '</td>' +
          '<td class="t">' + esc(r.title || '—') + '</td>' +
          '<td>' + esc(I18NTherapy[r.th] ? I18NTherapy[r.th][lang] : r.th) + '</td>' +
          '<td class="t">' + disChips(r, forceCat) + '</td>' +
          '<td class="t">' + tctChips(r) + '</td>' +
          '<td>' + modChips(r) + '</td>' +
          '<td class="t">' + journalCell(r) + '</td>' +
          '<td class="t">' + esc(r.au || '—') + '</td>' +
          '<td class="t">' + esc(r.ct || '—') + '</td>' +
          '<td class="num">' + esc(String(r.ns || '—')) + '</td>' +
          '<td class="num">' + gb(r.size) + '</td>' +
          '<td>' + igCell(r) + '</td>' +
          '<td><button class="exp" data-acc="' + r.acc + '" aria-expanded="false">＋</button></td></tr>' +
          '<tr class="det" id="d-' + r.acc + '" hidden><td colspan="14"><div class="detin" id="di-' + r.acc + '"></div></td></tr>';
      }).join('') || '<tr><td colspan="14" class="st-unk">' + esc(t('search_none')) + '</td></tr>';
      var tot = out.reduce(function (s, r) { return s + (r.size || 0); }, 0);
      document.getElementById('cnt').innerHTML = t('hits') + ' <em>' + out.length + '</em> ' + t('of_total') + ' ' + rows.length +
        ' · ' + t('total_size') + ' <em>' + gb(tot) + '</em>';
      applyI18n(host);
      document.dispatchEvent(new CustomEvent('dsh:tables-rendered'));
      var anchor = location.hash.replace('#', '');
      if (anchor) { var tr = document.getElementById('r-' + anchor); if (tr) tr.scrollIntoView({ block: 'center' }); }
    }
    host.querySelectorAll('.chip[data-k]').forEach(function (c) {
      c.addEventListener('click', function () {
        var k = c.dataset.k, v = c.dataset.v;
        if (v === '__all') delete F[k];
        else {
          if (!F[k]) F[k] = [];
          var i = F[k].indexOf(v);
          if (i >= 0) F[k].splice(i, 1); else F[k].push(v);
          if (!F[k].length) delete F[k];
        }
        host.querySelectorAll('.chip[data-k="' + k + '"]').forEach(function (x) {
          x.classList.toggle('on', v !== '__all' && !!F[k] && F[k].indexOf(x.dataset.v) >= 0);
        });
        render();
      });
    });
    document.getElementById('f-mt').addEventListener('click', function (e) { onlyM = !onlyM; e.currentTarget.classList.toggle('on', onlyM); render(); });
    document.getElementById('f-vr').addEventListener('click', function (e) { onlyV = !onlyV; e.currentTarget.classList.toggle('on', onlyV); render(); });
    document.getElementById('f-rst').addEventListener('click', function () {
      for (var k in F) delete F[k]; onlyM = onlyV = false;
      document.getElementById('f-q').value = '';
      host.querySelectorAll('.chip').forEach(function (x) { x.classList.remove('on'); });
      render();
    });
    document.getElementById('f-q').addEventListener('input', render);
    document.addEventListener('change', function (e) {
      if (e.target && e.target.id === 'dl-all' && window.DSH_DOWNLOADS) window.DSH_DOWNLOADS.toggleAll(e.target.checked);
    });
    host.querySelectorAll('th[data-sort]').forEach(function (hd) {
      hd.style.cursor = 'pointer';
      hd.addEventListener('click', function () {
        var k = hd.dataset.sort;
        if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = 1; }
        render();
      });
    });
    host.addEventListener('click', function (e) {
      var btn = e.target.closest('.exp'); if (!btn) return;
      var acc = btn.dataset.acc, det = document.getElementById('d-' + acc), body = document.getElementById('di-' + acc);
      var open = !det.hidden;
      if (open) { det.hidden = true; btn.textContent = '＋'; btn.setAttribute('aria-expanded', 'false'); return; }
      if (!body.dataset.done) { body.innerHTML = detailHTML(rows.filter(function (r) { return r.acc === acc; })[0]); body.dataset.done = '1'; }
      det.hidden = false; btn.textContent = '－'; btn.setAttribute('aria-expanded', 'true');
      loadFiles(acc, document.getElementById('fl-' + acc));
    });
    document.addEventListener('dsh:lang', function () {
      var open = [].slice.call(host.querySelectorAll('tr.det:not([hidden])')).map(function (tr) { return tr.id.slice(2); });
      render();
      open.forEach(function (acc) {
        var det = document.getElementById('d-' + acc); if (det) det.hidden = false;
        var b = host.querySelector('.exp[data-acc="' + acc + '"]'); if (b) b.textContent = '－';
      });
    });
    render();
    if (opts.q) { var m = document.getElementById('f-q'); m.value = opts.q; render(); }
  }

  function detailHTML(r) {
    if (!r) return '';
    var links = [];
    links.push('<a href="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=' + encodeURIComponent(r.acc) + '" target="_blank" rel="noopener">' + esc(t('geo_link')) + ' ↗</a>');
    if (r.pmid) links.push('<a href="https://pubmed.ncbi.nlm.nih.gov/' + encodeURIComponent(r.pmid) + '/" target="_blank" rel="noopener">' + esc(t('pubmed_link')) + ' · PMID ' + esc(r.pmid) + ' ↗</a>');
    if (r.bp) links.push('<span class="mono">' + esc(r.bp) + '</span>');
    links.push('<a href="' + url('guideline.html') + '">' + esc(t('nav_guideline')) + ' →</a>');
    var rows2 = [
      [t('cols')[2], esc(I18NTherapy[r.th] ? I18NTherapy[r.th][lang] : r.th)],
      [t('cols')[3], esc(r.dis.join(' / '))],
      [t('cols')[5], esc(r.mo || '—') + (r.src ? ' <span class="st-unk">(' + esc(r.src) + ')</span>' : '')],
      ['GEO type', esc(r.gdstype || '—')],
      [t('cols')[9], esc(String(r.ns)) + (r.nsrc ? ' (' + num(r.nsrc) + ')' : '')],
      [t('cols')[10], gb(r.size)],
      ['Release', esc(r.pdat || '—')],
    ];
    var local = r.local || {};
    var localNote = [];
    if (local.n) localNote.push('<span class="b q">' + num(local.n) + ' ' + (lang === 'zh' ? '个本地文件' : 'local files') + '</span>');
    if (local.tar) localNote.push('<span class="b q">' + num(local.tar) + ' ' + (lang === 'zh' ? '个 tar 成员' : 'tar members') + '</span>');
    if (local.web) localNote.push('<span class="b o">⚠ ' + num(local.web) + ' ' + (lang === 'zh' ? '个网页文件（非测序数据）' : 'HTML/aspx files (not data)') + '</span>');
    if (local.bad) localNote.push('<span class="b o">⚠ ' + num(local.bad) + ' ' + (lang === 'zh' ? '个校验异常' : 'integrity warnings') + '</span>');
    return '<div class="note"><b>' + esc(r.acc) + '</b> · ' + links.join(' · ') +
      (localNote.length ? '<div style="margin-top:5px">' + localNote.join(' ') + '</div>' : '') + '</div>' +
      (r.sum ? '<p style="margin:6px 0">' + esc(r.sum) + '</p>' : '') +
      '<table style="box-shadow:none;border:1px solid var(--line)"><tbody>' +
      rows2.map(function (kv) { return '<tr><th style="width:130px;position:static">' + kv[0] + '</th><td>' + kv[1] + '</td></tr>'; }).join('') +
      '</tbody></table>' +
      '<div style="margin-top:8px"><b>' + esc(t('files')) + '：</b> <span id="fl-' + r.acc + '">' + esc(t('files_btn')) + '…</span></div>';
  }
  function loadFiles(acc, host) {
    if (!host || host.dataset.loaded) return;
    host.dataset.loaded = '1';
    host.textContent = '…';
    fetch(url('data/files/' + encodeURIComponent(acc) + '.json')).then(function (r) { return r.json(); }).then(function (d) {
      var parts = [];
      if (d.files && d.files.length) {
        parts.push('<div class="filelist">' + d.files.map(function (f) {
          var bad = f.st && f.st !== 'OK';
          return '<div title="' + esc(f.p) + '">' + (bad ? '⚠️ ' : '') + esc(f.p) + ' <span class="st-unk">' + esc(f.h || '') + '</span></div>';
        }).join('') + '</div>');
      } else parts.push('<span class="st-unk">' + esc(t('files_none')) + '</span>');
      if (d.tars && d.tars.length) {
        parts.push('<div style="margin-top:6px">' + d.tars.map(function (tt) {
          return '<div><code>' + esc(tt.p) + '</code> · ' + num(tt.n) + ' ' + (lang === 'zh' ? '个成员' : 'members') + '</div>';
        }).join('') + '</div>');
      }
      host.innerHTML = parts.join('');
    })['catch'](function (e) { host.innerHTML = '<span class="err">' + esc(e.message) + '</span>'; });
  }

  /* ---------------- 页面启动 ---------------- */
  function boot() {
    renderTop();
    initSearch();
    load('meta').then(function (m) {
      MANIFEST = Object.assign({}, MANIFEST, m);
      applyLabels(MANIFEST);
      var host = document.getElementById('meta-line');
      if (host) {
        host.innerHTML = num(m.n_ds) + ' ' + t('datasets') + ' · ' + num(m.n_samples) + ' ' + t('samples') + ' · ' +
          m.gb + ' GB' + ' · ' + num(m.n_verified) + ' ' + t('stat_verified') + ' · ' +
          t('updated') + ' ' + esc(m.generated);
      }
      document.querySelectorAll('[data-meta]').forEach(function (el) {
        var k = el.dataset.meta;
        if (k === 'gb') el.textContent = m.gb + ' GB';
        else if (k === 'tb') el.textContent = (m.gb / 1024).toFixed(2) + ' TB';
        else el.textContent = num(m[k]);
      });
      if (PAGE === 'home') renderHome();
      if (PAGE === 'catalog' || PAGE === 'category') load('datasets').then(function (rows) {
        DS = rows;
        var qs = new URLSearchParams(location.search).get('q') || '';
        if (PAGE === 'category') {
          var cat = HTML.dataset.cat;
          var sub = rows.filter(function (r) { return r.dis.indexOf(cat) >= 0; });
          renderCatPage(cat, sub, rows);
          buildTable(sub, { hostId: 'tbl-host', q: qs, forceCat: cat });
        } else buildTable(rows, { hostId: 'tbl-host', q: qs });
        var q2 = document.getElementById('q-global'); if (q2 && qs) q2.value = qs;
      });
      if (PAGE === 'guideline') load('datasets').then(function (rows) { DS = rows; renderGuideline(rows); });
    })['catch'](function (e) {
      var h = document.getElementById('tbl-host');
      if (h) h.innerHTML = '<div class="err">数据加载失败：' + esc(e.message) + '</div>';
    });
    document.querySelectorAll('.langsw button').forEach(function (b) {
      b.addEventListener('click', function () { setLang(b.dataset.lang); });
    });
    document.addEventListener('dsh:lang', function () {
      if (PAGE === 'home') renderHome();
      if (PAGE === 'catalog' && DS) buildTable(DS, { hostId: 'tbl-host', q: new URLSearchParams(location.search).get('q') || '' });
      if (PAGE === 'category' && DS) {
        var cid = HTML.dataset.cat;
        renderCatPage(cid, DS.filter(function (r) { return r.dis.indexOf(cid) >= 0; }), DS);
      }
      document.querySelectorAll('[data-i18n]').forEach(function (el) {
        var v = I18N[el.dataset.i18n]; if (v && v[lang] != null) el.textContent = v[lang];
      });
      var h = document.getElementById('meta-line');
      if (h && MANIFEST.n_ds) {
        h.innerHTML = num(MANIFEST.n_ds) + ' ' + t('datasets') + ' · ' + num(MANIFEST.n_samples) + ' ' + t('samples') + ' · ' +
          MANIFEST.gb + ' GB' + ' · ' + num(MANIFEST.n_verified) + ' ' + t('stat_verified') + ' · ' +
          t('updated') + ' ' + esc(MANIFEST.generated || '');
      }
      if (PAGE === 'guideline' && DS) renderGuideline(DS);
    });
  }

  /* ---------------- 类别详情页头部 ---------------- */
  function renderCatPage(cat, sub, all) {
    var meta = MANIFEST.cat_meta[cat] || {};
    var name = I18NCat[cat] ? I18NCat[cat][lang] : cat;
    document.title = name + ' · ' + t('site_name');
    var h = document.getElementById('cat-head');
    if (!h) return;
    var tot = sub.reduce(function (s, r) { return s + (r.size || 0); }, 0);
    var sm = sub.reduce(function (s, r) { return s + (r.nsrc || 0); }, 0);
    var kpi = [
      [t('stat_ds'), num(sub.length), ''],
      [t('stat_samples'), num(sm), ''],
      [t('stat_matched'), num(sub.filter(function (r) { return r.mt; }).length), 'g'],
      [t('stat_verified'), num(sub.filter(function (r) { return r.ig === 'COMPLETE_VERIFIED'; }).length), 'g'],
      [t('stat_pub'), num(sub.filter(function (r) { return r.j; }).length), ''],
      [t('stat_bytes'), gb(tot), ''],
    ];
    var mods = MODKEYS.filter(function (m) { return sub.some(function (r) { return r[MODFIELD[m]]; }); });
    var mx = Math.max.apply(null, mods.map(function (m) { return sub.filter(function (r) { return r[MODFIELD[m]]; }).length; }).concat([1]));
    var bars = mods.map(function (m) {
      var n = sub.filter(function (r) { return r[MODFIELD[m]]; }).length;
      return '<div class="bar"><span class="lb">' + m + '</span><span class="tr"><i style="width:' + (100 * n / mx) + '%"></i></span>' +
        '<span class="vl">' + n + ' / ' + sub.length + '</span></div>';
    }).join('');
    var ths = THORDER.filter(function (x) { return sub.some(function (r) { return r.th === x; }); });
    var mx2 = Math.max.apply(null, ths.map(function (x) { return sub.filter(function (r) { return r.th === x; }).length; }).concat([1]));
    var bars2 = ths.map(function (x) {
      var n = sub.filter(function (r) { return r.th === x; }).length;
      return '<div class="bar"><span class="lb">' + esc(I18NTherapy[x] ? I18NTherapy[x][lang] : x) + '</span><span class="tr"><i style="width:' + (100 * n / mx2) + '%"></i></span>' +
        '<span class="vl">' + n + ' / ' + sub.length + '</span></div>';
    }).join('');
    var tct = [];
    sub.forEach(function (r) { r.tct.forEach(function (x) { if (x && tct.indexOf(x) < 0) tct.push(x); }); });
    var others = all.filter(function (r) { return r.dis.indexOf(cat) < 0 && r.dis.some(function (d) { return sub.some(function (s) { return s.dis.indexOf(d) >= 0; }); }); }).length;
    h.innerHTML =
      '<div class="crumb"><a href="' + url('index.html') + '">' + esc(t('nav_home')) + '</a> / ' +
      '<a href="' + url('index.html') + '#cat-grid">' + esc(t('browse_disease')) + '</a> / ' + esc(name) + '</div>' +
      '<div class="hero"><div class="tile" style="color:' + (meta.color || '#1a7f5a') + '">' + svgUse(meta.icon) + '</div>' +
      '<div class="ht"><h1>' + esc(name) + '</h1><div class="sub">' + esc(meta['name_' + (lang === 'zh' ? 'en' : 'zh')] || '') + '</div>' +
      '<p>' + esc(meta['desc_' + lang] || '') + '</p></div></div>' +
      '<div class="kpis">' + kpi.map(function (k) {
        return '<div class="kpi"><i>' + esc(k[0]) + '</i><b class="' + k[2] + '">' + k[1] + '</b></div>';
      }).join('') + '</div>' +
      '<div class="two"><div><h3>' + esc(t('omics_profile')) + '</h3><div class="bars">' + (bars || '<span class="st-unk">—</span>') + '</div></div>' +
      '<div><h3>' + esc(t('therapy_profile')) + '</h3><div class="bars">' + (bars2 || '<span class="st-unk">—</span>') + '</div></div></div>' +
      '<div class="note"><b>' + esc(t('cat_intro')) + '</b> ' + esc(t('related_hint')) +
      (others ? ' ' + (lang === 'zh' ? '另有 ' + others + ' 个数据集通过其他疾病标签与本类别关联（见目录页）。' :
        'A further ' + others + ' datasets link to this category through other disease labels (see catalog).') : '') + '</div>' +
      '<div class="legend"><span>' + (lang === 'zh' ? 'T 细胞类型/状态覆盖：' : 'T-cell types covered: ') + '</span>' +
      tct.map(function (x) { return '<span class="b">' + esc(I18NTct[x] ? I18NTct[x][lang] : x) + '</span>'; }).join('') + '</div>' +
      '<h2>' + esc(t('datasets_in')) + '（' + num(sub.length) + '）</h2>';
  }

  /* ---------------- 关联与判定指南（静态渲染，保留原有分类口径） ---------------- */
  function renderGuideline(rows) {
    var host = document.getElementById('gl');
    if (!host) return;
    var n = function (fn) { return rows.filter(fn).length; };
    var catCount = {};
    rows.forEach(function (r) { r.dis.forEach(function (d) { catCount[d] = (catCount[d] || 0) + 1; }); });
    var catKeys = Object.keys(catCount).sort(function (a, b) { return catCount[b] - catCount[a]; });
    var thCount = {}; rows.forEach(function (r) { thCount[r.th] = (thCount[r.th] || 0) + 1; });
    var tctCount = {}; rows.forEach(function (r) { r.tct.forEach(function (x) { if (x) tctCount[x] = (tctCount[x] || 0) + 1; }); });
    var tctKeys = Object.keys(tctCount).sort(function (a, b) { return tctCount[b] - tctCount[a]; });

    function sub(name) { return rows.filter(function (r) { return r.dis.indexOf(name) >= 0; }); }

    host.innerHTML =
      '<h2>' + esc(lang === 'zh' ? '一、数据库关系' : '1. Database relations') + '</h2>' +
      '<div class="gsec"><div class="big">' + esc(lang === 'zh' ? '① 关系结构：数据集 → 疾病 → 组学 → 文件' : '① Structure: dataset → disease → omics → files') + '</div>' +
      '<p>' + esc(lang === 'zh'
        ? '数据库以 GEO Series（GSE）为主键，向下关联四条：疾病标签（多标签）、治疗类型、T 细胞类型/状态（多标签）、本地文件与 tar 成员。所有页面均读取同一份 JSON，因此目录页与类别页的计数完全一致。'
        : 'GEO Series (GSE) is the primary key, with four downward relations: disease labels (multi), therapy type, T-cell type/state (multi), and local files/tar members. Every page reads the same JSON, so counts on the catalog and category pages always agree.') + '</p>' +
      '<table><tr><th>' + esc(lang === 'zh' ? '关联键' : 'Key') + '</th><th>' + esc(lang === 'zh' ? '目标表 / 字段' : 'Target table / field') + '</th><th>' + esc(lang === 'zh' ? '基数' : 'Cardinality') + '</th><th>' + esc(lang === 'zh' ? '说明' : 'Notes') + '</th></tr>' +
      [['accession', 'datasets.accession ↔ annotation.accession ↔ files.dataset ↔ tar_members.dataset', '1:1 / 1:N',
        lang === 'zh' ? '主键；目录页与类别页的锚点即 GSE 编号' : 'Primary key; the anchor used by catalog and category pages'],
       ['diseases', 'annotation.diseases', '1:N', lang === 'zh' ? '“|”分隔的多标签，一级导航即此字段取值' : 'Pipe-separated multi-label; values drive the primary navigation'],
       ['therapy', 'annotation.therapy', '1:1', lang === 'zh' ? '以被检测细胞身份判定，而非患者治疗背景' : 'Decided by the identity of the profiled cells, not patient treatment history'],
       ['tcell_types', 'annotation.tcell_types', '1:N', lang === 'zh' ? '功能状态多标签，用于筛选耗尽/记忆/效应等' : 'Functional-state multi-label for exhaustion/memory/effector filters'],
       ['relpath', 'files.relpath → tar_members.tarfile', '1:N', lang === 'zh' ? '本地文件与 tar 包内成员的对应关系' : 'Maps local files to members inside tar archives'],
       ['pmid', 'annotation.pmid / datasets.pubmed → PubMed', '1:1', lang === 'zh' ? '外部文献关联，页面直接跳转 PubMed' : 'External literature link, resolved to PubMed']]
        .map(function (r) { return '<tr><td class="mono">' + esc(r[0]) + '</td><td class="mono">' + esc(r[1]) + '</td><td>' + esc(r[2]) + '</td><td>' + esc(r[3]) + '</td></tr>'; }).join('') +
      '</table></div>' +

      '<h2>' + esc(lang === 'zh' ? '二、分类定义与判定依据' : '2. Class definitions and evidence') + '</h2>' +
      '<div class="gsec"><div class="big">' + esc(lang === 'zh' ? '① 治疗类型' : '① Therapy type') + '</div>' +
      '<table><tr><th>' + esc(t('cols')[2]) + '</th><th>' + esc(t('f_evidence')) + '</th><th>' + esc(t('datasets')) + '</th></tr>' +
      THORDER.map(function (k) {
        var ev = { 'CAR-T': lang === 'zh' ? '样本 cell type 出现 CAR/嵌合抗原受体；或标题/design 明确为 CAR-T 研究' : 'Sample cell type mentions CAR/chimeric antigen receptor, or title/design states CAR-T',
          'CAR-T+内源T(混合)': lang === 'zh' ? '同一数据集同时包含 CAR-T 与内源 T 样本' : 'The same series contains both CAR-T and endogenous T samples',
          '内源T': lang === 'zh' ? '标题明确 endogenous T cell / expansion of endogenous，或样本标注 non-transduced / mock' : 'Title states endogenous T cell / expansion of endogenous, or samples are non-transduced/mock',
          'TCR-T/工程化T': lang === 'zh' ? '工程化 TCR（transgenic/engineered TCR、NY-ESO-1 等），非 CAR 结构' : 'Engineered TCR (transgenic/engineered TCR, NY-ESO-1) rather than a CAR construct',
          '非T细胞/对照': lang === 'zh' ? '标题示明为肿瘤细胞系或非 T 细胞' : 'Title indicates a tumour cell line or non-T cells',
          '未明确': lang === 'zh' ? '无足够证据判定' : 'Insufficient evidence' }[k];
        return '<tr><td><span class="b">' + esc(I18NTherapy[k] ? I18NTherapy[k][lang] : k) + '</span></td><td>' + esc(ev) + '</td><td>' + (thCount[k] || 0) + '</td></tr>';
      }).join('') + '</table>' +
      '<div class="note"><b>' + esc(lang === 'zh' ? '为何不按“患者是否接受 CAR-T 治疗”判定？' : 'Why not classify by whether patients received CAR-T?') + '</b> ' +
      esc(lang === 'zh'
        ? '大量研究在 CAR-T 治疗患者体内追踪内源 T 细胞，以治疗背景判定会误归为 CAR-T，故以被检测细胞的身份为准。'
        : 'Many studies track endogenous T cells inside CAR-T-treated patients; classifying by treatment background would mislabel them, so the identity of the profiled cells is used instead.') + '</div></div>' +

      '<div class="gsec"><div class="big">' + esc(lang === 'zh' ? '② 疾病背景（一级导航）' : '② Disease background (primary navigation)') + '</div>' +
      '<table><tr><th>' + esc(t('cols')[3]) + '</th><th>' + esc(t('datasets')) + '</th><th>' + esc(t('samples')) + '</th><th>' + esc(lang === 'zh' ? '代表数据集' : 'Example datasets') + '</th></tr>' +
      catKeys.map(function (d) {
        var s = sub(d);
        return '<tr><td><a class="b p" href="' + catUrl(d) + '">' + esc(I18NCat[d] ? I18NCat[d][lang] : d) + '</a></td>' +
          '<td class="num">' + s.length + '</td><td class="num">' + num(s.reduce(function (a, r) { return a + (r.nsrc || 0); }, 0)) + '</td>' +
          '<td>' + s.slice(0, 6).map(function (r) { return '<a href="' + url('catalog.html') + '#' + r.acc + '">' + esc(r.acc) + '</a>'; }).join('、') + (s.length > 6 ? ' …' : '') + '</td></tr>';
      }).join('') + '</table>' +
      '<div class="note">' + esc(lang === 'zh'
        ? '「基础/体外研究」指无患者疾病背景的体外/机制研究，不是数据缺陷，适合分子机制对比而非队列分析。一个数据集可同时属于多个疾病标签，因此各类别数据集数之和大于总数。'
        : '"Basic / in vitro" means mechanistic work without patient disease background — not a data defect; suited to mechanism comparison rather than cohort analysis. A dataset may carry several disease labels, so category counts sum to more than the total.') + '</div></div>' +

      '<div class="gsec"><div class="big">' + esc(lang === 'zh' ? '③ T 细胞类型与功能状态' : '③ T-cell type and functional state') + '</div>' +
      '<table><tr><th>' + esc(t('cols')[4]) + '</th><th>' + esc(t('datasets')) + '</th><th>' + esc(lang === 'zh' ? '说明' : 'Description') + '</th></tr>' +
      tctKeys.map(function (k) {
        return '<tr><td><span class="b">' + esc(I18NTct[k] ? I18NTct[k][lang] : k) + '</span></td><td class="num">' + tctCount[k] + '</td><td>' +
          esc(MANIFEST.tct_desc && MANIFEST.tct_desc[k] ? MANIFEST.tct_desc[k][lang] : '') + '</td></tr>';
      }).join('') + '</table></div>' +

      '<div class="gsec"><div class="big">' + esc(lang === 'zh' ? '④ 组学模态与完整性' : '④ Omics modalities and integrity') + '</div>' +
      '<p>' + esc(lang === 'zh'
        ? '组学模态综合本地文件名、tar 包内成员名与 GEO gdstype 判定；仅凭文件名会漏判（例如 GSE160174 的 scRNA 证据来自 .bw 覆盖度文件）。标注来源为 GEO 官方分类者说明本地文件中无直接证据。'
        : 'Modalities combine local file names, tar member names and GEO gdstype; file names alone miss cases (e.g. the scRNA evidence for GSE160174 comes from .bw coverage files). Entries marked as coming from the official GEO classification have no direct local file evidence.') + '</p>' +
      '<table><tr><th>Modality</th><th>' + esc(t('datasets')) + '</th><th>' + esc(lang === 'zh' ? '说明' : 'Description') + '</th></tr>' +
      MODKEYS.map(function (m) {
        var c = n(function (r) { return r[MODFIELD[m]]; });
        return '<tr><td><span class="b ' + (MODCOLOR[m] || 'o') + '">' + m + '</span></td><td class="num">' + c + '</td><td>' +
          esc(MANIFEST.mod_desc && MANIFEST.mod_desc[m] ? MANIFEST.mod_desc[m][lang] : '') + '</td></tr>';
      }).join('') + '</table>' +
      '<table style="margin-top:12px"><tr><th>' + esc(t('cols')[11]) + '</th><th>' + esc(t('datasets')) + '</th><th>' + esc(lang === 'zh' ? '含义' : 'Meaning') + '</th></tr>' +
      IGORDER.map(function (k) {
        var c = n(function (r) { return r.ig === k; });
        return '<tr><td class="st-' + ({ COMPLETE_VERIFIED: 'ok', UNVERIFIED: 'unk', TRUNCATED: 'warn', PARTIAL_BROKEN: 'warn', CORRUPT: 'bad', FAILED_ALL: 'bad', NO_DATA: 'bad' }[k]) + '">' +
          esc((MANIFEST['ig_' + lang] && MANIFEST['ig_' + lang][k]) || k) + '</td><td class="num">' + c + '</td><td>' +
          esc(MANIFEST.ig_desc && MANIFEST.ig_desc[k] ? MANIFEST.ig_desc[k][lang] : '') + '</td></tr>';
      }).join('') + '</table></div>' +

      '<h2>' + esc(lang === 'zh' ? '三、推荐使用路径' : '3. Recommended workflows') + '</h2>' +
      '<div class="gsec">' +
      [lang === 'zh' ? '① 做 CAR-T 耗竭/持久性分析 → 治疗=CAR-T + T 细胞=耗竭/功能障碍 + 完整性=✅已验证'
        : '① CAR-T exhaustion/persistence → therapy=CAR-T + T-cell=Exhaustion/dysfunction + integrity=✅ Verified',
       lang === 'zh' ? '② 做 scRNA+scTCR 联合克隆追踪 → 组学=scRNA+scTCR，再点「仅 T 细胞多组学配套」'
        : '② Joint scRNA+scTCR clonal tracking → omics=scRNA+scTCR, then "Only multi-omics matched"',
       lang === 'zh' ? '③ 做表观调控机制 → 组学=scATAC（共 ' + n(function (r) { return r.atac; }) + ' 个含 scATAC）'
        : '③ Epigenetic regulation → omics=scATAC (' + n(function (r) { return r.atac; }) + ' datasets with scATAC)',
       lang === 'zh' ? '④ 做疾病队列对比 → 先在首页按疾病类别进入，再按期刊年份排序'
        : '④ Disease cohort comparison → enter by disease category on the home page, then sort by journal year',
       lang === 'zh' ? '⑤ 需立即开始分析 → 勾选「仅官方校验通过」，避免踩到截断数据'
        : '⑤ Start analysis immediately → enable "Only officially verified" to avoid truncated data']
        .map(function (s) { return '<p><span class="kpi2">' + esc(s) + '</span></p>'; }).join('') +
      '<div class="note">' + esc(lang === 'zh'
        ? '数据文件保存在数据库服务器本地目录，网页仅发布公开元数据与文件相对路径（不含原始测序数据、凭据或密钥），因此网站可在 GitHub Pages 上静态运行。'
        : 'Raw data stays on the database server; the site publishes only public metadata and relative file paths (no raw sequencing data, credentials or keys), so it runs statically on GitHub Pages.') + '</div></div>';
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  window.DSH_SITE = { setLang: setLang, getLang: function () { return lang; }, load: load, esc: esc, url: url };
})();
