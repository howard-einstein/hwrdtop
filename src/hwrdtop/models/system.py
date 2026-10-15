"""Typed snapshots of system and process state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemoryStats:
    """Memory totals and utilization in bytes and percent."""

    total_bytes: int
    used_bytes: int
    percent: float


@dataclass(frozen=True, slots=True)
class TaskCounts:
    """Counts of observed processes by state."""

    total: int
    running: int
    sleeping: int


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    """The process attributes shown in the monitor."""

    pid: int
    ppid: int
    user: str
    cpu_percent: float
    memory_percent: float
    resident_bytes: int
    state: str
    cpu_time_seconds: float
    command: str


@dataclass(frozen=True, slots=True)
class SystemSnapshot:
    """One point-in-time view of system and process activity."""

    cpu_percent: float
    per_core_cpu_percent: tuple[float, ...]
    memory: MemoryStats
    swap: MemoryStats
    load_average: tuple[float, float, float]
    uptime_seconds: float
    tasks: TaskCounts
    processes: tuple[ProcessInfo, ...]
