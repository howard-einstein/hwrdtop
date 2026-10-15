# HWRDTOP

HWRDTOP is a live Linux system and process monitor for the terminal, built with
Textual and psutil. It displays CPU, memory, load, uptime, and a sortable,
filterable process list.

## Install and run

Python 3.11 or newer is required.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m hwrdtop
```

The editable install also provides the `hwrdtop` command. Set the refresh rate
in seconds with `--refresh-rate` (or `-r`):

```sh
hwrdtop --refresh-rate 0.5
```

The refresh rate is measured in seconds and defaults to `1.0`. Use `-h` to see
the available command-line options.

## How it works

At startup, `hwrdtop.__main__` parses the refresh-rate option and creates the
Textual application. The app schedules a refresh on that interval. Each refresh
runs the collector in a worker thread, so reading system and process
information does not block terminal input or drawing. When the snapshot is
ready, the UI updates the system panel and rebuilds the process table.

The Linux collector uses `psutil` for CPU, memory, swap, uptime, task, and
process data. Process entries that disappear or cannot be inspected are
skipped. CPU percentages can be zero for a process until psutil has a previous
sample to compare against. Process signaling also runs outside the UI thread;
the selected signal is sent only after confirmation.

The code is divided by responsibility:

| Path | Responsibility |
| --- | --- |
| `src/hwrdtop/app.py` | Textual app, refresh scheduling, table controls, and wiring |
| `src/hwrdtop/collectors/` | System collector interface and Linux `psutil` implementation |
| `src/hwrdtop/models/` | Snapshot data classes and process sorting, filtering, and tree helpers |
| `src/hwrdtop/ui/` | System metrics panel and process-signal dialog |
| `src/hwrdtop/__main__.py` | `python -m hwrdtop` and console-script entry point |
| `tests/` | Collector, process-helper, and Textual interaction tests |

The collector protocol keeps operating-system-specific data access separate
from the UI and models. Linux is the only implemented platform currently.

## Keys

| Key | Action |
| --- | --- |
| Up / Down | Move through processes |
| PgUp / PgDn | Move by a page |
| `c` / F1 | Sort by CPU usage |
| `m` / F2 | Sort by memory usage |
| `p` / F3 | Sort by PID |
| `n` / F4 | Sort by process name |
| `/` | Search process names |
| Enter | Close search and keep the filter |
| Escape | Clear and close search |
| `t` | Toggle process tree |
| `k` | Open the signal/kill confirmation |
| `q` | Quit |

The active sort column is highlighted. CPU and memory sorts are descending;
PID and name sorts are ascending. A newly observed process can show 0% CPU until
psutil has enough samples to calculate its usage. Processes that disappear or
cannot be inspected are skipped, and a process that cannot be signaled reports
the error in the UI.

## Configuration and scope

The refresh rate is currently configured with the CLI flag; the planned
`~/.config/hwrdtop/config.toml`, theme, process detail, and network/disk panels
are not part of this MVP. The collector interface isolates system data access;
this release implements the Linux collector. CPU bars show logical cores, and
task counts include processes whose state could be read.

## Tests

Install the development dependency and run the test suite with:

```sh
python -m pip install -e '.[dev]'
python -m pytest
```# hwrdtop
