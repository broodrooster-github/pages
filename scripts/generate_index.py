#!/usr/bin/env python3
"""Generate the GitHub Pages game catalog from Godot web exports."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "index.html"
ICON_CANDIDATES = (
    "index.icon.png",
    "index.apple-touch-icon.png",
    "index.png",
)


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


def find_games() -> list[dict[str, str | None]]:
    games: list[dict[str, str | None]] = []

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
            }
        )

    return sorted(
        games,
        key=lambda game: re.sub(r"[^a-z0-9]+", "", str(game["title"]).casefold()),
    )


def render_card(game: dict[str, str | None]) -> str:
    title = html.escape(str(game["title"]))
    directory = str(game["directory"])
    encoded_directory = quote(directory)
    icon = game["icon"]

    if icon:
        artwork = (
            f'<img src="./{encoded_directory}/{quote(str(icon))}" '
            f'alt="" loading="lazy">'
        )
    else:
        artwork = '<span class="card-placeholder" aria-hidden="true">BR</span>'

    return f"""\
      <a class="game-card" href="./{encoded_directory}/">
        <span class="game-artwork">{artwork}</span>
        <span class="game-info">
          <strong>{title}</strong>
          <span>Play in browser <span aria-hidden="true">→</span></span>
        </span>
      </a>"""


def render_page(games: list[dict[str, str | None]]) -> str:
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
</body>
</html>
"""


def main() -> None:
    games = find_games()
    OUTPUT.write_text(render_page(games), encoding="utf-8")
    print(f"Generated {OUTPUT.name} with {len(games)} games")


if __name__ == "__main__":
    main()
