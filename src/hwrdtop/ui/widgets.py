"""Dashboard widgets for the live system overview."""

from __future__ import annotations

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from hwrdtop.models.system import MemoryStats, SystemSnapshot


def _usage_style(percent: float) -> str:
    """Choose a warning color for a utilization percentage."""
    if percent >= 85:
        return "bold #ff6b6b"
    if percent >= 60:
        return "bold #ffd166"
    return "bold #67e8a5"


def _bar(percent: float, width: int = 12) -> Text:
    """Render a compact utilization bar with threshold coloring."""
    bounded = min(100.0, max(0.0, percent))
    filled = round(width * bounded / 100)
    result = Text("[", style="dim")
    result.append("█" * filled, style=_usage_style(bounded))
    result.append("░" * (width - filled), style="#3b454b")
    result.append("]", style="dim")
    return result


def _format_bytes(value: int) -> str:
    """Format a byte count using a compact binary unit."""
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TiB"


def _memory_line(label: str, stats: MemoryStats) -> Text:
    line = Text(f"{label} ", style="bold #d9e2dc")
    line.append_text(_bar(stats.percent))
    line.append(
        f" {_format_bytes(stats.used_bytes)} / {_format_bytes(stats.total_bytes)} "
        f"{stats.percent:.0f}%",
        style=_usage_style(stats.percent),
    )
    return line


def _duration(seconds: float) -> str:
    total = max(0, int(seconds))
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    prefix = f"{days}d " if days else ""
    return f"{prefix}{hours:02d}:{minutes:02d}:{seconds:02d}"


class SystemPanel(Static):
    """Compact live system metrics with per-core CPU bars."""

    def set_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Render the latest system snapshot."""
        title = Text("HWRDTOP", style="bold #67e8e5")
        title.append("  LIVE SYSTEM MONITOR", style="bold #d9e2dc")
        title.append("  Linux", style="#96a6a8")

        cpu_line = Text("CPU  ", style="bold #d9e2dc")
        cpu_line.append_text(_bar(snapshot.cpu_percent, width=16))
        cpu_line.append(
            f" {snapshot.cpu_percent:.0f}% overall",
            style=_usage_style(snapshot.cpu_percent),
        )

        core_grid = Table.grid(expand=True, padding=(0, 1))
        for _ in range(4):
            core_grid.add_column(ratio=1)
        core_cells: list[Text] = []
        for index, percent in enumerate(snapshot.per_core_cpu_percent):
            cell = Text(f"C{index:02d} ", style="dim")
            cell.append_text(_bar(percent, width=8))
            cell.append(f" {percent:.0f}%", style=_usage_style(percent))
            core_cells.append(cell)
        for offset in range(0, len(core_cells), 4):
            row = core_cells[offset : offset + 4]
            row.extend(Text() for _ in range(4 - len(row)))
            core_grid.add_row(*row)

        details = Text("LOAD  ", style="bold #d9e2dc")
        details.append("  ".join(f"{load:.2f}" for load in snapshot.load_average))
        details.append("     UP  ", style="bold #d9e2dc")
        details.append(_duration(snapshot.uptime_seconds))
        details.append("     TASKS  ", style="bold #d9e2dc")
        details.append(
            f"{snapshot.tasks.total} total  {snapshot.tasks.running} running  "
            f"{snapshot.tasks.sleeping} sleeping"
        )

        self.update(
            Group(
                title,
                cpu_line,
                core_grid,
                Group(
                    _memory_line("MEM ", snapshot.memory),
                    _memory_line("SWAP", snapshot.swap),
                ),
                details,
            )
        )
