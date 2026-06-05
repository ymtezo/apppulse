import platform
import socket


def get_device_id():
    return socket.gethostname()


def get_platform_info():
    return {
        "device_id": get_device_id(),
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
    }
