#!/usr/bin/env python3
"""Generate the GitHub Pages game catalog from Godot web exports."""

from __future__ import annotations

import html
import re
import subprocess
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import TypedDict
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "index.html"
ICON_CANDIDATES = (
    "index.icon.png",
    "index.apple-touch-icon.png",
    "index.png",
)


class Game(TypedDict):
    title: str
    directory: str
    icon: str | None
    updated: datetime | None


RELATIVE_TIME_SCRIPT = """
<script>
(function () {
  function plural(count, unit) {
    return count + " " + unit + (count === 1 ? "" : "s");
  }

  function formatAgo(iso) {
    var from = new Date(iso);
    if (Number.isNaN(from.getTime())) return "";

    var to = new Date();
    if (from > to) return "Updated just now";

    var years = to.getFullYear() - from.getFullYear();
    var months = to.getMonth() - from.getMonth();
    var days = to.getDate() - from.getDate();
    var hours = to.getHours() - from.getHours();
    var minutes = to.getMinutes() - from.getMinutes();

    if (minutes < 0) {
      minutes += 60;
      hours -= 1;
    }
    if (hours < 0) {
      hours += 24;
      days -= 1;
    }
    if (days < 0) {
      days += new Date(to.getFullYear(), to.getMonth(), 0).getDate();
      months -= 1;
    }
    if (months < 0) {
      months += 12;
      years -= 1;
    }

    var parts = [];
    if (years) parts.push(plural(years, "year"));
    if (months) parts.push(plural(months, "month"));
    if (days) parts.push(plural(days, "day"));
    if (hours) parts.push(plural(hours, "hour"));
    if (minutes) parts.push(plural(minutes, "minute"));
    if (!parts.length) return "Updated just now";
    return "Updated " + parts.join(", ") + " ago";
  }

  function refresh() {
    document.querySelectorAll("time.game-updated[datetime]").forEach(function (el) {
      var from = new Date(el.dateTime);
      var label = formatAgo(el.dateTime);
      if (label) el.textContent = label;
      if (!Number.isNaN(from.getTime())) el.title = from.toLocaleString();
    });
  }

  refresh();
  setInterval(refresh, 60000);
})();
</script>
"""


class TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.casefold() == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.parts).split())


def read_title(index_file: Path) -> str:
    parser = TitleParser()
    parser.feed(index_file.read_text(encoding="utf-8", errors="replace"))
    return parser.title or index_file.parent.name


def git_last_updated(directory: Path) -> datetime | None:
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "-1",
                "--format=%cI",
                "--",
                str(directory.relative_to(ROOT)),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    iso = result.stdout.strip()
    if not iso:
        return None

    return datetime.fromisoformat(iso)


def filesystem_last_updated(directory: Path) -> datetime | None:
    mtimes: list[float] = []
    for path in directory.rglob("*"):
        if path.is_file():
            mtimes.append(path.stat().st_mtime)
    if not mtimes:
        return None
    return datetime.fromtimestamp(max(mtimes), tz=timezone.utc)


def last_updated(directory: Path) -> datetime | None:
    return git_last_updated(directory) or filesystem_last_updated(directory)


def format_updated(updated: datetime) -> str:
    aware = updated if updated.tzinfo else updated.replace(tzinfo=timezone.utc)
    return aware.isoformat()


def find_games() -> list[Game]:
    games: list[Game] = []

    for directory in ROOT.iterdir():
        if not directory.is_dir() or directory.name.startswith((".", "_")):
            continue

        index_file = directory / "index.html"
        if not index_file.is_file():
            continue

        icon = next(
            (name for name in ICON_CANDIDATES if (directory / name).is_file()),
            None,
        )
        games.append(
            {
                "title": read_title(index_file),
                "directory": directory.name,
                "icon": icon,
                "updated": last_updated(directory),
            }
        )

    return sorted(games, key=_game_sort_key)


def _game_sort_key(game: Game) -> tuple[float, str]:
    updated = game["updated"]
    recency = -updated.timestamp() if updated is not None else float("inf")
    title_key = re.sub(r"[^a-z0-9]+", "", game["title"].casefold())
    return (recency, title_key)


