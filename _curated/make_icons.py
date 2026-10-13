#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_icons.py — 生成疾病类别原创 SVG 图标（统一线条/尺寸/配色，可编辑）。
输出：
  site/assets/icons/<id>.svg      单图标文件（简洁线性风格）
  site/assets/icons/sprite.svg    全部图标 symbol 集合（供 <use> 引用）
图标全部为几何路径手写，无外部字体/付费素材，可直接用文本编辑器修改。
统一规格：viewBox 0 0 48 48 · 线宽 2 · 圆头圆角 · 48 网格对齐。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_content import CATEGORIES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "site", "assets", "icons")

# 每个类别：外层符号 + 内部几何语义（全部原创，仅用直线/圆/弧）
PATHS = {
    "b-cell-lymphoma": [
        '<circle cx="21" cy="25.5" r="11"/>',
        '<path d="M21 17v17M18 19h6M18 32h6"/>',
        '<path d="M27 14l1.9 3.9 4.3.6-3.1 3 .7 4.3-3.8-2-3.8 2 .7-4.3-3.1-3 4.3-.6z"/>',
    ],
    "multiple-myeloma": [
        '<path d="M24 5.5c5.7 0 10 3.4 10 7.6v3.4c0 4.6-2.1 8.2-5.4 10.4"/>',
        '<path d="M24 5.5c-5.7 0-10 3.4-10 7.6v3.4c0 4.6 2.1 8.2 5.4 10.4"/>',
        '<ellipse cx="24" cy="16.5" rx="10" ry="4.2"/>',
        '<circle cx="20" cy="34.5" r="3.4"/>',
        '<circle cx="28.5" cy="34.5" r="3.4"/>',
        '<circle cx="24.3" cy="40" r="3.4"/>',
    ],
    "leukemia": [
        '<rect x="5.5" y="13.5" width="37" height="21" rx="5"/>',
        '<path d="M5.5 24h11l3-5.5 4.5 11 3-5.5h15.5"/>',
        '<circle cx="38" cy="18.5" r="2.6"/>',
        '<circle cx="12" cy="30" r="2.6"/>',
    ],
    "t-cell-lymphoma": [
        '<circle cx="20" cy="26" r="11.5"/>',
        '<path d="M14 27c1.4 2.6 3.6 4.3 6 4.8 2.4-.5 4.6-2.2 6-4.8"/>',
        '<path d="M13 32.5h14"/>',
        '<path d="M37.5 6.5l-7 11M41 10.5l-8 4"/>',
        '<circle cx="39" cy="8" r="2.5"/>',
    ],
    "glioblastoma": [
        '<path d="M24 6.5c9.4 0 17 6.6 17 14.7 0 5.3-3 9.9-7.8 12.5l-.9 7.8-6.3-4-3 4-6.4-4-3 4-.8-7.6C7.9 31.3 7 26.8 7 21.2 7 13.1 14.6 6.5 24 6.5Z"/>',
        '<circle cx="24" cy="20" r="5.6"/>',
        '<path d="M24 9.6v4.8M24 25.6v4.6M11.6 20h4.8M31.6 20h4.8M15 11.5l3.4 3.4M33 11.5l-3.4 3.4M15.6 28.6l3.1-3.1M32.4 28.6l-3.1-3.1"/>',
    ],
    "pediatric-cns": [
        '<circle cx="22" cy="21" r="11.5"/>',
        '<path d="M34 20c0 2.5-.6 4-1.8 6.2"/>',
        '<path d="M22 9c-3.2 7.4-3.2 16.2 0 23.6M10.5 21h23"/>',
        '<path d="M15.5 33.5h9"/>',
        '<circle cx="36.5" cy="33" r="4.2"/>',
        '<circle cx="36.5" cy="33" r="1.3"/>',
    ],
    "solid-tumor": [
        '<path d="M24 6.5c6.4 0 10.5 4.1 10.5 9.6 0 4.1-2.3 7.1-5.7 8.7 5.9 1.4 9.7 5.3 9.7 10.6H9.5c0-5.3 3.8-9.2 9.7-10.6-3.4-1.6-5.7-4.6-5.7-8.7C13.5 10.6 17.6 6.5 24 6.5Z"/>',
        '<circle cx="24" cy="16" r="3.6"/>',
        '<path d="M16 41.5h16"/>',
    ],
    "autoimmune-gvhd": [
        '<path d="M24 5.5l5.7 3.3-.5 6.3 4.8 4-3.4 5.3 1.7 6.1-6 2-1.5 6.1h-1.6l-1.5-6.1-6-2 1.7-6.1-3.4-5.3 4.8-4-.5-6.3z"/>',
        '<path d="M24 10.5v15"/>',
        '<path d="M19 12.5l5 4.5 5-4.5"/>',
    ],
    "infection-virus": [
        '<circle cx="24" cy="18.5" r="10"/>',
        '<path d="M24 5.5v3M24 28.5v3M11 18.5h3M34 18.5h3M14.8 9.3l2.1 2.1M31.1 25.6l2.1 2.1M33.2 9.3l-2.1 2.1M16.9 25.6l-2.1 2.1"/>',
        '<circle cx="20.5" cy="17.5" r="1.4"/><circle cx="27.5" cy="17.5" r="1.4"/>',
        '<path d="M20.5 22.5c1.2 1 2.3 1.4 3.5 1.4s2.3-.4 3.5-1.4"/>',
        '<path d="M12 39c2.5-3.4 5.7-5.1 9.6-5.1 2.6 0 4.5-1.2 5.7-3.6"/>',
    ],
    "healthy-donor": [
        '<circle cx="24" cy="14" r="7.5"/>',
        '<path d="M10.5 42c0-7.5 6-12.5 13.5-12.5S37.5 34.5 37.5 42"/>',
        '<path d="M38.5 9.5l3.2 3.2 6-6"/>',
    ],
    "in-vitro": [
        '<circle cx="13" cy="12" r="5"/>',
        '<circle cx="24" cy="12" r="5"/>',
        '<circle cx="35" cy="12" r="5"/>',
        '<circle cx="13" cy="23" r="5"/>',
        '<circle cx="24" cy="23" r="5"/>',
        '<circle cx="35" cy="23" r="5"/>',
        '<circle cx="13" cy="34" r="5"/>',
        '<circle cx="24" cy="34" r="5"/>',
        '<circle cx="35" cy="34" r="2.6"/>',
    ],
}

