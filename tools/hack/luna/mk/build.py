import sys
import os
import shutil
import PyInstaller.__main__
from pathlib import Path

CURRENT_DIR = Path(__file__).parent.resolve()
AGENT_ROOT = CURRENT_DIR.parent
SPEC_FILE = CURRENT_DIR / "build.spec"
DIST_DIR = AGENT_ROOT / "dist"
WORK_DIR = AGENT_ROOT / "build"

def clean_build_artifacts():
    """Clean previous build artifacts"""
    print(f"Cleaning build artifacts in {AGENT_ROOT}...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)

def build_agent():
    """Run PyInstaller"""
    print("Starting PyInstaller build...")
    
    if not SPEC_FILE.exists():
        print(f"Error: Spec file not found at {SPEC_FILE}")
        sys.exit(1)

    original_cwd = os.getcwd()
    os.chdir(CURRENT_DIR)
    print(f"Changed working directory to: {os.getcwd()}")

    args = [
        str(SPEC_FILE),
        '--distpath', str(DIST_DIR),
        '--workpath', str(WORK_DIR),
        '--noconfirm',
        '--clean'
    ]
    
    try:
        PyInstaller.__main__.run(args)
        print(f"Build successful. Artifacts in: {DIST_DIR}")
    except Exception as e:
        print(f"PyInstaller failed: {e}")
        sys.exit(1)
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    clean_build_artifacts()
    build_agent()