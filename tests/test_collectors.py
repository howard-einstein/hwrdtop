from types import SimpleNamespace

import pytest

from hwrdtop.collectors.linux import LinuxCollector


class FakeProcess:
    def __init__(self, info: dict[str, object], cpu: float, memory: float) -> None:
        self.info = info
        self.pid = int(info["pid"])
        self._cpu = cpu
        self._memory = memory

    def cpu_percent(self, interval: float | None = None) -> float:
        return self._cpu

    def memory_percent(self) -> float:
        return self._memory


def test_linux_collector_builds_snapshot_and_counts_process_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hwrdtop.collectors.linux as linux

    process = FakeProcess(
        {
            "pid": 10,
            "ppid": 1,
            "username": "alice",
            "status": "running",
            "memory_info": SimpleNamespace(rss=4096),
            "cpu_times": SimpleNamespace(user=2.0, system=1.0),
            "name": "worker",
        },
        cpu=12.5,
        memory=3.25,
    )
    monkeypatch.setattr(
        linux.psutil,
        "cpu_percent",
        lambda **kwargs: [42.0, 18.0] if kwargs.get("percpu") else 42.0,
    )
    monkeypatch.setattr(
        linux.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(total=1000, used=400, percent=40.0),
    )
    monkeypatch.setattr(
        linux.psutil,
        "swap_memory",
        lambda: SimpleNamespace(total=500, used=100, percent=20.0),
    )
    monkeypatch.setattr(linux.psutil, "process_iter", lambda **_kwargs: [process])
    monkeypatch.setattr(linux.psutil, "pids", lambda: [1, 10])
    monkeypatch.setattr(linux.psutil, "boot_time", lambda: 100.0)
    monkeypatch.setattr(linux.os, "getloadavg", lambda: (1.0, 0.5, 0.25))
    monkeypatch.setattr(linux.time, "time", lambda: 160.0)

    snapshot = LinuxCollector().collect()

    assert snapshot.cpu_percent == 42.0
    assert snapshot.per_core_cpu_percent == (42.0, 18.0)
    assert snapshot.memory.used_bytes == 400
    assert snapshot.swap.percent == 20.0
    assert snapshot.load_average == (1.0, 0.5, 0.25)
    assert snapshot.uptime_seconds == 60.0
    assert snapshot.tasks.total == 2
    assert snapshot.tasks.running == 1
    assert snapshot.processes[0].cpu_time_seconds == 3.0
    assert snapshot.processes[0].resident_bytes == 4096


def test_linux_collector_skips_processes_that_disappear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import psutil
    import hwrdtop.collectors.linux as linux

    class VanishingProcess:
        pid = 99
        info: dict[str, object] = {"pid": 99}

        def cpu_percent(self, interval: float | None = None) -> float:
            raise psutil.NoSuchProcess(99)

    monkeypatch.setattr(
        linux.psutil,
        "cpu_percent",
        lambda **kwargs: [0.0] if kwargs.get("percpu") else 0.0,
    )
    monkeypatch.setattr(
        linux.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(total=100, used=10, percent=10.0),
    )
    monkeypatch.setattr(
        linux.psutil,
        "swap_memory",
        lambda: SimpleNamespace(total=0, used=0, percent=0.0),
    )
    monkeypatch.setattr(
        linux.psutil, "process_iter", lambda **_kwargs: [VanishingProcess()]
    )
    monkeypatch.setattr(linux.psutil, "pids", lambda: [1])
    monkeypatch.setattr(linux.psutil, "boot_time", lambda: 100.0)
    monkeypatch.setattr(linux.os, "getloadavg", lambda: (0.0, 0.0, 0.0))
    monkeypatch.setattr(linux.time, "time", lambda: 160.0)

    snapshot = LinuxCollector().collect()

    assert snapshot.processes == ()
