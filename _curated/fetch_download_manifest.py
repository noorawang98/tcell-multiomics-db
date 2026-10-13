#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_download_manifest.py — 预先核实各数据集的下载地址，产出 site/data/downloads.json。

设计原则（对应需求）：
  1. **不猜测**：只使用官方元数据给出的文件名。
     - GEO 补充文件：读取官方 suppl 目录列表 + 官方 suppl/filelist.txt（含精确字节数）；
       两者文件名必须一致才算“已核实”。
     - 本地已下载副本仅用于交叉核对（文件名+字节数），不作为文件名来源。
  2. **SRA 仅在关联 accession 经官方核实后才给出**：
     - 证据链 GSE -> datasets.bioproject（GEO 官方 series matrix 字段）
       -> NCBI SRA runinfo / ENA portal（按 BioProject 查询）返回 study_accession 与 run_accession。
     - EGA 等受控访问数据不生成任何下载命令，仅记录“需申请访问”。
  3. 失败的探测不编造结果：标记 verified/unavailable 与原因，网页据此提示“暂无可验证下载链接”。

用法:
    python3 fetch_download_manifest.py                 # 探测全部 GEO 数据集
    python3 fetch_download_manifest.py --datasets GSE168940,GSE151511
    python3 fetch_download_manifest.py --offline       # 只用本地缓存 + catalog.sqlite（不发网络请求）
    python3 fetch_download_manifest.py --sra           # 额外核实 SRA/BioProject 关联（较慢）
    python3 fetch_download_manifest.py --workers 6 --timeout 25
