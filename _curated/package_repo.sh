#!/bin/bash
# ============================================================================
# 打包可发布的仓库：站点文件放在仓库【根目录】，构建工具放在 _curated/
#
#   bash package_repo.sh
#   REPO=/tmp/x OUT=/path bash package_repo.sh     # 自定义暂存/输出目录
#
# 产物（默认写入 <仓库根>/_repo_build/）：
#   tcell-multiomics-db.zip        ← 解压后根目录就是站点，可直接 push
#   gh-pages-site.zip              ← 只含站点文件（用于覆盖 gh-pages 分支）
#   tcell-multiomics-db.bundle     ← git clone 用
# ============================================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$HERE/README.md" ] && [ -d "$HERE/_curated" ]; then SRC="$HERE"
elif [ -f "$HERE/../README.md" ] && [ -d "$HERE/../_curated" ]; then SRC="$(cd "$HERE/.." && pwd)"
else SRC="$HERE"; fi
REPO="${REPO:-/tmp/tcell-db-repo}"
OUT="${OUT:-$SRC/_repo_build}"
mkdir -p "$OUT"

copy_tree() {   # 逐文件复制（部分挂载不支持 copystat）
  local from="$1" to="$2"
  mkdir -p "$to"
  (cd "$from" && find . -type f -print0 | while IFS= read -r -d '' f; do
      mkdir -p "$to/$(dirname "$f")"; cp "$f" "$to/$f"
   done)
}

echo "[1/4] 生成站点（catalog.sqlite → site/data/*.json → 页面）"
cd "$SRC/_curated"
WS_REMOTE="$(git -C "$SRC" remote get-url origin 2>/dev/null | sed 's#.*/##; s#\.git$##' || true)"
python3 export_json.py --site site --repo-name "${DSH_REPO_NAME:-${WS_REMOTE:-tcell-multiomics-db}}" >/dev/null
python3 make_icons.py >/dev/null
python3 build_site.py | tail -1

echo "[2/4] 组装仓库到 $REPO（站点在根目录，工具在 _curated/）"
rm -rf "$REPO"; mkdir -p "$REPO"
cd "$SRC"
cp README.md .gitignore LICENSE CITATION.cff run.sh "$REPO"/ 2>/dev/null || true
mkdir -p "$REPO/.github/workflows" && cp .github/workflows/*.yml "$REPO/.github/workflows/"
# 站点 → 仓库根目录
copy_tree "$SRC/_curated/site" "$REPO"
# 构建工具与数据 → _curated/
mkdir -p "$REPO/_curated"
find "$SRC/_curated" -maxdepth 1 -type f \( -name '*.py' -o -name '*.sh' -o -name '*.tsv' -o -name '*.sqlite' \) \
  -exec cp {} "$REPO/_curated/" \;
find "$REPO" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

echo "[3/4] 初始化 git 并提交"
cd "$REPO"
git init -b main >/dev/null 2>&1 || git init >/dev/null
git config user.email "dsh-assistant@users.noreply.github.com"
git config user.name "DSH Assistant"
git add -A
MSG=$(mktemp)
cat > "$MSG" <<'EOF'
feat: T 细胞多组学数据库（中英双语静态站点 + 批量下载脚本）

站点文件位于仓库根目录（index.html / catalog.html / guideline.html / pages/ / data/ / assets/），
构建工具与数据库位于 _curated/。

- 首页按疾病类别导航：11 类，卡片给出数据集/样本数、组学类型与数量
- catalog.html 134 条记录：多维筛选、列排序、行内展开文件清单
- guideline.html：数据库关系、分类判定依据、推荐使用路径
- 全局搜索 + 中英一键切换（?lang=zh|en）
- 疾病类别原创 SVG 图标（make_icons.py 生成）
- 批量下载：fetch_download_manifest.py 核实官方下载地址后写入 downloads.json，
  网页勾选数据集生成 download_datasets.sh / download_sra.sh（断点续传/重试/日志/失败汇总）
- 数据来源：NCBI GEO 公开元数据 + PubMed；不含原始测序数据与任何凭据

Built with Deepseek Harness assistant
EOF
git commit -q -F "$MSG"; rm -f "$MSG"

echo "[4/4] 打包"
cd "$OUT"
rm -f tcell-multiomics-db.zip gh-pages-site.zip tcell-multiomics-db.bundle tcell-multiomics-db.tar.gz
( cd "$SRC/_curated/site" && zip -q -r -X "$OUT/gh-pages-site.zip" . )
cp gh-pages-site.zip tcell-multiomics-db.zip
( cd "$REPO" && zip -q -r -X "$OUT/tcell-multiomics-db.zip" . -x '.git/*' '*.DS_Store' )
( cd "$REPO" && git bundle create "$OUT/tcell-multiomics-db.bundle" --all >/dev/null )
# 额外产出一个「解压后就直接是 git 仓库」的包：含 .git 与首次提交，解压后只需 git remote + push
( cd "$REPO" && zip -q -r -X "$OUT/tcell-db-ready-to-push.zip" . -x '*.DS_Store' )
echo
echo "仓库：$REPO  ($(git -C "$REPO" ls-files | wc -l) 个文件)"
ls -lh "$OUT"/tcell-multiomics-db.zip "$OUT"/gh-pages-site.zip "$OUT"/tcell-multiomics-db.bundle | awk '{print "  " $5, $9}'
