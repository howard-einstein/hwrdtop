"""Pure helpers for filtering, sorting, and arranging process rows."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from hwrdtop.models.system import ProcessInfo

SortKey = str


def filter_processes(
    processes: Sequence[ProcessInfo], query: str
) -> list[ProcessInfo]:
    """Filter process command names, ignoring case and surrounding spaces."""
    normalized = query.strip().casefold()
    if not normalized:
        return list(processes)
    return [process for process in processes if normalized in process.command.casefold()]


def sort_processes(
    processes: Sequence[ProcessInfo], sort_by: SortKey
) -> list[ProcessInfo]:
    """Sort by a supported field with stable, predictable tie-breakers."""
    sort_keys = {
        "cpu": lambda process: (-process.cpu_percent, process.pid),
        "mem": lambda process: (-process.memory_percent, process.pid),
        "pid": lambda process: (process.pid,),
        "name": lambda process: (process.command.casefold(), process.pid),
    }
    try:
        key = sort_keys[sort_by]
    except KeyError as error:
        raise ValueError(f"unsupported process sort key: {sort_by}") from error
    return sorted(processes, key=key)


def tree_processes(
    processes: Sequence[ProcessInfo],
) -> list[tuple[ProcessInfo, str]]:
    """Return parent-first process rows with branch prefixes for display."""
    by_pid = {process.pid: process for process in processes}
    children: dict[int, list[ProcessInfo]] = defaultdict(list)
    roots: list[ProcessInfo] = []

    for process in processes:
        if process.ppid == process.pid or process.ppid not in by_pid:
            roots.append(process)
        else:
            children[process.ppid].append(process)

    ordered: list[tuple[ProcessInfo, str]] = []
    visited: set[int] = set()

    def visit(process: ProcessInfo, prefix: str, is_last: bool) -> None:
        if process.pid in visited:
            return
        visited.add(process.pid)
        branch = "└─ " if is_last else "├─ "
        ordered.append((process, f"{prefix}{branch}" if prefix else ""))
        descendants = children.get(process.pid, [])
        child_prefix = f"{prefix}{'   ' if is_last else '│  '}" if prefix else "   "
        for index, child in enumerate(descendants):
            visit(child, child_prefix, index == len(descendants) - 1)

    for index, root in enumerate(roots):
        visit(root, "", index == len(roots) - 1)

    for process in processes:
        if process.pid not in visited:
            visit(process, "", True)
    return ordered
