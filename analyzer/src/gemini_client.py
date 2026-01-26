"""Gemini API client wrapper."""

import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union
import google.generativeai as genai
from PIL import Image
import io

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.gemini_utils import parse_json_response

from .config import config, logger


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
        The last exception if all retries fail
    """
    last_error: Exception = RuntimeError("All retry attempts failed without returning a result")

    for attempt in range(retries):
        try:
            response = generate_func()
            return parse_json_response(response.text)
        except Exception as e:
            last_error = e
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

    # Convert bytes to PIL Image if needed
    if isinstance(image_data, bytes):
        image = Image.open(io.BytesIO(image_data))
    else:
        image = image_data

    return _execute_with_retry(
        lambda: model.generate_content([prompt, image]),
        retries
    )


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

    # Convert bytes to PIL Image if needed
    if isinstance(image_data, bytes):
        image = Image.open(io.BytesIO(image_data))
    else:
        image = image_data

    full_prompt = f"{prompt}\n\nAdditional context:\n{additional_text}"

    return _execute_with_retry(
        lambda: model.generate_content([full_prompt, image]),
        retries
    )


def test_connection() -> bool:
    """Test the Gemini API connection."""
    try:
        model = get_model()
        response = model.generate_content("Say 'OK' if you can hear me.")
        return 'ok' in response.text.lower()
    except Exception as e:
        logger.error(f"Gemini connection test failed: {e}")
        return False
