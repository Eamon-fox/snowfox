"""Check that the packaged Windows Qt extension can load its native DLLs."""

import ctypes
import os
import sys
from pathlib import Path


def main() -> int:
    if os.name != "nt":
        raise SystemExit("Windows bundle verification must run on Windows")

    bundle = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/SnowFox")
    internal = bundle / "_internal"
    extension = internal / "PySide6" / "QtCore.pyd"
    if not extension.is_file():
        raise SystemExit(f"Missing packaged Qt extension: {extension}")

    directories = [internal, internal / "PySide6", internal / "shiboken6"]
    handles = [os.add_dll_directory(str(path.resolve())) for path in directories]
    try:
        ctypes.WinDLL(str(extension.resolve()))
    finally:
        for handle in handles:
            handle.close()

    print(f"Packaged QtCore loads: {extension}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
