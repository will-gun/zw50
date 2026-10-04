import csv
import html
import json
from datetime import datetime
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo
from urllib.request import urlopen


SOURCE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
ROOT = Path(__file__).parent
INPUT_FILE = ROOT / "candi.csv"
OUTPUT_FILE = ROOT / "index.html"
SCRIPT_FILE = Path(__file__).name


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


def update_html(
    existing_html: str,
    rows: list[tuple[int, str, str]],
    updated_at: datetime,
) -> str:
    updated_label = updated_at.strftime("%Y年%m月%d日 %H:%M（台灣時間）")
    table_rows = "\n".join(
        "        <tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            index, html.escape(code), html.escape(name)
        )
        for index, code, name in rows
    )
    tbody_start = "      <tbody>\n"
    tbody_end = "      </tbody>"
    timestamp_marker = '<p class="data-updated">資料更新時間：'
    if existing_html.count(tbody_start) != 1 or existing_html.count(tbody_end) != 1:
        raise ValueError("Expected exactly one table body in index.html")
    if existing_html.count(timestamp_marker) != 1:
        raise ValueError("Expected exactly one data update timestamp in index.html")

    table_content_start = existing_html.index(tbody_start) + len(tbody_start)
    table_content_end = existing_html.index(tbody_end, table_content_start)
    updated_html = (
        existing_html[:table_content_start]
        + table_rows
        + "\n"
        + existing_html[table_content_end:]
    )

    timestamp_start = updated_html.index(timestamp_marker) + len(timestamp_marker)
    timestamp_end = updated_html.index("</p>", timestamp_start)
    return updated_html[:timestamp_start] + updated_label + updated_html[timestamp_end:]


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
    existing_html = OUTPUT_FILE.read_text(encoding="utf-8")
    updated_html = update_html(existing_html, rows, updated_at)
    OUTPUT_FILE.write_text(updated_html, encoding="utf-8")
    publish_changes()


if __name__ == "__main__":
    main()