"""
import argparse, concurrent.futures as cf, datetime, gzip, html, json, os, re, sqlite3, sys, time
import urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "catalog.sqlite")
SITE = os.path.join(HERE, "site")
CACHE = os.path.join(HERE, "download_cache")
UA = "tcell-multiomics-db/1.0 (static site manifest builder; contact: repository maintainer)"
GEO_ACC = re.compile(r"^GSE\d+$")

GEO_DIR = "https://ftp.ncbi.nlm.nih.gov/geo/series/{snnn}/{acc}/suppl/"
SRA_RUNINFO = "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc={acc}"
ENA_REPORT = ("https://www.ebi.ac.uk/ena/portal/api/filereport?accession={acc}"
              "&result=read_run&fields=run_accession,study_accession,fastq_ftp,fastq_bytes,sra_bytes"
              "&format=tsv&limit=0")

HREF = re.compile(r'href="([^"?/][^"]*)"[^>]*>')
SIZE_H = re.compile(r'href="[^"]*"[^>]*>\s*[^<]*</a>\s+([\d-]+ [\d:]+)\s+([\d.]+[KMGTP]?)\s*$')
SIZE_MULT = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4, "P": 1024 ** 5}


def human(n):
    n = float(n or 0)
    for u, m in (("TB", 1024 ** 4), ("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if n >= m:
            return f"{n/m:.2f} {u}"
    return f"{int(n)} B"


def fetch(url, timeout=20, retries=1, cache_dir=None):
    """带缓存的 GET（二进制）。cache_dir 为 None 时不缓存。"""
    key = None
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        key = os.path.join(cache_dir, re.sub(r"[^A-Za-z0-9._-]", "_", url)[-160:])
        if os.path.exists(key) and os.path.getsize(key) > 0:
            with open(key, "rb") as f:
                return f.read()
    last = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
                if url.endswith(".gz") and data[:2] == b"\x1f\x8b":
                    data = gzip.decompress(data)
                if key:
                    with open(key, "wb") as f:
                        f.write(data)
                return data
        except Exception as e:                      # 网络/404/超时统一处理
            last = e
            time.sleep(0.8 * (i + 1))
    return {"error": f"{type(last).__name__}: {last}"} if last else {"error": "unknown"}


def list_suppl(acc, timeout=20):
    """官方 suppl 目录列表 → [(filename, size_bytes_or_None), ...]（按出现顺序）。"""
    url = GEO_DIR.format(snnn=acc[:-3] + "nnn", acc=acc)
    raw = fetch(url, timeout=timeout)
    if isinstance(raw, dict):
        return {"error": raw["error"]}
    text = raw.decode("utf-8", "replace")
    if "Index of" not in text:
        return {"error": "suppl 目录列表不可用（可能该数据集无补充文件）"}
    out, order = {}, []
    for line in text.splitlines():
        m = HREF.search(line)
        if not m:
            continue
        name = html.unescape(m.group(1))
        # 排除父目录、外部链接（如页脚的 HHS 政策）与 filelist.txt 本身
        if name.endswith("/") or name in ("filelist.txt",) or "://" in name or name.startswith("../"):
            continue
        if "/" in name:            # suppl 目录下的条目不会含子路径
            continue
        # 目录列表只给四舍五入后的体积，精确体积以 filelist.txt / HEAD 为准
        sm = re.search(r"</a>\s+([\d-]+ [\d:]+)\s+([\d.]+)([KMGTP]?)\s*$", line)
        size = None
        if sm and sm.group(3):
            size = int(float(sm.group(2)) * SIZE_MULT[sm.group(3)])
        out[name] = {"name": name, "url": url + name, "listed_size": size,
                     "mtime": sm.group(1) if sm else ""}
        order.append(name)
    return {"files": [out[n] for n in order]}


def parse_filelist(acc, timeout=20):
    """官方 suppl/filelist.txt → {name: exact_bytes}（只取 File 行；Archive 行单独返回）。"""
    url = GEO_DIR.format(snnn=acc[:-3] + "nnn", acc=acc) + "filelist.txt"
    raw = fetch(url, timeout=timeout)
    if isinstance(raw, dict):
        return {"error": raw["error"]}
    text = raw.decode("utf-8", "replace")
    if not text.startswith("#Archive/File") and "\t" not in text.split("\n")[0]:
        return {"error": "filelist.txt 非官方格式"}
    files, arch = {}, None
    for line in text.splitlines()[1:]:
        p = line.split("\t")
        if len(p) < 5:
            continue
        kind, name, _t, size, _ty = p[0], p[1], p[2], p[3], p[4]
        try:
            size = int(size)
        except ValueError:
            continue
        if kind == "Archive":
            arch = {"name": name, "bytes": size}
        elif kind == "File":
            files[name] = size
    return {"files": files, "archive": arch}


def local_filelist(acc):
    """本地已保存的官方 filelist（离线交叉核对用）。"""
    p = os.path.join(HERE, "geo_filelist", acc + ".txt")
    if not os.path.exists(p):
        return {}
    out = {}
    with open(p, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    if not lines or "Archive/File" not in lines[0]:
        return {}
    for line in lines[1:]:
        p2 = line.split("\t")
        if len(p2) >= 5 and p2[0] == "File":
            try:
                out[p2[1]] = int(p2[3])
            except ValueError:
                pass
    return out


def head_size(url, timeout=20):
    """HEAD 请求核实 URL 可达并取精确字节数（GEO FTP 支持 HEAD）。"""
    class Head(urllib.request.Request):
        def get_method(self):
            return "HEAD"
    try:
        with urllib.request.urlopen(Head(url, headers={"User-Agent": UA}), timeout=timeout) as r:
            cl = r.headers.get("Content-Length")
            return (r.status, int(cl) if cl and cl.isdigit() else None)
    except urllib.error.HTTPError as e:
        return (e.code, None)
    except Exception:
        return (0, None)


def sra_for(bioproject, timeout=30):
    """按 BioProject 查询官方 SRA 元数据（NCBI runinfo 优先，ENA 兜底）。
    仅当返回的 study_accession 与请求的 BioProject 一致时才认为关联已核实。"""
    if not bioproject:
        return {"available": False, "reason": "数据集记录中没有 BioProject accession"}
    runs, study, src = [], None, None
    raw = fetch(SRA_RUNINFO.format(acc=bioproject), timeout=timeout, retries=1)
    if not isinstance(raw, dict):
        lines = raw.decode("utf-8", "replace").splitlines()
        if len(lines) > 1:
            hdr = lines[0].split(",")
            idx = {k: i for i, k in enumerate(hdr)}
            for ln in lines[1:]:
                c = ln.split(",")
                if len(c) < len(hdr):
                    continue
                try:
                    _mb = int(c[idx["size_MB"]]) if idx.get("size_MB") is not None and c[idx["size_MB"]].isdigit() else 0
                except Exception:
                    _mb = 0
                runs.append({"run": c[idx["Run"]], "study": c[idx.get("SRAStudy", 0)],
                             "bioproject": c[idx.get("BioProject", 0)],
                             "bytes": _mb * 1024 * 1024 if _mb else None, "size_mb": _mb or "",
                             "layout": c[idx.get("LibraryLayout", 0)] if "LibraryLayout" in idx else "",
                             "platform": c[idx.get("Platform", 0)] if "Platform" in idx else ""})
            src = "NCBI SRA runinfo"
    if not runs:
        raw = fetch(ENA_REPORT.format(acc=bioproject), timeout=timeout, retries=1)
        if not isinstance(raw, dict):
            lines = [l for l in raw.decode("utf-8", "replace").splitlines() if l.strip()]
            if len(lines) > 1:
                hdr = lines[0].split("\t")
                idx = {k: i for i, k in enumerate(hdr)}
                for ln in lines[1:]:
                    c = ln.split("\t")
                    if len(c) < len(hdr):
                        continue
                    fb = c[idx.get("fastq_bytes", 0)] if "fastq_bytes" in idx else ""
                    sizes = [int(x) for x in fb.split(";") if x.isdigit()] if fb else []
                    ftp = c[idx["fastq_ftp"]] if "fastq_ftp" in idx else ""
                    urls = ["https://" + u for u in ftp.split(";") if u]
                    runs.append({"run": c[idx["run_accession"]], "study": c[idx.get("study_accession", 0)],
                                 "bioproject": bioproject, "size_mb": "",
                                 "bytes": sum(sizes) if sizes else None, "ftp": urls,
                                 "layout": "", "platform": ""})
                src = "ENA portal API"
    if not runs:
        return {"available": False, "reason": "官方 SRA/ENA 查询未返回任何 run（可能原始数据不在 SRA 或受控访问）"}
    studies = {r.get("study") for r in runs if r.get("study")}
    bps = {r.get("bioproject") for r in runs if r.get("bioproject")}
    if bioproject not in bps:
        return {"available": False,
                "reason": f"官方元数据显示 {bioproject} 未直接对应这些 run（study={','.join(sorted(studies))}），不予提供",
                "studies": sorted(studies)}
    study = sorted(studies)[0] if studies else None
    run_bytes = {r["run"]: r["bytes"] for r in runs if r.get("bytes")}
    ftp = {}
    for r in runs:
        for i, u in enumerate(r.get("ftp") or []):
            ftp[r["run"] + (".fq%d" % (i + 1) if len(r["ftp"]) > 1 else "")] = u
    total = sum(run_bytes.values()) if run_bytes else None
    return {"available": True, "source": src, "bioproject": bioproject, "study": study,
            "runs": [r["run"] for r in runs], "n_runs": len(runs), "bytes": total,
            "run_bytes": run_bytes,
            # 直链来自官方 API（ENA fastq_ftp），仅在存在时提供
            "ftp": ftp or None,
            "size_note": ("run 体积为官方 size_MB 换算的估算值" if src == "NCBI SRA runinfo" else "run 体积来自 ENA fastq_bytes"),
            "license_hint": "SRA 公开数据（Consent: public）", "checked": datetime.date.today().isoformat()}


def exact_sizes(files, exact, arch, lfl, args):
    """给每个文件补上精确字节数，并统计核实方式。"""
    for f in files:
        n = f["n"]
        if n in exact:                                     # 官方 filelist.txt（File 行）
            f["b"], f["size_src"] = exact[n], "filelist.txt(精确)"
        elif arch and arch.get("name") == n:                # 官方 filelist.txt（Archive 行）
            f["b"], f["size_src"] = arch.get("bytes"), "filelist.txt(精确)"
        elif n in lfl:                                      # 本地保存的官方 filelist
            f["b"], f["size_src"] = lfl[n], "local-filelist(精确)"
        else:
            f["size_src"] = "dir-list(四舍五入)" if f.get("b") else "unknown"
        f["local_match"] = bool(n in lfl and f.get("b") and lfl[n] == f["b"])
    # 分类：已精确 / 仅有四舍五入值 / 无大小
    for f in files:
        f["exact"] = f["size_src"].endswith("(精确)") or f["size_src"].startswith("HEAD")


def head_refine(files, args):
    """用 HEAD 请求核实 URL 可达（GEO FTP 支持 HEAD，返回精确 Content-Length）。
    抽样上限 args.head；--all-sizes 时对全部文件核实。"""
    if not files:
        return
    idxs = list(range(len(files))) if args.all_sizes else list(range(0, len(files), max(1, len(files) // args.head)))[:args.head] if args.head else []
    idxs = sorted(set(idxs))

    def one(i):
        st, sz = head_size(files[i]["u"], timeout=args.timeout)
        return i, st, sz

    for i, st, sz in map(one, idxs):
        files[i]["head"] = st
        if st == 200 and sz:
            files[i]["b"], files[i]["size_src"], files[i]["exact"] = sz, "HEAD(Content-Length)", True


def process(acc, args, bp=""):
    """核实单个数据集的官方下载地址。只使用官方元数据给出的文件名与地址，绝不猜测。"""
    rec = {"acc": acc, "bioproject": bp or "",
           "geo": {"state": "unavailable", "files": [], "n_files": 0, "bytes": 0,
                   "n_exact": 0, "n_known_size": 0, "bad_urls": []},
           "sra": {"available": False, "reason": "未核实（使用 --sra 开启 SRA/BioProject 核实）"}}
    lst = list_suppl(acc, timeout=args.timeout)
    if "error" in lst:
        rec["geo"]["reason"] = lst["error"]
        rec["geo"]["official_dir"] = GEO_DIR.format(snnn=acc[:-3] + "nnn", acc=acc)
    else:
        fl = parse_filelist(acc, timeout=args.timeout)
        exact = fl.get("files", {}) if "error" not in fl else {}
        arch = fl.get("archive") if "error" not in fl else None
        lfl = local_filelist(acc)
        files = [{"n": f["name"], "u": f["url"], "b": f.get("listed_size"), "mtime": f.get("mtime", "")}
                 for f in lst["files"]]
        exact_sizes(files, exact, arch, lfl, args)
        head_refine(files, args)
        bad = [f["n"] for f in files if f.get("head") not in (None, 200)]
        total = sum(f["b"] for f in files if f.get("b"))
        n_exact = sum(1 for f in files if f.get("exact"))
        n_known = sum(1 for f in files if f.get("b"))
        # 状态：全部文件都有精确体积且 URL 可达 → verified；否则 partial
        state = "verified" if (files and not bad and n_exact == len(files)) else ("partial" if files else "unavailable")
        rec["geo"] = {
            "state": state, "files": files, "n_files": len(files), "bytes": total,
            "n_exact": n_exact, "n_known_size": n_known, "bad_urls": bad,
            "official_dir": GEO_DIR.format(snnn=acc[:-3] + "nnn", acc=acc),
            "archive": arch, "checked": datetime.date.today().isoformat(),
            "official_filelist": sorted(exact.keys())[:400] if exact else [],
            "local_filelist_matches": sum(1 for f in files if f.get("local_match")),
        }
        if not files:
            rec["geo"]["reason"] = "官方 suppl 目录中没有补充文件"
        elif bad:
            rec["geo"]["reason"] = f"有 {len(bad)} 个地址 HEAD 请求未返回 200，已标记为不可用"
        elif n_exact < len(files):
            rec["geo"]["reason"] = f"其中 {len(files) - n_exact} 个文件只能得到四舍五入体积"
    if args.sra:
        rec["sra"] = sra_for(bp, timeout=max(args.timeout, 30))
    return rec


def build_payload(out, args):
    """把结果整理为可发布的 downloads.json 结构（含汇总统计）。"""
    st = {
        "n": len(out),
        "verified": sum(1 for r in out.values() if r["geo"]["state"] == "verified"),
        "partial": sum(1 for r in out.values() if r["geo"]["state"] == "partial"),
        "unavailable": sum(1 for r in out.values() if r["geo"]["state"] == "unavailable"),
        "sra_available": sum(1 for r in out.values() if r["sra"].get("available")),
        "n_files": sum(len(r["geo"].get("files", [])) for r in out.values()),
        "n_files_exact": sum(r["geo"].get("n_exact", 0) for r in out.values()),
        "n_files_approx": sum(r["geo"].get("n_known_size", 0) - r["geo"].get("n_exact", 0) for r in out.values()),
        "bytes": sum(r["geo"].get("bytes") or 0 for r in out.values()),
        "sra_bytes": sum(r["sra"].get("bytes") or 0 for r in out.values() if r["sra"].get("available")),
        "n_local_checked": sum(1 for r in out.values() if r["geo"].get("local_filelist_matches")),
    }
    return {
        "generated": datetime.date.today().isoformat(),
        "gen_ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mode": "offline(local only)" if args.offline else "online",
        "source": {
            "zh": "GEO 官方 suppl 目录列表 + 官方 suppl/filelist.txt（精确字节数）+ HEAD 抽样核实；"
                  "SRA 关联来自 NCBI SRA runinfo / ENA portal API（按数据集记录中的 BioProject 查询）",
            "en": "GEO official suppl directory listing + official suppl/filelist.txt (exact bytes) + sampled "
                  "HEAD checks; SRA linkage from NCBI SRA runinfo / ENA portal API, queried by the BioProject "
                  "recorded in the series metadata",
        },
        "policy": {
            "zh": "文件名与地址只取自官方元数据，绝不由 GSE 编号推测；无法核实的记录不给下载命令。",
            "en": "File names and URLs come from official metadata only and are never inferred from a GEO ID; "
                  "records that cannot be verified produce no download command.",
        },
        "stats": st,
        "datasets": out,
    }


def write_payload(out, args, quiet=False):
    payload = build_payload(out, args)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, args.out)
    if not quiet:
        print(f"\n写出 {args.out}  {os.path.getsize(args.out)/1024:.1f} KB")
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="", help="逗号分隔的 GSE 列表（默认全部）")
    ap.add_argument("--out", default=os.path.join(SITE, "data", "downloads.json"))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--head", type=int, default=5, help="每个数据集抽样 HEAD 核实的文件数（0=关闭）")
    ap.add_argument("--all-sizes", action="store_true", help="对每个文件都做 HEAD 核实（最准确，最慢）")
    ap.add_argument("--sra", action="store_true", help="同时核实 SRA/BioProject 关联（较慢）")
    ap.add_argument("--offline", action="store_true", help="不发网络请求，只用本地缓存与 catalog.sqlite")
    ap.add_argument("--force", action="store_true", help="忽略 --out 中已有结果，全部重跑")
    args = ap.parse_args()
    if args.offline:
        args.head = 0
        args.all_sizes = False
        args.sra = False

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    meta = {r["accession"]: dict(r) for r in con.execute("SELECT accession,bioproject,taxon FROM datasets")}
    accs = [a for a in meta if GEO_ACC.match(a)]
    if args.datasets:
        want = {x.strip() for x in args.datasets.split(",") if x.strip()}
        accs = [a for a in accs if a in want]
    accs.sort()

    # 断点续跑：把 --out 里已完成且仍存在的结果直接沿用（--force 可全部重跑）
    out = {}
    if os.path.exists(args.out) and not args.force:
        try:
            old = json.load(open(args.out, encoding="utf-8")).get("datasets", {})
            out = {k: v for k, v in old.items() if k in accs and k in meta}
        except Exception:
            out = {}
    todo = [a for a in accs if a not in out]
    print(f"核实下载地址：目标 {len(accs)} 个数据集 · 沿用已有 {len(out)} 条 · 本次待查 {len(todo)} 条"
          f"（workers={args.workers}, head={args.head}, all_sizes={args.all_sizes}, sra={args.sra}）")
    if not todo:
        write_payload(out, args)
        print("无需新增核实。")
        return

    done, t0 = 0, time.time()
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process, a, args, meta[a].get("bioproject") or ""): a for a in todo}
        for fu in cf.as_completed(futs):
            a = futs[fu]
            try:
                out[a] = fu.result()
            except Exception as e:
                out[a] = {"acc": a, "geo": {"state": "unavailable", "reason": f"核实异常：{e}", "files": []},
                          "sra": {"available": False, "reason": "未核实"}}
            done += 1
            g = out[a]["geo"]
            print(f"  [{done}/{len(todo)} {time.time()-t0:5.0f}s] {a:12s} {g['state']:11s} "
                  f"files={len(g.get('files', [])):3d} exact={g.get('n_exact', 0):3d} {human(g.get('bytes')):>10s}"
                  + (f"  SRA {out[a]['sra'].get('n_runs')} runs" if out[a]["sra"].get("available") else ""),
                  flush=True)
            # 每完成一条就落盘：网络中断也不会丢掉已完成结果
            if done % 3 == 0:
                write_payload(out, args, quiet=True)

    payload = write_payload(out, args)
    st = payload["stats"]
    print(f"  已核实 {st['verified']} · 部分核实 {st['partial']} · 无法核实 {st['unavailable']} · "
          f"SRA 可用 {st['sra_available']}")
    print(f"  文件 {st['n_files']}（精确体积 {st['n_files_exact']} / 近似 {st['n_files_approx']}）· "
          f"GEO 合计 {human(st['bytes'])} · SRA 合计 {human(st['sra_bytes'])}")


if __name__ == "__main__":
    main()
