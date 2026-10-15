"""Platform-specific system data collectors."""

from hwrdtop.collectors.base import SystemCollector
from hwrdtop.collectors.linux import LinuxCollector

__all__ = ["LinuxCollector", "SystemCollector"]
