"""
pdf_utils.py
Extracts text from uploaded PDF or TXT study notes.
Never raises an unhandled exception into the UI layer.
"""

from pypdf import PdfReader
import io


MAX_CHARS = 20000  # safety cap so we don't send megabytes of notes to Gemini


def extract_text_from_upload(uploaded_file) -> dict:
    """
    Accepts a Streamlit UploadedFile (PDF or TXT).

    Returns:
        {
            "success": bool,
            "text": str,
            "message": str,
            "pages": int
        }
    """
    if uploaded_file is None:
        return {"success": False, "text": "", "message": "No file uploaded.", "pages": 0}

    filename = uploaded_file.name.lower()

    try:
        if filename.endswith(".txt"):
            raw = uploaded_file.read()
            text = raw.decode("utf-8", errors="ignore")
            text = text.strip()
            if not text:
                return {
                    "success": False, "text": "", "pages": 0,
                    "message": "The TXT file appears to be empty.",
                }
            return {
                "success": True,
                "text": text[:MAX_CHARS],
                "pages": 1,
                "message": f"Loaded {len(text)} characters from TXT file.",
            }

        elif filename.endswith(".pdf"):
            file_bytes = uploaded_file.read()
            reader = PdfReader(io.BytesIO(file_bytes))
            num_pages = len(reader.pages)

            extracted_chunks = []
            for page in reader.pages:
                try:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        extracted_chunks.append(page_text.strip())
                except Exception:
                    continue

            full_text = "\n\n".join(extracted_chunks).strip()

            if not full_text:
                return {
                    "success": False,
                    "text": "",
                    "pages": num_pages,
                    "message": (
                        "No extractable text was found in this PDF. "
                        "It may be a scanned/image-based PDF without a text layer."
                    ),
                }

            return {
                "success": True,
                "text": full_text[:MAX_CHARS],
                "pages": num_pages,
                "message": f"Extracted text from {num_pages} page(s).",
            }

        else:
            return {
                "success": False, "text": "", "pages": 0,
                "message": "Unsupported file type. Please upload a PDF or TXT file.",
            }

    except Exception as e:
        return {
            "success": False, "text": "", "pages": 0,
            "message": f"Could not read the file. It may be corrupted or password-protected. ({type(e).__name__})",
        }
