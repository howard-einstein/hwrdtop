"""Textual application wiring collectors, process controls, and widgets."""

from __future__ import annotations

import asyncio
import signal

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Input, Static

from hwrdtop.collectors.base import SystemCollector
from hwrdtop.collectors.linux import supported_collector
from hwrdtop.models.processes import filter_processes, sort_processes, tree_processes
from hwrdtop.models.system import ProcessInfo, SystemSnapshot
from hwrdtop.ui.dialogs import KillDialog
from hwrdtop.ui.widgets import SystemPanel

_SORT_COLUMNS = {
    "cpu": "cpu",
    "mem": "mem",
    "pid": "pid",
    "name": "command",
}


class HWRDTopApp(App[None]):
    """Live system monitor with asynchronous collection and process controls."""

    TITLE = "HWRDTOP"
    SUB_TITLE = "LINUX SYSTEM MONITOR"
    CSS = """
    Screen {
        background: #101719;
        color: #d9e2dc;
    }
    Header {
        background: #182126;
        color: #67e8e5;
    }
    #system-panel {
        height: auto;
        min-height: 5;
        max-height: 16;
        padding: 0 1;
        background: #141d21;
        border-bottom: solid #314147;
    }
    #search {
        height: 3;
        margin: 0 1;
        border: tall #67e8e5;
    }
    .hidden {
        display: none;
    }
    #message {
        height: 1;
        padding: 0 1;
        color: #ffd166;
    }
    DataTable {
        height: 1fr;
        border: none;
        scrollbar-color: #45666a;
        scrollbar-color-hover: #67e8e5;
        background: #101719;
    }
    DataTable > .datatable--header {
        background: #202c30;
        color: #b5c4c1;
    }
    DataTable > .datatable--cursor {
        background: #214345;
        color: #ffffff;
    }
    Footer {
        background: #182126;
        color: #a8b5b2;
    }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("c", "sort_cpu", "CPU", show=True),
        Binding("f1", "sort_cpu", "", show=False),
        Binding("m", "sort_mem", "MEM", show=True),
        Binding("f2", "sort_mem", "", show=False),
        Binding("p", "sort_pid", "PID", show=True),
        Binding("f3", "sort_pid", "", show=False),
        Binding("n", "sort_name", "Name", show=True),
        Binding("f4", "sort_name", "", show=False),
        Binding("/", "focus_search", "Search", show=True),
        Binding("escape", "clear_search", "", show=False),
        Binding("t", "toggle_tree", "Tree", show=True),
        Binding("k", "kill_selected", "Kill", show=True),
    ]

    def __init__(
        self,
        refresh_rate: float = 1.0,
        collector: SystemCollector | None = None,
    ) -> None:
        super().__init__()
        if refresh_rate <= 0:
            raise ValueError("refresh_rate must be greater than zero")
        self.refresh_rate = refresh_rate
        self.collector = collector or supported_collector()
        self.sort_by = "cpu"
        self.tree_view = False
        self._snapshot: SystemSnapshot | None = None
        self._refreshing = False
        self._visible_processes: list[ProcessInfo] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield SystemPanel(id="system-panel")
        yield Input(
            placeholder="Filter process names...", id="search", classes="hidden"
        )
        yield Static("Starting data collector...", id="message")
        yield DataTable(zebra_stripes=True, cursor_type="row", id="process-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#process-table", DataTable)
        for key, label, width in (
            ("pid", "PID", 8),
            ("user", "USER", 12),
            ("cpu", "CPU%", 8),
            ("mem", "MEM%", 8),
            ("res", "RES", 10),
            ("state", "STATE", 10),
            ("time", "TIME", 10),
            ("command", "COMMAND", 32),
        ):
            table.add_column(label, key=key, width=width)
        table.focus()
        self.set_interval(self.refresh_rate, self._tick)
        self._tick()

    def _tick(self) -> None:
        if not self._refreshing:
            self.run_worker(self._collect_and_render(), group="collector", exclusive=True)

    async def _collect_and_render(self) -> None:
        self._refreshing = True
        try:
            snapshot = await asyncio.to_thread(self.collector.collect)
        except Exception as error:
            self.query_one("#message", Static).update(f"Collector error: {error}")
            return
        finally:
            self._refreshing = False

        self._snapshot = snapshot
        self.query_one(SystemPanel).set_snapshot(snapshot)
        self.query_one("#message", Static).update(
            f"SORT: {self.sort_by.upper()}    "
            f"VIEW: {'TREE' if self.tree_view else 'FLAT'}    "
            f"PROCESSES: {len(snapshot.processes)}"
        )
        self._render_processes()

    def _render_processes(self) -> None:
        if self._snapshot is None:
            return
        table = self.query_one("#process-table", DataTable)
        search = self.query_one("#search", Input)
        selected_pid: int | None = None
        if self._visible_processes and table.row_count:
            row = min(table.cursor_row, len(self._visible_processes) - 1)
            selected_pid = self._visible_processes[row].pid

        processes = filter_processes(self._snapshot.processes, search.value)
        processes = sort_processes(processes, self.sort_by)
        rows = tree_processes(processes) if self.tree_view else [
            (process, "") for process in processes
        ]

        table.clear(columns=False)
        self._visible_processes = [process for process, _prefix in rows]
        self._update_sort_headers(table)
        for process, prefix in rows:
            table.add_row(
                str(process.pid),
                process.user,
                f"{process.cpu_percent:.1f}",
                f"{process.memory_percent:.1f}",
                self._format_resident(process.resident_bytes),
                process.state,
                self._format_cpu_time(process.cpu_time_seconds),
                f"{prefix}{process.command}",
                key=str(process.pid),
            )
        if self._visible_processes:
            target = next(
                (
                    index
                    for index, process in enumerate(self._visible_processes)
                    if process.pid == selected_pid
                ),
                0,
            )
            table.move_cursor(row=target, animate=False)

    def _update_sort_headers(self, table: DataTable) -> None:
        for key, label in (
            ("pid", "PID"),
            ("cpu", "CPU%"),
            ("mem", "MEM%"),
            ("command", "COMMAND"),
        ):
            active = _SORT_COLUMNS[self.sort_by] == key
            table.columns[key].label = Text(
                label,
                style="bold #101719 on #67e8a5" if active else "bold #b5c4c1",
            )

    @staticmethod
    def _format_resident(value: int) -> str:
        amount = float(value)
        for unit in ("B", "K", "M", "G", "T"):
            if amount < 1024 or unit == "T":
                return f"{amount:.1f}{unit}"
            amount /= 1024
        return f"{amount:.1f}T"

    @staticmethod
    def _format_cpu_time(seconds: float) -> str:
        total = max(0, int(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _set_sort(self, key: str) -> None:
        self.sort_by = key
        self._render_processes()
        self.query_one("#message", Static).update(
            f"SORT: {key.upper()}    "
            f"VIEW: {'TREE' if self.tree_view else 'FLAT'}    "
            f"PROCESSES: {len(self._snapshot.processes) if self._snapshot else 0}"
        )

    def action_sort_cpu(self) -> None:
        self._set_sort("cpu")

    def action_sort_mem(self) -> None:
        self._set_sort("mem")

    def action_sort_pid(self) -> None:
        self._set_sort("pid")

    def action_sort_name(self) -> None:
        self._set_sort("name")

    def action_focus_search(self) -> None:
        search = self.query_one("#search", Input)
        search.remove_class("hidden")
        search.focus()

    @on(Input.Submitted, "#search")
    def close_search(self) -> None:
        self.query_one("#search", Input).add_class("hidden")
        self.query_one("#process-table", DataTable).focus()

    @on(Input.Changed, "#search")
    def filter_search(self) -> None:
        self._render_processes()

    def action_clear_search(self) -> None:
        search = self.query_one("#search", Input)
        search.value = ""
        search.add_class("hidden")
        self.query_one("#process-table", DataTable).focus()

    def action_toggle_tree(self) -> None:
        self.tree_view = not self.tree_view
        self._render_processes()
        mode = "TREE" if self.tree_view else "FLAT"
        self.query_one("#message", Static).update(f"Process view: {mode}")

    async def action_kill_selected(self) -> None:
        table = self.query_one("#process-table", DataTable)
        if not self._visible_processes or table.row_count == 0:
            self.query_one("#message", Static).update("No process selected")
            return
        index = min(table.cursor_row, len(self._visible_processes) - 1)
        process = self._visible_processes[index]
        await self.push_screen(
            KillDialog(process.pid, self.collector), self._on_kill_result
        )

    def _on_kill_result(self, result: tuple[int, int] | None) -> None:
        if result is None:
            return
        pid, signal_number = result
        signal_name = signal.Signals(signal_number).name
        self.query_one("#message", Static).update(
            f"Sent {signal_name} to process {pid}"
        )
