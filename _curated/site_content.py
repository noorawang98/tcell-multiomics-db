#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""site_content.py — 网站文案与疾病类别元数据的唯一来源（中文/英文）。
被 make_icons.py（图标）与 build_site.py（页面）共用，避免两处文案漂移。
所有介绍均基于 annotation.tsv / datasets 的真实字段，不含虚构疾病或数据。
"""

# id(与 annotation.diseases 取值完全一致) -> 图标文件、配色、双语名称与介绍
CATEGORIES = [
    dict(id="B细胞淋巴瘤", icon="b-cell-lymphoma", color="#2E6FB7",
         zh="B 细胞淋巴瘤", en="B-cell lymphoma",
         desc_zh="DLBCL、FL、MCL、PMBCL 等 B 细胞来源淋巴瘤，CAR-T 疗效与耗竭机制研究最集中的疾病方向。",
         desc_en="B-cell derived lymphomas (DLBCL, FL, MCL, PMBCL); the densest focus for CAR-T efficacy and exhaustion studies."),
    dict(id="多发性骨髓瘤 MM", icon="multiple-myeloma", color="#7A5AA8",
         zh="多发性骨髓瘤 MM", en="Multiple myeloma (MM)",
         desc_zh="骨髓浆细胞肿瘤，BCMA 靶向 CAR-T 的主要适应症，含单细胞与 TCR 克隆追踪数据。",
         desc_en="Plasma-cell malignancy in bone marrow; the main indication for BCMA-directed CAR-T, with single-cell and TCR clonotype tracking data."),
    dict(id="白血病 ALL/CLL/AML", icon="leukemia", color="#0F8A6A",
         zh="白血病 ALL/CLL/AML", en="Leukemia (ALL/CLL/AML)",
         desc_zh="急性淋巴细胞白血病、慢性淋巴细胞白血病与急性髓系白血病，含 CD19/CD22 靶向治疗与复发机制研究。",
         desc_en="Acute lymphoblastic, chronic lymphocytic and acute myeloid leukemia, including CD19/CD22-directed therapy and relapse mechanisms."),
    dict(id="T细胞淋巴瘤/白血病", icon="t-cell-lymphoma", color="#A8577A",
         zh="T 细胞淋巴瘤/白血病", en="T-cell lymphoma/leukemia",
         desc_zh="T 细胞自身来源的淋巴增殖性疾病，含肿瘤性 T 细胞单细胞图谱，样本量小、属稀缺方向。",
         desc_en="Lymphoproliferative disease of T-cell origin with malignant T-cell single-cell profiles; small but scarce cohorts."),
    dict(id="胶质母细胞瘤 GBM", icon="glioblastoma", color="#B4632E",
         zh="胶质母细胞瘤 GBM", en="Glioblastoma (GBM)",
         desc_zh="中枢神经系统高级别胶质瘤，实体瘤 CAR-T 的主要难点方向，含 bulk 与单细胞、CRISPR 筛选。",
         desc_en="High-grade glioma of the CNS; a key hard target for solid-tumour CAR-T, with bulk/single-cell and CRISPR-screen data."),
    dict(id="儿童/中枢神经系统肿瘤", icon="pediatric-cns", color="#C2803A",
         zh="儿童/中枢神经系统肿瘤", en="Pediatric / CNS tumours",
         desc_zh="儿童患者与中枢神经系统肿瘤（含 DIPG、髓母细胞瘤等），多与 GBM、实体瘤标签共现。",
         desc_en="Paediatric patients and CNS tumours (incl. DIPG, medulloblastoma), frequently co-tagged with GBM and solid tumours."),
    dict(id="其他实体瘤", icon="solid-tumor", color="#4A7C59",
         zh="其他实体瘤", en="Other solid tumours",
         desc_zh="胰腺癌、肝癌、胃癌、乳腺癌等未单独成类的实体瘤，以肿瘤浸润 T 细胞与微环境研究为主。",
         desc_en="Pancreatic, liver, gastric, breast and other solid tumours not forming their own class; mostly tumour-infiltrating T cell and microenvironment studies."),
    dict(id="自身免疫/GVHD", icon="autoimmune-gvhd", color="#0D7C8C",
         zh="自身免疫/GVHD", en="Autoimmunity / GVHD",
         desc_zh="自身免疫病与移植物抗宿主病（GVHD），关注免疫耐受失衡与异体 T 细胞反应。",
         desc_en="Autoimmune disease and graft-versus-host disease (GVHD), focused on loss of tolerance and allogeneic T-cell responses."),
    dict(id="感染/病毒", icon="infection-virus", color="#B03A3A",
         zh="感染/病毒", en="Infection / virus",
         desc_zh="病毒感染背景下的 T 细胞应答（含病毒特异性 T 细胞），规模较小但对照价值明确。",
         desc_en="T-cell responses in viral infection (incl. virus-specific T cells); small in scale but valuable as controls."),
    dict(id="健康供者/基础", icon="healthy-donor", color="#3F7FA6",
         zh="健康供者/基础", en="Healthy donors / baseline",
         desc_zh="健康供者样本与未治疗基线，多为配对设计中的对照臂，适合做参照与正常范围界定。",
         desc_en="Healthy-donor samples and treatment-naive baselines, mostly control arms in paired designs for reference ranges."),
    dict(id="基础/体外研究", icon="in-vitro", color="#6B7A8F",
         zh="基础/体外研究", en="Basic / in vitro",
         desc_zh="无患者疾病背景的体外与机制研究（CAR 结构、培养条件、基因敲除等），适合分子机制对比而非队列分析。",
         desc_en="In vitro and mechanistic studies without patient disease background (CAR construct, culture conditions, gene knockout); suited to mechanism comparison rather than cohort analysis."),
]
# 文件名 slug：疾病类别名可能含空格与 "/"（如 "白血病 ALL/CLL/AML"），
# 直接用名称做文件名会产生子目录并破坏链接，故统一使用 ASCII slug。
for _i, _c in enumerate(CATEGORIES, 1):
    _c["slug"] = "c%02d" % _i
CAT_BY_ID = {c["id"]: c for c in CATEGORIES}
SLUG_BY_ID = {c["id"]: c["slug"] for c in CATEGORIES}

# 治疗类型（annotation.therapy 实际取值）
THERAPIES = ["CAR-T", "CAR-T+内源T(混合)", "内源T", "TCR-T/工程化T", "非T细胞/对照", "未明确"]
THERAPY_EN = {"CAR-T": "CAR-T", "CAR-T+内源T(混合)": "CAR-T + endogenous T (mixed)",
              "内源T": "Endogenous T", "TCR-T/工程化T": "TCR-T / engineered T",
              "非T细胞/对照": "Non-T / control", "未明确": "Unclassified"}

# T 细胞类型与功能状态（annotation.tcell_types 实际取值）
TCT = ["CD8", "CD4", "Treg", "γδT", "TIL", "记忆/干性", "耗竭/功能障碍", "效应/活化", "NKT/MAIT/其他", "未标注"]
TCT_EN = {"CD8": "CD8", "CD4": "CD4", "Treg": "Treg", "γδT": "γδ T", "TIL": "TIL",
          "记忆/干性": "Memory/stemness", "耗竭/功能障碍": "Exhaustion/dysfunction",
          "效应/活化": "Effector/activated", "NKT/MAIT/其他": "NKT/MAIT/other", "未标注": "Not annotated"}
TCT_DESC_ZH = {"CD8": "细胞毒性 T 细胞，CAR-T 疗效主效应细胞", "CD4": "辅助性 T 细胞 / Th1 / Th2 / Th17 / Tfh",
               "Treg": "调节性 T 细胞（FOXP3+），抑制抗肿瘤免疫", "γδT": "γδ T 细胞，MHC 非依赖杀伤",
               "TIL": "肿瘤浸润淋巴细胞", "记忆/干性": "记忆/干性表型（Tscm/Tcm/Tem/Tn），与持久性相关",
               "耗竭/功能障碍": "耗竭或功能失调（PD-1/TIM-3/LAG-3 高表达）", "效应/活化": "效应或活化状态、增殖",
               "NKT/MAIT/其他": "NKT、MAIT、NK 样等非常规 T 细胞", "未标注": "GEO 样本字段未给出 T 细胞类型"}
TCT_DESC_EN = {"CD8": "Cytotoxic T cells; main effector population for CAR-T efficacy",
               "CD4": "Helper T cells / Th1 / Th2 / Th17 / Tfh", "Treg": "Regulatory T cells (FOXP3+), suppress antitumour immunity",
               "γδT": "γδ T cells; MHC-independent killing", "TIL": "Tumour-infiltrating lymphocytes",
               "记忆/干性": "Memory/stemness phenotypes (Tscm/Tcm/Tem/Tn); linked to persistence",
               "耗竭/功能障碍": "Exhausted or dysfunctional (high PD-1/TIM-3/LAG-3)",
               "效应/活化": "Effector/activated and proliferating states",
               "NKT/MAIT/其他": "Unconventional T cells: NKT, MAIT, NK-like",
               "未标注": "No T-cell type given in the GEO sample fields"}

# 组学模态（MOD_KEYS 与 export_json.py 一致）
MOD_EN = {"scRNA": "scRNA", "bulkRNA": "bulkRNA", "scATAC": "scATAC", "bulkATAC": "bulkATAC",
          "scTCR": "scTCR", "bulkTCR": "bulkTCR", "methylation": "methylation",
          "CRISPR-screen": "CRISPR-screen"}
MOD_DESC_ZH = {
    "scRNA": "单细胞转录组：细胞类型与状态的主要来源", "bulkRNA": "批量转录组：队列规模大、可做差异与预后分析",
    "scATAC": "单细胞染色质可及性：调控元件与转录因子活性", "bulkATAC": "批量染色质可及性（ATAC-seq）",
    "scTCR": "单细胞 TCR 序列：克隆型与谱系追踪", "bulkTCR": "批量 TCR 测序：克隆多样性与扩增",
    "methylation": "DNA 甲基化：表观记忆与耗竭印记", "CRISPR-screen": "CRISPR 功能筛选：基因依赖性",
}
MOD_DESC_EN = {
    "scRNA": "Single-cell transcriptome: main source of cell type and state",
    "bulkRNA": "Bulk transcriptome: large cohorts for differential and survival analysis",
    "scATAC": "Single-cell chromatin accessibility: regulatory elements and TF activity",
    "bulkATAC": "Bulk chromatin accessibility (ATAC-seq)",
    "scTCR": "Single-cell TCR sequences: clonotypes and lineage tracking",
    "bulkTCR": "Bulk TCR sequencing: clonal diversity and expansion",
    "methylation": "DNA methylation: epigenetic memory and exhaustion imprint",
    "CRISPR-screen": "CRISPR functional screens: gene dependencies",
}

# 完整性状态（datasets.integrity 实际取值）
INTEGRITY = ["COMPLETE_VERIFIED", "UNVERIFIED", "TRUNCATED", "PARTIAL_BROKEN", "CORRUPT", "FAILED_ALL", "NO_DATA"]
IG_EN = {"COMPLETE_VERIFIED": "✅ Verified", "UNVERIFIED": "◻︎ Unchecked", "TRUNCATED": "⚠️ Truncated",
         "PARTIAL_BROKEN": "⚠️ Partly broken", "CORRUPT": "❌ Corrupt", "FAILED_ALL": "❌ All failed",
         "NO_DATA": "❌ No data"}
IG_DESC_ZH = {"COMPLETE_VERIFIED": "GEO 官方 filelist.txt 的成员数与字节数完全匹配，可放心使用",
              "UNVERIFIED": "无官方 filelist 可对照，但 gzip/tar 结构正常（实际可用）",
              "TRUNCATED": "tar 包被截断，成员数少于官方清单", "PARTIAL_BROKEN": "含 .filepart（下载残片）或 .aspx（网页错误页）文件",
              "CORRUPT": "含 gzip CRC 校验失败文件", "FAILED_ALL": "全部文件下载失败，仅存残片", "NO_DATA": "目录为空，无任何数据"}
IG_DESC_EN = {"COMPLETE_VERIFIED": "Member count and byte size exactly match the official GEO filelist.txt",
              "UNVERIFIED": "No official filelist to compare, but gzip/tar structure is intact (usable)",
              "TRUNCATED": "tar archive truncated; fewer members than the official manifest",
              "PARTIAL_BROKEN": "Contains .filepart download remnants or .aspx error pages",
              "CORRUPT": "Contains files failing gzip CRC check", "FAILED_ALL": "All downloads failed; only remnants remain",
              "NO_DATA": "Empty directory, no data"}

# 界面文案
UI = {
    "site_name": {"zh": "T 细胞多组学数据库", "en": "T-cell Multi-omics Database"},
    "site_sub": {"zh": "GEO CAR-T / T 细胞多组学数据目录", "en": "GEO CAR-T / T-cell multi-omics catalogue"},
    "nav_home": {"zh": "首页", "en": "Home"},
    "nav_catalog": {"zh": "数据集目录", "en": "Catalog"},
    "nav_guideline": {"zh": "关联与判定指南", "en": "Relations & methods"},
    "search_ph": {"zh": "搜索 GSE / 标题 / 疾病 / 期刊 / 作者…", "en": "Search GSE / title / disease / journal / author…"},
    "search_hint": {"zh": "输入关键词后回车查看全部结果", "en": "Press Enter to see all results"},
    "search_none": {"zh": "无匹配数据集", "en": "No matching dataset"},
    "search_results": {"zh": "条匹配", "en": "matches"},
    "search_enter": {"zh": "在目录中查看全部", "en": "View all in catalog"},
    "lang": {"zh": "中文", "en": "EN"},
    "browse_disease": {"zh": "按疾病类别浏览", "en": "Browse by disease category"},
    "disease_intro": {"zh": "一级导航即数据库中的疾病类别，逐类列出可核对的临床、组学类型与数量。",
                      "en": "Primary navigation lists the disease categories actually present in the database, each with verifiable clinical and omics counts."},
    "datasets": {"zh": "数据集", "en": "datasets"},
    "samples": {"zh": "样本", "en": "samples"},
    "open_category": {"zh": "进入该类别", "en": "Open category"},
    "filter": {"zh": "筛选", "en": "Filter"},
    "reset": {"zh": "✕ 重置全部", "en": "✕ Reset all"},
    "only_matched": {"zh": "仅 T 细胞多组学配套", "en": "Only multi-omics matched"},
    "only_verified": {"zh": "仅官方校验通过", "en": "Only officially verified"},
    "hits": {"zh": "命中", "en": "Matched"},
    "of_total": {"zh": "个数据集 / 共", "en": "datasets / of"},
    "total_size": {"zh": "合计", "en": "total"},
    "back_home": {"zh": "← 返回首页", "en": "← Back to home"},
    "back_cat": {"zh": "← 返回类别", "en": "← Back to category"},
    "related": {"zh": "关联记录", "en": "Related records"},
    "catalog_hint": {"zh": "目录中的每条记录均给出 GEO 原始链接、PubMed 文献链接与本地文件清单。",
                     "en": "Every catalog record links to its GEO entry, PubMed record and local file manifest."},
    "files": {"zh": "本地文件", "en": "Local files"},
    "files_btn": {"zh": "查看文件清单", "en": "Show file manifest"},
    "files_none": {"zh": "该数据集在本地无已下载文件", "en": "No local files downloaded for this dataset"},
    "geo_link": {"zh": "GEO 原始页面", "en": "GEO record"},
    "pubmed_link": {"zh": "PubMed 文献", "en": "PubMed"},
    "footer_copy": {"zh": "© 2026 TCMDB 项目 · 网站与整理代码以 MIT 许可发布；数据来自 NCBI GEO / PubMed，版权归原数据方。",
                    "en": "© 2026 TCMDB project · site and curation code released under the MIT licence; data from NCBI GEO / PubMed remains with the original submitters."},
    "footer_built": {"zh": "Built with Deepseek Harness assistant", "en": "Built with Deepseek Harness assistant"},
    "footer_src": {"zh": "数据来源：NCBI GEO（E-utilities + FTP series matrix）与 PubMed 官方记录；仅收录公开元数据。",
                   "en": "Source: NCBI GEO (E-utilities + FTP series matrix) and PubMed; public metadata only."},
    "updated": {"zh": "更新于", "en": "Updated"},
    "all_cats": {"zh": "全部疾病类别", "en": "All disease categories"},
    "stat_ds": {"zh": "数据集总数", "en": "Datasets"},
    "stat_bytes": {"zh": "数据总量", "en": "Total size"},
    "stat_verified": {"zh": "官方校验通过", "en": "Officially verified"},
    "stat_matched": {"zh": "多组学配套", "en": "Multi-omics matched"},
    "stat_pub": {"zh": "已发表文献", "en": "Published"},
    "stat_samples": {"zh": "样本总数", "en": "Samples"},
    "stat_cats": {"zh": "疾病类别", "en": "Disease categories"},
    "omics_profile": {"zh": "组学类型分布", "en": "Omics profile"},
    "therapy_profile": {"zh": "治疗类型分布", "en": "Therapy profile"},
    "years": {"zh": "数据发布年份", "en": "GEO release years"},
    "cat_intro": {"zh": "类别说明", "en": "About this category"},
    "datasets_in": {"zh": "该类别数据集", "en": "Datasets in this category"},
    "cols": {"zh": ["GSE", "标题", "治疗类型", "疾病", "T细胞类型/状态", "组学", "期刊 (年)", "第一作者",
                    "贡献者(Submitter)", "样本", "大小", "完整性"],
             "en": ["GSE", "Title", "Therapy", "Disease", "T-cell type / state", "Omics", "Journal (year)",
                    "First author", "Submitter", "Samples", "Size", "Integrity"]},
    "h1_home": {"zh": "GEO CAR-T / T 细胞多组学数据库", "en": "GEO CAR-T / T-cell multi-omics database"},
    "nav_home": {"zh": "首页", "en": "Home"},
    "select_page": {"zh": "选择当前筛选结果", "en": "Select current filter results"},
    "col_sel": {"zh": "勾选后生成下载脚本", "en": "Tick to include in the download script"},
    "dl_tip": {"zh": "勾选数据集后点「生成下载脚本」，核对清单再下载 .sh；浏览器不会执行下载。",
               "en": "Tick datasets, click \"Generate download script\", review the list, then download the .sh; the browser performs no download."},
    "dl_verified": {"zh": "个已核实可下载", "en": "verified downloadable"},
    "dl_checked": {"zh": "个已核实数据集", "en": "datasets checked"},
    "na": {"zh": "未判定", "en": "n/a"},
    "none": {"zh": "", "en": ""},
    "f_therapy": {"zh": "治疗类型", "en": "Therapy"},
    "col_acc": {"zh": "GSE", "en": "GSE"},
    "col_title": {"zh": "标题", "en": "Title"},
    "col_th": {"zh": "治疗类型", "en": "Therapy"},
    "col_dis": {"zh": "疾病", "en": "Disease"},
    "col_tct": {"zh": "T细胞类型/状态", "en": "T-cell type / state"},
    "col_mo": {"zh": "组学", "en": "Omics"},
    "col_journal": {"zh": "期刊 (年)", "en": "Journal (year)"},
    "col_au": {"zh": "第一作者", "en": "First author"},
    "col_ct": {"zh": "贡献者(Submitter)", "en": "Submitter"},
    "col_ns": {"zh": "样本", "en": "Samples"},
    "col_size": {"zh": "大小", "en": "Size"},
    "col_ig": {"zh": "完整性", "en": "Integrity"},
    "all": {"zh": "全部", "en": "All"},
    "f_disease": {"zh": "疾病", "en": "Disease"},
    "f_omics": {"zh": "组学", "en": "Omics"},
    "f_integrity": {"zh": "完整性", "en": "Integrity"},
    "f_tct": {"zh": "T细胞类型/状态", "en": "T-cell type/state"},
    "f_evidence": {"zh": "判定依据", "en": "Evidence"},
    "page_catalog": {"zh": "数据集目录", "en": "Dataset catalog"},
    "page_guideline": {"zh": "数据库关系与判定指南", "en": "Database relations and methods"},
    "site_title": {"zh": "GEO CAR-T / T 细胞多组学数据库", "en": "GEO CAR-T / T-cell multi-omics database"},
    "related_hint": {"zh": "同一数据集常被多个疾病标签覆盖，跨类别查询请用全局搜索或目录页筛选。",
                     "en": "A dataset often carries several disease labels; use global search or catalog filters to cross categories."},
}
