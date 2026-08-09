from __future__ import annotations

import os
import sys


class PlatformMetricError(RuntimeError):
    """Raised when a required host metric cannot be measured safely."""


def _windows_peak_working_set_bytes() -> int:
    import ctypes
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    process = kernel32.GetCurrentProcess()
    if not psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
        error = ctypes.get_last_error()
        raise PlatformMetricError(f"WINDOWS_GET_PROCESS_MEMORY_INFO_FAILED:{error}")
    return int(counters.PeakWorkingSetSize)


def _windows_total_physical_memory_bytes() -> int:
    import ctypes
    from ctypes import wintypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
    kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        error = ctypes.get_last_error()
        raise PlatformMetricError(f"WINDOWS_GLOBAL_MEMORY_STATUS_FAILED:{error}")
    return int(status.ullTotalPhys)


def peak_rss_bytes() -> int:
    """Return peak resident/working-set bytes without making ``resource`` an import-time dependency."""
    if sys.platform == "win32":
        return _windows_peak_working_set_bytes()

    try:
        import resource
    except ModuleNotFoundError as exc:  # pragma: no cover - platform-specific fail-closed path
        raise PlatformMetricError("PEAK_RSS_UNAVAILABLE_ON_PLATFORM") from exc

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux and other common Unix variants report KiB; macOS reports bytes.
    return int(value if sys.platform == "darwin" else value * 1024)


def memory_total_bytes() -> int:
    """Return physical memory bytes on Windows or POSIX, failing closed when unavailable."""
    if sys.platform == "win32":
        return _windows_total_physical_memory_bytes()

    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, ValueError, OSError) as exc:  # pragma: no cover - uncommon host path
        raise PlatformMetricError("TOTAL_PHYSICAL_MEMORY_UNAVAILABLE_ON_PLATFORM") from exc
    return int(pages * page_size)
