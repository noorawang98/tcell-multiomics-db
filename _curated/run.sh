#!/bin/bash
# ============================================================================
# 一键生成与预览（不需要 sudo）
#
#   bash run.sh              # 完整流程：核实下载地址 -> 生成站点 -> 启动本地预览
#   bash run.sh build        # 只生成，不启动服务器
#   bash run.sh quick        # 跳过网络核实（沿用已有 downloads.json），只重建页面
#   bash run.sh local        # 额外生成“可双击打开”的 site-local/
#   PORT=8902 bash run.sh    # 换端口（默认 8901）
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"
MODE="${1:-all}"
PORT="${PORT:-8901}"

if [ "$MODE" != "quick" ]; then
  echo "[1/5] 初始化（不覆盖已有完整文件）"
  [ -f catalog.sqlite ] || { echo "缺少 catalog.sqlite，无法继续" >&2; exit 1; }
  [ -s downloads.json ] || true
  echo "[2/5] 核实官方下载地址 -> site/data/downloads.json"
  echo "      （只使用 GEO 官方目录列表与官方 suppl/filelist.txt 的文件名，"
  echo "        并按数据集记录中的 BioProject 核实 SRA 关联；失败记录标记为无法核实）"
  python3 export_json.py --site site --repo-name "${DSH_REPO_NAME:-tcell-multiomics-db}"
  timeout "${FETCH_TIMEOUT:-1500}" python3 -u fetch_download_manifest.py \
      --sra --workers "${WORKERS:-6}" --timeout "${HTTP_TIMEOUT:-20}" \
      --head "${HEAD_N:-5}" || echo "  注意：下载地址核实未全部完成（已保留部分结果）"
else
  echo "[1/5] quick 模式：跳过网络核实"
fi

echo "[3/5] 生成疾病类别图标"
python3 make_icons.py

echo "[4/5] 生成静态页面"
python3 build_site.py

if [ "$MODE" = "local" ]; then
  echo "[4b/5] 生成可直接双击打开的版本 site-local/"
  python3 build_site.py --out site-local --inline
fi

cat <<EOF

[5/5] 完成
  部署目录：$(pwd)/site
  下载清单：$(pwd)/site/data/downloads.json
  文件清单：$(pwd)/site/data/datasets.json

预览方式（任选其一）：
  A. 本地服务器（推荐，含 data/ 外链 JSON）
       python3 -m http.server $PORT -d site
       然后浏览器打开   http://127.0.0.1:$PORT/
  B. 双击打开（不需要服务器；需先执行 bash run.sh local）
       site-local/index.html
       site-local/catalog.html
       site-local/guideline.html

注意：直接双击 site/index.html 时，浏览器会拦截 data/*.json 的读取（file:// 安全策略），
      因此请用 A 或先生成 site-local/。这不是端口问题，也不需要开放任何端口。
EOF

if [ "$MODE" = "all" ] || [ "$MODE" = "serve" ]; then
  echo "启动预览服务：http://127.0.0.1:$PORT/   （Ctrl+C 停止）"
  exec python3 -m http.server "$PORT" -d site
fi
