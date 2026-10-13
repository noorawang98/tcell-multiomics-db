#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_site.py — 生成可部署到 GitHub Pages 的静态站点（中英双语可切换）。

输入：site/data/*.json（由 export_json.py 从 catalog.sqlite 导出）
     site_content.py（类别与界面文案唯一来源）
     site/assets/app.css · site/assets/site.js · site/assets/icons/*（由 make_icons.py 生成）
输出：site/index.html、site/catalog.html、site/guideline.html、
     site/pages/<疾病类别>.html、site/404.html、site/.nojekyll

页面全部为静态文件，运行时只读取同目录下的 JSON，无后端依赖。
"""
import html, json, os, shutil, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import site_content as SC

SITE = os.path.join(HERE, "site")
DATA = os.path.join(SITE, "data")
DEFAULT_REPO = "tcell-multiomics-db"   # 仅作 meta.repo 记录；实际子路径由 data-base 相对解析

INLINE_MODE = False     # --inline：把 JSON 内联进页面，使 file:// 双击打开也能用
INLINE_CACHE = {}       # 页面名 -> 已生成的 <script> 块

# 各页面需要内联的资源（按页裁剪，避免每页都塞入全部数据）
INLINE_SETS = {
    "index.html": ["meta", "categories", "downloads"],
    "catalog.html": ["meta", "categories", "downloads", "datasets", "search-index"],
    "guideline.html": ["meta", "categories", "datasets"],
    "404.html": [],
}
for _n in range(1, 32):
    INLINE_SETS["pages/c%02d.html" % _n] = ["meta", "categories", "datasets", "downloads"]


def inline_block(filename):
    """为某个页面生成内联数据 <script>（--inline 模式）。"""
    if not INLINE_MODE:
        return ""
    if filename in INLINE_CACHE:
        return INLINE_CACHE[filename]
    names = INLINE_SETS.get(filename)
    if names is None:
        names = ["meta", "datasets", "downloads"]
    payload = {}
    for n in names:
        d = _read_json(n + ".json")
        if d is not None:
            payload[n] = d
    block = ('<script id="dsh-inline" type="application/json">' + jdump(payload) + '</script>\n'
             '<script>window.DSH_INLINE=(JSON.parse('
             'document.getElementById("dsh-inline").textContent)||{});</script>')
    INLINE_CACHE[filename] = block
    return block

MENU = [("home", "index.html", "nav_home"), ("catalog", "catalog.html", "nav_catalog"),
        ("guideline", "guideline.html", "nav_guideline")]


def jdump(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def page(filename, base, page_id, title_zh, title_en, body, cat=None, filter_=None, desc="",
         downloads_ui=False):
    """生成一页完整 HTML。base = '.', '..' 等（GitHub Pages 子路径下相对引用）。"""
    # 类别页位于 site/pages/ 下，顶栏与品牌链接必须带 ../ 前缀，否则会指向 pages/index.html
    navbase = "" if base == "." else base + "/"
    navs = "".join(
        f'<a data-nav="{pid}" href="{navbase}{f}" data-i18n="{key}">{SC.UI[key]["zh"]}</a>'
        for pid, f, key in MENU)
    dlbar = ("""
<div class="dlbar" id="dl-bar" hidden><span class="dlcount" data-dl-n=""></span>
  <span class="dlacts" data-dl-actions=""></span>
  <button class="btn" data-dl="selectpage" data-i18n="select_page">选择当前筛选结果</button>
</div>
<div class="dlpanel" id="dl-panel" hidden></div>""" if downloads_ui else "")
    catattr = f' data-cat="{html.escape(cat)}"' if cat else ""
    titleattr = (f' data-title-zh="{html.escape(title_zh)}" data-title-en="{html.escape(title_en)}"')
    filt = f' data-filter="{filter_}"' if filter_ else ""
    sprite = open(os.path.join(SITE, "assets", "icons", "sprite-inline.html"), encoding="utf-8").read()
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-base="{base}" data-page="{page_id}"{catattr}{filt}{titleattr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{html.escape(desc or SC.UI['site_sub']['zh'])}">
<meta name="generator" content="DSH static site builder · Built with Deepseek Harness assistant">
<title>{html.escape(title_zh)}</title>
<link rel="icon" href="{base}/assets/icons/sprite.svg" type="image/svg+xml">
<link rel="stylesheet" href="{base}/assets/app.css">
</head>
<body>
{sprite}
<header class="top"><div class="topin">
  <a class="brand" href="{navbase}index.html"><span class="mk">T</span><span>{SC.UI['site_name']['zh']}<small>{SC.UI['site_sub']['zh']}</small></span></a>
  <nav class="main">{navs}</nav>
  <span class="spacer"></span>
  <div class="searchbox">
    <input id="q-global" type="search" autocomplete="off" placeholder="{SC.UI['search_ph']['zh']}" aria-label="search">
    <div class="sres" id="q-global-res" role="listbox"></div>
  </div>
  <div class="langsw" role="group" aria-label="language">
    <button data-lang="zh" type="button">中文</button><button data-lang="en" type="button">EN</button>
  </div>
</div></header>
<main class="wrap">
{body}
{dlbar}
<footer class="foot">
  <div data-i18n="footer_src">{SC.UI['footer_src']['zh']}</div>
  <div>{SC.UI['site_sub']['zh']} · <span id="meta-line">…</span></div>
  <div data-i18n="footer_copy">{SC.UI['footer_copy']['zh']}</div>
  <div class="built">{SC.UI['footer_built']['zh']}</div>
</footer>
</main>
<script id="dsh-manifest" type="application/json">{jdump({})}</script>
<script id="dsh-i18n" type="application/json">{jdump(SC.UI)}</script>
{inline_block(filename)}
<script src="{base}/assets/site.js"></script>
<script src="{base}/assets/downloads.js"></script>
</body></html>
"""


def _read_json(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def manifest_payload(meta):
    """注入页面的静态标签表与元数据（含 label 映射，供前端双语渲染）。

    页面内嵌部分剔除 gen_ts（生成时刻），使重复构建产出逐字节一致，
    便于用 git 校验「重建结果 == 提交内容」。
    """
    meta = {k: v for k, v in meta.items() if k != "gen_ts"}
    cat_meta = {}
    for c in SC.CATEGORIES:
        cat_meta[c["id"]] = {"icon": c["icon"], "color": c["color"], "zh": c["zh"], "en": c["en"],
                             "name_zh": c["zh"], "name_en": c["en"],
                             "desc_zh": c["desc_zh"], "desc_en": c["desc_en"]}
    return {
        "meta": meta,
        "th_label": {k: {"zh": k, "en": SC.THERAPY_EN.get(k, k)} for k in SC.THERAPIES},
        "tct_label": {k: {"zh": k, "en": SC.TCT_EN.get(k, k)} for k in SC.TCT},
        "tct_desc": {k: {"zh": SC.TCT_DESC_ZH.get(k, ""), "en": SC.TCT_DESC_EN.get(k, "")} for k in SC.TCT},
        "mod_label": {k: {"zh": k, "en": v} for k, v in SC.MOD_EN.items()},
        "mod_desc": {k: {"zh": SC.MOD_DESC_ZH.get(k, ""), "en": SC.MOD_DESC_EN.get(k, "")} for k in SC.MOD_EN},
        "ig_label": {"COMPLETE_VERIFIED": {"zh": "✅ 已验证", "en": SC.IG_EN["COMPLETE_VERIFIED"]},
                     "UNVERIFIED": {"zh": "◻︎ 未对照", "en": SC.IG_EN["UNVERIFIED"]},
                     "TRUNCATED": {"zh": "⚠️ 截断", "en": SC.IG_EN["TRUNCATED"]},
                     "PARTIAL_BROKEN": {"zh": "⚠️ 部分损坏", "en": SC.IG_EN["PARTIAL_BROKEN"]},
                     "CORRUPT": {"zh": "❌ 损坏", "en": SC.IG_EN["CORRUPT"]},
                     "FAILED_ALL": {"zh": "❌ 全部失败", "en": SC.IG_EN["FAILED_ALL"]},
                     "NO_DATA": {"zh": "❌ 无数据", "en": SC.IG_EN["NO_DATA"]}},
        "ig_desc": {k: {"zh": SC.IG_DESC_ZH.get(k, ""), "en": SC.IG_DESC_EN.get(k, "")} for k in SC.INTEGRITY},
        "cat_label": {c["id"]: {"zh": c["zh"], "en": c["en"]} for c in SC.CATEGORIES},
        "cat_slug": SC.SLUG_BY_ID,
        "page_cat": {c["id"]: f'pages/{c["slug"]}.html' for c in SC.CATEGORIES},
        "cat_meta": cat_meta,
        "keys": ["COMPLETE_VERIFIED", "UNVERIFIED", "TRUNCATED", "PARTIAL_BROKEN", "CORRUPT", "FAILED_ALL", "NO_DATA"],
        "mod_keys": list(SC.MOD_EN.keys()),
        # 只内嵌统计摘要（明细约 330 KB，线上走 data/downloads.json，
        # --inline 构建时由 DSH_INLINE.downloads 提供完整清单）
        "dl_stats": (lambda d: (d or {}).get("stats"))(_read_json("downloads.json")),
    }


# 注意：除 meta.gen_ts（生成时刻）外，本脚本输出是确定性的，
# 便于 git 中比较「重建是否与提交一致」；页面不含任何硬编码站点 URL。
def build_index(meta):
    kpis = [
        ("stat_ds", f'{meta["n_ds"]}'), ("stat_samples", f'{meta["n_samples"]:,}'),
        ("stat_bytes", f'{meta["gb"]} GB'), ("stat_verified", f'{meta["n_verified"]}'),
        ("stat_matched", f'{meta["n_matched"]}'), ("stat_pub", f'{meta["n_pub"]}'),
        ("stat_cats", f'{len(SC.CATEGORIES)}'),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><i data-i18n="{k}">{SC.UI[k]["zh"]}</i><b{" class=g" if k in ("stat_verified", "stat_matched") else ""}>{v}</b></div>'
        for k, v in kpis)
    body = f"""<h1 data-i18n="h1_home">{SC.UI['site_title']['zh']}</h1>
<div class="sub"><span id="meta-line">…</span></div>
<div class="kpis">{kpi_html}</div>
<div class="note"><b data-i18n="browse_disease">{SC.UI['browse_disease']['zh']}</b>
  <span data-i18n="disease_intro">{SC.UI['disease_intro']['zh']}</span></div>
<h2 data-i18n="browse_disease">{SC.UI['browse_disease']['zh']}</h2>
<div class="cgrid" id="cat-grid"><div class="loading">loading…</div></div>
<h2 data-i18n="nav_guideline">{SC.UI['nav_guideline']['zh']}</h2>
<div class="note"><span data-i18n="catalog_hint">{SC.UI['catalog_hint']['zh']}</span>
  <a href="catalog.html" data-i18n="page_catalog">{SC.UI['page_catalog']['zh']}</a> ·
  <a href="guideline.html" data-i18n="page_guideline">{SC.UI['page_guideline']['zh']}</a></div>
"""
    return page("index.html", ".", "home", SC.UI["site_title"]["zh"], SC.UI["site_title"]["en"], body,
                desc="T-cell multi-omics database: disease categories, datasets, omics modalities and integrity status.")


def build_catalog(meta):
    body = f"""<h1 data-i18n="page_catalog">{SC.UI['page_catalog']['zh']}</h1>
<div class="sub"><span id="meta-line">…</span> ·
  <a href="guideline.html" data-i18n="nav_guideline">{SC.UI['nav_guideline']['zh']}</a></div>
<div class="note"><span data-i18n="catalog_hint">{SC.UI['catalog_hint']['zh']}</span></div>
<div id="tbl-host"><div class="loading">loading…</div></div>
"""
    return page("catalog.html", ".", "catalog", SC.UI["site_title"]["zh"], SC.UI["site_title"]["en"], body,
                downloads_ui=True)


def build_category(meta, cat):
    c = SC.CAT_BY_ID[cat]
    body = f"""<div id="cat-head"><div class="loading">loading…</div></div>
<div id="tbl-host"><div class="loading">loading…</div></div>
<div class="note"><a href="../catalog.html" data-i18n="nav_catalog">{SC.UI['nav_catalog']['zh']}</a> ·
  <a href="../guideline.html" data-i18n="nav_guideline">{SC.UI['nav_guideline']['zh']}</a></div>
"""
    return page(f'pages/{c["slug"]}.html', "..", "category", f'{c["zh"]} · {SC.UI["site_name"]["zh"]}',
                f'{c["en"]} · {SC.UI["site_name"]["en"]}', body, cat=cat, desc=c["desc_en"],
                downloads_ui=True)


def build_guideline(meta):
    body = f"""<h1 data-i18n="page_guideline">{SC.UI['page_guideline']['zh']}</h1>
<div class="sub"><span id="meta-line">…</span></div>
<div id="gl"><div class="loading">loading…</div></div>
"""
    return page("guideline.html", ".", "guideline", SC.UI["page_guideline"]["zh"], SC.UI["page_guideline"]["en"], body)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="生成静态站点")
    ap.add_argument("--out", default=SITE,
                    help="输出目录（默认 _curated/site；可用 site-local 生成可双击打开的版本）")
    ap.add_argument("--inline", action="store_true",
                    help="把 data/*.json 内联进页面，使 file:// 双击打开也能用（页面变大）")
    args = ap.parse_args()
    meta = json.load(open(os.path.join(DATA, "meta.json"), encoding="utf-8"))
    cats = json.load(open(os.path.join(DATA, "categories.json"), encoding="utf-8"))
    for c in cats:                      # slug 由 site_content 统一定义，不依赖导出快照
        c["slug"] = SC.SLUG_BY_ID[c["id"]]
    repo = os.environ.get("DSH_REPO_NAME") or meta.get("repo") or DEFAULT_REPO
    meta["repo"] = repo   # 页面不需要硬编码站点 URL：子路径由 data-base 相对解析
    payload = manifest_payload(meta)
    if args.inline:
        payload["downloads"] = None          # 由 DSH_INLINE 提供，避免重复
    mjson = jdump(payload)

    global INLINE_MODE
    INLINE_MODE = bool(args.inline)

    OUT = os.path.abspath(args.out)
    assert os.path.abspath(SITE) == OUT or not os.path.exists(OUT) or os.path.isdir(OUT), OUT
    os.makedirs(os.path.join(OUT, "pages"), exist_ok=True)
    written = []

    def w(path, content):
        p = os.path.join(OUT, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        written.append((path, len(content)))

    # 页面共用的 manifest / i18n 注入：page() 内已写出占位，这里回填真实内容
    def fill(content):
        content = content.replace('<script id="dsh-manifest" type="application/json">{}</script>',
                                  f'<script id="dsh-manifest" type="application/json">{mjson}</script>')
        return content

    w("index.html", fill(build_index(meta)))
    w("catalog.html", fill(build_catalog(meta)))
    w("guideline.html", fill(build_guideline(meta)))
    for c in cats:
        w(f'pages/{c["slug"]}.html', fill(build_category(meta, c["id"])))
    # 404：GitHub Pages 上直接用相对路径回首页（不依赖仓库名）
    w("404.html", """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>404 · 页面不存在</title>
<link rel="stylesheet" href="./assets/app.css"></head><body><main class="wrap">
<h1>404 · 页面不存在 / Page not found</h1>
<p class="sub">请从首页重新进入：<a href="./index.html">首页 Home</a> · <a href="./catalog.html">数据集目录 Catalog</a> ·
<a href="./guideline.html">关系与判定指南 Relations &amp; methods</a></p>
<p class="sub">The requested page is not part of this static site. Raw data is not published here.</p>
</main></body></html>
""")
    w(".nojekyll", "")  # 关闭 Jekyll，保证 _ 前缀文件与 assets 目录原样发布
    # assets/ 与 data/ 原样复制到输出目录（site-local 等自定义目录需要）
    if os.path.abspath(OUT) != os.path.abspath(SITE):
        for sub in ("assets", "data"):
            src, dst = os.path.join(SITE, sub), os.path.join(OUT, sub)
            if os.path.isdir(src):
                shutil.rmtree(dst, ignore_errors=True)
                # 逐文件读写复制：某些挂载（FUSE/NTFS）不支持 copystat，copytree 会失败
                for root, _dirs, names in os.walk(src):
                    rel = os.path.relpath(root, src)
                    target = dst if rel == "." else os.path.join(dst, rel)
                    os.makedirs(target, exist_ok=True)
                    for n in names:
                        with open(os.path.join(root, n), "rb") as fi, \
                             open(os.path.join(target, n), "wb") as fo:
                            fo.write(fi.read())
    for name, size in written:
        print(f"  {name:28s} {size/1024:7.1f} KB")
    tot = sum(s for _, s in written)
    print(f"输出目录：{OUT}")
    print(f"完成：{len(written)} 个页面 / {tot/1024:.0f} KB · 仓库名 {repo} · "
          f"base 通过 data-base 自适应子路径 · "
          f"{'内联数据（可直接双击打开）' if args.inline else '外链 JSON'}")


if __name__ == "__main__":
    main()
