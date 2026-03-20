import pdfplumber
import os

def extract_text_from_pdf(pdf_path: str, password: str = None) -> str:

    extracted_text = ""

    try:
        # Open the PDF 
        with pdfplumber.open(pdf_path, password=password) as pdf:
            print(f"PDF has {len(pdf.pages)} pages")

            for page_num, page in enumerate(pdf.pages):
                # Extract text from each page
                page_text = page.extract_text()

                if page_text:
                    extracted_text += f"\n--- Page {page_num + 1} ---\n"
                    extracted_text += page_text

                # trying to extract tables 
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        extracted_text += "\n--- Table Data ---\n"
                        for row in table:
                            if row:
                                clean_row = [str(cell).strip() if cell else "" for cell in row]
                                extracted_text += " | ".join(clean_row) + "\n"

    except Exception as e:
        print(f"Error extracting PDF: {str(e)}")
        raise e

    return extracted_text


def save_uploaded_pdf(file_bytes: bytes, filename: str) -> str:

    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    file_path = os.path.join(uploads_dir, filename)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    print(f"PDF saved to: {file_path}")
    return file_path