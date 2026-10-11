"""Gemini API client wrapper."""

import atexit
import time
import json
from typing import Optional, Dict, Any, Union
from google import genai
from google.genai import errors, types
from PIL import Image
import io

from .config import config, logger

# shared module path is set up by config.py (imported above)
from shared.gemini_utils import parse_json_response


class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors."""

    pass


class GeminiRateLimitError(GeminiAPIError):
    """Exception for rate limit errors."""

    pass


class GeminiResponseError(GeminiAPIError):
    """Exception for invalid response errors."""

    pass


_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    """Create the reusable SDK client after application configuration is loaded."""
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=config.GOOGLE_API_KEY,
            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
        )
    return _client


def close_client() -> None:
    """Release the SDK's HTTP connections when processing exits."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


atexit.register(close_client)


def _generation_config(analysis_type: Optional[str] = None) -> types.GenerateContentConfig:
    """Keep the same sampling settings and structured schemas for every request."""
    generation_config = types.GenerateContentConfig(
        temperature=0.1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=16384,
    )
    if analysis_type:
        system_instruction, response_schema = _get_schema_config(analysis_type)
        generation_config.system_instruction = system_instruction
        if response_schema:
            generation_config.response_mime_type = "application/json"
            generation_config.response_schema = response_schema
    return generation_config


def _get_schema_config(analysis_type: str):
    """Get system instruction and response schema for an analysis type.

    Returns:
        Tuple of (system_instruction_string, pydantic_model_class_or_None).
    """
    from .prompts import (
        THUMBNAIL_SYSTEM_INSTRUCTION,
        TITLE_DESC_SYSTEM_INSTRUCTION,
    )
    from .batch_api.schemas import (
        ThumbnailAnalysisSchema,
        TitleDescriptionAnalysisSchema,
    )

    if analysis_type == "thumbnail":
        return THUMBNAIL_SYSTEM_INSTRUCTION, ThumbnailAnalysisSchema
    elif analysis_type == "title_description":
        return TITLE_DESC_SYSTEM_INSTRUCTION, TitleDescriptionAnalysisSchema
    return None, None


def _execute_with_retry(generate_func, retries: int = 3) -> Dict[str, Any]:
    """Execute a Gemini generation with retry logic.

    Args:
        generate_func: Function that calls client.models.generate_content()
        retries: Number of retry attempts

    Returns:
        Parsed JSON response

    Raises:
        GeminiAPIError: For API-related errors
        GeminiRateLimitError: For rate limit errors
        GeminiResponseError: For invalid response errors
    """
    last_error: Exception = RuntimeError("All retry attempts failed without returning a result")

    for attempt in range(retries):
        try:
            response = generate_func()

            # Validate response exists
            if response is None:
                raise GeminiResponseError("Gemini returned None response")

            # Check for blocked responses
            if response.prompt_feedback:
                if response.prompt_feedback.block_reason not in (None, types.BlockedReason.BLOCKED_REASON_UNSPECIFIED):
                    raise GeminiResponseError(f"Response blocked: {response.prompt_feedback.block_reason}")

            # Validate response text exists
            text = response.text
            if not text:
                raise GeminiResponseError("Gemini response has no text content")

            return parse_json_response(text)

        except json.JSONDecodeError as e:
            # JSON parsing error - don't retry, it won't help
            logger.error(f"JSON parsing error: {e}")
            raise GeminiResponseError(f"Failed to parse JSON response: {e}")

        except errors.APIError as e:
            if e.code == 400:
                raise GeminiAPIError(f"Invalid request: {e}") from e
            if e.code == 429:
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{retries}): {e}")
                last_error = GeminiRateLimitError(str(e))
                wait_time = config.RETRY_DELAY * (2**attempt) * 2
            else:
                logger.warning(f"Google API error (attempt {attempt + 1}/{retries}): {e}")
                last_error = GeminiAPIError(str(e))
                wait_time = config.RETRY_DELAY * (attempt + 1)
            if attempt < retries - 1:
                time.sleep(wait_time)

        except GeminiResponseError:
            # Re-raise response errors without retry
            raise

        except Exception as e:
            # Unexpected errors - log with full context
            logger.error(
                f"Unexpected error during Gemini call (attempt {attempt + 1}/{retries}): {type(e).__name__}: {e}"
            )
            last_error = GeminiAPIError(f"Unexpected error: {type(e).__name__}: {e}")
            if attempt < retries - 1:
                time.sleep(config.RETRY_DELAY * (attempt + 1))

    raise last_error


def analyze_text(prompt: str, text: str, retries: int = 3, analysis_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze text using Gemini.

    Args:
        prompt: The analysis prompt with instructions
        text: The text to analyze
        retries: Number of retry attempts
        analysis_type: Optional analysis type for schema-aware model

    Returns:
        Parsed JSON response from Gemini
    """
    client = get_client()
    generation_config = _generation_config(analysis_type)

    # When using response_schema, use the concise user prompt
    if analysis_type:
        from .prompts import TITLE_DESC_USER_PROMPT

        full_prompt = f"{TITLE_DESC_USER_PROMPT}\n\nText to analyze:\n{text}"
    else:
        full_prompt = f"{prompt}\n\nText to analyze:\n{text}"

    return _execute_with_retry(
        lambda: client.models.generate_content(
            model=config.GEMINI_MODEL, contents=full_prompt, config=generation_config
        ),
        retries,
    )


def analyze_image(
    prompt: str, image_data: Union[bytes, Image.Image], retries: int = 3, analysis_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze an image using Gemini Vision.

    Args:
        prompt: The analysis prompt with instructions
        image_data: Image as bytes or PIL Image
        retries: Number of retry attempts
        analysis_type: Optional analysis type for schema-aware model

    Returns:
        Parsed JSON response from Gemini
    """
    client = get_client()
    generation_config = _generation_config(analysis_type)
    image = None
    should_close = False

    try:
        # Convert bytes to PIL Image if needed
        if isinstance(image_data, bytes):
            image = Image.open(io.BytesIO(image_data))
            should_close = True  # We created this image, so we should close it
        else:
            image = image_data
            should_close = False  # Caller owns this image

        # When using response_schema, use the concise user prompt
        if analysis_type:
            from .prompts import THUMBNAIL_USER_PROMPT

            effective_prompt = THUMBNAIL_USER_PROMPT
        else:
            effective_prompt = prompt

        return _execute_with_retry(
            lambda: client.models.generate_content(
                model=config.GEMINI_MODEL, contents=[effective_prompt, image], config=generation_config
            ),
            retries,
        )
    finally:
        # Clean up image resource if we created it
        if should_close and image is not None:
            try:
                image.close()
            except Exception:
                pass  # Ignore close errors


def test_connection() -> bool:
    """Test the Gemini API connection."""
    try:
        response = get_client().models.generate_content(
            model=config.GEMINI_MODEL,
            contents="Say 'OK' if you can hear me.",
            config=_generation_config(),
        )

        # Validate response exists and has text
        if response is None:
            logger.error("Gemini connection test failed: No response received")
            return False

        if not hasattr(response, "text") or not response.text:
            logger.error("Gemini connection test failed: Response has no text")
            return False

        return "ok" in response.text.lower()

    except errors.APIError as e:
        logger.error(f"Gemini connection test failed (API error): {e}")
        return False
    except Exception as e:
        logger.error(f"Gemini connection test failed ({type(e).__name__}): {e}")
        return False
