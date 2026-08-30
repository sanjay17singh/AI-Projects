"""The only module that constructs LangChain OpenAI clients. Agents call
get_chat_model()/get_embeddings_model() rather than instantiating ChatOpenAI
directly, so tests can monkeypatch this module's factories with fakes."""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import Settings


def get_chat_model(settings: Settings, fast: bool = False, temperature: float = 0.0) -> ChatOpenAI:
    model = settings.openai_model_fast if fast else settings.openai_model
    return ChatOpenAI(model=model, api_key=settings.openai_api_key, temperature=temperature)


def get_embeddings_model(settings: Settings) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)
