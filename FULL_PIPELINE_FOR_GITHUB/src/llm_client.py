"""
llm_client.py — Thin wrapper around vLLM's OpenAI-compatible REST API.
Both heavy (Qwen-72B) and light (Mistral-7B) clients are exposed here.
Includes exponential backoff retry on transient failures.
"""
import logging
import time

from openai import OpenAI
from src.config import (
    VLLM_HEAVY_BASE_URL, VLLM_LIGHT_BASE_URL,
    HEAVY_MODEL_NAME, LIGHT_MODEL_NAME,
    HEAVY_MAX_TOKENS, LIGHT_MAX_TOKENS, TEMPERATURE
)

from src.utils import setup_logger
logger = setup_logger(__name__)

MAX_RETRIES_LLM  = 3       # max attempts per LLM call
RETRY_BASE_DELAY = 2       # seconds — doubles each attempt (2, 4, 8)

# Lazy singletons — created once, reused across all nodes
_heavy_client: OpenAI | None = None
_light_client: OpenAI | None = None


def get_heavy_client() -> OpenAI:
    """Returns the heavy vLLM client (Qwen-72B). Used by Nodes 2, 3, 6."""
    global _heavy_client
    if _heavy_client is None:
        _heavy_client = OpenAI(
            base_url=VLLM_HEAVY_BASE_URL,
            api_key="EMPTY"   # vLLM does not require a real key
        )
    return _heavy_client


def get_light_client() -> OpenAI:
    """Returns the light vLLM client (Mistral-7B). Used by Nodes 1, 4, 5."""
    global _light_client
    if _light_client is None:
        _light_client = OpenAI(
            base_url=VLLM_LIGHT_BASE_URL,
            api_key="EMPTY"
        )
    return _light_client


def _call_with_retry(client: OpenAI, model: str, system_prompt: str,
                     user_prompt: str, max_tokens: int) -> str:
    """
    Internal helper that calls the vLLM chat endpoint with exponential backoff.
    Raises the last exception if all retries are exhausted.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES_LLM + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=TEMPERATURE,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            last_error = e
            wait = RETRY_BASE_DELAY ** attempt
            logger.warning(
                f"[llm_client] Attempt {attempt}/{MAX_RETRIES_LLM} failed "
                f"for model '{model}': {e}. Retrying in {wait}s..."
            )
            time.sleep(wait)

    raise RuntimeError(
        f"[llm_client] All {MAX_RETRIES_LLM} attempts failed for model '{model}'. "
        f"Last error: {last_error}"
    )


def call_heavy(system_prompt: str, user_prompt: str) -> str:
    """
    Calls Qwen-72B-AWQ via the heavy vLLM endpoint.
    Retries up to 3 times with exponential backoff on failure.
    """
    return _call_with_retry(
        get_heavy_client(), HEAVY_MODEL_NAME,
        system_prompt, user_prompt, HEAVY_MAX_TOKENS
    )


def call_light(system_prompt: str, user_prompt: str) -> str:
    """
    Calls Mistral-7B via the light vLLM endpoint.
    Retries up to 3 times with exponential backoff on failure.
    """
    return _call_with_retry(
        get_light_client(), LIGHT_MODEL_NAME,
        system_prompt, user_prompt, LIGHT_MAX_TOKENS
    )
