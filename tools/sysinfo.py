"""检测本机 CPU/内存/磁盘信息,用于评估训练资源。"""
import ctypes
import os
import platform
import shutil


def main():
    print('cpu_logical:', os.cpu_count())
    try:
        import psutil
        print('cpu_physical:', psutil.cpu_count(logical=False))
        print('cpu_freq_mhz:', psutil.cpu_freq().max if psutil.cpu_freq() else 'n/a')
        print('ram_total_gb: %.1f' % (psutil.virtual_memory().total / 2**30))
        print('ram_avail_gb: %.1f' % (psutil.virtual_memory().available / 2**30))
    except ImportError:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        m = MEMORYSTATUSEX()
        m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        print('ram_total_gb: %.1f' % (m.ullTotalPhys / 2**30))
        print('ram_avail_gb: %.1f' % (m.ullAvailPhys / 2**30))
    total, used, free = shutil.disk_usage(os.getcwd())
    print('disk_free_gb: %.1f' % (free / 2**30))
    print('platform:', platform.platform())


if __name__ == '__main__':
    main()
