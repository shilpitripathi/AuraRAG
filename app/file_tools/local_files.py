import os
import re
import shutil
from pathlib import Path

from app.rag.loader import load_document
from app.rag.chunker import split_text
from app.rag.vector_store import add_chunks


from functools import lru_cache


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@lru_cache(maxsize=1)
def get_allowed_directories() -> list[Path]:
    """
    Get the set of verified, resolved allowed user directories:
    - %USERPROFILE%\\Downloads
    - %USERPROFILE%\\Documents
    - %USERPROFILE%\\Desktop
    Includes OneDrive mapped locations if present on Windows.
    """
    user_home = Path(os.environ.get("USERPROFILE", Path.home())).resolve()

    candidates = [
        user_home / "Downloads",
        user_home / "Documents",
        user_home / "OneDrive" / "Documents",
        user_home / "Desktop",
        user_home / "OneDrive" / "Desktop",
    ]

    allowed = []
    for c in candidates:
        if c.exists() and c.is_dir():
            resolved = c.resolve()
            if resolved not in allowed:
                allowed.append(resolved)

    return allowed


def is_path_allowed(path: str | Path) -> bool:
    """
    Verify that a file path is strictly within approved user directories
    and does not perform directory traversal attacks.
    """
    try:
        target = Path(path).resolve()
    except Exception:
        return False

    allowed_dirs = get_allowed_directories()
    for allowed_dir in allowed_dirs:
        try:
            if target.is_relative_to(allowed_dir):
                return True
        except (ValueError, AttributeError):
            try:
                target.relative_to(allowed_dir)
                return True
            except ValueError:
                pass

    return False


def list_files(
    directory: str | None = None,
    extension: str | None = None
) -> list[dict]:
    """
    List files from approved user directories.
    Returns safe metadata: filename, extension, path, size.
    Never returns file contents.
    """
    allowed_dirs = get_allowed_directories()
    target_dirs = []

    if directory:
        dir_clean = directory.strip().lower()
        matched = False
        for ad in allowed_dirs:
            if dir_clean in ad.name.lower():
                target_dirs.append(ad)
                matched = True

        if not matched:
            # Check if explicit path was passed
            cand = Path(directory).resolve()
            if is_path_allowed(cand) and cand.is_dir():
                target_dirs.append(cand)
            else:
                raise PermissionError(f"Access denied: Directory '{directory}' is outside approved user folders.")
    else:
        target_dirs = allowed_dirs

    ext_filter = extension.lower().strip() if extension else None
    if ext_filter and not ext_filter.startswith("."):
        ext_filter = f".{ext_filter}"

    results = []
    seen_paths = set()
    skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "appdata", ".vscode", "temp", "tmp"}

    for d in target_dirs:
        d_path = str(d)
        if not os.path.exists(d_path) or not os.path.isdir(d_path):
            continue

        entries_to_check = []
        try:
            with os.scandir(d_path) as it:
                for entry in it:
                    try:
                        if entry.is_file():
                            entries_to_check.append(entry)
                        elif entry.is_dir() and entry.name.lower() not in skip_dirs and not entry.name.startswith('.'):
                            try:
                                with os.scandir(entry.path) as sub_it:
                                    for sub_entry in sub_it:
                                        if sub_entry.is_file():
                                            entries_to_check.append(sub_entry)
                            except Exception:
                                pass
                    except Exception:
                        continue
        except Exception:
            continue

        for entry in entries_to_check:
            try:
                name = entry.name
                item_ext = os.path.splitext(name)[1].lower()
                if item_ext not in SUPPORTED_EXTENSIONS:
                    continue

                if ext_filter and item_ext != ext_filter:
                    continue

                resolved = Path(entry.path).resolve()
                if resolved in seen_paths:
                    continue

                if not is_path_allowed(resolved):
                    continue

                seen_paths.add(resolved)
                results.append({
                    "filename": name,
                    "extension": item_ext,
                    "path": str(resolved),
                    "size": entry.stat().st_size
                })
            except Exception:
                continue

    return results


NUM_WORD_MAP = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"
}


def normalize_text_numbers(text: str) -> str:
    res = text
    for word, digit in NUM_WORD_MAP.items():
        res = re.sub(r'(?<![a-zA-Z0-9])' + word + r'(?![a-zA-Z0-9])', digit, res, flags=re.IGNORECASE)
    return res


