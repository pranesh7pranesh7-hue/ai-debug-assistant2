"""Code Uploader Module: Handles raw text, single .py files, and .zip archives."""
import os
import tempfile
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.code_submission import CodeSubmission
from app.modules.code_upload.validators import (
    normalize_code,
    validate_file_extension,
    validate_file_size,
    validate_code_syntax,
)
from app.utils.file_utils import compute_sha256, extract_zip_to_dir


class CodeUploader:
    """Manages ingestion and persistence of submitted Python and multi-language code."""

    @staticmethod
    def process_raw_code(
        db: Session,
        user_id: int,
        raw_code: str,
        filename: str = "script.py",
        language: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> CodeSubmission:
        """Validate and store raw code string with explicit or auto-detected language."""
        from app.services.language_detector import LanguageDetector

        # Resolve language: prioritize explicit language if provided, else fallback to detection
        resolved_lang = None
        if language and language.strip().lower() not in ("auto", "unknown", ""):
            cleaned_lang = language.strip().lower()
            resolved_lang = LanguageDetector.NORMALIZED_NAMES.get(cleaned_lang, language.strip())

        if not resolved_lang:
            resolved_lang = LanguageDetector.detect_language(filename=filename, code=raw_code)
            if resolved_lang == "Unknown":
                resolved_lang = "Python"

        raw_code = normalize_code(raw_code, filename=filename, language=resolved_lang)
        validate_file_size(len(raw_code.encode("utf-8")))
        validate_file_extension(filename)
        validate_code_syntax(raw_code, filename=filename, language=resolved_lang)

        source_hash = compute_sha256(raw_code)

        # Check for existing submission with same hash by same user
        existing = (
            db.query(CodeSubmission)
            .filter(
                CodeSubmission.user_id == user_id,
                CodeSubmission.source_hash == source_hash,
                CodeSubmission.filename == filename,
            )
            .first()
        )
        if existing:
            if existing.language != resolved_lang:
                existing.language = resolved_lang
                db.commit()
                db.refresh(existing)
            return existing

        submission = CodeSubmission(
            user_id=user_id,
            project_id=project_id,
            filename=filename,
            language=resolved_lang,
            source_hash=source_hash,
            raw_code=raw_code,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission

    @staticmethod
    def process_file_upload(
        db: Session,
        user_id: int,
        filename: str,
        file_bytes: bytes,
        language: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> List[CodeSubmission]:
        """Process an uploaded single source file or .zip file."""
        validate_file_size(len(file_bytes))
        validate_file_extension(filename)

        submissions: List[CodeSubmission] = []

        from app.services.language_detector import LanguageDetector

        if LanguageDetector.is_supported_file(filename):
            try:
                code_str = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raise ValidationError("Uploaded file must be UTF-8 encoded source code.")
            sub = CodeUploader.process_raw_code(
                db=db,
                user_id=user_id,
                raw_code=code_str,
                filename=filename,
                language=language,
                project_id=project_id,
            )
            submissions.append(sub)

        elif filename.lower().endswith(".zip"):
            with tempfile.TemporaryDirectory() as tmpdir:
                extracted = extract_zip_to_dir(file_bytes, tmpdir)
                if not extracted:
                    raise ValidationError("The uploaded ZIP archive contains no supported code files.")

                for rel_path, code_str in extracted:
                    try:
                        sub = CodeUploader.process_raw_code(
                            db=db,
                            user_id=user_id,
                            raw_code=code_str,
                            filename=rel_path,
                            language=language if (language and language.strip().lower() not in ("auto", "unknown", "")) else None,
                            project_id=project_id,
                        )
                        submissions.append(sub)
                    except Exception:
                        # If a file has syntax errors or validation issues, still store it for analysis
                        source_hash = compute_sha256(code_str)
                        det_lang = LanguageDetector.detect_language(filename=rel_path, code=code_str)
                        if det_lang == "Unknown":
                            det_lang = "Python"
                        sub = CodeSubmission(
                            user_id=user_id,
                            project_id=project_id,
                            filename=rel_path,
                            language=det_lang,
                            source_hash=source_hash,
                            raw_code=code_str,
                        )
                        db.add(sub)
                        db.commit()
                        db.refresh(sub)
                        submissions.append(sub)

        return submissions
