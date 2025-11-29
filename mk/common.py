# mk/common.py
import sys
from pathlib import Path

# Define mk directory and project root directory
# Assuming structure: root/mk/common.py
MK_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = MK_DIR.parent

# Define common paths
ASSETS_DIR = PROJECT_ROOT / "assets"
DEPS_BIN_DIR = PROJECT_ROOT / "deps" / "bin"
DIST_DIR = PROJECT_ROOT / "install"
TOOLS_DIR = PROJECT_ROOT / "tools"
AGENT_DIR = PROJECT_ROOT / "agent"
DOCS_FILES = ["README.md", "LICENSE", "CHANGES.md"]

def add_path():
    """
    Add mk directory to sys.path for cross-script imports
    """
    if str(MK_DIR) not in sys.path:
        sys.path.append(str(MK_DIR))