def render_card(game: Game) -> str:
    title = html.escape(game["title"])
    directory = game["directory"]
    encoded_directory = quote(directory)
    icon = game["icon"]
    updated = game["updated"]

    if icon:
        artwork = (
            f'<img src="./{encoded_directory}/{quote(str(icon))}" '
            f'alt="" loading="lazy">'
        )
    else:
        artwork = '<span class="card-placeholder" aria-hidden="true">BR</span>'

    if updated is not None:
        iso = html.escape(format_updated(updated))
        updated_html = f'<time class="game-updated" datetime="{iso}">Updated</time>'
    else:
        updated_html = ""

    return f"""\
      <a class="game-card" href="./{encoded_directory}/">
        <span class="game-artwork">{artwork}</span>
        <span class="game-info">
          <strong>{title}</strong>
          {updated_html}
          <span>Play in browser <span aria-hidden="true">→</span></span>
        </span>
      </a>"""


def render_page(games: list[Game]) -> str:
    cards = "\n".join(render_card(game) for game in games)
    game_word = "game" if len(games) == 1 else "games"

    return f"""\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>Broodrooster Games</title>
  <style>
    :root {{
      color-scheme: dark;
      --background: #101317;
      --surface: #191e24;
      --surface-hover: #222a33;
      --border: #303943;
      --text: #f4f7fa;
      --muted: #9ca9b7;
      --accent: #f2b84b;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      min-height: 100vh;
      margin: 0;
      color: var(--text);
      background: var(--background);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }}

    main {{
      width: min(1120px, calc(100% - 2rem));
      margin: 0 auto;
      padding: clamp(3rem, 8vw, 7rem) 0;
    }}

    header {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 1.5rem;
      margin-bottom: 2rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem;
    }}

    .eyebrow {{
      margin: 0 0 0.5rem;
      color: var(--accent);
      font-size: 0.75rem;
      font-weight: 800;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(2.25rem, 7vw, 4.75rem);
      line-height: 0.95;
      letter-spacing: -0.055em;
    }}

    .game-count {{
      flex: none;
      margin: 0 0 0.3rem;
      color: var(--muted);
    }}

    .game-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, 245px), 1fr));
      gap: 1rem;
    }}

    .game-card {{
      min-width: 0;
      overflow: hidden;
      color: inherit;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      text-decoration: none;
      transition: border-color 150ms ease, background 150ms ease,
        transform 150ms ease;
    }}

    .game-card:hover {{
      background: var(--surface-hover);
      border-color: #566575;
      transform: translateY(-3px);
    }}

    .game-card:focus-visible {{
      outline: 3px solid var(--accent);
      outline-offset: 3px;
    }}

    .game-artwork {{
      display: grid;
      width: 100%;
      aspect-ratio: 16 / 10;
      overflow: hidden;
      place-items: center;
      background: #252c35;
      border-bottom: 1px solid var(--border);
    }}

    .game-artwork img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}

    .card-placeholder {{
      color: var(--muted);
      font-size: 2rem;
      font-weight: 900;
      letter-spacing: -0.08em;
    }}

    .game-info {{
      display: grid;
      gap: 0.5rem;
      padding: 1rem 1.1rem 1.2rem;
    }}

    .game-info strong {{
      overflow: hidden;
      font-size: 1.05rem;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .game-updated {{
      color: var(--muted);
      font-size: 0.8rem;
      line-height: 1.35;
    }}

    .game-info > span {{
      color: var(--muted);
      font-size: 0.85rem;
    }}

    @media (max-width: 540px) {{
      main {{
        width: min(100% - 1.25rem, 1120px);
        padding-top: 2.5rem;
      }}

      header {{
        align-items: start;
        flex-direction: column;
      }}
    }}

    @media (prefers-reduced-motion: reduce) {{
      .game-card {{
        transition: none;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <p class="eyebrow">Broodrooster</p>
        <h1>Games</h1>
      </div>
      <p class="game-count">{len(games)} {game_word}</p>
    </header>
    <section class="game-grid" aria-label="Games">
{cards}
    </section>
  </main>
{RELATIVE_TIME_SCRIPT}
</body>
</html>
"""


def main() -> None:
    games = find_games()
    OUTPUT.write_text(render_page(games), encoding="utf-8")
    print(f"Generated {OUTPUT.name} with {len(games)} games")


if __name__ == "__main__":
    main()
