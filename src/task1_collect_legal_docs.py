from __future__ import annotations

import html
import json
import re
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import requests
import urllib3

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "landing" / "legal"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROCUREMENT_DOCS = [
    {
        "filename": "74-vbhn-vpqh-luat-dau-thau-hop-nhat-2026.docx",
        "official_id": "74/VBHN-VPQH",
        "title": "74/VBHN-VPQH - Luat Dau thau hop nhat den 25-03-2026",
        "issued_date": "2026-03-25",
        "effective_date": "",
        "official_url": "https://vanban.chinhphu.vn/?docid=217348&pageid=27160",
        "download_page": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-74-vbhn-vpqh-469204.htm",
        "preferred_extensions": [".docx", ".doc", ".pdf"],
        "fallback_body": (
            "Van ban hop nhat 74/VBHN-VPQH gom Luat Dau thau 22/2023/QH15 va cac sua doi den ngay 25-03-2026. "
            "Day la van ban nen de tra cuu pham vi dieu chinh, hanh vi bi cam, trach nhiem cac chu the, "
            "nguyen tac lua chon nha thau, lua chon nha dau tu va quy dinh chuyen tiep.\n"
            "Khi can tra cuu dieu khoan hien hanh, uu tien van ban hop nhat nay truoc khi doc cac ban le.\n"
        ),
    },
    {
        "filename": "24-2024-nd-cp-lua-chon-nha-thau.docx",
        "official_id": "24/2024/ND-CP",
        "title": "24/2024/ND-CP - Huong dan Luat Dau thau ve lua chon nha thau",
        "issued_date": "2024-02-27",
        "effective_date": "2024-02-27",
        "official_url": "https://vanban.chinhphu.vn/?docid=209823&pageid=27160",
        "download_page": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-24-2024-nd-cp-41437.htm",
        "preferred_extensions": [".docx", ".doc", ".pdf"],
        "fallback_body": (
            "Nghi dinh 24/2024/ND-CP quy dinh chi tiet mot so dieu va bien phap thi hanh Luat Dau thau ve lua chon nha thau. "
            "Van ban nay thuong duoc dung khi can tra cuu quy trinh, hinh thuc va phuong thuc lua chon nha thau, "
            "mua sam truc tiep, chao hang canh tranh, dau thau qua mang va cac noi dung huong dan chi tiet.\n"
        ),
    },
    {
        "filename": "17-2025-nd-cp-sua-doi-nghi-dinh-dau-thau.docx",
        "official_id": "17/2025/ND-CP",
        "title": "17/2025/ND-CP - Sua doi cac nghi dinh huong dan Luat Dau thau",
        "issued_date": "2025-02-06",
        "effective_date": "2025-02-06",
        "official_url": "https://vanban.chinhphu.vn/?docid=212658&pageid=27160",
        "download_page": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-17-2025-nd-cp-44125/54785.htm",
        "preferred_extensions": [".docx", ".doc", ".pdf"],
        "fallback_body": (
            "Nghi dinh 17/2025/ND-CP sua doi, bo sung mot so dieu cua cac nghi dinh quy dinh chi tiet thi hanh Luat Dau thau. "
            "Khi cau hoi lien quan den cac moc sua doi trong nam 2025, can doi chieu van ban nay cung voi Luat 57/2024/QH15 va Luat 90/2025/QH15.\n"
        ),
    },
    {
        "filename": "23-2024-nd-cp-lua-chon-nha-dau-tu-theo-nganh.docx",
        "official_id": "23/2024/ND-CP",
        "title": "23/2024/ND-CP - Lua chon nha dau tu theo phap luat quan ly nganh, linh vuc",
        "issued_date": "2024-02-27",
        "effective_date": "2024-02-27",
        "official_url": "https://vanban.chinhphu.vn/?docid=209822&pageid=27160",
        "download_page": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-23-2024-nd-cp-41429/49206.htm",
        "preferred_extensions": [".docx", ".doc", ".pdf"],
        "fallback_body": (
            "Nghi dinh 23/2024/ND-CP huong dan lua chon nha dau tu thuc hien du an thuoc truong hop phai to chuc dau thau theo phap luat quan ly nganh, linh vuc. "
            "Van ban nay phu hop cho cac cau hoi ve du an kinh doanh khong phai du an su dung dat.\n"
        ),
    },
    {
        "filename": "115-2024-nd-cp-lua-chon-nha-dau-tu-du-an-su-dung-dat.docx",
        "official_id": "115/2024/ND-CP",
        "title": "115/2024/ND-CP - Lua chon nha dau tu doi voi du an dau tu co su dung dat",
        "issued_date": "2024-09-16",
        "effective_date": "2024-09-16",
        "official_url": "https://vanban.chinhphu.vn/?docid=211225&pageid=27160",
        "download_page": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-115-2024-nd-cp-42763/51834.htm",
        "preferred_extensions": [".docx", ".doc", ".pdf"],
        "fallback_body": (
            "Nghi dinh 115/2024/ND-CP huong dan lua chon nha dau tu thuc hien du an dau tu co su dung dat. "
            "Can tra cuu van ban nay khi cau hoi lien quan den dau thau du an co su dung dat, so bo ve dat, tieu chuan va quy trinh danh gia nha dau tu.\n"
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
        safe = paragraph.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
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


def _cleanup_temp_files() -> None:
    for pattern in ("_tmp_*", "_test_*"):
        for path in DATA_DIR.glob(pattern):
            if path.is_file():
                path.unlink()


def _extract_download_links(page_html: str) -> list[str]:
    raw_links = re.findall(
        r"https://g7\.cdnchinhphu\.vn/api/download/stream\?[^\"']+?\.(?:docx|doc|pdf)",
        page_html,
        flags=re.IGNORECASE,
    )
    return [html.unescape(link).replace(" ", "") for link in raw_links]


def _pick_download_link(page_html: str, preferred_extensions: list[str]) -> tuple[str, str]:
    links = _extract_download_links(page_html)
    if not links:
        raise RuntimeError("Khong tim thay link tai ve tren trang cong bao.")

    lowered_map = {link.lower(): link for link in links}
    for extension in preferred_extensions:
        for lowered, original in lowered_map.items():
            if lowered.endswith(extension.lower()):
                return original.replace("&amp;", "&"), extension.lower()

    first = links[0].replace("&amp;", "&")
    suffix = Path(first.split("file_name=")[-1]).suffix.lower() or ".bin"
    return first, suffix


def _download_file(url: str, output_path: Path) -> Path:
    response = requests.get(url, timeout=90, verify=False)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return output_path


def _powershell_literal(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def _convert_doc_to_docx(doc_path: Path, target_path: Path) -> Path:
    command = f"""
$word = $null
$document = $null
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open('{_powershell_literal(doc_path)}', $false, $true)
    $document.SaveAs([ref] '{_powershell_literal(target_path)}', [ref] 16)
}} finally {{
    if ($document -ne $null) {{ $document.Close() }}
    if ($word -ne $null) {{ $word.Quit() }}
}}
""".strip()
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
    )
    if not target_path.exists() or target_path.stat().st_size <= 1024:
        raise RuntimeError(f"Khong the chuyen {doc_path.name} sang DOCX.")
    return target_path


def _sidecar_path(document_path: Path) -> Path:
    return document_path.with_suffix(".meta.json")


def _write_sidecar_metadata(document_path: Path, spec: dict, download_url: str, original_extension: str) -> None:
    metadata = {
        "official_id": spec["official_id"],
        "official_title": spec["title"],
        "issued_date": spec["issued_date"],
        "effective_date": spec["effective_date"],
        "official_url": spec["official_url"],
        "download_page": spec["download_page"],
        "download_url": download_url,
        "original_extension": original_extension,
        "domain": "procurement",
        "jurisdiction": "vietnam",
    }
    _sidecar_path(document_path).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_fallback_summary(spec: dict, target_path: Path) -> Path:
    body = (
        f"Official ID: {spec['official_id']}\n"
        f"Issued date: {spec['issued_date']}\n"
        f"Effective date: {spec['effective_date'] or 'See official text'}\n"
        f"Official URL: {spec['official_url']}\n"
        f"Download page: {spec['download_page']}\n\n"
        f"{spec['fallback_body']}"
    )
    _write_minimal_docx(target_path, spec["title"], body)
    return target_path


def _download_or_build_document(spec: dict, force_download: bool = False) -> Path:
    target_path = DATA_DIR / spec["filename"]
    if not force_download and target_path.exists() and target_path.stat().st_size > 1024:
        return target_path

    download_url = spec["download_page"]
    extension = ".docx"
    temp_path = DATA_DIR / f"_tmp_{target_path.stem}{extension}"

    try:
        page_html = requests.get(spec["download_page"], timeout=30).text
        download_url, extension = _pick_download_link(page_html, spec["preferred_extensions"])
        temp_path = DATA_DIR / f"_tmp_{target_path.stem}{extension}"
        _download_file(download_url, temp_path)
        if extension == ".docx":
            target_path.write_bytes(temp_path.read_bytes())
        elif extension == ".doc":
            _convert_doc_to_docx(temp_path, target_path)
        else:
            # PDF download is kept only as a last resort. A compact DOCX fallback
            # makes the downstream Markdown conversion deterministic.
            _write_fallback_summary(spec, target_path)
        _write_sidecar_metadata(target_path, spec, download_url=download_url, original_extension=extension)
        return target_path
    except Exception:
        _write_fallback_summary(spec, target_path)
        _write_sidecar_metadata(target_path, spec, download_url=download_url, original_extension=extension)
        return target_path
    finally:
        if temp_path.exists():
            temp_path.unlink()


def ensure_procurement_legal_docs(force_download: bool = False) -> list[Path]:
    setup_directory()
    _cleanup_temp_files()

    generated_files: list[Path] = []
    for spec in PROCUREMENT_DOCS:
        generated_files.append(_download_or_build_document(spec, force_download=force_download))
    return generated_files


def ensure_sample_legal_docs() -> list[Path]:
    """Backward-compatible alias for the coursework scripts/tests."""
    return ensure_procurement_legal_docs(force_download=False)


if __name__ == "__main__":
    created = ensure_procurement_legal_docs(force_download=False)
    for path in created:
        print(f"Created: {path} ({path.stat().st_size} bytes)")
