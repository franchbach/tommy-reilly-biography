# -*- coding: utf-8 -*-
"""合并 en/*.md -> book_en.html (供 Edge headless 打印 PDF)"""
import os, re
import markdown

BASE = r"D:\Desktop\TommyReillyBook"
ASSETS = os.path.join(BASE, "zh", "assets")

CSS = """
@page { size: A4; margin: 2cm 2.2cm; }
body { font-family: 'Georgia', 'Times New Roman', serif; font-size: 11pt; line-height: 1.65; color: #1a1a1a; max-width: 100%; }
h1 { font-size: 20pt; text-align: center; margin: 28pt 0 14pt; page-break-before: always; border-bottom: 2px solid #999; padding-bottom: 8pt; }
h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 14pt; margin: 20pt 0 10pt; color: #333; }
h3 { font-size: 12pt; margin: 14pt 0 8pt; color: #444; }
p { margin: 6pt 0; text-align: justify; }
img { max-width: 100%; max-height: 420pt; display: block; margin: 10pt auto; border: 1px solid #ddd; }
blockquote { border-left: 3px solid #aaa; margin: 8pt 0 8pt 12pt; padding-left: 10pt; color: #444; font-style: italic; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 8pt 0; }
th, td { border: 1px solid #bbb; padding: 4pt 6pt; text-align: left; }
th { background: #f0f0f0; }
ul, ol { margin: 6pt 0; }
li { margin: 2pt 0; }
code { background: #f5f5f5; padding: 1pt 3pt; font-size: 9.5pt; }
"""

def main():
    files = sorted(os.listdir(os.path.join(BASE, "en")))
    md_files = [f for f in files if f.endswith(".md")]
    parts = []
    for fname in md_files:
        text = open(os.path.join(BASE, "en", fname), encoding="utf-8").read()
        # 图片路径 -> 本地绝对路径 (Edge 打印可加载)
        text = re.sub(r'\]\(\.\./zh/assets/([^)]+)\)', lambda m: '](%s/%s)' % (ASSETS, m.group(1)), text)
        html = markdown.markdown(text, extensions=["tables", "fenced_code"])
        parts.append(html)
    full = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>A Complete Book For Tommy Reilly</title>
<style>%s</style></head><body>%s</body></html>""" % (CSS, "\n".join(parts))
    out = os.path.join(BASE, "book_en.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(full)
    print("HTML 生成:", out, "%.1f KB" % (os.path.getsize(out) / 1024))

if __name__ == "__main__":
    main()
