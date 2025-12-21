"""Utility functions."""


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text to maximum length with suffix."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def count_tokens(text: str) -> int:
    """Estimate token count using tiktoken or fallback."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4
