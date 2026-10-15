"""Modal dialogs used for process control."""

from __future__ import annotations

import asyncio
import signal

import psutil
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static

from hwrdtop.collectors.base import SystemCollector


class KillDialog(ModalScreen[tuple[int, int] | None]):
    """Confirm signaling a selected process and choose the signal."""

    DEFAULT_CSS = """
    KillDialog {
        align: center middle;
        background: $background 80%;
    }
    #kill-dialog {
        width: 56;
        height: auto;
        padding: 1 2;
        border: round #67e8e5;
        background: #182126;
    }
    #kill-dialog Label {
        margin-bottom: 1;
    }
    #kill-error {
        color: #ff6b6b;
        height: auto;
        margin-top: 1;
    }
    #kill-actions {
        height: 3;
        margin-top: 1;
        align-horizontal: right;
    }
    #kill-actions Button {
        margin-left: 1;
    }
    """

    def __init__(self, pid: int, collector: SystemCollector) -> None:
        super().__init__()
        self.pid = pid
        self.collector = collector

    def compose(self) -> ComposeResult:
        with Vertical(id="kill-dialog"):
            yield Label(f"Send a signal to process {self.pid}?")
            yield Select(
                [
                    ("SIGTERM  ·  graceful", signal.SIGTERM),
                    ("SIGINT  ·  interrupt", signal.SIGINT),
                    ("SIGKILL  ·  force", signal.SIGKILL),
                ],
                value=signal.SIGTERM,
                allow_blank=False,
                id="signal-choice",
            )
            yield Static("", id="kill-error")
            with Horizontal(id="kill-actions"):
                yield Button("Cancel", id="kill-cancel")
                yield Button("Send signal", variant="error", id="kill-confirm")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "kill-cancel":
            self.dismiss(None)
        elif event.button.id == "kill-confirm":
            choice = self.query_one("#signal-choice", Select).value
            try:
                await asyncio.to_thread(
                    self.collector.signal_process, self.pid, int(choice)
                )
            except (psutil.Error, ProcessLookupError, PermissionError, OSError) as error:
                self.query_one("#kill-error", Static).update(str(error))
                return
            self.dismiss((self.pid, int(choice)))
