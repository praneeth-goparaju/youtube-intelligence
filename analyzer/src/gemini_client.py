"""Gemini API client wrapper."""

import time
import json
from typing import Optional, Dict, Any, Union
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
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


# Initialize the Gemini client
genai.configure(api_key=config.GOOGLE_API_KEY)

# Model instances: keyed by (analysis_type or 'default')
_models: Dict[str, genai.GenerativeModel] = {}


def get_model(analysis_type: Optional[str] = None) -> genai.GenerativeModel:
    """Get or create Gemini model instance.

    When analysis_type is provided and response_schema models are available,
    creates a model with system_instruction and response_schema for structured output.
    Falls back to the default model configuration otherwise.

    Args:
        analysis_type: Optional analysis type ('thumbnail' or 'title_description')
                       for schema-aware model creation.
    """
    cache_key = analysis_type or 'default'

    if cache_key not in _models:
        model_kwargs = {
            'model_name': config.GEMINI_MODEL,
        }
        gen_config = {
            'temperature': 0.1,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 8192,
        }

        # Try to use structured output for specific analysis types
        if analysis_type:
            try:
                system_instruction, response_schema = _get_schema_config(analysis_type)
                if system_instruction:
                    model_kwargs['system_instruction'] = system_instruction
                if response_schema:
                    gen_config['response_mime_type'] = 'application/json'
                    gen_config['response_schema'] = response_schema
            except ImportError:
                # Pydantic not available — fall back to default
                pass

        model_kwargs['generation_config'] = gen_config
        _models[cache_key] = genai.GenerativeModel(**model_kwargs)

    return _models[cache_key]


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

    if analysis_type == 'thumbnail':
        return THUMBNAIL_SYSTEM_INSTRUCTION, ThumbnailAnalysisSchema
    elif analysis_type == 'title_description':
        return TITLE_DESC_SYSTEM_INSTRUCTION, TitleDescriptionAnalysisSchema
    return None, None


def _execute_with_retry(generate_func, retries: int = 3) -> Dict[str, Any]:
    """Execute a Gemini generation with retry logic.

    Args:
        generate_func: Function that calls model.generate_content()
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
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                    raise GeminiResponseError(f"Response blocked: {response.prompt_feedback.block_reason}")

            # Validate response text exists
            if not hasattr(response, 'text') or not response.text:
                raise GeminiResponseError("Gemini response has no text content")

            return parse_json_response(response.text)

        except json.JSONDecodeError as e:
            # JSON parsing error - don't retry, it won't help
            logger.error(f"JSON parsing error: {e}")
            raise GeminiResponseError(f"Failed to parse JSON response: {e}")

        except google_exceptions.ResourceExhausted as e:
            # Rate limit - wait longer before retry
            logger.warning(f"Rate limit hit (attempt {attempt + 1}/{retries}): {e}")
            last_error = GeminiRateLimitError(str(e))
            if attempt < retries - 1:
                wait_time = config.RETRY_DELAY * (2 ** attempt) * 2  # Longer wait for rate limits
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        except google_exceptions.InvalidArgument as e:
            # Invalid request - don't retry
            logger.error(f"Invalid argument error: {e}")
            raise GeminiAPIError(f"Invalid request: {e}")

        except google_exceptions.GoogleAPIError as e:
            # Other Google API errors - may be transient
            logger.warning(f"Google API error (attempt {attempt + 1}/{retries}): {e}")
            last_error = GeminiAPIError(str(e))
            if attempt < retries - 1:
                time.sleep(config.RETRY_DELAY * (attempt + 1))

        except GeminiResponseError:
            # Re-raise response errors without retry
            raise

        except Exception as e:
            # Unexpected errors - log with full context
            logger.error(f"Unexpected error during Gemini call (attempt {attempt + 1}/{retries}): {type(e).__name__}: {e}")
            last_error = GeminiAPIError(f"Unexpected error: {type(e).__name__}: {e}")
            if attempt < retries - 1:
                time.sleep(config.RETRY_DELAY * (attempt + 1))

    raise last_error


def analyze_text(prompt: str, text: str, retries: int = 3,
                 analysis_type: Optional[str] = None) -> Dict[str, Any]:
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
    model = get_model(analysis_type)

    # When using response_schema, use the concise user prompt
    if analysis_type:
        from .prompts import TITLE_DESC_USER_PROMPT
        full_prompt = f"{TITLE_DESC_USER_PROMPT}\n\nText to analyze:\n{text}"
    else:
        full_prompt = f"{prompt}\n\nText to analyze:\n{text}"

    return _execute_with_retry(
        lambda: model.generate_content(full_prompt),
        retries
    )


def analyze_image(prompt: str, image_data: Union[bytes, Image.Image], retries: int = 3,
                  analysis_type: Optional[str] = None) -> Dict[str, Any]:
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
    model = get_model(analysis_type)
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
            lambda: model.generate_content([effective_prompt, image]),
            retries
        )
    finally:
        # Clean up image resource if we created it
        if should_close and image is not None:
            try:
                image.close()
            except Exception:
                pass  # Ignore close errors


def analyze_image_with_text(prompt: str, image_data: Union[bytes, Image.Image],
                            additional_text: str, retries: int = 3) -> Dict[str, Any]:
    """
    Analyze an image with additional text context using Gemini Vision.

    Args:
        prompt: The analysis prompt with instructions
        image_data: Image as bytes or PIL Image
        additional_text: Additional text context
        retries: Number of retry attempts

    Returns:
        Parsed JSON response from Gemini
    """
    model = get_model()
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

        full_prompt = f"{prompt}\n\nAdditional context:\n{additional_text}"

        return _execute_with_retry(
            lambda: model.generate_content([full_prompt, image]),
            retries
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
        model = get_model()
        response = model.generate_content("Say 'OK' if you can hear me.")

        # Validate response exists and has text
        if response is None:
            logger.error("Gemini connection test failed: No response received")
            return False

        if not hasattr(response, 'text') or not response.text:
            logger.error("Gemini connection test failed: Response has no text")
            return False

        return 'ok' in response.text.lower()

    except google_exceptions.GoogleAPIError as e:
        logger.error(f"Gemini connection test failed (API error): {e}")
        return False
    except Exception as e:
        logger.error(f"Gemini connection test failed ({type(e).__name__}): {e}")
        return False
