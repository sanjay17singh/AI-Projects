"""T04 (+): RecursiveCharacterTextSplitter produces expected overlapping
chunk sizes/count."""

from langchain_core.documents import Document

from app.utils.text_splitting import split_document


def test_long_document_splits_into_expected_overlapping_chunks():
    doc = Document(page_content="x" * 2500, metadata={"k": "v"})
    chunks = split_document(doc)

    assert len(chunks) == 3
    assert [len(c.page_content) for c in chunks] == [1000, 1000, 800]
    for chunk in chunks:
        assert chunk.metadata == {"k": "v"}


def test_short_document_yields_single_chunk():
    doc = Document(page_content="short text", metadata={})
    chunks = split_document(doc)
    assert len(chunks) == 1
    assert chunks[0].page_content == "short text"
