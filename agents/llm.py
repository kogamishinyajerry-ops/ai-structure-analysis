"""LLM utility for agents."""

from __future__ import annotations

import logging
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def get_llm_client() -> OpenAI | None:
    """Return an initialized OpenAI client or None if key is missing."""
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not found in settings.")
        return None
    return OpenAI(api_key=settings.openai_api_key)


def extract_structured_data(
    prompt: str,
    response_model: type[T],
    system_message: str = "You are a specialized structural engineering assistant.",
    model: str | None = None,
) -> T | None:
    """Invoke LLM with JSON mode and parse result into a Pydantic model."""
    client = get_llm_client()
    if not client:
        return None

    target_model = model or settings.openai_model

    # Inject schema into prompt if not already there or to be safe
    schema_json = response_model.model_json_schema()
    full_prompt = (
        f"{prompt}\n\n"
        "Your response MUST be a valid JSON object matching this schema:\n"
        f"{schema_json}"
    )

    try:
        response = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": full_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if not content:
            return None

        return response_model.model_validate_json(content)
    except Exception as e:
        logger.error(f"Error during structured extraction: {e}")
        return None
