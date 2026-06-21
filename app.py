from __future__ import annotations

import streamlit as st

from src.procurement_law_agent import ProcurementLawAgent
from src.task1_collect_legal_docs import ensure_procurement_legal_docs
from src.task3_convert_markdown import convert_all
from src.task4_chunking_indexing import STANDARDIZED_DIR, VECTORSTORE_PATH, build_index
from src.task8_pageindex_vectorless import PAGEINDEX_CACHE_PATH, upload_documents


st.set_page_config(
    page_title="Procurement Law Agent",
    page_icon=":page_with_curl:",
    layout="wide",
)


REQUIRED_PROCUREMENT_MARKDOWN = [
    "74-vbhn-vpqh-luat-dau-thau-hop-nhat-2026.md",
    "24-2024-nd-cp-lua-chon-nha-thau.md",
    "17-2025-nd-cp-sua-doi-nghi-dinh-dau-thau.md",
    "23-2024-nd-cp-lua-chon-nha-dau-tu-theo-nganh.md",
    "115-2024-nd-cp-lua-chon-nha-dau-tu-du-an-su-dung-dat.md",
]


def _has_prepared_procurement_markdown() -> bool:
    legal_dir = STANDARDIZED_DIR / "legal"
    return legal_dir.exists() and all((legal_dir / filename).exists() for filename in REQUIRED_PROCUREMENT_MARKDOWN)


def _count_existing_markdown_files() -> int:
    if not STANDARDIZED_DIR.exists():
        return 0
    return len(list(STANDARDIZED_DIR.rglob("*.md")))


@st.cache_resource(show_spinner=False)
def ensure_knowledge_base(force_rebuild: bool = False) -> dict:
    docs = ensure_procurement_legal_docs(force_download=False)
    if _has_prepared_procurement_markdown() and not force_rebuild:
        converted_count = _count_existing_markdown_files()
    else:
        converted_count = len(convert_all())

    chunks = build_index(force_rebuild=force_rebuild or not VECTORSTORE_PATH.exists())
    if force_rebuild or not PAGEINDEX_CACHE_PATH.exists():
        upload_documents(domain="procurement", allowed_types={"legal"})
    return {
        "documents": len(docs),
        "converted": converted_count,
        "chunks": len(chunks),
    }


if "agent" not in st.session_state:
    st.session_state.agent = ProcurementLawAgent()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "kb_status" not in st.session_state:
    with st.spinner("Dang nap bo van ban Luat Dau thau va tao chi muc..."):
        st.session_state.kb_status = ensure_knowledge_base()


with st.sidebar:
    st.title("ProcurementLawAgent")
    st.caption("Gemini-backed RAG agent for Vietnam procurement law.")
    status = st.session_state.kb_status
    st.write(f"Legal source files: {status['documents']}")
    st.write(f"Markdown files: {status['converted']}")
    st.write(f"Indexed chunks: {status['chunks']}")

    if st.button("Rebuild knowledge base"):
        with st.spinner("Dang rebuild corpus..."):
            ensure_knowledge_base.clear()
            st.session_state.kb_status = ensure_knowledge_base(force_rebuild=True)
        st.success("Knowledge base da duoc cap nhat.")

    if st.button("Clear chat history"):
        st.session_state.agent.reset()
        st.session_state.messages = []
        st.success("Da xoa lich su hoi dap.")

    st.markdown("---")
    st.caption(
        "Scope: Luat Dau thau hop nhat 74/VBHN-VPQH va cac nghi dinh huong dan "
        "24/2024/ND-CP, 17/2025/ND-CP, 23/2024/ND-CP, 115/2024/ND-CP."
    )


st.title("Agent tu van Luat Dau thau")
st.write(
    "Hoi dap bang tieng Viet, co citation inline va uu tien noi ro ngay hieu luc, "
    "van ban can doi chieu, va pham vi ap dung."
)


def unique_sources(sources: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for source in sources:
        metadata = source.get("metadata", {})
        key = metadata.get("official_id") or metadata.get("path") or metadata.get("source")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if prompt := st.chat_input("Vi du: Chi dinh thau duoc ap dung trong truong hop nao?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Dang truy xuat van ban va sinh cau tra loi..."):
            result = st.session_state.agent.answer(prompt)
        st.markdown(result["answer"])

        with st.expander("Nguon su dung"):
            for index, source in enumerate(unique_sources(result["sources"]), start=1):
                metadata = source.get("metadata", {})
                title = metadata.get("title") or metadata.get("source", f"source_{index}")
                official_id = metadata.get("official_id", "")
                effective_date = metadata.get("effective_date", "")
                source_url = metadata.get("source_url", "")
                st.markdown(
                    f"**{index}. {title}**  \n"
                    f"- Official ID: `{official_id or 'n/a'}`  \n"
                    f"- Effective date: `{effective_date or 'n/a'}`  \n"
                    f"- Score: `{source.get('score', 0.0):.3f}`  \n"
                    f"- URL: {source_url or 'n/a'}"
                )
                st.code(source.get("content", "")[:900], language="markdown")

    st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