TPL = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48"
     role="img" aria-label="{label}" fill="none" stroke="{color}" stroke-width="2"
     stroke-linecap="round" stroke-linejoin="round">
  <!-- 原创图标 · 类别：{zh} / {en} · 可自由编辑路径编辑自定形状 -->
  <g>{paths}</g>
</svg>
'''

SYMBOL = '''  <symbol id="ic-{icon}" viewBox="0 0 48 48" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{paths}</symbol>
'''


def main():
    os.makedirs(OUT, exist_ok=True)
    syms = []
    for c in CATEGORIES:
        p = "".join(PATHS[c["icon"]])
        with open(os.path.join(OUT, c["icon"] + ".svg"), "w", encoding="utf-8") as f:
            f.write(TPL.format(label=c["en"], color=c["color"], zh=c["zh"], en=c["en"], paths=p))
        syms.append(SYMBOL.format(icon=c["icon"], paths=p))
        print("  ✓", c["icon"] + ".svg", c["color"])
    head = ('<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">\n'
            '  <!-- 疾病类别图标 sprite：由 make_icons.py 生成，颜色随 currentColor -->\n')
    with open(os.path.join(OUT, "sprite.svg"), "w", encoding="utf-8") as f:
        f.write(head + "".join(syms) + "</svg>\n")
    # 供 build_site.py 内联进页面（避免 fetch 额外请求）
    with open(os.path.join(OUT, "sprite-inline.html"), "w", encoding="utf-8") as f:
        f.write(head + "".join(syms) + "</svg>\n")
    print("  ✓ sprite.svg / sprite-inline.html  (%d 图标)" % len(syms))


if __name__ == "__main__":
    main()
