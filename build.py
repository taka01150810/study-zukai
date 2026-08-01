#!/usr/bin/env python3
"""Obsidian Vault の 図解/ フォルダから HTML を集めて、公開用サイトを組み立てる。

使い方:
    python3 build.py

Vault 側の `Study/**/図解/*.html` を探し、このリポジトリ直下に
`<書籍スラッグ>/<章番号>.html` としてコピーしたうえで、
トップページ `index.html` を書き出す。
章を書き足したあとに再実行すれば、目次も自動で更新される。
"""

import html
import re
import shutil
import unicodedata
from pathlib import Path

# 図解の元データが置いてある Obsidian Vault のパス
VAULT = Path.home() / "obsidian"

# 出力先。このスクリプトが置かれているディレクトリ（= リポジトリ直下）
DIST = Path(__file__).resolve().parent

# 書籍フォルダ名 -> (URL に使う英数字スラッグ, トップページに出す表示名, 副題)
BOOKS = {
    "詳解-Terraform": ("terraform", "詳解 Terraform 第3版", "Infrastructure as Code"),
    "初めてのLangChain": ("langchain", "初めての LangChain", "LLM アプリケーション開発"),
    "データ指向アプリケーションデザイン": ("ddia", "データ指向アプリケーションデザイン", "分散システムとデータ基盤"),
    "FAST-API": ("fastapi", "FastAPI", "Python の Web API フレームワーク"),
}

# 出力を消してよいディレクトリかどうかの判定に使う（誤って他を消さないための保険）
KNOWN_SLUGS = {slug for slug, _, _ in BOOKS.values()}


def nfc(text):
    """macOS のファイル名は濁点が分かれた形（NFD）で返るため、比較前に形をそろえる。

    例: "データ" は見た目は同じでも "テ" + 濁点 の2文字として返ることがあり、
    そのままだと辞書のキーと一致しない。
    """
    return unicodedata.normalize("NFC", text)


def find_source_dirs():
    """Vault の中から 図解/ ディレクトリを探し、対応する書籍設定と組にして返す。"""
    found = []
    for zukai_dir in sorted((VAULT / "Study").rglob("図解")):
        if not zukai_dir.is_dir():
            continue
        # 図解/ の親をたどって、BOOKS に登録された書籍フォルダ名を探す
        book_key = next((nfc(p.name) for p in zukai_dir.parents if nfc(p.name) in BOOKS), None)
        if book_key is None:
            print(f"  skip (未登録の書籍): {zukai_dir}")
            continue
        found.append((book_key, zukai_dir))
    return found


def parse_chapter(path):
    """ファイル名 "3. ステートを管理する.html" を (3, "ステートを管理する") に分解する。"""
    stem = nfc(path.stem).strip()
    m = re.match(r"^(\d+)[.．]?\s*(.*)$", stem)
    if m:
        return int(m.group(1)), m.group(2).strip() or stem
    # 数字が付いていないファイルは末尾に回す
    return 9999, stem


def collect():
    """図解 HTML を出力先にコピーし、目次を組み立てるためのデータを返す。"""
    books = []
    for book_key, src_dir in find_source_dirs():
        slug, title, subtitle = BOOKS[book_key]
        out_dir = DIST / slug
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)

        chapters = []
        for src in sorted(src_dir.glob("*.html")):
            num, chap_title = parse_chapter(src)
            # URL に日本語やスペースが入らないよう、章番号だけのファイル名にする
            name = f"{num:02d}.html" if num != 9999 else f"{src.stem}.html"
            shutil.copy2(src, out_dir / name)
            chapters.append({"num": num, "title": chap_title, "href": f"{slug}/{name}"})

        chapters.sort(key=lambda c: c["num"])
        if chapters:
            books.append({"slug": slug, "title": title, "subtitle": subtitle, "chapters": chapters})
            print(f"  {title}: {len(chapters)} 章")

    # Vault 側で図解を消した書籍は、公開サイトからも取り下げる。
    # KNOWN_SLUGS に載っているディレクトリだけを対象にして、無関係なものを消さないようにする。
    live = {b["slug"] for b in books}
    for slug in sorted(KNOWN_SLUGS - live):
        stale = DIST / slug
        if stale.is_dir():
            shutil.rmtree(stale)
            print(f"  削除 (元データなし): {slug}/")

    # トップページの並び順を BOOKS の記述順にそろえる（探索順に左右されないようにする）
    order = [slug for slug, _, _ in BOOKS.values()]
    books.sort(key=lambda b: order.index(b["slug"]))
    return books


