"""Collector interface shared by operating-system implementations."""

from __future__ import annotations

from typing import Protocol

from hwrdtop.models.system import SystemSnapshot


class SystemCollector(Protocol):
    """System and process data access used by the application."""

    def collect(self) -> SystemSnapshot:
        """Collect one current system snapshot."""
        ...

    def signal_process(self, pid: int, signal_number: int) -> None:
        """Send a signal to a process."""
        ...
