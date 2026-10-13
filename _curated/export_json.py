#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""export_json.py — 从 catalog.sqlite 导出可公开发布的静态 JSON。
catalog.sqlite -> site/data/*.json   （唯一数据源，网页只读 JSON）

用法:
    python3 export_json.py [--site DIR] [--raw-base URL]

字段口径与 build_pages.py 完全一致（integrity / 模态 v2 / matched / 标注）。
不导出任何凭据：只导出 GEO/PubMed 公开元数据与本地文件相对路径。
"""
import argparse, datetime, json, os, re, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "catalog.sqlite")
DEFAULT_SITE = os.path.join(HERE, "site")
GEO_ACC = re.compile(r"^(GSE\d+|GES\d+)$")

# 疾病一级导航顺序（与 annotation.tsv 实际取值一一对应，不新增类别）
DISEASE_ORDER = [
    "B细胞淋巴瘤", "多发性骨髓瘤 MM", "白血病 ALL/CLL/AML", "T细胞淋巴瘤/白血病",
    "胶质母细胞瘤 GBM", "儿童/中枢神经系统肿瘤", "其他实体瘤", "自身免疫/GVHD",
    "感染/病毒", "健康供者/基础", "基础/体外研究",
]
MOD_KEYS = [("scRNA", "rna"), ("bulkRNA", "bulkRNA"), ("scATAC", "atac"), ("bulkATAC", "bulkATAC"),
            ("scTCR", "tcr"), ("bulkTCR", "bulkTCR"), ("methylation", "methyl"), ("CRISPR-screen", "screen")]

ICON_ZH = {"COMPLETE_VERIFIED": "✅ 已验证", "TRUNCATED": "⚠️ 截断",
           "PARTIAL_BROKEN": "⚠️ 部分损坏", "CORRUPT": "❌ 损坏", "FAILED_ALL": "❌ 全部失败",
           "UNVERIFIED": "◻︎ 未对照", "NO_DATA": "❌ 无数据"}
ICON_CSS = {"COMPLETE_VERIFIED": "ok", "TRUNCATED": "warn", "PARTIAL_BROKEN": "warn",
            "CORRUPT": "bad", "FAILED_ALL": "bad", "NO_DATA": "bad", "UNVERIFIED": "unk"}


def b(v):
    return str(v or "").strip() in ("1", "True", "true")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=DEFAULT_SITE, help="输出站点目录（默认 _curated/site）")
    ap.add_argument("--raw-base", default="", help="原始数据根 URL，例如 https://host/GEO_cart")
    ap.add_argument("--repo-name", default="tcell-multiomics-db", help="GitHub 仓库名（用于 Pages 子路径）")
    ap.add_argument("--dataset-links", action="store_true",
                    help="把公开可访问的原始数据 URL 写入 JSON（默认不写，避免链接到受限数据）")
    args = ap.parse_args()

    site = os.path.abspath(args.site)
    data_dir = os.path.join(site, "data")
    os.makedirs(data_dir, exist_ok=True)

    if not os.path.exists(DB):
        sys.exit("缺少 catalog.sqlite：请先运行 rebuild_all.sh")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    ds = {r["accession"]: dict(r) for r in con.execute("SELECT * FROM datasets")}
    ann = {r["accession"]: dict(r) for r in con.execute("SELECT * FROM annotation")}

    # ---- 本地文件清单（只保留 GSE 目录，过滤 .dsh-vision-router 等非数据集行）----
    files = {}
    for r in con.execute("SELECT dataset,relpath,size_bytes,size_human,mtime,status FROM files ORDER BY relpath"):
        if not GEO_ACC.match(r["dataset"] or ""):
            continue
        files.setdefault(r["dataset"], []).append({
            "p": r["relpath"], "s": int(r["size_bytes"] or 0),
            "h": r["size_human"] or "", "m": r["mtime"] or "", "st": r["status"] or "",
        })
    tars = {}
    for r in con.execute("SELECT dataset,tarfile,member FROM tar_members ORDER BY tarfile,member"):
        if not GEO_ACC.match(r["dataset"] or ""):
            continue
        tars.setdefault(r["dataset"], {}).setdefault(r["tarfile"], []).append(r["member"])
    gz_bad = {r[0] for r in con.execute("SELECT relpath FROM gz_integrity WHERE status<>'OK'")}

    out_rows = []
    for acc in sorted(ds):
        d = ds[acc]
        a = ann.get(acc, {})
        size = int(d.get("total_bytes") or 0)
        fs = files.get(acc, [])
        entry = {
            "acc": acc,
            "title": d.get("title") or "",
            "sum": (d.get("summary") or "").strip(),
            "taxon": d.get("taxon") or "",
            "ns": (str(d.get("n_samples") or "").strip() or "—"),
            "nsrc": d.get("n_samples_hdr") or 0,
            "th": a.get("therapy") or "未明确",
            "dis": [x for x in (a.get("diseases") or "").split("|") if x],
            "tct": [x for x in (a.get("tcell_types") or "").split("|") if x],
            "j": a.get("journal") or "",
            "y": str(a.get("year") or ""),
            "au": a.get("authors") or "",
            "ct": a.get("contributor") or "",
            "pmid": (str(a.get("pmid") or "") or str(d.get("pubmed") or "")).strip(),
            "pdat": d.get("pdat") or "",
            "bp": d.get("bioproject") or "",
            "gdstype": d.get("gdstype") or "",
            "design": (a.get("design") or "").strip(),
            "size": size,
            "gb": round(size / 1024 ** 3, 3),
            "tb": round(size / 1024 ** 4, 4),
            "nf": int(d.get("n_files") or 0),
            "ig": d.get("integrity") or "",
            "igc": ICON_CSS.get(d.get("integrity"), "unk"),
            "igz": ICON_ZH.get(d.get("integrity"), d.get("integrity") or "—"),
            "mt": bool(d.get("matched")),
            "nmod": int(d.get("nmod") or 0),
            "mo": d.get("modalities") or "",
            "src": d.get("mod_src") or "",
            "ev": d.get("evidence") or "",
            "rna": b(d.get("scrna")), "atac": b(d.get("scatac")), "tcr": b(d.get("sctcr")),
            "prot": b(d.get("proteome")), "bulkRNA": b(d.get("bulk_rna")),
            "bulkATAC": b(d.get("bulk_atac")), "bulkTCR": b(d.get("bulk_tcr")),
            "methyl": b(d.get("methyl")), "screen": b(d.get("screen")),
            "rc": d.get("rna_class") or "", "ac": d.get("atac_class") or "",
            "tc": d.get("tcr_class") or "", "mc": d.get("methyl_class") or "",
            "nsc": d.get("rna_sc_n") or 0, "nbulk": d.get("rna_bulk_n") or 0,
            "local": {"n": len(fs), "tar": sum(len(v) for v in tars.get(acc, {}).values()),
                      "bad": sum(1 for f in fs if f["p"] in gz_bad),
                      # 浏览器保存的网页（HTML/aspx）不是测序数据，单独标出以免误用
                      "web": sum(1 for f in fs if re.search(r"\.(html|htm|aspx)\b|acc=GSE", f["p"], re.I))},
        }
        if args.dataset_links and args.raw_base:
            rb = args.raw_base.rstrip("/")
            entry["fl"] = [{"u": f"{rb}/{f['p']}", "s": f["s"], "h": f["h"]} for f in fs]
            entry["tar"] = [{"u": f"{rb}/{t}", "mem": len(m)} for t, m in tars.get(acc, {}).items()]
        out_rows.append(entry)

    # ---- 汇总统计 ----
    tot = sum(r["size"] for r in out_rows)
    n_ok = sum(1 for r in out_rows if r["ig"] == "COMPLETE_VERIFIED")
    n_bad = sum(1 for r in out_rows if r["ig"] in ("FAILED_ALL", "CORRUPT", "PARTIAL_BROKEN", "TRUNCATED"))
    meta = {
        "generated": datetime.date.today().isoformat(),
        "gen_ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "repo": args.repo_name,
        "raw_base": args.raw_base,
        "n_ds": len(out_rows),
        "n_samples": sum(int(r["nsrc"] or 0) for r in out_rows),
        "bytes": tot, "tb": round(tot / 1024 ** 4, 3), "gb": round(tot / 1024 ** 3, 1),
        "n_verified": n_ok, "n_issue": n_bad,
        "n_matched": sum(1 for r in out_rows if r["mt"]),
        "n_pub": sum(1 for r in out_rows if r["j"]),
        "n_files": sum(r["local"]["n"] for r in out_rows),
        "n_tarmem": sum(r["local"]["tar"] for r in out_rows),
        "n_local": sum(1 for r in out_rows if r["local"]["n"]),
        "n_bad_gz": len(gz_bad),
        "source": "NCBI GEO（E-utilities + FTP series matrix）+ PubMed 官方记录",
        "mod_keys": [k for k, _ in MOD_KEYS],
    }

    # ---- 疾病类别（一级导航）----
    seen = set()
    for r in out_rows:
        seen.update(r["dis"])
    order = [d for d in DISEASE_ORDER if d in seen] + sorted(seen - set(DISEASE_ORDER))
    cats = []
    for d in order:
        rows = [r for r in out_rows if d in r["dis"]]
        if not rows:
            continue
        mods = {}
        for name, key in MOD_KEYS:
            n = sum(1 for r in rows if r[key])
            if n:
                mods[name] = n
        ths = {}
        for r in rows:
            ths[r["th"]] = ths.get(r["th"], 0) + 1
        cats.append({
            "id": d, "n": len(rows),
            "n_bio": sum(1 for r in rows if r["taxon"] == "Homo sapiens"),
            "n_samples": sum(int(r["nsrc"] or 0) for r in rows),
            "n_matched": sum(1 for r in rows if r["mt"]),
            "n_verified": sum(1 for r in rows if r["ig"] == "COMPLETE_VERIFIED"),
            "n_pub": sum(1 for r in rows if r["j"]),
            "n_cell": sum(1 for r in rows if r["taxon"] != "Homo sapiens"),
            "size": sum(r["size"] for r in rows),
            "tb": round(sum(r["size"] for r in rows) / 1024 ** 4, 3),
            "mods": mods, "ths": ths,
            "accs": [r["acc"] for r in rows],
            "tct": sorted({t for r in rows for t in r["tct"] if t}),
            "y0": min([r["y"] for r in rows if r["y"]] or ["—"]),
            "y1": max([r["y"] for r in rows if r["y"]] or ["—"]),
        })

    # ---- 数据集文件清单（每数据集一个 JSON，供展开查看）----
    fl_dir = os.path.join(data_dir, "files")
    os.makedirs(fl_dir, exist_ok=True)
    for acc in sorted(ds):
        if not GEO_ACC.match(acc):
            continue
        payload = {"acc": acc, "files": files.get(acc, []),
                   "tars": [{"p": t, "n": len(m), "mem": m[:400]} for t, m in sorted(tars.get(acc, {}).items())]}
        with open(os.path.join(fl_dir, acc + ".json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    # ---- 搜索索引（全局搜索用，轻量）----
    idx = [{"a": r["acc"], "t": r["title"][:220], "d": "|".join(r["dis"]), "th": r["th"],
            "c": "|".join(r["tct"]), "j": r["j"], "y": r["y"], "au": r["au"], "ct": r["ct"],
            "mo": ",".join(k for k, kk in MOD_KEYS if r[kk]), "ig": r["igz"],
            "s": r["gb"], "m": 1 if r["mt"] else 0} for r in out_rows]

    def dump(name, obj, pretty=False):
        p = os.path.join(data_dir, name)
        with open(p, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(obj, f, ensure_ascii=False, indent=1)
            else:
                json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        print(f"  {name:22s} {os.path.getsize(p)/1024:8.1f} KB")
        return p

    print("导出 →", site)
    dump("datasets.json", out_rows)
    dump("categories.json", cats)
    dump("meta.json", meta, pretty=True)
    dump("search-index.json", idx)
    print(f"  data/files/*.json      {len([a for a in ds if GEO_ACC.match(a)])} 个数据集文件清单")
    print(f"完成：{len(out_rows)} 数据集 / {len(cats)} 疾病类别 / {tot/1024**4:.3f} TB")


if __name__ == "__main__":
    main()
