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

# Model instance
_model: Optional[genai.GenerativeModel] = None


def get_model() -> genai.GenerativeModel:
    """Get or create Gemini model instance."""
    global _model

    if _model is None:
        _model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            generation_config={
                'temperature': 0.1,  # Low temperature for consistent structured output
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 8192,
            }
        )

    return _model


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


def analyze_text(prompt: str, text: str, retries: int = 3) -> Dict[str, Any]:
    """
    Analyze text using Gemini.

    Args:
        prompt: The analysis prompt with instructions
        text: The text to analyze
        retries: Number of retry attempts

    Returns:
        Parsed JSON response from Gemini
    """
    model = get_model()
    full_prompt = f"{prompt}\n\nText to analyze:\n{text}"

    return _execute_with_retry(
        lambda: model.generate_content(full_prompt),
        retries
    )


def analyze_image(prompt: str, image_data: Union[bytes, Image.Image], retries: int = 3) -> Dict[str, Any]:
    """
    Analyze an image using Gemini Vision.

    Args:
        prompt: The analysis prompt with instructions
        image_data: Image as bytes or PIL Image
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

        return _execute_with_retry(
            lambda: model.generate_content([prompt, image]),
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
