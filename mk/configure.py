# mk/configure.py
import shutil
import sys
from pathlib import Path

# Try to import common, handle path if running this script directly
try:
    from common import ASSETS_DIR
except ImportError:
    # Fallback logic when running as standalone script
    sys.path.append(str(Path(__file__).parent))
    from common import ASSETS_DIR

def configure_ocr_model():
    assets_ocr_dir = ASSETS_DIR / "MaaCommonAssets" / "OCR"
    if not assets_ocr_dir.exists():
        print(f"Error: MaaCommonAssets OCR dir not found at: {assets_ocr_dir}")
        # Do not force exit here, let caller decide whether to ignore
        return False

    target_ocr_dir = ASSETS_DIR / "resource" / "model" / "ocr"
    
    # Only copy when target does not exist to avoid overwriting user customizations
    if not target_ocr_dir.exists():
        print(f"Copying default OCR model to {target_ocr_dir}...")
        try:
            shutil.copytree(
                assets_ocr_dir / "ppocr_v5" / "zh_cn",
                target_ocr_dir,
                dirs_exist_ok=True,
            )
            print("OCR model configured successfully.")
        except Exception as e:
            print(f"Failed to copy OCR model: {e}")
            return False
    else:
        print("Found existing OCR directory, skipping default import.")
    
    return True

if __name__ == "__main__":
    if not configure_ocr_model():
        sys.exit(1)