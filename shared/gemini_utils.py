"""Shared Gemini API utilities for YouTube Intelligence System.

This module provides common patterns for working with Gemini API responses,
including JSON extraction and retry logic.

NOTE: The extract_json_from_response function is specifically designed to strip
ALL markdown code-block wrapping (backticks, language specifiers like ```json) that
PI.dev and other harness environments struggle to render in terminal views.
"""

import json
import re
import time
from typing import Dict, Any, Callable, TypeVar

T = TypeVar("T")


def extract_json_from_response(response_text: str) -> str:
    """Extract clean JSON from Gemini response, stripping ALL markdown wrapping.

    Handles code blocks like ```json ... ``` and any leftover backtick wrappers
    that can break terminal/harness display or JSON parsing.

    Args:
        response_text: Raw response text from Gemini

    Returns:
        Cleaned JSON string ready for parsing
    """
    text = response_text.strip()

    # Remove a leading code fence and optional language label
    if text.startswith("```"):
        text = re.sub(r"^```\w*\s*", "", text, flags=re.IGNORECASE)

    # Remove trailing fence if present
    if text.endswith("```"):
        text = text[:-3].strip()

    # Final safety pass for accidental surrounding fences
    while text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()

    return text.strip()


def parse_json_response(response_text: str) -> Dict[str, Any]:
    """Parse Gemini response as JSON, handling markdown formatting.

    Args:
        response_text: Raw response text from Gemini

    Returns:
        Parsed JSON as dictionary

    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    clean_text = extract_json_from_response(response_text)
    return json.loads(clean_text)


def call_with_retry(
    func: Callable[[], T], retries: int = 3, retry_delay: float = 1.0, error_message: str = "Operation failed"
) -> T:
    """Execute a function with retry logic and exponential backoff.

    Args:
        func: Function to execute (should return the result)
        retries: Maximum number of retry attempts
        retry_delay: Base delay between retries (multiplied by attempt number)
        error_message: Message for the final error

    Returns:
        Result from the function

    Raises:
        The last exception if all retries fail
    """
    last_error: Exception = RuntimeError(f"{error_message}: All {retries} retry attempts failed")

    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                sleep_time = retry_delay * (attempt + 1)
                time.sleep(sleep_time)

    raise last_error


def validate_gemini_response(response) -> str:
    """Validate Gemini response and extract text.

    Args:
        response: Gemini API response object

    Returns:
        Response text

    Raises:
        RuntimeError: If response is invalid or empty
    """
    if not response:
        raise RuntimeError("Empty response from Gemini API")
    if not hasattr(response, "text"):
        raise RuntimeError("Response has no text attribute")
    if not response.text:
        raise RuntimeError("Response text is empty")
    return response.text
