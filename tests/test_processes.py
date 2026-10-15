from hwrdtop.models.processes import filter_processes, sort_processes, tree_processes
from hwrdtop.models.system import ProcessInfo


def process(
    pid: int,
    command: str,
    cpu: float = 0.0,
    memory: float = 0.0,
    ppid: int = 1,
) -> ProcessInfo:
    return ProcessInfo(
        pid=pid,
        ppid=ppid,
        user="test",
        cpu_percent=cpu,
        memory_percent=memory,
        resident_bytes=1024,
        state="sleeping",
        cpu_time_seconds=1.0,
        command=command,
    )


def test_sort_cpu_and_memory_descending_with_pid_tie_breaker() -> None:
    processes = [process(9, "zeta", 30, 4), process(4, "alpha", 30, 8)]

    assert [item.pid for item in sort_processes(processes, "cpu")] == [4, 9]
    assert [item.pid for item in sort_processes(processes, "mem")] == [4, 9]


def test_sort_pid_and_name_ascending() -> None:
    processes = [process(9, "zeta"), process(4, "Alpha")]

    assert [item.pid for item in sort_processes(processes, "pid")] == [4, 9]
    assert [item.pid for item in sort_processes(processes, "name")] == [4, 9]


def test_filter_is_case_insensitive_and_matches_command_name() -> None:
    processes = [process(2, "Python worker"), process(3, "nginx")]

    assert [item.pid for item in filter_processes(processes, " PYTHON ")] == [2]
    assert len(filter_processes(processes, " ")) == 2


def test_tree_orders_children_after_their_parent() -> None:
    parent = process(10, "parent", ppid=1)
    child = process(11, "child", ppid=10)

    rows = tree_processes([child, parent])

    assert [item.pid for item, _prefix in rows] == [10, 11]
    assert rows[0][1] == ""
    assert rows[1][1].strip().endswith("─")
