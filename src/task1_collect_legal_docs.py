from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "landing" / "legal"

SAMPLE_DOCX_DOCUMENTS = [
    {
        "filename": "bo-luat-hinh-su-2015.docx",
        "title": "Bo luat Hinh su 2015 - Chuong XX",
        "body": (
            "Chuong XX quy dinh cac toi pham ve ma tuy, trong do co hanh vi tang tru, van chuyen, "
            "mua ban trai phep chat ma tuy va cac muc hinh phat tuong ung.\n" * 18
        ),
    },
    {
        "filename": "nghi-dinh-105-2021.docx",
        "title": "Nghi dinh 105/2021/ND-CP",
        "body": (
            "Nghi dinh nay huong dan thi hanh Luat Phong, chong ma tuy 2021, gom co quan co tham quyen, "
            "quan ly nguoi su dung trai phep chat ma tuy va quy trinh cai nghien.\n" * 18
        ),
    },
]


def setup_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _write_minimal_docx(path: Path, title: str, body: str) -> None:
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""
    doc_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""
    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>{title}</dc:title>
  <dc:creator>Codex</dc:creator>
</cp:coreProperties>"""
    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>Codex</Application>
</Properties>"""

    paragraphs = [title, ""] + body.splitlines()
    paragraph_xml = []
    for paragraph in paragraphs:
        safe = (
            paragraph.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        paragraph_xml.append(f'<w:p><w:r><w:t xml:space="preserve">{safe}</w:t></w:r></w:p>')

    document_xml = (
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>"""
        """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">"""
        f"<w:body>{''.join(paragraph_xml)}"
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" '
        'w:bottom="1440" w:left="1440"/></w:sectPr></w:body></w:document>'
    )

    with ZipFile(path, "w", ZIP_DEFLATED) as docx_file:
        docx_file.writestr("[Content_Types].xml", content_types)
        docx_file.writestr("_rels/.rels", rels)
        docx_file.writestr("docProps/core.xml", core)
        docx_file.writestr("docProps/app.xml", app)
        docx_file.writestr("word/document.xml", document_xml)
        docx_file.writestr("word/_rels/document.xml.rels", doc_rels)


def _cleanup_small_placeholder_pdfs() -> None:
    for pdf_file in DATA_DIR.glob("*.pdf"):
        sibling_docx = pdf_file.with_suffix(".docx")
        if sibling_docx.exists() or pdf_file.stat().st_size < 4096:
            pdf_file.unlink()


def ensure_sample_legal_docs() -> list[Path]:
    setup_directory()
    _cleanup_small_placeholder_pdfs()
    temp_test = DATA_DIR / "temp-test.docx"
    if temp_test.exists():
        temp_test.unlink()

    generated_files: list[Path] = []
    for document in SAMPLE_DOCX_DOCUMENTS:
        path = DATA_DIR / document["filename"]
        if not path.exists() or path.stat().st_size <= 1024:
            _write_minimal_docx(path, document["title"], document["body"])
        generated_files.append(path)

    return generated_files


if __name__ == "__main__":
    created = ensure_sample_legal_docs()
    for path in created:
        print(f"Created: {path} ({path.stat().st_size} bytes)")
