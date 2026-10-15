"""Linux implementation of the system collector using psutil."""

from __future__ import annotations

import os
import time

import psutil

from hwrdtop.models.system import (
    MemoryStats,
    ProcessInfo,
    SystemSnapshot,
    TaskCounts,
)

_PROCESS_ATTRIBUTES = [
    "pid",
    "ppid",
    "username",
    "status",
    "memory_info",
    "cpu_times",
    "name",
]


class LinuxCollector:
    """Collect live Linux metrics and tolerate inaccessible processes."""

    def collect(self) -> SystemSnapshot:
        """Read system metrics and the process attributes available now."""
        cpu_percent = psutil.cpu_percent(interval=None)
        per_core_cpu = tuple(psutil.cpu_percent(interval=None, percpu=True))
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        processes: list[ProcessInfo] = []
        running = 0
        sleeping = 0

        for process in psutil.process_iter(attrs=_PROCESS_ATTRIBUTES, ad_value=None):
            try:
                info = process.info
                status = info.get("status") or "?"
                if status == psutil.STATUS_RUNNING:
                    running += 1
                elif status in (psutil.STATUS_SLEEPING, psutil.STATUS_DISK_SLEEP):
                    sleeping += 1

                memory_info = info.get("memory_info")
                cpu_times = info.get("cpu_times")
                cpu_seconds = (
                    float(cpu_times.user + cpu_times.system) if cpu_times else 0.0
                )
                cpu_usage = process.cpu_percent(interval=None)
                processes.append(
                    ProcessInfo(
                        pid=int(info.get("pid") or process.pid),
                        ppid=int(info.get("ppid") or 0),
                        user=str(info.get("username") or "?"),
                        cpu_percent=max(0.0, float(cpu_usage)),
                        memory_percent=max(0.0, float(process.memory_percent())),
                        resident_bytes=int(memory_info.rss) if memory_info else 0,
                        state=str(status),
                        cpu_time_seconds=cpu_seconds,
                        command=str(info.get("name") or "?"),
                    )
                )
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                continue

        load_average = os.getloadavg()
        uptime_seconds = max(0.0, time.time() - psutil.boot_time())
        return SystemSnapshot(
            cpu_percent=max(0.0, float(cpu_percent)),
            per_core_cpu_percent=per_core_cpu,
            memory=MemoryStats(
                total_bytes=int(memory.total),
                used_bytes=int(memory.used),
                percent=float(memory.percent),
            ),
            swap=MemoryStats(
                total_bytes=int(swap.total),
                used_bytes=int(swap.used),
                percent=float(swap.percent),
            ),
            load_average=tuple(float(value) for value in load_average),
            uptime_seconds=uptime_seconds,
            tasks=TaskCounts(
                total=len(psutil.pids()), running=running, sleeping=sleeping
            ),
            processes=tuple(processes),
        )

    def signal_process(self, pid: int, signal_number: int) -> None:
        """Send a signal to a process, leaving permission errors to the caller."""
        psutil.Process(pid).send_signal(signal_number)


def supported_collector() -> LinuxCollector:
    """Return the platform collector or explain the current platform limit."""
    import sys

    if not sys.platform.startswith("linux"):
        raise RuntimeError("HWRDTOP currently supports Linux only")
    return LinuxCollector()
