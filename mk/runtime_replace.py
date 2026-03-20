# mk/runtime_replace.py
import json
import shutil
import argparse
import sys
import zipfile
import subprocess
from pathlib import Path

# Provide a root path reference
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

def parse_args():
    parser = argparse.ArgumentParser(description="MaaGFL Runtime Replacer (Luna Build)")
    parser.add_argument("--base", required=True, help="Path to the base GUI directory (unzipped)")
    parser.add_argument("--luna-pkg", required=True, help="Path to the Luna MaaFramework zip file")
    parser.add_argument("--output", required=True, help="Path to the output directory")
    return parser.parse_args()

def extract_and_replace_dlls(base_dir: Path, luna_zip: Path):
    """
    Extract DLLs from Luna zip (bin/) and replace them in the base directory (runtimes/win-x64/native/).
    """
    # Define the target directory structure for MFAAvalonia
    target_native_dir = base_dir / "runtimes" / "win-x64" / "native"
    
    if not target_native_dir.exists():
        print(f"Error: Target native directory not found: {target_native_dir}")
        sys.exit(1)

    print(f"Opening Luna package: {luna_zip}")
    try:
        with zipfile.ZipFile(luna_zip, 'r') as zf:
            # List all files in the zip
            for file_info in zf.infolist():
                # We only care about files inside "bin/"
                if file_info.filename.startswith("bin/") and not file_info.is_dir():
                    filename = Path(file_info.filename).name
                    
                    # Construct target path
                    target_path = target_native_dir / filename
                    
                    # Check if we should replace (optional: only replace if exists, or force replace)
                    # Here we force replace/copy all files from bin/ to native/
                    print(f"Replacing/Copying: {filename}")
                    
                    # Extract directly to target path
                    # ZipFile.extract extracts with full path, so we read and write bytes
                    with zf.open(file_info) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                        
    except Exception as e:
        print(f"Error during DLL replacement: {e}")
        sys.exit(1)

def update_interface_json(base_dir: Path):
    """
    Modify interface.json to update Win32 controller settings.
    """
    json_path = base_dir / "interface.json"
    if not json_path.exists():
        print(f"Error: interface.json not found at {json_path}")
        sys.exit(1)

    print(f"Updating interface.json at {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        found = False
        if "controller" in data and isinstance(data["controller"], list):
            for ctrl in data["controller"]:
                if ctrl.get("type") == "Win32" and "win32" in ctrl:
                    print("Found Win32 controller configuration. Updating mouse/keyboard to 4.")
                    ctrl["win32"]["mouse"] = 4
                    ctrl["win32"]["keyboard"] = 4
                    found = True
        
        if not found:
            print("Warning: No 'Win32' controller configuration found to update.")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        print(f"Error updating interface.json: {e}")
        sys.exit(1)

def build_and_copy_luna_gui(output_path: Path):
    """
    Builds the luna tool using PyInstaller and copies it to the target root.
    """
    luna_dir = PROJECT_ROOT / "tools" / "hack" / "luna"
    build_script = luna_dir / "mk" / "build.py"
    
    if not build_script.exists():
        print(f"Error: Luna build script not found at {build_script}")
        sys.exit(1)

    print("Building Luna GUI application...")
    try:
        subprocess.check_call([sys.executable, str(build_script)])
    except subprocess.CalledProcessError as e:
        print(f"Error building Luna GUI: {e}")
        sys.exit(1)
        
    luna_dist = luna_dir / "dist" / "luna"
    if not luna_dist.exists():
        print(f"Error: Luna build output not found at {luna_dist}")
        sys.exit(1)
        
    print(f"Copying Luna artifacts from {luna_dist} to {output_path}...")
    # Using dirs_exist_ok=True to merge _internal folder into root 
    # and place luna.exe directly next to MaaGFL GUI exe.
    shutil.copytree(luna_dist, output_path, dirs_exist_ok=True)
    print("Luna GUI integration complete.")

def main():
    args = parse_args()
    base_path = Path(args.base)
    luna_zip_path = Path(args.luna_pkg)
    output_path = Path(args.output)

    if not base_path.exists():
        print(f"Error: Base directory {base_path} does not exist.")
        sys.exit(1)

    if not luna_zip_path.exists():
        print(f"Error: Luna package {luna_zip_path} does not exist.")
        sys.exit(1)

    # 1. Create a copy of the base directory to the output directory
    if output_path.exists():
        shutil.rmtree(output_path)
    
    print(f"Cloning base artifact to {output_path}...")
    shutil.copytree(base_path, output_path)

    # 2. Perform DLL replacement
    extract_and_replace_dlls(output_path, luna_zip_path)

    # 3. Modify JSON
    update_interface_json(output_path)
    
    # 4. Compile and append Luna executable
    build_and_copy_luna_gui(output_path)

    print(f"[OK] Runtime replace completed. Output: {output_path}")

if __name__ == "__main__":
    main()