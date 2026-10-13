/* 批量下载脚本生成器（纯前端，只读 downloads.json；不宣称浏览器已完成数据下载）
   生成逻辑要点：
     - 只使用官方元数据核实过的文件名/URL；无法核实的记录不生成任何命令
     - GEO 补充文件与 SRA 原始数据分开：默认 GEO，SRA 需已核实关联 accession
     - 断点续传（curl -C - / wget -c）、有限重试、逐文件日志、失败继续、结束汇总
     - 不 sudo、不自动解压、不覆盖已完整的文件
*/
(function () {
  'use strict';
  var HTML = document.documentElement;
  var BASE = HTML.dataset.base || '.';
  var DL = null;                 // downloads.json 内容
  var I18N = JSON.parse(document.getElementById('dsh-i18n').textContent);
  var MANIFEST = JSON.parse(document.getElementById('dsh-manifest').textContent);
  var lang = window.DSH_SITE ? window.DSH_SITE.getLang() : 'zh';
  var sel = {};                  // {GSE: true}
  var ui = {
    zh: {
      title: '批量下载脚本', open: '批量下载', select: '选择', selected: '已选',
      gen: '生成下载脚本', dlsh: '下载 .sh', dlsh_sra: '下载 SRA 脚本 .sh',
      type_geo: 'GEO 补充文件', type_sra: 'SRA 原始测序数据',
      sra_only_verified: 'SRA 仅在已核实关联 accession 时提供',
      preview: '待下载清单（生成前核对）', noverify: '暂无可验证下载链接',
      files: '文件', size: '体积', exact: '精确', approx: '近似', unknown: '未知',
      copies: '复制脚本', copied: '已复制到剪贴板', clear: '清空选择', close: '关闭',
      select_page: '选择当前筛选结果', select_all: '全选本页', deselect: '取消全选',
      none_selected: '请先勾选数据集', n_sel: '已选数据集', note_browser:
        '浏览器不会执行下载：脚本生成后由你在本地运行。',
      note_sra: 'SRA 脚本只下载 run 归档（prefetch）；FASTQ 转换需另行执行 fasterq-dump，且需要额外磁盘空间。',
      run_hint: '本地运行：bash download_datasets.sh',
      col_sel: '选择', verified: '已核实', partial: '部分核实', unavailable: '无法核实',
      reason: '说明', local_match: '本地交叉核对'
    },
    en: {
      title: 'Batch download script', open: 'Batch download', select: 'Select', selected: 'selected',
      gen: 'Generate download script', dlsh: 'Download .sh', dlsh_sra: 'Download SRA script .sh',
      type_geo: 'GEO supplementary files', type_sra: 'SRA raw sequencing data',
      sra_only_verified: 'SRA is offered only when the linked accession is verified',
      preview: 'Files to download (check before generating)', noverify: 'No verifiable download link',
      files: 'files', size: 'size', exact: 'exact', approx: 'approx', unknown: 'unknown',
      copies: 'Copy script', copied: 'Copied to clipboard', clear: 'Clear selection', close: 'Close',
      select_page: 'Select current filter results', select_all: 'Select all', deselect: 'Deselect all',
      none_selected: 'Select at least one dataset', n_sel: 'selected datasets', note_browser:
        'The browser does not download anything: the script runs on your own machine.',
      note_sra: 'The SRA script only downloads run archives (prefetch); FASTQ conversion requires a separate '
        + 'fasterq-dump step and extra disk space.',
      run_hint: 'Run locally: bash download_datasets.sh',
      col_sel: 'Pick', verified: 'verified', partial: 'partly verified', unavailable: 'not verifiable',
      reason: 'Note', local_match: 'local cross-check'
    }
  };
  function t(k) { return ui[lang][k] != null ? ui[lang][k] : k; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function human(b) {
    b = Number(b) || 0;
    if (!b) return '—';
    var u = [['TB', 1099511627776], ['GB', 1073741824], ['MB', 1048576], ['KB', 1024]];
    for (var i = 0; i < u.length; i++) if (b >= u[i][1]) return (b / u[i][1]).toFixed(b / u[i][1] >= 10 ? 1 : 2) + ' ' + u[i][0];
    return b + ' B';
  }
  function slug(s) { return String(s).replace(/[^A-Za-z0-9._-]+/g, '_'); }

  function loadDownloads() {
    if (DL) return Promise.resolve(DL);
    // file:// 双击打开时使用内联数据；线上用内嵌 manifest；再退回 fetch
    if (window.DSH_INLINE && window.DSH_INLINE.downloads) { DL = window.DSH_INLINE.downloads; return Promise.resolve(DL); }
    if (MANIFEST.downloads) { DL = MANIFEST.downloads; return Promise.resolve(DL); }
    if (location.protocol === 'file:') { DL = { datasets: {}, stats: {} }; return Promise.resolve(DL); }
    return fetch(BASE + '/data/downloads.json').then(function (r) { return r.json(); }).then(function (d) { DL = d; return d; });
  }
  function rec(acc) { return DL && DL.datasets ? DL.datasets[acc] : null; }
  function downloadable(acc) {
    var r = rec(acc);
    return !!(r && r.geo && r.geo.files && r.geo.files.length);
  }

  /* ---------------- 脚本生成 ---------------- */
  function shellQuote(s) { return "'" + String(s).replace(/'/g, "'\\''") + "'"; }

  function scriptFor(accs, type) {
    var now = new Date().toISOString().slice(0, 16).replace('T', ' ');
    var geoAccs = accs.filter(function (a) { var r = rec(a); return r && r.geo.files && r.geo.files.length; });
    var sraAccs = accs.filter(function (a) { var r = rec(a); return r && r.sra && r.sra.available; });
    var useSra = type === 'sra';
    var list = useSra ? sraAccs : geoAccs;
    var totalBytes = list.reduce(function (s, a) {
      var r = rec(a);
      return s + (useSra ? (r.sra.bytes || 0) : (r.geo.bytes || 0));
    }, 0);
    var out = [];
    out.push('#!/usr/bin/env bash');
    out.push('# ' + (useSra ? 'SRA raw sequencing data' : 'GEO supplementary files') +
      ' batch download script');
    out.push('# Generated: ' + now + '  |  source: ' + 'official GEO / SRA metadata' +
      ' (see downloads.json provenance)');
    out.push('# ' + (useSra ? 'SRA raw data' : 'GEO supplementary files') + ' · ' +
      list.length + ' dataset(s) · ' + human(totalBytes) + ' · generated by the T-cell multi-omics database web page');
    out.push('# ---------------------------------------------------------------------------');
    out.push('# datasets:');
    list.forEach(function (a) {
      var r = rec(a);
      out.push('#   ' + a + '  ' + (useSra
        ? 'study=' + (r.sra.study || '?') + ' runs=' + r.sra.n_runs + ' (' + human(r.sra.bytes) + ')'
        : 'files=' + r.geo.n_files + ' (' + human(r.geo.bytes) + ', ' + r.geo.state + ')'));
    });
    if (!useSra) {
      var skipped = accs.length - geoAccs.length;
      if (skipped) out.push('# NOTE: ' + skipped + ' selected dataset(s) had no verifiable GEO link and were skipped.');
    } else {
      var noSra = accs.length - sraAccs.length;
      if (noSra) out.push('# NOTE: ' + noSra + ' selected dataset(s) have no verified SRA linkage and were skipped.');
    }
    out.push('# ---------------------------------------------------------------------------');
    out.push('set -uo pipefail');
    out.push('');
    out.push('BASE_DIR="$(cd "$(dirname "$0")" && pwd)"');
    out.push('RAW_DIR="${RAW_DIR:-$BASE_DIR/raw}"');
    out.push('LOG_DIR="${LOG_DIR:-$BASE_DIR/logs}"');
    out.push('RESUME="${RESUME:-1}"          # 1 = 断点续传（curl -C - / wget -c）');
    out.push('MAX_RETRY="${MAX_RETRY:-3}"     # 每个文件的有限重试次数');
    out.push('SRA_TOOLKIT_BIN="${SRA_TOOLKIT_BIN:-}"   # 可选：SRA Toolkit 的 bin 目录');
    out.push('mkdir -p "$RAW_DIR" "$LOG_DIR"');
    out.push('LOG="$LOG_DIR/download_$(date +%Y%m%d_%H%M%S).log"');
    out.push('FAILED_LIST="$LOG_DIR/failed_$(date +%Y%m%d_%H%M%S).txt"');
    out.push('FAILED=0; OK=0; SKIPPED=0');
    out.push('');
    out.push('log(){ printf \'%s %s\\n\' "$(date \'+%F %T\')" "$*" | tee -a "$LOG"; }');
    out.push('fail(){ printf \'%s\\n\' "$1" >> "$FAILED_LIST"; FAILED=$((FAILED+1)); log "[FAIL] $1"; }');
    out.push('');
    out.push('# ---- 依赖检查（不需要 sudo；缺 curl 时回退 wget）----');
    out.push('HAVE_CURL=0; HAVE_WGET=0');
    out.push('command -v curl >/dev/null 2>&1 && HAVE_CURL=1');
    out.push('command -v wget >/dev/null 2>&1 && HAVE_WGET=1');
    out.push('if [ "$HAVE_CURL" = 0 ] && [ "$HAVE_WGET" = 0 ]; then');
    out.push('  echo "需要 curl 或 wget（任一个）。安装示例：apt-get install -y curl / brew install curl" >&2; exit 2');
    out.push('fi');
    out.push('log "工具：curl=$HAVE_CURL wget=$HAVE_WGET"');

    out.push('if [ "$HAVE_CURL" = 1 ]; then');
    out.push('  CURL_VER="$(curl --version 2>/dev/null | head -1)"');
    out.push('  case "$CURL_VER" in *"libcurl/"*) : ;; *) log "提示：curl 为精简版，缺少进度/重试参数时脚本会自动降级" ;; esac');
    out.push('fi');
    out.push('DISK_AVAIL_KB=$(df -Pk "$RAW_DIR" 2>/dev/null | awk \'NR==2{print $4}\')');
    out.push('DISK_AVAIL_KB=${DISK_AVAIL_KB:-0}');
    out.push('NEED_KB=' + Math.ceil(totalBytes / 1024));
    out.push('if [ "$DISK_AVAIL_KB" -gt 0 ] && [ "$DISK_AVAIL_KB" -lt "$NEED_KB" ]; then');
    out.push('  log "警告：可用空间约 $((DISK_AVAIL_KB/1024/1024)) GB，小于清单合计约 $((NEED_KB/1024/1024)) GB（可继续，但可能中途失败）"');
    out.push('fi');
    out.push('');
    out.push('# 下载单个文件：$1=url $2=目标路径 $3=预期字节数(可空)');
    out.push('download_file(){');
    out.push('  local url="$1" dest="$2" want="${3:-}"');
    out.push('  mkdir -p "$(dirname "$dest")"');
    out.push('  if [ -s "$dest" ] && [ -n "$want" ] && [ "$(stat -c%s "$dest" 2>/dev/null || echo 0)" = "$want" ]; then');
    out.push('    log "[SKIP] 已存在且大小一致：$dest"; SKIPPED=$((SKIPPED+1)); return 0');
    out.push('  fi');
    out.push('  if [ -s "$dest" ] && [ -z "$want" ]; then');
    out.push('    log "[SKIP] 已存在（官方未给出体积，不覆盖）：$dest"; SKIPPED=$((SKIPPED+1)); return 0');
    out.push('  fi');
    out.push('  local n=0 ok=0');
    out.push('  while [ "$n" -lt "$MAX_RETRY" ]; do');
    out.push('    n=$((n+1))');
    out.push('    log "[GET ] $url -> $dest (第 $n/$MAX_RETRY 次)"');
    out.push('    if [ "$HAVE_CURL" = 1 ]; then');
    out.push('      if [ "$RESUME" = 1 ]; then');
    out.push('        curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 -C - -o "$dest" "$url" >>"$LOG" 2>&1 && ok=1');
    out.push('      else');
    out.push('        curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 -o "$dest" "$url" >>"$LOG" 2>&1 && ok=1');
    out.push('      fi');
    out.push('      if [ "$ok" = 0 ]; then');
    out.push('        curl -fL --retry 3 --retry-delay 2 -C - -o "$dest" "$url" >>"$LOG" 2>&1 && ok=1');
    out.push('      fi');
    out.push('    else');
    out.push('      if [ "$RESUME" = 1 ]; then');
    out.push('        wget -c --tries=3 --waitretry=2 --timeout=20 -O "$dest" "$url" >>"$LOG" 2>&1 && ok=1');
    out.push('      else');
    out.push('        wget --tries=3 --waitretry=2 --timeout=20 -O "$dest" "$url" >>"$LOG" 2>&1 && ok=1');
    out.push('      fi');
    out.push('    fi');
    out.push('    [ "$ok" = 1 ] && break');
    out.push('    log "[WARN] 第 $n 次失败：$url"; sleep $((n*3))');
    out.push('  done');
    out.push('  if [ "$ok" != 1 ]; then fail "$url -> $dest"; return 1; fi');
    out.push('  if [ -n "$want" ]; then');
    out.push('    local got; got=$(stat -c%s "$dest" 2>/dev/null || echo 0)');
    out.push('    if [ "$got" != "$want" ]; then');
    out.push('      log "[WARN] 体积不符（预期 $want，实际 $got），保留文件以便续传：$dest"');
    out.push('      fail "$dest 体积不符（预期 $want 实际 $got）"; return 1');
    out.push('    fi');
    out.push('  fi');
    out.push('  log "[OK  ] $dest ($(stat -c%s "$dest" 2>/dev/null) 字节)"');
    out.push('  OK=$((OK+1)); return 0');
    out.push('}');
    out.push('');
    if (useSra) {
      out.push('# ---- SRA Toolkit 检查（本脚本只下载 run 归档，不做 FASTQ 转换）----');
      out.push('if [ -n "$SRA_TOOLKIT_BIN" ]; then PATH="$SRA_TOOLKIT_BIN:$PATH"; fi');
      out.push('HAVE_PREFETCH=0; HAVE_FASTQDUMP=0');
      out.push('command -v prefetch >/dev/null 2>&1 && HAVE_PREFETCH=1');
      out.push('command -v fasterq-dump >/dev/null 2>&1 && HAVE_FASTQDUMP=1');
      out.push('if [ "$HAVE_PREFETCH" = 0 ]; then');
      out.push('  if [ "$HAVE_CURL" = 1 ] || [ "$HAVE_WGET" = 1 ]; then');
      out.push('    log "未找到 SRA Toolkit 的 prefetch：将改用 ENA/NCBI 的 HTTPS 直链（官方 API 给出的地址）"');
      out.push('  else');
      out.push('    echo "需要 SRA Toolkit（prefetch）或 curl/wget。" >&2');
      out.push('    echo "SRA Toolkit 安装（无需 sudo，解压即用）：" >&2');
      out.push('    echo "  curl -O https://ftp-trace.ncbi.nlm.nih.gov/sra/sdk/current/sratoolkit.current-ubuntu64.tar.gz" >&2');
      out.push('    echo "  tar -xzf sratoolkit.current-ubuntu64.tar.gz" >&2');
      out.push('    exit 2');
      out.push('  fi');
      out.push('fi');
      out.push('log "SRA Toolkit：prefetch=$HAVE_PREFETCH fasterq-dump=$HAVE_FASTQDUMP"');
      out.push('');
      out.push('download_run(){');
      out.push('  local run="$1" dest="$2" want="${3:-}"');
      out.push('  mkdir -p "$(dirname "$dest")"');
      out.push('  if [ -f "$dest" ] && [ ! -d "$dest" ]; then');
      out.push('    log "[SKIP] 已存在：$dest"; SKIPPED=$((SKIPPED+1)); return 0');
      out.push('  fi');
      out.push('  if [ -d "$dest" ] && [ -s "$dest/${run}.sra" ]; then');
      out.push('    log "[SKIP] 已存在：$dest/${run}.sra"; SKIPPED=$((SKIPPED+1)); return 0');
      out.push('  fi');
      out.push('  if [ "$HAVE_PREFETCH" = 1 ]; then');
      out.push('    log "[GET ] prefetch $run -> $dest"');
      out.push('    prefetch --max-size u --output-directory "$(dirname "$dest")" "$run" >>"$LOG" 2>&1');
      out.push('    if [ -d "$dest" ] && [ -s "$dest/${run}.sra" ]; then log "[OK  ] $dest/${run}.sra"; OK=$((OK+1)); return 0; fi');
      out.push('    if [ -f "$dest" ]; then log "[OK  ] $dest"; OK=$((OK+1)); return 0; fi');
      out.push('    log "[WARN] prefetch 失败，改用官方 HTTPS 直链"');
      out.push('  fi');
      out.push('  if [ -n "${SRA_URL[$run]:-}" ]; then');
      out.push('    download_file "${SRA_URL[$run]}" "$dest/${run}.sra" "$want"');
      out.push('  else');
      out.push('    fail "$run 无官方直链且 prefetch 不可用（请安装 SRA Toolkit）"; return 1');
      out.push('  fi');
      out.push('}');
      out.push('');
    }
    out.push('# ================= 数据集 =================');
    list.forEach(function (a) {
      var r = rec(a);
      var d = '$RAW_DIR/' + shellQuote(a);
      out.push('');
      out.push('# ---- ' + a + (useSra
        ? ' · SRA study ' + (r.sra.study || '?') + ' · ' + r.sra.n_runs + ' runs · ' + human(r.sra.bytes)
        : ' · ' + r.geo.n_files + ' files · ' + human(r.geo.bytes)) + ' ----');
      out.push('mkdir -p ' + d);
      if (!useSra) {
        r.geo.files.forEach(function (f) {
          out.push('download_file ' + shellQuote(f.u) + ' ' + d + '/' + shellQuote(slug(f.n)) +
            ' ' + (f.b && f.exact ? String(f.b) : "''"));
        });
      } else {
        var runs = r.sra.runs || [];
        var per = runs.length ? Math.round((r.sra.bytes || 0) / runs.length) : 0;
        // 用官方 runinfo/ENA 给出的每个 run 的体积（有则用精确值）
        // 直链只使用官方 API（ENA fastq_ftp）返回的地址；没有直链时只用 prefetch
        var direct = r.sra.ftp || {};
        if (Object.keys(direct).length) {
          out.push('# 官方 API 给出的 FASTQ 直链（无 prefetch 时使用）');
          out.push('declare -A SRA_URL=()');
          Object.keys(direct).forEach(function (k) {
            out.push('SRA_URL[' + shellQuote(k.split('.')[0]) + ']=' + shellQuote(direct[k]));
          });
        } else {
          out.push('# 官方接口未给出 FASTQ 直链：仅使用 prefetch（未安装时记录失败，不拼造地址）');
        }
        runs.forEach(function (run) {
          var b = (r.sra.run_bytes && r.sra.run_bytes[run]) ? r.sra.run_bytes[run] : (per || '');
          out.push('download_run ' + shellQuote(run) + ' ' + d + '/' + shellQuote(run) + ' ' + (b ? String(b) : "''"));
        });
      }
    });
    out.push('');
    out.push('# ================= 汇总 =================');
    out.push('echo');
    out.push('log "完成：成功 $OK · 跳过（已存在）$SKIPPED · 失败 $FAILED"');
    out.push('if [ "$FAILED" -gt 0 ]; then');
    out.push('  echo "以下条目失败（可重跑本脚本续传，已完整文件会跳过）："');
    out.push('  cat "$FAILED_LIST"');
    out.push('  echo "失败清单：$FAILED_LIST"; echo "日志：$LOG"');
    out.push('  exit 1');
    out.push('fi');
    out.push('echo "全部下载完成。日志：$LOG"');
    if (useSra) {
      out.push('');
      out.push('# ---- FASTQ 转换（默认不执行；需额外磁盘空间）----');
      out.push('# prefetch 只得到 .sra 归档。转 FASTQ 需要 fasterq-dump，');
      out.push('# 空间约为 .sra 的 3-6 倍（压缩 FASTQ 用 --gzip 可减小峰值）。');
      out.push('# 示例（逐个 run 执行）：');
      out.push('#   for f in "$RAW_DIR"/*/*.sra; do fasterq-dump --gzip --outdir "$RAW_DIR/$(basename "$(dirname "$f")")" "$f"; done');
      out.push('# 若本机没有 fasterq-dump，脚本不会自动安装，也不使用 sudo。');
    }
    out.push('');
    out.push('# 说明：本脚本不解压 .tar/.gz（避免自动展开占用大量空间）；');
    out.push('#       需要解包时请自行执行 tar -xf / gunzip。');
    return out.join('\n') + '\n';
  }

  /* ---------------- 下载 / 复制 ---------------- */
  function saveFile(name, text) {
    var blob = new Blob([text], { type: 'text/x-shellscript;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  }

  /* ---------------- UI ---------------- */
  function selectedAccs() { return Object.keys(sel).filter(function (k) { return sel[k]; }).sort(); }

  function bar() {
    var n = selectedAccs().length;
    var el = document.getElementById('dl-bar');
    if (!el) return;
    if (!n) { el.hidden = true; return; }
    el.hidden = false;
    el.querySelector('[data-dl-n]').textContent = n + ' ' + t('n_sel');
    el.querySelector('[data-dl-actions]').innerHTML =
      '<button class="btn primary" data-dl="preview">' + esc(t('gen')) + '</button>' +
      '<button class="btn" data-dl="clear">' + esc(t('clear')) + '</button>';
  }

  function previewDialog() {
    var accs = selectedAccs();
    if (!accs.length) { alert(t('none_selected')); return; }
    var geoAccs = accs.filter(function (a) { var r = rec(a); return r && r.geo.files && r.geo.files.length; });
    var sraAccs = accs.filter(function (a) { var r = rec(a); return r && r.sra && r.sra.available; });
    var missing = accs.filter(function (a) { return !downloadable(a) && !(rec(a) && rec(a).sra && rec(a).sra.available); });
    var geoBytes = geoAccs.reduce(function (s, a) { return s + (rec(a).geo.bytes || 0); }, 0);
    var sraBytes = sraAccs.reduce(function (s, a) { return s + (rec(a).sra.bytes || 0); }, 0);

    var host = document.getElementById('dl-panel');
    var rows = accs.map(function (a) {
      var r = rec(a), g = r ? r.geo : { state: 'unavailable', files: [] }, sra = r ? r.sra : { available: false };
      var state = { verified: 'ok', partial: 'warn', unavailable: 'bad' }[g.state] || 'unk';
      var stateTxt = t(g.state === 'verified' ? 'verified' : g.state === 'partial' ? 'partial' : 'unavailable');
      var files = (g.files || []).slice(0, 6).map(function (f) {
        return '<div class="fl"><span class="mono">' + esc(f.n) + '</span><span class="dim">' +
          (f.b ? human(f.b) + (f.exact ? '' : ' (' + t('approx') + ')') : t('unknown')) + '</span></div>';
      }).join('');
      var more = (g.files || []).length > 6
        ? '<div class="dim">… ' + ((g.files || []).length - 6) + ' more</div>' : '';
      var sraLine = sra.available
        ? '<div class="sra-ok">SRA · study ' + esc(sra.study || '?') + ' · ' + sra.n_runs + ' runs · ' + human(sra.bytes) + '</div>'
        : '<div class="dim">' + esc(t('sra_only_verified')) + '：' + esc(sra.reason || '—') + '</div>';
      return '<div class="dcd"><div class="dhd"><a href="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=' +
        esc(a) + '" target="_blank" rel="noopener"><b>' + esc(a) + '</b></a>' +
        '<span class="chip-t st-' + state + '">' + esc(stateTxt) + '</span>' +
        '<span class="dim">' + (g.files || []).length + ' ' + esc(t('files')) + ' · ' + human(g.bytes) + '</span></div>' +
        (g.files && g.files.length ? '<div class="flist">' + files + more + '</div>'
          : '<div class="bad">' + esc(t('noverify')) + '：' + esc(g.reason || '—') + '</div>') +
        sraLine + '</div>';
    }).join('');

    host.innerHTML =
      '<div class="dlh"><b>' + esc(t('preview')) + '</b>' +
      '<button class="btn x" data-dl="close">✕</button></div>' +
      '<div class="dlnote">' + esc(t('note_browser')) + ' <span class="mono">' +
      esc(t('run_hint')) + '</span></div>' +
      '<div class="dsum"><span class="b ' + (geoAccs.length ? 'g' : 'n') + '">' + t('type_geo') + '：' +
      geoAccs.length + ' · ' + human(geoBytes) + '</span>' +
      '<span class="b ' + (sraAccs.length ? 'o' : 'n') + '">' + t('type_sra') + '：' +
      sraAccs.length + ' · ' + human(sraBytes) + '</span>' +
      (missing.length ? '<span class="b n">' + t('noverify') + '：' + missing.length + '</span>' : '') + '</div>' +
      '<div class="dcards">' + rows + '</div>' +
      '<div class="dlfoot">' +
      (geoAccs.length ? '<button class="btn primary" data-dl="save-geo">' + esc(t('dlsh')) + '</button>' : '') +
      (sraAccs.length ? '<button class="btn" data-dl="save-sra">' + esc(t('dlsh_sra')) + '</button>' +
        '<span class="dim">' + esc(t('note_sra')) + '</span>' : '') +
      '<button class="btn" data-dl="copy-geo">' + esc(t('copies')) + '</button>' +
      '</div>';
    host.hidden = false;
    host.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function bind() {
    document.addEventListener('click', function (e) {
      var b = e.target.closest('[data-dl]');
      if (!b) return;
      var act = b.dataset.dl, accs = selectedAccs();
      if (act === 'preview') return previewDialog();
      if (act === 'close') { document.getElementById('dl-panel').hidden = true; return; }
      if (act === 'clear') { sel = {}; syncBoxes(); bar(); document.getElementById('dl-panel').hidden = true; return; }
      if (act === 'save-geo') {
        var n = accs.filter(function (a) { return downloadable(a); }).length;
        if (!n) return alert(t('noverify'));
        return saveFile('download_datasets.sh', scriptFor(accs, 'geo'));
      }
      if (act === 'save-sra') {
        var n2 = accs.filter(function (a) { var r = rec(a); return r && r.sra.available; }).length;
        if (!n2) return alert(t('sra_only_verified'));
        return saveFile('download_sra.sh', scriptFor(accs, 'sra'));
      }
      if (act === 'copy-geo') {
        var txt = scriptFor(accs, 'geo');
        (navigator.clipboard ? navigator.clipboard.writeText(txt) : Promise.reject())
          .then(function () { b.textContent = t('copied'); setTimeout(function () { b.textContent = t('copies'); }, 1800); })
          ['catch'](function () { alert('clipboard unavailable'); });
        return;
      }
      if (act === 'selectpage') {
        var boxes = document.querySelectorAll('#f-tbl input.dlchk');
        var allOn = Array.prototype.every.call(boxes, function (x) { return x.checked; });
        Array.prototype.forEach.call(boxes, function (x) {
          x.checked = !allOn;
          sel[x.dataset.acc] = !allOn;
          if (!sel[x.dataset.acc]) delete sel[x.dataset.acc];
        });
        b.textContent = allOn ? t('select_page') : t('deselect');
        bar();
        return;
      }
    });
    document.addEventListener('change', function (e) {
      var c = e.target.closest('input.dlchk');
      if (!c) return;
      if (c.checked) sel[c.dataset.acc] = true; else delete sel[c.dataset.acc];
      var head = document.getElementById('dl-all');
      if (head) {
        var boxes = document.querySelectorAll('#f-tbl input.dlchk');
        head.checked = boxes.length > 0 && Array.prototype.every.call(boxes, function (x) { return x.checked; });
      }
      bar();
    });
    document.addEventListener('dsh:lang', function () {
      lang = window.DSH_SITE.getLang();
      bar();
      var p = document.getElementById('dl-panel');
      if (p && !p.hidden) previewDialog();
    });
  }

  function syncBoxes() {
    document.querySelectorAll('#f-tbl input.dlchk').forEach(function (x) {
      x.checked = !!sel[x.dataset.acc];
    });
    var head = document.getElementById('dl-all');
    if (head) head.checked = false;
  }

  window.DSH_DOWNLOADS = {
    toggleAll: function (on) {
      document.querySelectorAll('#f-tbl input.dlchk').forEach(function (x) {
        x.checked = on;
        if (on) sel[x.dataset.acc] = true; else delete sel[x.dataset.acc];
      });
      bar();
    },
    selected: selectedAccs,
    ready: loadDownloads,
    script: function (accs, kind) { return scriptFor(accs, kind); },   // CI/自检用
    bar: bar,
    computeSelected: selectedAccs
  };
  bind();
  document.addEventListener('dsh:tables-rendered', function () { syncBoxes(); bar(); });
  loadDownloads()['catch'](function () { DL = { datasets: {}, stats: {} }; });
})();
