# CAR-T / T-cell Multi-omics Database (TCMDB)

GEO 上 CAR-T 与 T 细胞多组学公开数据集的整理索引，纯静态站点，中英文可切换。

**站点地址**：https://noorawang98.github.io/tcell-multiomics-db/

## 站点内容

| 页面 | 内容 |
|---|---|
| `index.html` | 首页：按 **11 个疾病类别** 导航，每类给出数据集/样本数、组学类型与数量 |
| `catalog.html` | 数据集目录：**134 条记录**，按治疗/疾病/T 细胞类型/组学/完整性筛选，可排序，行内展开文件清单 |
| `guideline.html` | 数据库关系（关联键与基数）、分类判定依据、推荐使用路径 |
| `pages/c01…c11.html` | 各疾病类别详情页 |

合计 **134 个数据集 / 3298 个样本 / 155.3 GB**，其中 25 个为 T 细胞多组学配套，79 个通过 GEO 官方 filelist 校验。

**批量下载**：在 `catalog.html` 或类别页勾选数据集（或用「选择当前筛选结果」）→ 点「生成下载脚本」→ 核对清单 → 「下载 .sh」。
浏览器不执行下载，只生成可在本地运行的 Bash 脚本；脚本含断点续传、有限重试、逐文件日志、失败汇总，不使用 sudo、不自动解压。
SRA 原始数据作为独立选项，仅对已核实关联 accession 的数据集提供。

## 目录结构

```
├─ index.html catalog.html guideline.html 404.html .nojekyll   ← 站点（仓库根目录，可直接发布）
├─ pages/ data/ assets/                                         ← 站点页面、JSON、样式与图标
├─ _curated/                                                    ← 数据库与构建工具
│   ├─ catalog.sqlite           唯一数据源（134 数据集全字段）
│   ├─ annotation.tsv           疾病/治疗/T 细胞类型标注
│   ├─ dataset_master.tsv       数据集主表          pubmed.tsv  文献信息
│   ├─ modality_v2.tsv          组学模态判定结果
│   ├─ export_json.py           catalog.sqlite → data/*.json
│   ├─ fetch_download_manifest.py  核实官方下载地址 → data/downloads.json
│   ├─ make_icons.py            生成 11 个疾病类别 SVG 图标
│   ├─ build_site.py            生成全部页面（--inline 可生成可双击打开的版本）
│   ├─ site_content.py          类别定义与中英文文案
│   └─ build_site.sh run.sh package_repo.sh selftest_download.py
└─ .github/workflows/           pages.yml（可选：从数据库自动重建并发布）
```

## 本地预览

```bash
cd _curated
python3 -m http.server 8901        # 浏览 http://127.0.0.1:8901/
# 或生成可双击打开的版本（数据内联，无需服务器）
python3 build_site.py --out site-local --inline
```

## 更新数据或页面

```bash
cd _curated
python3 fetch_download_manifest.py --sra --workers 6   # 重新核实下载地址（可选）
bash build_site.sh                                     # 重建 data/*.json 与全部页面
bash package_repo.sh                                   # 重新打包 zip / bundle
```

新增数据集：在 `catalog.sqlite` 的 `datasets` / `annotation` 表补记录 → 重跑上面三步。

## 数据来源与许可

- 元数据：NCBI GEO（E-utilities + FTP series matrix）；文献：PubMed 官方记录
- 完整性：GEO 官方 `filelist.txt` 交叉比对、`tar -tf` 索引、`gzip -t` CRC
- 代码与文档：MIT（见 `LICENSE`）；**数据版权归原数据方**，本仓库不含原始测序数据与任何凭据
- 引用方式见 `CITATION.cff`
