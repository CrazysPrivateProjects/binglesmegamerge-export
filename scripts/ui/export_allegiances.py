import datetime
from pathlib import Path
from typing import List

import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UITextBox, UIWindow

from scripts.cat.cats import Cat
from scripts.cat.enums import CatAge, CatRank
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.utility import event_text_adjust, get_alive_clan_queens, ui_scale


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


def format_cat_entry(cat: Cat, short_desc: bool = False) -> str:
    """Formats a single cat as: <u>CatName</u> - description."""
    name = str(cat.name)
    try:
        desc = cat.describe_cat(short=short_desc)
    except TypeError:
        desc = cat.describe_cat()

    # Resolve any translation or pronoun tokens
    desc = event_text_adjust(Cat, desc, main_cat=cat)
    return f"<u>{name}</u> - {desc}"


def format_section(label: str, entries: List[str]) -> str:
    """Formats a markdown section. If empty, outputs 'N/A'."""
    if not entries:
        return f"**{label}:** N/A"
    if len(entries) == 1:
        return f"**{label}:** {entries[0]}"
    return f"**{label}:** {entries[0]}\n" + "\n".join(entries[1:])


def export_allegiances_to_markdown() -> Path:
    """Generates the allegiances markdown file in saves/clanprefix/logs

    and returns the file path.
    """
    clan_prefix = (
        str(game.clan.name)
        if (hasattr(game, "clan") and game.clan and hasattr(game.clan, "name"))
        else "clan"
    )
    log_dir = get_log_dir(clan_prefix)
    log_dir.mkdir(parents=True, exist_ok=True)

    living_cats = [
        c for c in Cat.all_cats.values() if c.status.alive_in_player_clan
    ]

    # Categorize cats
    living_clerics = []
    living_storytellers = []
    living_warriors_raw = []
    living_apprentices = []
    living_elders = []
    other_roles = {
        "Mediator": [],
        "Caretaker": [],
        "Denkeeper": [],
        "Messenger": [],
        "Gardener": [],
    }

    for cat in living_cats:
        rank = cat.status.rank
        if rank == CatRank.MEDICINE_CAT or rank == getattr(
            CatRank, "CLERIC", None
        ):
            living_clerics.append(cat)
        elif rank == getattr(CatRank, "STORYTELLER", None):
            living_storytellers.append(cat)
        elif rank == CatRank.WARRIOR:
            living_warriors_raw.append(cat)
        elif rank.is_any_apprentice_rank():
            living_apprentices.append(cat)
        elif rank == CatRank.ELDER:
            living_elders.append(cat)
        elif rank == CatRank.MEDIATOR:
            other_roles["Mediator"].append(cat)
        elif rank == getattr(CatRank, "CARETAKER", None):
            other_roles["Caretaker"].append(cat)
        elif rank == getattr(CatRank, "DENKEEPER", None):
            other_roles["Denkeeper"].append(cat)
        elif rank == getattr(CatRank, "MESSENGER", None):
            other_roles["Messenger"].append(cat)
        elif rank == getattr(CatRank, "GARDENER", None):
            other_roles["Gardener"].append(cat)

    # Queens and Kits
    queen_dict, living_kits = get_alive_clan_queens(living_cats)

    # Remove nursing queens from warriors/elders
    for q_id in queen_dict:
        queen_cat = Cat.fetch_cat(q_id)
        if not queen_cat:
            continue
        if queen_cat in living_warriors_raw:
            living_warriors_raw.remove(queen_cat)
        if queen_cat in living_elders:
            living_elders.remove(queen_cat)

    # Separate Senior Warriors from regular Warriors
    senior_warriors = []
    warriors = []
    for cat in living_warriors_raw:
        is_senior = (
            cat.status.rank == getattr(CatRank, "SENIOR_WARRIOR", None)
            or (
                hasattr(CatAge, "SENIOR_ADULT")
                and getattr(cat, "age", None) == CatAge.SENIOR_ADULT
            )
            or getattr(cat, "is_senior", False)
            or getattr(cat, "senior", False)
            or (getattr(cat, "moons", 0) >= 96)
        )
        if is_senior:
            senior_warriors.append(cat)
        else:
            warriors.append(cat)

    # Build sections
    sections = []

    # 1. Leader
    if game.clan.leader and game.clan.leader.status.alive_in_player_clan:
        sections.append(
            f"**Leader:** {format_cat_entry(game.clan.leader)}"
        )
    else:
        sections.append("**Leader:** N/A")

    # 2. Deputy
    if game.clan.deputy and game.clan.deputy.status.alive_in_player_clan:
        sections.append(
            f"**Deputy:** {format_cat_entry(game.clan.deputy)}"
        )
    else:
        sections.append("**Deputy:** N/A")

    # 3. Cleric (Medicine cats)
    sections.append(
        format_section("Cleric", [format_cat_entry(c) for c in living_clerics])
    )

    # 4. Storyteller
    sections.append(
        format_section(
            "Storyteller", [format_cat_entry(c) for c in living_storytellers]
        )
    )

    # 5. Other specialized roles (if populated)
    for role_name, cats in other_roles.items():
        if cats:
            sections.append(
                format_section(
                    role_name, [format_cat_entry(c) for c in cats]
                )
            )

    # 6. Senior Warriors
    sections.append(
        format_section(
            "Senior Warriors", [format_cat_entry(c) for c in senior_warriors]
        )
    )

    # 7. Warriors
    sections.append(
        format_section("Warriors", [format_cat_entry(c) for c in warriors])
    )

    # 8. Apprentices
    sections.append(
        format_section(
            "Apprentices", [format_cat_entry(c) for c in living_apprentices]
        )
    )

    # 9. Queens and Kits
    qk_entries = []
    for q_id, kits in queen_dict.items():
        queen = Cat.fetch_cat(q_id)
        if queen:
            qk_entries.append(format_cat_entry(queen))
    for k in living_kits:
        qk_entries.append(format_cat_entry(k, short_desc=True))
    sections.append(format_section("Queens and Kits", qk_entries))

    # 10. Elders
    sections.append(
        format_section("Elders", [format_cat_entry(c) for c in living_elders])
    )

    content = "\n".join(sections) + "\n"

    # Save to file
    moon = getattr(game.clan, "age", getattr(game.clan, "clanage", None))
    moon_prefix = f"moon{moon}_" if moon is not None else ""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"allegiances_{moon_prefix}{timestamp}"
    file_path = log_dir / f"{base_name}.md"

    counter = 1
    while file_path.exists():
        file_path = log_dir / f"{base_name}_{counter}.md"
        counter += 1

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return file_path


class ExportAllegiancesWindow(UIWindow):
    """Popup window confirming the allegiances markdown export."""

    def __init__(self, manager=MANAGER):
        super().__init__(
            rect=ui_scale(pygame.Rect((175, 180), (450, 220))),
            manager=manager,
            window_display_title="Export Allegiances",
            resizable=False,
        )

        try:
            saved_path = export_allegiances_to_markdown()
            message = (
                f"<b>Allegiances exported successfully!</b><br><br>"
                f"Saved to:<br>{saved_path.name}<br><br>"
                f"<font size=2>{saved_path.parent}</font>"
            )
        except Exception as e:
            message = f"<b>Failed to export allegiances:</b><br><br>{e}"

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