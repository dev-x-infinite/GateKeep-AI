from dataclasses import dataclass
from app.services.extractor import ExtractedPage


@dataclass
class TextChunk:
    """Represents a text chunk ready for embedding and indexing."""
    text: str
    page_number: int
    chunk_index: int


def chunk_pages(
    pages: list[ExtractedPage],
    chunk_size: int = 800,
    chunk_overlap: int = 100
) -> list[TextChunk]:
    """
    Chunks extracted pages into overlapping segments.
    Preserves page numbers and assigns a 0-indexed sequential chunk_index.
    """
    if chunk_size <= chunk_overlap:
        raise ValueError("chunk_size must be strictly greater than chunk_overlap.")

    chunks: list[TextChunk] = []
    current_chunk_index = 0

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        # If page text is within chunk_size, keep it as one chunk
        if len(text) <= chunk_size:
            chunks.append(
                TextChunk(
                    text=text,
                    page_number=page.page_number,
                    chunk_index=current_chunk_index
                )
            )
            current_chunk_index += 1
            continue

        # Sliding window with overlap
        start = 0
        step = chunk_size - chunk_overlap

        while start < len(text):
            end = start + chunk_size
            chunk_slice = text[start:end].strip()

            if chunk_slice:
                chunks.append(
                    TextChunk(
                        text=chunk_slice,
                        page_number=page.page_number,
                        chunk_index=current_chunk_index
                    )
                )
                current_chunk_index += 1

            # If this chunk reached or exceeded the end of the page text, stop
            if end >= len(text):
                break

            start += step

    return chunks
