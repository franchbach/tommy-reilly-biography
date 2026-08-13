# -*- coding: utf-8 -*-
"""批量翻译: zh/*.md -> en/de/ja/*.md (MiniMax-Text-01)

用法: python _translate.py <lang> [文件列表...]
  lang: en / de / ja
设计: 按空行切块, 每块一次请求, 保留 markdown 结构 (标题/图片/表格/列表/引用)
断点续跑: 进度缓存在 _progress_<lang>.json, 已完成的文件跳过
"""
import json, os, re, sys, time, urllib.request

# 仓库根 = 脚本所在目录的上级 (脚本位于 tools/ 子目录)
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZH_DIR = os.path.join(BASE, "zh")
PROGRESS = os.path.join(BASE, "_progress_%s.json")

LANG_NAMES = {"en": "English", "de": "German", "ja": "Japanese"}

def get_key():
    # 优先读环境变量, 其次 Hermes .env
    key = os.environ.get("MINIMAX_API_KEY")
    if key:
        return key
    for env_path in [r"C:\Users\smc03\AppData\Local\hermes\.env"]:
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("MINIMAX_API_KEY=") and not line.startswith("#"):
                        return line.split("=", 1)[1].strip()
    raise RuntimeError("no MINIMAX_API_KEY")

KEY = get_key()
ENDPOINT = "https://api.minimaxi.com/v1/chat/completions"
MODEL = "MiniMax-Text-01"

def translate_block(text, lang):
    """翻译一个块(1-N 行), 保持行数一致"""
    lang_name = LANG_NAMES[lang]
    n_lines = len(text.split("\n"))
    sys_prompt = (
        "You are a professional translator of a biography about Tommy Reilly, "
        "the legendary chromatic harmonica player. Translate the given text to %s. "
        "Rules: output ONLY the translation, same number of lines as input, "
        "preserve all markdown syntax (headings #, image tags ![...](...), "
        "table pipes |, list markers, blockquote >), keep proper nouns "
        "(Tommy Reilly, Sigmund Groven, Uwe Warschkow, piece titles in italics style) "
        "and URLs unchanged. Do not add explanations." % lang_name
    )
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": text},
        ],
        "max_tokens": 4096,
    }).encode("utf-8")
    for attempt in range(8):
        try:
            req = urllib.request.Request(
                ENDPOINT, data=body,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            out = d["choices"][0]["message"]["content"].strip()
            if not out:
                raise ValueError("empty output")
            # 行数校验: 不一致则合并为一行输出
            if out.count("\n") + 1 != n_lines and n_lines > 1:
                # 可能模型把多行合并了——逐行拆分尝试
                return out
            return out
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # MiniMax 限流: 长退避
                wait = 30 * (attempt + 1)
                print("  [429] 退避 %ds (attempt %d)" % (wait, attempt + 1))
                time.sleep(wait)
                continue
            if attempt == 7:
                raise
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            if attempt == 7:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")

def is_skippable(line):
    return not line.strip() or re.match(r"^!\[.*\]\(.*\)$", line.strip())

def translate_file(src_path, dst_path, lang):
    text = open(src_path, encoding="utf-8").read()
    lines = text.split("\n")
    # 切块: 连续非空行成块
    blocks = []
    cur = []
    for line in lines:
        if line.strip():
            cur.append(line)
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)

    out_lines = []
    for bi, block in enumerate(blocks):
        if all(is_skippable(l) for l in block):
            out_lines.extend(block)
            continue
        joined = "\n".join(block)
        try:
            translated = translate_block(joined, lang)
        except Exception as e:
            print("  [FAIL] block %d: %s" % (bi, e))
            translated = joined  # 失败保留原文, 便于事后检查
        out_lines.extend(translated.split("\n"))
        out_lines.append("")
        time.sleep(0.4)  # 限速: 每块之间留间隔, 避免触发 429
        if bi % 10 == 0:
            print("  block %d/%d" % (bi, len(blocks)))
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))

def main():
    lang = sys.argv[1]
    files = sys.argv[2:] or sorted(os.listdir(ZH_DIR))
    prog_path = PROGRESS % lang
    done = set()
    if os.path.exists(prog_path):
        done = set(json.load(open(prog_path, encoding="utf-8")))
    dst_dir = os.path.join(BASE, lang)
    os.makedirs(dst_dir, exist_ok=True)
    for fname in files:
        if not fname.endswith(".md"):
            continue
        if fname in done:
            print("skip (done):", fname)
            continue
        print("== %s -> %s: %s" % (lang, fname, LANG_NAMES[lang]))
        try:
            translate_file(os.path.join(ZH_DIR, fname), os.path.join(dst_dir, fname), lang)
        except Exception as e:
            print("[FILE FAIL] %s: %s" % (fname, e))
            continue  # 该文件保留原文占位, 不中断批次
        done.add(fname)
        json.dump(sorted(done), open(prog_path, "w", encoding="utf-8"))
        print("done:", fname)

if __name__ == "__main__":
    main()
