import io
from dataclasses import dataclass
from pypdf import PdfReader


@dataclass
class ExtractedPage:
    """Represents text extracted from a specific page of a document."""
    page_number: int
    text: str


def extract_text_from_file(file_bytes: bytes, filename: str) -> list[ExtractedPage]:
    """
    Extracts text from PDF or TXT file bytes.
    Preserves page numbers (1-indexed) for PDFs.
    
    Raises:
        ValueError: If the file type is unsupported or extraction yields no text.
    """
    clean_filename = filename.lower()

    if clean_filename.endswith(".txt"):
        return _extract_txt(file_bytes)
    elif clean_filename.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    else:
        raise ValueError(f"Unsupported file type for '{filename}'. Only .pdf and .txt files are supported.")


def _extract_txt(file_bytes: bytes) -> list[ExtractedPage]:
    """Extracts text from raw TXT bytes using UTF-8 with Latin-1 fallback."""
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("The uploaded TXT file is empty.")

    return [ExtractedPage(page_number=1, text=cleaned_text)]


def _extract_pdf(file_bytes: bytes) -> list[ExtractedPage]:
    """Extracts text page-by-page from raw PDF bytes using pypdf."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Failed to parse PDF file: {str(e)}")

    if len(reader.pages) == 0:
        raise ValueError("The uploaded PDF file contains no pages.")

    pages: list[ExtractedPage] = []
    total_extracted_characters = 0

    for idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        cleaned_page_text = page_text.strip()
        total_extracted_characters += len(cleaned_page_text)

        # Store page text even if empty to keep 1-based page numbering consistent
        pages.append(ExtractedPage(page_number=idx + 1, text=cleaned_page_text))

    if total_extracted_characters == 0:
        raise ValueError(
            "No extractable text found in PDF. Scanned images or password-protected PDFs are not supported."
        )

    return pages
