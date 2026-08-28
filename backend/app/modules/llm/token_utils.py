"""Token utilities: estimation, chunking, and context clipping."""

def estimate_tokens(text: str) -> int:
    """Rough estimation of token count (~4 characters per token for source code/English)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_context(text: str, max_tokens: int = 2000) -> str:
    """Truncate text to fit within token limit while retaining structural lines."""
    estimated = estimate_tokens(text)
    if estimated <= max_tokens:
        return text

    max_chars = max_tokens * 4
    lines = text.splitlines(keepends=True)
    accumulated: list[str] = []
    current_len = 0

    for line in lines:
        if current_len + len(line) > max_chars:
            accumulated.append("\n# ... [Context truncated for length] ...\n")
            break
        accumulated.append(line)
        current_len += len(line)

    return "".join(accumulated)