CSS = """
:root{
  --bg:#0f1220; --panel:#171b2e; --panel2:#1e2440; --ink:#e9ecff; --sub:#aab2dd;
  --line:#2c3358; --accent:#6c8cff; --accent2:#42d6c3;
  --shadow:0 10px 30px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{margin:0; background:radial-gradient(1200px 600px at 80% -10%, #20264a 0%, var(--bg) 55%);
  color:var(--ink); font-family:"Hiragino Kaku Gothic ProN","Yu Gothic",Meiryo,system-ui,sans-serif;
  line-height:1.7; letter-spacing:.01em; min-height:100vh;}
.wrap{max-width:1080px; margin:0 auto; padding:32px 20px 120px}
header.hero{border:1px solid var(--line); border-radius:22px; padding:34px 32px;
  background:linear-gradient(135deg,#1a2042 0%, #141831 100%); box-shadow:var(--shadow);
  position:relative; overflow:hidden;}
header.hero::after{content:""; position:absolute; right:-60px; top:-60px; width:240px; height:240px;
  background:radial-gradient(circle,#6c8cff44,transparent 70%);}
.chip{display:inline-block; font-size:12px; padding:4px 12px; border-radius:999px;
  background:#6c8cff22; border:1px solid #6c8cff55; color:#c5d0ff; margin-bottom:14px}
header.hero h1{margin:.1em 0 .3em; font-size:32px; line-height:1.35}
header.hero p{margin:.4em 0 0; color:var(--sub); max-width:760px}
section.book{margin-top:44px}
.sec-head{display:flex; align-items:center; gap:14px; margin-bottom:18px}
.sec-num{flex:0 0 auto; min-width:48px; height:48px; padding:0 14px; border-radius:14px;
  display:grid; place-items:center; font-weight:800; font-size:14px; color:#0c0f1e;
  background:linear-gradient(135deg,var(--accent),var(--accent2)); box-shadow:var(--shadow)}
.sec-head h2{margin:0; font-size:23px}
.sec-head .tag{font-size:12px; color:var(--sub); display:block; margin-top:2px; font-weight:400}
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:14px}
a.card{display:flex; gap:14px; align-items:flex-start; text-decoration:none;
  background:var(--panel); border:1px solid var(--line); border-radius:16px;
  padding:16px 18px; box-shadow:var(--shadow); transition:.15s}
a.card:hover{border-color:var(--accent); transform:translateY(-2px)}
a.card .no{flex:0 0 auto; min-width:34px; height:34px; border-radius:10px; display:grid;
  place-items:center; font-size:13px; font-weight:700; color:#c5d0ff;
  background:#6c8cff1f; border:1px solid #6c8cff44}
a.card .t{color:var(--ink); font-size:14.5px; line-height:1.5}
footer{margin-top:64px; padding-top:24px; border-top:1px solid var(--line);
  color:var(--sub); font-size:13px}
footer a{color:var(--accent2)}
@media(max-width:680px){
  header.hero{padding:26px 20px}
  header.hero h1{font-size:25px}
  .wrap{padding:20px 14px 80px}
}
"""


def render_index(books):
    """トップページの HTML 文字列を組み立てる。"""
    total = sum(len(b["chapters"]) for b in books)
    parts = [
        '<div class="wrap">',
        '<header class="hero">',
        '<span class="chip">技術書の図解ノート</span>',
        "<h1>Study 図解</h1>",
        "<p>読んだ技術書の内容を、専門用語を極力使わずに図で読める形にまとめたノートです。"
        f"現在 {len(books)} 冊 / 全 {total} 章。各ページは単体で完結した HTML です。</p>",
        "</header>",
    ]

    for i, book in enumerate(books, 1):
        parts += [
            '<section class="book">',
            '<div class="sec-head">',
            f'<div class="sec-num">{len(book["chapters"])}章</div>',
            f'<div><h2>{html.escape(book["title"])}</h2>'
            f'<span class="tag">{html.escape(book["subtitle"])}</span></div>',
            "</div>",
            '<div class="grid">',
        ]
        for chap in book["chapters"]:
            no = "序" if chap["num"] == 0 else (str(chap["num"]) if chap["num"] != 9999 else "—")
            parts.append(
                f'<a class="card" href="{html.escape(chap["href"])}">'
                f'<span class="no">{no}</span>'
                f'<span class="t">{html.escape(chap["title"])}</span></a>'
            )
        parts += ["</div>", "</section>"]

    parts += [
        "<footer>",
        "書籍の内容そのものではなく、学習のために自分の言葉で要約・図解したノートです。"
        '詳細は各書籍の原典を参照してください。 / '
        '<a href="https://github.com/taka01150810/study-zukai">GitHub</a>',
        "</footer>",
        "</div>",
    ]

    body = "\n".join(parts)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Study 図解 — 技術書のやさしい図解ノート</title>\n"
        f"<style>{CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def main():
    if not VAULT.exists():
        raise SystemExit(f"Vault が見つかりません: {VAULT}")

    print(f"収集元: {VAULT}")
    books = collect()
    if not books:
        raise SystemExit("図解 HTML が1つも見つかりませんでした")

    (DIST / "index.html").write_text(render_index(books), encoding="utf-8")
    total = sum(len(b["chapters"]) for b in books)
    print(f"完了: {len(books)} 冊 / {total} 章 -> {DIST}")


if __name__ == "__main__":
    main()
