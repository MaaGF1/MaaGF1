# mk/install.py
import shutil
import sys
import json
from pathlib import Path

# Import common and configure
sys.path.append(str(Path(__file__).parent))
from common import (
    PROJECT_ROOT, DIST_DIR, DEPS_BIN_DIR, ASSETS_DIR, 
    AGENT_DIR, TOOLS_DIR, DOCS_FILES
)
from configure import configure_ocr_model

def get_version():
    return sys.argv[1] if len(sys.argv) > 1 else "v0.0.1"

def clean_install_dir():
    if DIST_DIR.exists():
        print(f"Cleaning previous installation at {DIST_DIR}...")
        shutil.rmtree(DIST_DIR)

def install_deps():
    """
    Copy MFAAvalonia binary files (v1.8+ structure)
    """
    if not DEPS_BIN_DIR.exists() or not any(DEPS_BIN_DIR.iterdir()):
        print(f"Error: Dependencies not found in {DEPS_BIN_DIR}")
        sys.exit(1)

    print(f"Copying binaries from {DEPS_BIN_DIR} to {DIST_DIR}...")
    shutil.copytree(
        DEPS_BIN_DIR,
        DIST_DIR,
        ignore=shutil.ignore_patterns("*.pdb", "*.xml", "MFAUpdater*", "*.zip"),
        dirs_exist_ok=True
    )

def install_resources(version: str):
    print("Installing resources...")
    
    # 1. Configure OCR
    configure_ocr_model()

    # 2. Copy resource folders
    for folder in ["resource", "resource_en"]:
        src = ASSETS_DIR / folder
        dst = DIST_DIR / folder
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)

    # 3. Handle interface.json
    src_interface = ASSETS_DIR / "interface.json"
    dst_interface = DIST_DIR / "interface.json"
    
    if src_interface.exists():
        shutil.copy2(src_interface, DIST_DIR)
        try:
            with open(dst_interface, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            data["version"] = version
            
            with open(dst_interface, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Updated version to {version} in interface.json")
        except Exception as e:
            print(f"Warning: Failed to update version in interface.json: {e}")

def install_python_scripts():
    """Install agent and tools"""
    # Agent
    if AGENT_DIR.exists():
        print(f"Installing agent: {AGENT_DIR}")
        shutil.copytree(
            AGENT_DIR, 
            DIST_DIR / "agent", 
            ignore=shutil.ignore_patterns("__pycache__"), 
            dirs_exist_ok=True
        )
    
    # Tools
    if TOOLS_DIR.exists():
        print(f"Installing tools: {TOOLS_DIR}")
        shutil.copytree(TOOLS_DIR, DIST_DIR / "tools", dirs_exist_ok=True)

def install_docs():
    for file_name in DOCS_FILES:
        src = PROJECT_ROOT / file_name
        if src.exists():
            shutil.copy2(src, DIST_DIR)

if __name__ == "__main__":
    ver = get_version()
    print(f"Starting installation for version: {ver}")
    print(f"Project Root: {PROJECT_ROOT}")
    
    clean_install_dir()
    install_deps()
    install_resources(ver)
    install_python_scripts()
    install_docs()
    
    print(f"[OK] Installation completed successfully at: {DIST_DIR}")