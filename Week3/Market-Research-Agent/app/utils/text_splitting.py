from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

_DEFAULT_CHUNK_SIZE = 1000
_DEFAULT_CHUNK_OVERLAP = 150
_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=_DEFAULT_CHUNK_SIZE, chunk_overlap=_DEFAULT_CHUNK_OVERLAP
)


def split_document(
    document: Document, chunk_size: int | None = None, chunk_overlap: int | None = None
) -> list[Document]:
    """chunk_size/chunk_overlap default to the module constants (matching
    Settings.chunk_size/chunk_overlap) so existing callers are unaffected;
    pass explicit values (e.g. from Settings) to sweep chunking strategy in
    an evaluation run without editing source."""
    if chunk_size is None and chunk_overlap is None:
        return _SPLITTER.split_documents([document])
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or _DEFAULT_CHUNK_SIZE,
        chunk_overlap=chunk_overlap or _DEFAULT_CHUNK_OVERLAP,
    )
    return splitter.split_documents([document])
