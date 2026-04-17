"""LLM utility for agents using Minimax (Anthropic SDK)."""

from __future__ import annotations
import logging
import json
import re
from typing import Any, Type, TypeVar
from pydantic import BaseModel
import anthropic
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def get_llm_client() -> anthropic.Anthropic | None:
    """Return an initialized Minimax (Anthropic-compatible) client or None if key is missing."""
    if not settings.minimax_api_key:
        logger.warning("MINIMAX_API_KEY not found in settings.")
        return None
    
    # Minimax uses the Anthropic SDK with a custom base URL
    return anthropic.Anthropic(
        api_key=settings.minimax_api_key,
        base_url="https://api.minimaxi.com/anthropic"
    )


def extract_structured_data(
    prompt: str,
    response_model: Type[T],
    system_message: str = "You are a specialized structural engineering assistant.",
    model: str | None = None,
) -> T | None:
    """Invoke LLM and parse result into a Pydantic model."""
    client = get_llm_client()
    if not client:
        return None

    target_model = model or settings.openai_model # Defaulted to MiniMax-M2.7 in config

    # Inject schema into prompt
    schema_json = response_model.model_json_schema()
    full_prompt = f"{prompt}\n\nYour response MUST be a valid JSON object matching this schema:\n{json.dumps(schema_json, indent=2)}\n\nOutput ONLY the raw JSON."

    try:
        message = client.messages.create(
            model=target_model,
            max_tokens=4096,
            system=system_message,
            messages=[
                {"role": "user", "content": full_prompt},
            ],
            temperature=0.1,
        )
        
        # Extract text from content blocks
        content_text = ""
        for block in message.content:
            if block.type == "text":
                content_text += block.text
        
        if not content_text:
            return None

        # Try to find JSON block if LLM included commentary
        json_match = re.search(r'(\{.*\})', content_text, re.DOTALL)
        if json_match:
            content_text = json_match.group(1)

        return response_model.model_validate_json(content_text)
    except Exception as e:
        logger.error(f"Error during structured extraction: {e}")
        return None
