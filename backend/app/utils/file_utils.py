"""File handling, hashing, and temporary workspace utilities."""
import hashlib
import os
import zipfile
from typing import List, Tuple


def compute_sha256(content: str) -> str:
    """Compute standard SHA-256 hash for raw code string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_signature(line: int, column: int, rule_id: str, message: str) -> str:
    """Compute unique deterministic signature for a bug finding to enable caching/deduplication."""
    raw = f"{line}:{column}:{rule_id}:{message.strip().lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


from app.services.language_detector import LanguageDetector

def extract_zip_to_dir(zip_bytes: bytes, target_dir: str) -> List[Tuple[str, str]]:
    """Extract a ZIP archive in memory to a directory and return (relative_path, content) pairs for supported files."""
    extracted_files: List[Tuple[str, str]] = []
    zip_path = os.path.join(target_dir, "upload.zip")
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.namelist():
            # Prevent zip slip vulnerability
            resolved_path = os.path.abspath(os.path.join(target_dir, member))
            if not resolved_path.startswith(os.path.abspath(target_dir)):
                continue

            if LanguageDetector.is_supported_file(member) and not member.startswith("__MACOSX"):
                zip_ref.extract(member, target_dir)
                file_path = os.path.join(target_dir, member)
                if os.path.isfile(file_path):
                    with open(file_path, "r", encoding="utf-8", errors="replace") as pf:
                        extracted_files.append((member, pf.read()))

    return extracted_files
