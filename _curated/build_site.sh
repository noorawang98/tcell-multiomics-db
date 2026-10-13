#!/bin/bash
# 一步重建可发布站点：catalog.sqlite -> site/data/*.json -> site/*.html
#
#   bash build_site.sh              # 站内页面（外链 JSON，用于 GitHub Pages 部署）
#
# 生成后：
#   python3 -m http.server 8901 -d site      # 浏览器预览（推荐）
#   直接双击 site/index.html                  # 需要 --inline 版本，见下
#
# 想直接双击打开（file://，无需任何服务器）：
#   python3 build_site.py --out site-local --inline
#   然后双击 site-local/index.html
set -e
cd "$(dirname "$0")"
python3 export_json.py --site site --repo-name "${DSH_REPO_NAME:-tcell-multiomics-db}"
python3 make_icons.py
python3 build_site.py
echo
echo "完成：$PWD/site"
echo "预览（任选其一）："
echo "  1) python3 -m http.server 8901 -d site   →  http://127.0.0.1:8901/"
echo "  2) python3 build_site.py --out site-local --inline  →  双击 site-local/index.html"
