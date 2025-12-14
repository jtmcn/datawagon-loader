"""Rich console abstraction layer for DataWagon CLI output.

This module provides a centralized interface for all CLI output operations,
replacing Click's echo/secho and tabulate with Rich-powered alternatives.
Handles NO_COLOR environment variable and CI/CD compatibility.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

# Singleton console instance
_console: Optional[Console] = None


def get_console() -> Console:
    """Get or create the singleton Rich Console instance.

    Respects NO_COLOR environment variable and detects CI environments.

    Returns:
        Console: Rich Console instance
    """
    global _console
    if _console is None:
        no_color = os.getenv("NO_COLOR", "").lower() in ("1", "true", "yes")
        is_ci = os.getenv("CI", "").lower() in ("1", "true", "yes")
        force_terminal = not (no_color or is_ci)

        _console = Console(
            force_terminal=force_terminal,
            no_color=no_color,
            highlight=False,  # Prevent auto-highlighting of paths
        )
    return _console


# ============================================================================
# STATUS MESSAGES (replaces click.secho with colors)
# ============================================================================


def success(message: str, emoji: bool = True) -> None:
    """Display success message in green with checkmark.

    Args:
        message: Success message to display
        emoji: Include ✓ emoji (default: True)
    """
    console = get_console()
    prefix = "✓ " if emoji else ""
    console.print(f"[green]{prefix}{message}[/green]")


def error(message: str, emoji: bool = True) -> None:
    """Display error message in red with cross.

    Args:
        message: Error message to display
        emoji: Include ✗ emoji (default: True)
    """
    console = get_console()
    prefix = "✗ " if emoji else ""
    console.print(f"[red]{prefix}{message}[/red]")


def warning(message: str, emoji: bool = True) -> None:
    """Display warning message in yellow with warning symbol.

    Args:
        message: Warning message to display
        emoji: Include ⚠ emoji (default: True)
    """
    console = get_console()
    prefix = "⚠ " if emoji else ""
    console.print(f"[yellow]{prefix}{message}[/yellow]")


def info(message: str, bold: bool = False) -> None:
    """Display informational message.

    Args:
        message: Info message to display
        bold: Make text bold (default: False)
    """
    console = get_console()
    style = "bold" if bold else ""
    console.print(message, style=style)


def status(message: str) -> None:
    """Display status/progress message in blue.

    Args:
        message: Status message to display
    """
    console = get_console()
    console.print(f"[blue]{message}[/blue]")


def brand(message: str, bold: bool = True) -> None:
    """Display brand message in magenta.

    Args:
        message: Brand message to display
        bold: Make text bold (default: True)
    """
    console = get_console()
    style = "magenta bold" if bold else "magenta"
    console.print(message, style=style)


def newline() -> None:
    """Print a blank line."""
    console = get_console()
    console.print()


# ============================================================================
# STRUCTURAL ELEMENTS
# ============================================================================


def header(title: str, style: str = "cyan") -> None:
    """Display section header with decorative border.

    Args:
        title: Header title text
        style: Rich color style (default: cyan)
    """
    console = get_console()
    console.print(Rule(title, style=style))


def section_separator(title: str = "") -> None:
    """Display horizontal rule separator.

    Args:
        title: Optional title for separator
    """
    console = get_console()
    console.print(Rule(title if title else "", style="dim"))


def panel(
    content: str,
    title: Optional[str] = None,
    style: str = "cyan",
    border_style: str = "cyan",
) -> None:
    """Display content in a bordered panel.

    Args:
        content: Content to display in panel
        title: Optional panel title
        style: Content style
        border_style: Border color style
    """
    console = get_console()
    console.print(
        Panel(
            content,
            title=title,
            border_style=border_style,
            style=style,
        )
    )


# ============================================================================
# TABLES (replaces tabulate)
# ============================================================================


def table(
    data: List[List[Any]],
    headers: List[str],
    title: Optional[str] = None,
    show_lines: bool = False,
) -> None:
    """Display data in a formatted Rich table with borders.

    Args:
        data: List of rows (each row is a list of values)
        headers: Column headers
        title: Optional table title
        show_lines: Show lines between rows (default: False)
    """
    console = get_console()

    rich_table = Table(
        title=title,
        show_header=True,
        header_style="bold cyan",
        show_lines=show_lines,
        border_style="dim",
    )

    # Add columns
    for header in headers:
        # Right-align numeric-looking headers
        if "count" in header.lower():
            rich_table.add_column(header, justify="right")
        else:
            rich_table.add_column(header, justify="left")

    # Add rows
    for row in data:
        rich_table.add_row(*[str(cell) for cell in row])

    console.print(rich_table)


# ============================================================================
# FILE LISTS (special formatting for file displays)
# ============================================================================


def file_list(
    files: Sequence[str],
    max_display: int = 10,
    title: Optional[str] = None,
    count_total: Optional[int] = None,
) -> None:
    """Display list of files with optional truncation.

    Args:
        files: List of file names/paths
        max_display: Maximum number of files to show before truncating
        title: Optional title for the list
        count_total: Total count if different from len(files)
    """
    console = get_console()

    if title:
        console.print(f"\n[green]{title}[/green]")

    display_count = min(len(files), max_display)
    for file in files[:display_count]:
        console.print(f"  {file}")

    total = count_total if count_total is not None else len(files)
    if total > display_count:
        remaining = total - display_count
        console.print(f"  [dim]...and {remaining} more[/dim]")


# ============================================================================
# INLINE STATUS (replaces click.echo with nl=False pattern)
# ============================================================================


def inline_status_start(message: str) -> None:
    """Start inline status message (no newline).

    Args:
        message: Status message
    """
    console = get_console()
    console.print(message, end=" ")


def inline_status_end(success: bool, success_msg: str = "Success", error_msg: str = "Failed") -> None:
    """Complete inline status with success/error indicator.

    Args:
        success: Whether operation succeeded
        success_msg: Message for success (default: "Success")
        error_msg: Message for failure (default: "Failed")
    """
    console = get_console()
    if success:
        console.print(f"[green]✓ {success_msg}[/green]")
    else:
        console.print(f"[red]✗ {error_msg}[/red]")


# ============================================================================
# USER INTERACTION (click.confirm wrapper)
# ============================================================================


def confirm(message: str, default: bool = False, abort: bool = True) -> bool:
    """Prompt user for confirmation (wraps click.confirm).

    Args:
        message: Confirmation prompt
        default: Default value if user just hits enter
        abort: Abort on 'no' response

    Returns:
        User's response
    """
    # Still use click.confirm as it handles terminal interaction well
    import click

    return click.confirm(message, default=default, abort=abort)
