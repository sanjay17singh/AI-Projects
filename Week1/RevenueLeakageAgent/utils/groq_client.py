"""Small Groq integration that explains precomputed Pandas results."""

import json
import os
from typing import Any

from groq import APIConnectionError, APIStatusError, AuthenticationError, Groq


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def groq_is_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def explain_results(question: str, result: dict[str, Any]) -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL
    client = Groq(api_key=api_key)
    prompt = (
        "Answer the user's revenue-analysis question using only the calculated JSON result below. "
        "Pandas already performed every calculation. Do not invent values or claim access to raw data. "
        "Be concise, call out the most important numbers, and mention when a result list is empty.\n\n"
        f"Question: {question}\nCalculated result: {json.dumps(result, default=str)}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a careful revenue leakage analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=600,
        )
    except AuthenticationError as exc:
        raise RuntimeError("Groq rejected the API key. Check GROQ_API_KEY.") from exc
    except APIConnectionError as exc:
        raise RuntimeError("Could not connect to Groq. Check your network and try again.") from exc
    except APIStatusError as exc:
        raise RuntimeError(f"Groq returned an API error: {exc.status_code}.") from exc
    return response.choices[0].message.content or "Groq returned an empty response."