def find_file(
    query_or_name: str,
    directory: str | None = None
) -> list[dict]:
    """
    Find local files in approved directories based on user description.
    Supports tokenized/fuzzy matching and number word normalization.
    Returns matching candidates.
    If multiple match, returns all candidates so the user can choose.
    """
    all_files = list_files(directory=directory)
    if not all_files:
        return []

    q = query_or_name.strip().lower()
    q_norm = normalize_text_numbers(q)

    # Determine desired extension if mentioned
    desired_ext = None
    if ".pdf" in q or "pdf" in q.split():
        desired_ext = ".pdf"
    elif ".docx" in q or "docx" in q.split() or "doc" in q.split():
        desired_ext = ".docx"
    elif ".txt" in q or "txt" in q.split() or "text" in q.split():
        desired_ext = ".txt"

    # Extract keywords (ignoring common conversational filler words)
    stop_words = {
        "my", "the", "a", "an", "file", "document", "pdf", "docx", "txt",
        "upload", "find", "get", "called", "named", "from", "in", "downloads",
        "documents", "desktop", "please", "can", "you", "to", "for"
    }
    clean_q_spaces = q_norm.replace("_", " ").replace("-", " ")
    raw_tokens = re.findall(r'[a-zA-Z0-9]+', clean_q_spaces)
    keywords = [t for t in raw_tokens if t not in stop_words and len(t) > 0]

    if not keywords:
        keywords = [t for t in raw_tokens if len(t) > 1]

    scored_candidates = []

    for f in all_files:
        fname = f["filename"].lower()
        fname_base = Path(fname).stem
        fname_norm = normalize_text_numbers(fname)
        fname_base_norm = Path(fname_norm).stem
        f_ext = f["extension"]

        if desired_ext and f_ext != desired_ext:
            continue

        score = 0

        # Exact match (normalized or raw)
        if q == fname or q == fname_base or q_norm == fname_norm or q_norm == fname_base_norm:
            score += 100

        # Full keyword string in filename
        full_kw_phrase = " ".join(keywords)
        if full_kw_phrase and full_kw_phrase in fname.replace("_", " ").replace("-", " "):
            score += 50

        # Keyword match scoring
        for kw in keywords:
            kw_norm = NUM_WORD_MAP.get(kw, kw)
            if kw in fname or kw_norm in fname:
                score += 15
            elif kw in fname_base.split("_") or kw_norm in fname_base.split("_") or kw in fname_base.split("-"):
                score += 20

        if score > 0:
            scored_candidates.append((score, f))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in scored_candidates]



def select_file(
    file_path_or_name: str,
    candidates: list[dict] | None = None
) -> dict:
    """
    Safely select and validate a candidate file.
    Enforces path safety and ensures arbitrary paths cannot be invented.
    """
    # 1. If candidate list provided, check for a match
    if candidates:
        for c in candidates:
            if file_path_or_name == c["path"] or file_path_or_name.lower() == c["filename"].lower():
                return c

    # 2. Check as a direct path
    cand_path = Path(file_path_or_name).resolve()

    if not is_path_allowed(cand_path):
        raise PermissionError(f"Access denied: File '{file_path_or_name}' is outside approved directories.")

    if not cand_path.exists() or not cand_path.is_file():
        raise FileNotFoundError(f"File not found: '{file_path_or_name}'")

    item_ext = cand_path.suffix.lower()
    if item_ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{item_ext}'. AuraRAG supports: {list(SUPPORTED_EXTENSIONS)}")

    return {
        "filename": cand_path.name,
        "extension": item_ext,
        "path": str(cand_path),
        "size": cand_path.stat().st_size
    }


def upload_to_rag(file_path: str) -> dict:
    """
    Send the selected file through the existing AuraRAG ingestion pipeline.
    Reuses load_document -> split_text -> add_chunks.
    """
    cand_path = Path(file_path).resolve()

    if not is_path_allowed(cand_path):
        raise PermissionError(f"Access denied: File '{file_path}' is outside approved directories.")

    if not cand_path.exists() or not cand_path.is_file():
        raise FileNotFoundError(f"File not found: '{file_path}'")

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    filename = cand_path.name
    dest_path = data_dir / filename

    # Copy to data directory to match existing /upload architecture
    shutil.copy2(cand_path, dest_path)

    # Ingest using existing RAG pipeline
    text = load_document(str(dest_path))
    chunks = split_text(text)
    stored_chunks = add_chunks(chunks, filename)

    return {
        "filename": filename,
        "message": f"Successfully uploaded and ingested '{filename}' into AuraRAG.",
        "number_of_chunks": stored_chunks,
        "success": True
    }
