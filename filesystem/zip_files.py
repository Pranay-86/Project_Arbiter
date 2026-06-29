import zipfile
import shutil
from pathlib import Path
from tools.tool_base import Tool
from core.logger import get_logger

logger = get_logger("zip_files")


class ZipFilesTool(Tool):

    name = "zip_files"
    description = (
        "Create a zip archive from files/folders, or extract an existing zip. "
        "Set action to 'zip' to compress, 'unzip' to extract."
    )
    parameters = {
        "action":      "string — zip | unzip",
        "source":      "string — file/folder to zip, or .zip file to extract",
        "destination": "string — output zip path (for zip) or extract folder (for unzip)"
    }

    def execute(self, action: str, source: str, destination: str = "") -> dict:
        action = action.strip().lower()
        src    = Path(source).expanduser().resolve()

        if not src.exists():
            return {"error": f"Source not found: '{source}'"}

        if action == "zip":
            dest = Path(destination).expanduser() if destination else src.with_suffix(".zip")
            try:
                if src.is_dir():
                    shutil.make_archive(str(dest.with_suffix("")), "zip", str(src))
                else:
                    with zipfile.ZipFile(str(dest), "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.write(str(src), src.name)
                logger.info("zip_files: zipped %s → %s", src, dest)
                return {"status": "zipped", "archive": str(dest)}
            except Exception as exc:
                return {"error": str(exc)}

        elif action == "unzip":
            dest = Path(destination).expanduser() if destination else src.parent / src.stem
            try:
                dest.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(str(src), "r") as zf:
                    zf.extractall(str(dest))
                logger.info("zip_files: extracted %s → %s", src, dest)
                return {"status": "extracted", "destination": str(dest)}
            except Exception as exc:
                return {"error": str(exc)}

        return {"error": f"Unknown action '{action}'. Use 'zip' or 'unzip'."}
