import asyncio

from hwrdtop.app import HWRDTopApp
from hwrdtop.models.system import (
    MemoryStats,
    ProcessInfo,
    SystemSnapshot,
    TaskCounts,
)
from hwrdtop.ui.dialogs import KillDialog


class FakeCollector:
    def collect(self) -> SystemSnapshot:
        processes = (
            ProcessInfo(10, 1, "alice", 8.0, 2.0, 2048, "running", 3.0, "python"),
            ProcessInfo(11, 10, "alice", 2.0, 4.0, 4096, "sleeping", 1.0, "worker"),
            ProcessInfo(12, 1, "root", 1.0, 1.0, 1024, "sleeping", 0.5, "nginx"),
        )
        memory = MemoryStats(10000, 5000, 50.0)
        return SystemSnapshot(
            cpu_percent=20.0,
            per_core_cpu_percent=(20.0, 30.0),
            memory=memory,
            swap=MemoryStats(1000, 100, 10.0),
            load_average=(0.5, 0.4, 0.3),
            uptime_seconds=3600.0,
            tasks=TaskCounts(3, 1, 2),
            processes=processes,
        )

    def signal_process(self, pid: int, signal_number: int) -> None:
        return None


def test_textual_app_mounts_and_process_controls_work() -> None:
    async def exercise() -> None:
        app = HWRDTopApp(refresh_rate=60.0, collector=FakeCollector())
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause(0.1)
            table = app.query_one("#process-table")
            assert table.row_count == 3

            await pilot.press("m")
            assert app.sort_by == "mem"

            await pilot.press("/")
            search = app.query_one("#search")
            search.value = "PYTHON"
            await pilot.pause(0.1)
            assert [process.pid for process in app._visible_processes] == [10]

            await pilot.press("escape")
            assert app.query_one("#search").value == ""

            await pilot.press("t")
            assert app.tree_view
            assert [process.pid for process in app._visible_processes] == [10, 11, 12]

            await pilot.press("k")
            await pilot.pause(0.1)
            assert isinstance(app.screen, KillDialog)
            await pilot.click("#kill-cancel")
            await pilot.pause(0.1)
            assert not isinstance(app.screen, KillDialog)

    asyncio.run(exercise())
