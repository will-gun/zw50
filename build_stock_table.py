import csv
import html
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import urlopen


SOURCE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
ROOT = Path(__file__).parent
INPUT_FILE = ROOT / "candi.csv"
OUTPUT_FILE = ROOT / "index.html"
SCRIPT_FILE = Path(__file__).name
ADSENSE_CLIENT = os.environ.get("ADSENSE_CLIENT", "ca-pub-1921376099483649").strip()
ADSENSE_SLOT = os.environ.get("ADSENSE_SLOT", "2393790626").strip()


def load_codes(limit: int = 50) -> list[str]:
    with INPUT_FILE.open(newline="", encoding="utf-8") as source:
        return [row[0].strip() for row in csv.reader(source) if row and row[0].strip()][
            :limit
        ]


def load_names() -> dict[str, str]:
    with urlopen(SOURCE_URL, timeout=15) as response:
        records = json.load(response)
    return {
        str(record["公司代號"]).strip(): (
            record.get("公司簡稱") or record.get("公司名稱", "")
        ).strip()
        for record in records
    }


def build_html(rows: list[tuple[int, str, str]], updated_at: datetime) -> str:
    updated_label = updated_at.strftime("%Y年%m月%d日 %H:%M（台灣時間）")
    table_rows = "\n".join(
        "        <tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            index, html.escape(code), html.escape(name)
        )
        for index, code, name in rows
    )
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>選股策略名稱：ZW50</title>
{f'  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={html.escape(ADSENSE_CLIENT)}" crossorigin="anonymous"></script>' if ADSENSE_CLIENT and ADSENSE_SLOT else ''}
  <style>
    :root {{ color-scheme: light; font-family: system-ui, -apple-system, sans-serif; }}
    body {{ margin: 0; background: #f4f6f8; color: #17212b; }}
    main {{ max-width: 760px; margin: 0 auto; padding: 40px 20px; }}
    h1 {{ margin: 0 0 20px; font-size: 1.8rem; }}
    .strategy-intro {{ margin: 0 0 10px; line-height: 1.7; }}
    .strategy-factors {{ margin: 0 0 10px; padding-left: 24px; line-height: 1.7; }}
    .strategy-update {{ margin: 0 0 20px; line-height: 1.7; }}
    .data-updated {{ margin: -10px 0 20px; color: #61707d; font-size: 0.9rem; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; box-shadow: 0 8px 24px #17212b14; }}
    th, td {{ padding: 11px 14px; border-bottom: 1px solid #e4e9ee; text-align: left; }}
    th {{ background: #17324d; color: #fff; font-weight: 600; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    tbody tr:hover {{ background: #edf5f7; }}
    th:first-child, td:first-child {{ width: 90px; text-align: center; }}
    th:nth-child(2), td:nth-child(2) {{ width: 180px; font-variant-numeric: tabular-nums; }}
    footer {{ max-width: 760px; margin: 0 auto; padding: 0 20px 24px; color: #61707d; text-align: center; font-size: 0.9rem; }}
    footer p {{ margin: 0; }}
    footer a {{ color: #17324d; }}
  </style>
</head>
<body>
  <main>
        <h1>選股策略名稱：ZW50</h1>
        <p class="strategy-intro">ZW50 以個股近十年的價格表現為篩選依據，綜合評估以下三項因子：</p>
        <ul class="strategy-factors">
            <li>十年期間的回檔幅度</li>
            <li>十年期間的漲跌波動程度</li>
            <li>十年期間的累積漲幅</li>
        </ul>
        <p class="strategy-update">以下為依據上述因子篩選出的 50 檔候選股票，名單每日更新。</p>
        <p class="data-updated">資料更新時間：{updated_label}</p>
{f'''    <ins class="adsbygoogle"
            style="display:block; text-align:center;"
            data-ad-layout="in-article"
            data-ad-format="fluid"
            data-ad-client="{html.escape(ADSENSE_CLIENT)}"
            data-ad-slot="{html.escape(ADSENSE_SLOT)}"
            ></ins>
        <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>''' if ADSENSE_CLIENT and ADSENSE_SLOT else ''}
    <table>
      <thead><tr><th>index</th><th>數字code</th><th>中文名稱</th></tr></thead>
      <tbody>
{table_rows}
      </tbody>
    </table>
  </main>
    <footer>
        <p>© 2026 痞客兔. All rights reserved. | <a href="/privacy.html" target="_blank">隱私權政策 Privacy Policy</a></p>
    </footer>
</body>
</html>
"""


def publish_changes() -> None:
    files_to_commit = [INPUT_FILE.name, OUTPUT_FILE.name, SCRIPT_FILE]
    subprocess.run(["git", "add", *files_to_commit], cwd=ROOT, check=True)
    staged_changes = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False
    )
    if staged_changes.returncode == 0:
        print("No changes to commit.")
        return
    subprocess.run(
        ["git", "commit", "--allow-empty-message", "-m", ""], cwd=ROOT, check=True
    )
    subprocess.run(["git", "push", "origin", "HEAD"], cwd=ROOT, check=True)


def main() -> None:
    codes = load_codes()
    names = load_names()
    missing = [code for code in codes if code not in names]
    if missing:
        raise ValueError(f"Missing stock names: {', '.join(missing)}")
    rows = [(index, str(int(code)), names[code]) for index, code in enumerate(codes, 1)]
    updated_at = datetime.now(ZoneInfo("Asia/Taipei"))
    OUTPUT_FILE.write_text(build_html(rows, updated_at), encoding="utf-8")
    publish_changes()


if __name__ == "__main__":
    main()