from langchain_text_splitters import RecursiveCharacterTextSplitter
 
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50

_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
 
 
def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Split *text* into overlapping chunks for downstream embedding.
 
    Parameters
    ----------
    text : str
        Raw text extracted from a course document (PDF, PPTX, or DOCX).
    chunk_size : int
        Maximum number of characters per chunk.  Default: 512.
    chunk_overlap : int
        Number of characters shared between adjacent chunks.  Default: 50.
        Overlap preserves sentence context across chunk boundaries so the
        LLM can answer questions that span two adjacent chunks.
 
    Returns
    -------
    list[str]
        Ordered list of non-empty text chunks.
        Returns [] when *text* is empty or whitespace-only.
 
    Raises
    ------
    TypeError
        If *text* is not a str.
    ValueError
        If chunk_size <= 0, chunk_overlap < 0, or
        chunk_overlap >= chunk_size.
 
    Examples
    --------
    >>> chunks = chunk_text("Hello world. " * 100)
    >>> len(chunks) > 1
    True
    >>> all(len(c) <= 512 for c in chunks)
    True
    >>> chunk_text("")
    []
    >>> chunk_text("Short.")
    ['Short.']
    >>> chunk_text("   \\n\\t  ")
    []
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be str, got {type(text).__name__}")
 
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be > 0, got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"chunk_overlap must be >= 0, got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be less than "
            f"chunk_size ({chunk_size})"
        )
 
    if not text.strip():
        return []
 
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=_SEPARATORS,
        keep_separator=True,
    )
 
    raw_chunks = splitter.split_text(text)
 
    return [chunk for chunk in raw_chunks if chunk.strip()]
