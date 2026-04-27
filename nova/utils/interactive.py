"""Interactive terminal helpers for Nova CLI surfaces."""

from __future__ import annotations

import os
import select
import shutil
import sys
import textwrap

IS_WINDOWS = sys.platform.startswith("win")
if not IS_WINDOWS:
    import termios
    import tty


def is_tty() -> bool:
    try:
        return bool(sys.stdin.isatty()) and bool(sys.stdout.isatty())
    except Exception:
        return False


def terminal_columns(default: int = 96) -> int:
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:
        return default


def _visible_line_count(rendered: str) -> int:
    return rendered.count("\n")


def _fallback_select(options: list[str], *, title: str = "", default: int = 0) -> int:
    if title:
        print(title)
    for index, option in enumerate(options, start=1):
        marker = "▸" if index - 1 == default else " "
        print(f"  {marker} {index}. {option}")
    try:
        answer = input("\n  -> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if answer.isdigit():
        selected = int(answer) - 1
        if 0 <= selected < len(options):
            return selected
    return default


def select_menu(
    options: list[str],
    *,
    title: str = "",
    descriptions: list[str] | None = None,
    default: int = 0,
    footer: str = "↑/↓ mover · Enter confirmar · número salto directo",
) -> int:
    if not options:
        return 0
    if not is_tty():
        return _fallback_select(options, title=title, default=default)

    descriptions = descriptions or []
    current = max(0, min(default, len(options) - 1))
    rendered_line_count = 0

    def draw(first: bool = False) -> None:
        nonlocal rendered_line_count
        width = max(56, min(terminal_columns(), 100))
        content_width = max(24, width - 8)
        out: list[str] = []
        if not first and rendered_line_count:
            out.append(f"\033[{rendered_line_count}F")
            for _ in range(rendered_line_count):
                out.append("\033[2K")
                out.append("\033[1E")
            out.append(f"\033[{rendered_line_count}F")

        line_count = 0
        if title:
            out.append(f"\n  {title}\n")
            out.append("  Usa ↑/↓ y Enter para elegir una acción.\n\n")
            line_count += 4

        for index, option in enumerate(options):
            marker = "▸" if index == current else " "
            label = f"{index + 1}. {option}"
            out.append(f"  {marker} {label}\n")
            line_count += 1
            if index < len(descriptions) and descriptions[index]:
                wrapped = textwrap.wrap(
                    descriptions[index],
                    width=content_width,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                for row in wrapped:
                    out.append(f"      {row}\n")
                    line_count += 1

        out.append(f"\n  {footer}\n")
        line_count += 2
        rendered = "".join(out)
        rendered_line_count = _visible_line_count(rendered)
        sys.stdout.write(rendered)
        sys.stdout.flush()

    def read_key() -> str:
        if IS_WINDOWS:
            import msvcrt

            first = msvcrt.getch()
            if first in (b"\r", b"\n"):
                return "\r"
            if first == b"\x03":
                return "\x03"
            if first in (b"\x00", b"\xe0"):
                second = msvcrt.getch()
                if second == b"H":
                    return "UP"
                if second == b"P":
                    return "DOWN"
                return second.decode(errors="ignore")
            return first.decode(errors="ignore")
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setraw(fd)
        try:
            first = os.read(fd, 1)
            if first in (b"\r", b"\n"):
                termios.tcflush(fd, termios.TCIFLUSH)
                return "\r"
            if first == b"\x03":
                return "\x03"
            if first == b"\x1b":
                ready, _, _ = select.select([fd], [], [], 0.05)
                if not ready:
                    return "\x1b"
                second = os.read(fd, 1)
                if second == b"[":
                    ready2, _, _ = select.select([fd], [], [], 0.05)
                    if not ready2:
                        return "["
                    third = os.read(fd, 1)
                    if third == b"A":
                        return "UP"
                    if third == b"B":
                        return "DOWN"
                    return third.decode(errors="ignore")
                return second.decode(errors="ignore")
            return first.decode(errors="ignore")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    draw(first=True)
    while True:
        key = read_key()
        if key == "\r":
            return current
        if key == "\x03":
            raise KeyboardInterrupt
        if key in ("UP", "k", "K") and current > 0:
            current -= 1
            draw()
            continue
        if key in ("DOWN", "j", "J") and current < len(options) - 1:
            current += 1
            draw()
            continue
        if key.isdigit():
            selected = int(key) - 1
            if 0 <= selected < len(options):
                current = selected
                draw()
                continue
