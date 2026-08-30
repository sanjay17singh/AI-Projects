from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

_SPLITTER = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)


def split_document(document: Document) -> list[Document]:
    return _SPLITTER.split_documents([document])
