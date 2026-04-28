import os


def read_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.txt':
        return _read_txt(path)
    elif ext == '.docx':
        return _read_docx(path)
    elif ext == '.pdf':
        return _read_pdf(path)
    else:
        raise ValueError(
            f"Формат '{ext}' не поддерживается. Используйте TXT, DOCX или PDF."
        )


def _read_txt(path: str) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'cp1251', 'cp1252', 'latin-1'):
        try:
            with open(path, 'r', encoding=enc) as f:
                text = f.read()
            if text.strip():
                return text.strip()
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(
        "Не удалось прочитать файл. Попробуйте сохранить его в кодировке UTF-8."
    )


def _read_docx(path: str) -> str:
    try:
        from docx import Document
    except ImportError:
        raise ValueError("Установите python-docx:\n  pip install python-docx")
    try:
        doc = Document(path)
        parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not parts:
            raise ValueError("Документ не содержит текста.")
        return '\n'.join(parts)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Ошибка чтения DOCX: {e}")


def _read_pdf(path: str) -> str:
    try:
        from file_reader.pdf_reader import read_pdf
        text = read_pdf(path)
    except Exception as e:
        raise ValueError(f"Ошибка чтения PDF: {e}")
    if not text or not text.strip():
        raise ValueError(
            "PDF не содержит извлекаемого текста\n(возможно, отсканированный документ)."
        )
    return text.strip()
