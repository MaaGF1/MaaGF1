# mk/check.py
import sys
from typing import List
from pathlib import Path

# Import MaaFw
try:
    from maa.resource import Resource
    from maa.tasker import Tasker, LoggingLevelEnum
except ImportError:
    print("Error: maafw not installed. Please run 'pip install maafw'")
    sys.exit(1)

# Import common
sys.path.append(str(Path(__file__).parent))
from common import PROJECT_ROOT

def check(dirs: List[Path]) -> bool:
    resource = Resource()
    print(f"Checking {len(dirs)} directories...")

    for dir_path in dirs:
        print(f"Checking bundle: {dir_path} ...")
        # MaaFw requires absolute path or path relative to CWD
        try:
            status = resource.post_bundle(dir_path).wait().status
            if not status.succeeded:
                print(f"[FAIL] Failed to load bundle: {dir_path}")
                return False
            print(f"[OK] Success: {dir_path}")
        except Exception as e:
            print(f"[ERROR] Exception checking {dir_path}: {e}")
            return False

    print("All directories checked.")
    return True

def main():
    # If no arguments, check assets/resource by default
    if len(sys.argv) < 2:
        target_dirs = [PROJECT_ROOT / "assets" / "resource"]
    else:
        target_dirs = [Path(arg) for arg in sys.argv[1:]]

    Tasker.set_stdout_level(LoggingLevelEnum.All)

    if not check(target_dirs):
        sys.exit(1)

if __name__ == "__main__":
    main()