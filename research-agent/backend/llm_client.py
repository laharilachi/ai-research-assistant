"""LLM client integration using LangChain.
Supports Groq (preferred) and OpenAI with unified calling interface.
"""
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from backend.config import (
    GROQ_API_KEY,
    OPENAI_API_KEY,
    get_active_provider,
)


def get_llm(
    provider_override: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> tuple[BaseChatModel, str, str]:
    """Factory function returning a configured LangChain Chat model.
    
    Returns:
        tuple[BaseChatModel, str, str]: (chat_model, provider_name, model_name)
    """
    provider, model_name = get_active_provider(provider_override)

    if provider == "groq":
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=60,
        )
        return llm, provider, model_name

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=60,
        )
        return llm, provider, model_name

    raise ValueError(f"Unsupported LLM provider: {provider}")


def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider_override: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """Helper to invoke the active LLM with a system and human prompt.
    
    Returns:
        str: Response text content
    """
    llm, _, _ = get_llm(
        provider_override=provider_override,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    response = llm.invoke(messages)
    return str(response.content)
