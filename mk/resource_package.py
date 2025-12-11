# mk/resource_package.py
import sys
import json
import shutil
import zipfile
import argparse
from pathlib import Path

# Import common configuration
sys.path.append(str(Path(__file__).parent))
from common import PROJECT_ROOT, ASSETS_DIR, DIST_DIR, RESOURCE_TARGETS

def parse_args():
    parser = argparse.ArgumentParser(description="MaaGFL Resource Packager")
    parser.add_argument("version", help="Version tag (e.g., v1.0.0)")
    return parser.parse_args()

def prepare_dist_dir():
    """Ensure the distribution directory exists."""
    if not DIST_DIR.exists():
        DIST_DIR.mkdir(parents=True, exist_ok=True)

def create_resource_package(version: str):
    """
    Create a zip file containing the specified resources.
    The interface.json will be updated with the provided version.
    """
    print(f"Starting resource packaging for version: {version}")
    
    # Define output zip name
    zip_name = f"MaaGF1-Resource-{version}.zip"
    zip_path = DIST_DIR / zip_name
    
    # Use a temporary directory structure for zipping to keep paths clean
    # We will write directly to the zip file to avoid temp dir cleanup issues
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for item_name in RESOURCE_TARGETS:
                src_path = ASSETS_DIR / item_name
                
                if not src_path.exists():
                    print(f"Warning: Source {item_name} not found in {ASSETS_DIR}, skipping.")
                    continue

                if item_name == "interface.json":
                    # Special handling for interface.json: Update version
                    print(f"Processing {item_name} with version injection...")
                    try:
                        with open(src_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        
                        # Update version
                        data["version"] = version
                        
                        # Convert back to JSON string
                        json_str = json.dumps(data, ensure_ascii=False, indent=4)
                        
                        # Write to zip
                        zf.writestr(item_name, json_str)
                    except Exception as e:
                        print(f"Error processing interface.json: {e}")
                        sys.exit(1)
                
                elif src_path.is_dir():
                    # Recursive copy for directories
                    print(f"Archiving directory: {item_name}")
                    for file in src_path.rglob("*"):
                        if file.is_file():
                            # Calculate arcname (path inside zip)
                            # e.g. assets/resource/img.png -> resource/img.png
                            arcname = file.relative_to(ASSETS_DIR)
                            zf.write(file, arcname)
                
                else:
                    # Regular file copy
                    print(f"Archiving file: {item_name}")
                    zf.write(src_path, item_name)
                    
        print(f"[OK] Resource package created successfully: {zip_path}")

    except Exception as e:
        print(f"Error creating zip package: {e}")
        sys.exit(1)

if __name__ == "__main__":
    args = parse_args()
    prepare_dist_dir()
    create_resource_package(args.version)