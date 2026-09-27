import datetime
from pathlib import Path
from typing import List

import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UITextBox, UIWindow

from scripts.cat.cats import Cat
from scripts.cat.enums import CatGroup
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.utility import ui_scale


def get_log_dir(clan_prefix: str) -> Path:
    """Finds or creates the saves/clanprefix/logs directory."""
    direct = Path("saves") / clan_prefix / "logs"
    if (Path("saves") / clan_prefix).exists():
        return direct

    # Check parent directories in case the current working directory differs
    for parent in Path(__file__).resolve().parents:
        target = parent / "saves" / clan_prefix
        if target.exists():
            return target / "logs"

    return direct


def export_thoughts_to_markdown() -> Path:
    """Generates the thoughts markdown file in saves/clanprefix/logs

    and returns the file path.
    """
    clan_prefix = (
        str(game.clan.name)
        if (hasattr(game, "clan") and game.clan and hasattr(game.clan, "name"))
        else "clan"
    )
    log_dir = get_log_dir(clan_prefix)
    log_dir.mkdir(parents=True, exist_ok=True)

    clan_cats: List[Cat] = []
    outside_cats: List[Cat] = []
    starclan_cats: List[Cat] = []
    df_cats: List[Cat] = []
    ur_cats: List[Cat] = []

    # Categorize all loaded, non-faded cats
    for cat in Cat.all_cats.values():
        if cat.faded:
            continue

        if cat.dead:
            if cat.status.group == CatGroup.STARCLAN:
                starclan_cats.append(cat)
            elif cat.status.group == CatGroup.DARK_FOREST:
                df_cats.append(cat)
            else:
                ur_cats.append(cat)
        elif cat.status.alive_in_player_clan:
            clan_cats.append(cat)
        elif cat.status.is_outsider or cat.status.is_other_clancat or cat.status.is_lost():
            outside_cats.append(cat)

    # Sort each group by rank order, then age (Leader -> Deputy -> Warriors -> Apps -> Kits)
    rank_sort = lambda c: (Cat.rank_order(c), Cat.get_adjusted_age(c))
    clan_cats.sort(key=rank_sort, reverse=True)
    outside_cats.sort(key=rank_sort, reverse=True)
    starclan_cats.sort(key=rank_sort, reverse=True)
    df_cats.sort(key=rank_sort, reverse=True)
    ur_cats.sort(key=rank_sort, reverse=True)

    lines = []

    def format_cat_thought(c: Cat) -> str:
        thought = str(c.thought).strip() if getattr(c, "thought", None) else ""
        if not thought:
            try:
                c.thoughts()
                thought = str(c.thought).strip()
            except Exception:
                thought = "Is resting"
        return f"{c.name}: {thought}"

    # 1. Living Clan Cats (no header, directly at the top)
    if clan_cats:
        for c in clan_cats:
            lines.append(format_cat_thought(c))

    # 2. Outside Cats
    if outside_cats:
        lines.append("**Cats Outside the Clan**")
        for c in outside_cats:
            lines.append(format_cat_thought(c))

    # 3. StarClan Cats
    if starclan_cats:
        lines.append("**StarClan Cats**")
        for c in starclan_cats:
            lines.append(format_cat_thought(c))

    # 4. Dark Forest Cats (if any)
    if df_cats:
        lines.append("**Dark Forest Cats**")
        for c in df_cats:
            lines.append(format_cat_thought(c))

    # 5. Unknown Residence Cats (if any)
    if ur_cats:
        lines.append("**Unknown Residence Cats**")
        for c in ur_cats:
            lines.append(format_cat_thought(c))

    content = "\n".join(lines) + "\n"

    # Filename formatting
    moon = getattr(game.clan, "age", getattr(game.clan, "clanage", None))
    moon_prefix = f"moon{moon}_" if moon is not None else ""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"thoughts_{moon_prefix}{timestamp}"
    file_path = log_dir / f"{base_name}.md"

    counter = 1
    while file_path.exists():
        file_path = log_dir / f"{base_name}_{counter}.md"
        counter += 1

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return file_path


class ExportThoughtsWindow(UIWindow):
    """Popup window confirming the thoughts markdown export."""

    def __init__(self, manager=MANAGER):
        super().__init__(
            rect=ui_scale(pygame.Rect((175, 180), (450, 220))),
            manager=manager,
            window_display_title="Export Thoughts",
            resizable=False,
        )

        try:
            saved_path = export_thoughts_to_markdown()
            message = (
                f"<b>Thoughts exported successfully!</b><br><br>"
                f"Saved to:<br>{saved_path.name}<br><br>"
                f"<font size=2>{saved_path.parent}</font>"
            )
        except Exception as e:
            message = f"<b>Failed to export thoughts:</b><br><br>{e}"

        self.info_box = UITextBox(
            html_text=message,
            relative_rect=ui_scale(pygame.Rect((20, 15), (370, 110))),
            manager=manager,
            container=self,
        )

        self.close_button = UIButton(
            relative_rect=ui_scale(pygame.Rect((145, 135), (120, 32))),
            text="Close",
            manager=manager,
            container=self,
        )

    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if hasattr(self, "close_button") and event.ui_element == self.close_button:
                self.kill()