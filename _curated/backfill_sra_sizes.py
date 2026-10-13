#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backfill_sra_sizes.py — 为已有 downloads.json 补齐 SRA 每个 run 的官方体积。

不重新核实 GEO 文件清单，只按 BioProject 重新查询 NCBI SRA runinfo（或 ENA），
把每个 run 的字节数写回 json，使网页能显示 SRA 下载量与所需空间。
用法： python3 backfill_sra_sizes.py [--workers 6] [--only-missing]
"""
import argparse, concurrent.futures as cf, importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fdm", os.path.join(HERE, "fetch_download_manifest.py"))
fdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fdm)
DL = os.path.join(HERE, "site", "data", "downloads.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only-missing", action="store_true", help="只补 run_bytes 缺失的数据集")
    ap.add_argument("--out", default=DL)
    args = ap.parse_args()

    data = json.load(open(args.out, encoding="utf-8"))
    targets = [a for a, r in data["datasets"].items()
               if r["sra"].get("available") and (not args.only_missing or not r["sra"].get("run_bytes"))]
    print(f"需要补齐 SRA run 体积的数据集：{len(targets)}")
    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fdm.sra_for, data["datasets"][a]["bioproject"], 30): a for a in targets}
        for fu in cf.as_completed(futs):
            a = futs[fu]
            try:
                new = fu.result()
            except Exception as e:
                print(f"  {a} 查询失败：{e}")
                continue
            if new.get("available"):
                old = data["datasets"][a]["sra"]
                old.update({k: v for k, v in new.items() if v is not None})
                data["datasets"][a]["sra"] = old
            done += 1
            if done % 10 == 0:
                json.dump(data, open(args.out + ".tmp", "w", encoding="utf-8"),
                          ensure_ascii=False, separators=(",", ":"))
                os.replace(args.out + ".tmp", args.out)
                print(f"  [{done}/{len(targets)}] 已写入检查点", flush=True)

    sra_bytes = sum(r["sra"].get("bytes") or 0 for r in data["datasets"].values() if r["sra"].get("available"))
    data["stats"]["sra_bytes"] = sra_bytes
    data["stats"]["sra_with_size"] = sum(1 for r in data["datasets"].values()
                                         if r["sra"].get("available") and r["sra"].get("run_bytes"))
    json.dump(data, open(args.out + ".tmp", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    os.replace(args.out + ".tmp", args.out)
    print(f"完成：SRA 合计 {sra_bytes/1024**4:.2f} TB · 有体积信息的数据集 {data['stats']['sra_with_size']}")


if __name__ == "__main__":
    main()
