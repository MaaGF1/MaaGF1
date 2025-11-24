import shutil
import sys
import json
import os
from pathlib import Path

try:
    from configure import configure_ocr_model
except ImportError:
    def configure_ocr_model():
        print("Warning: configure.py not found, skipping OCR configuration.")

# Define paths
working_dir = Path(__file__).parent
install_path = working_dir / "install"
deps_path = working_dir / "deps" / "bin"
version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"

def clean_install_dir():
    """Remove existing install directory to ensure a clean build."""
    if install_path.exists():
        print(f"Cleaning previous installation at {install_path}...")
        shutil.rmtree(install_path)

def install_deps():
    """
    Copy MFAAvalonia binaries.
    v1.8+ Structure:
    - Root: MFAAvalonia.exe, MaaAgentBinary/
    - Runtimes: runtimes/win-x64/native/
    
    We copy the entire structure to preserve .NET dependencies.
    """
    if not deps_path.exists() or not any(deps_path.iterdir()):
        print(f"Error: Dependencies not found in {deps_path}")
        print("Please ensure MFAAvalonia is downloaded and extracted correctly.")
        sys.exit(1)

    print(f"Copying base binaries from {deps_path} to {install_path}...")
    
    # Copy tree, filtering out debug symbols and unnecessary files
    shutil.copytree(
        deps_path,
        install_path,
        ignore=shutil.ignore_patterns("*.pdb", "*.xml", "MFAUpdater*"),
        dirs_exist_ok=True
    )

def install_resources():
    """Install assets and configure interface.json."""
    print("Installing resources...")
    
    # Run configuration logic
    configure_ocr_model()

    # Copy resource folders
    for folder in ["resource", "resource_en"]:
        src = working_dir / "assets" / folder
        dst = install_path / folder
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)

    # Handle interface.json
    src_interface = working_dir / "assets" / "interface.json"
    dst_interface = install_path / "interface.json"
    
    if src_interface.exists():
        shutil.copy2(src_interface, install_path)
        
        # Inject version into interface.json
        try:
            with open(dst_interface, "r", encoding="utf-8") as f:
                interface = json.load(f)
            
            interface["version"] = version
            
            with open(dst_interface, "w", encoding="utf-8") as f:
                json.dump(interface, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Warning: Failed to update version in interface.json: {e}")

def install_agent():
    """Install Python agent scripts."""
    src_agent = working_dir / "agent"
    dst_agent = install_path / "agent"

    if src_agent.exists():
        print(f"Installing agent scripts: {src_agent} -> {dst_agent}")
        # Copy agent folder, excluding python cache
        shutil.copytree(
            src_agent, 
            dst_agent, 
            ignore=shutil.ignore_patterns("__pycache__"), 
            dirs_exist_ok=True
        )
    else:
        print("Warning: 'agent' directory not found.")

def install_tools():
    """Install utility tools."""
    src_tools = working_dir / "tools"
    dst_tools = install_path / "tools"

    if src_tools.exists():
        print(f"Installing tools: {src_tools} -> {dst_tools}")
        shutil.copytree(src_tools, dst_tools, dirs_exist_ok=True)

def install_docs():
    """Copy documentation files."""
    for file in ["README.md", "LICENSE", "CHANGES.md"]:
        src = working_dir / file
        if src.exists():
            shutil.copy2(src, install_path)

if __name__ == "__main__":
    print(f"Starting installation for version: {version}")
    
    clean_install_dir()
    install_deps()
    install_resources()
    install_agent()
    install_tools()
    install_docs()
    
    print(f"Installation completed successfully at: {install_path}")