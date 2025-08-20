import base64
import os
import tempfile
import traceback
from typing import Annotated

import aiohttp
from dishka.integrations.fastapi import FromDishka
from fastapi import HTTPException
from loguru import logger

from sigil.presentation.base_response import PostResponseBase, create_response
from sigil.schemas.requests import SlideRequestSchema
from sigil.schemas.responses import SlideResponseSchema
from sigil.services.recognizer import RecognizerService


async def solve_slide_captcha(
    recognizer: Annotated[RecognizerService, FromDishka()],
    request: SlideRequestSchema,
) -> PostResponseBase[SlideResponseSchema]:
    request.validate_input()

    # Get image data either from base64 or URL
    if request.puzzle_image_b64:  # Process base64 image
        base64_data = request.puzzle_image_b64
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]

        # Decode base64 string to image data
        image_data = base64.b64decode(base64_data)

    else:  # Process image URL
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url=request.puzzle_image_url) as response:
                    if not response.ok:
                        error_text = await response.text()
                        msg = f"Error downloading image: HTTP {response.status} - {error_text}"
                        logger.error(msg)
                        raise HTTPException(status_code=400, detail=msg)

                    if not response.content_type.startswith("image/"):
                        msg = f"Error downloading image: HTTP {response.status} - {response.content_type}"
                        logger.error(msg)
                        raise HTTPException(status_code=400, detail=msg)

                    image_data = await response.read()

        except aiohttp.ClientError as e:
            msg = f"Error downloading image: {str(e)}"
            logger.error(msg)
            raise HTTPException(status_code=400, detail=msg)

    # Create a temporary file to store the image
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(image_data)

    try:
        box, confidence = recognizer.identify_gap(source=temp_file_path, show_result=True, verbose=True)

        result = SlideResponseSchema(
            status="successful" if confidence > 0.5 else "failed",
            x=box[0] - 8,
        )

        return create_response(data=result)

    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"Error identifying gap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        try:
            os.unlink(temp_file_path)
            logger.info(f"Temporary file removed: {temp_file_path}")
        except Exception as e:
            logger.error(f"Error removing temporary file: {e}")
