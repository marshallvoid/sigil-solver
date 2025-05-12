import os
import base64
import tempfile
from typing import Optional
from contextlib import asynccontextmanager
from loguru import logger
import httpx

from dishka.integrations.fastapi import (
    FromDishka,
    FastapiProvider,
    inject_sync,
    setup_dishka,
)
from dishka import make_container
from fastapi import APIRouter, FastAPI, HTTPException

from provider import RecognizerProvider
from recognizer import Recognizer
from pydantic import BaseModel, Field
from PIL import Image

router = APIRouter()

class SlideResponseModel(BaseModel):
    status: str
    box: list
    confidence: float
    slideXProportion: float
    imageWidth: int
    imageHeight: int
    x: float
    x1: float
    slideDistance: float


class SlideRequestModel(BaseModel):
    pieceImageB64: Optional[str] = Field(default=None, description="Base64 encoded image data")
    puzzleImageB64: Optional[str] = Field(default=None, description="Base64 encoded image data")

    pieceImageUrl: Optional[str] = Field(default=None, description="URL to the puzzle image")
    puzzleImageUrl: Optional[str] = Field(default=None, description="URL to the puzzle image")

    marginLeft: Optional[float] = Field(default=9.0, description="Left coordinate of the puzzle image")
    shrinkSize: Optional[float] = Field(default=340.0, description="Shrink size of the puzzle image")
    pieceShrinkWidth: Optional[float] = Field(default=67.75, description="Width of the puzzle piece")
    
    # Piece padding values
    piecePaddingLeft: Optional[float] = Field(default=7.0, description="Left padding of the piece image")
    piecePaddingRight: Optional[float] = Field(default=17.0, description="Right padding of the piece image")


    class Config:
        schema_extra = {
            "example": {
                "puzzleImageB64": "data:image/jpeg;base64,/9j/4AAQSkZJRgAB...",
                "puzzleImageUrl": "https://example.com/captcha.jpg"
            }
        }
        
    def validate_input(self):
        """Validate that at least one image source is provided"""
        if not self.puzzleImageB64 and not self.puzzleImageUrl:
            raise HTTPException(
                status_code=400,
                detail="Either puzzleImageB64 or puzzleImageUrl must be provided"
            )

@router.post("/slide", response_model=SlideResponseModel)
@inject_sync
async def solve_slide_captcha(
    recognizer: FromDishka[Recognizer],
    request: SlideRequestModel,
) -> SlideResponseModel:
    logger.info("Processing captcha slide request")
    
    # Validate that at least one image source is provided
    request.validate_input()
    
    # Get image data either from base64 or URL
    if request.puzzleImageB64:
        # Process base64 image
        logger.debug("Processing base64 image")
        base64_data = request.puzzleImageB64
        if ',' in base64_data:
            base64_data = base64_data.split(',', 1)[1]
        
        # Decode base64 string to image data
        image_data = base64.b64decode(base64_data)
    else:
        # Process image URL
        logger.debug(f"Downloading image from URL: {request.puzzleImageUrl}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(request.puzzleImageUrl)
                response.raise_for_status()
                image_data = response.content
        except httpx.HTTPError as e:
            logger.error(f"Error downloading image: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to download image from URL: {str(e)}"
            )
    
    # Create a temporary file to store the image
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(image_data)
    
    try:
        # Use the temporary file path as source
        logger.debug(f"Processing image saved at: {temp_file_path}")
        box, confidence = recognizer.identify_gap(
            source=temp_file_path, 
            show_result=True, 
            verbose=True
        )
        
        # Calculate slideXProportion based on box x-coordinate and image width
        with Image.open(temp_file_path) as img:
            image_width = img.width
            image_height = img.height

            x1 = box[0] - 8

            # Get x-coordinate (center of the box) relative to total width
            slide_x_proportion = (box[0] - 8) / image_width
            
            # Calculate actual slide distance considering shrink factor, margin and piece width
            original_to_ui_ratio = request.shrinkSize / image_width

            slide_distance = x1 * request.shrinkSize/image_width
            
            logger.debug(f"Image dimensions: {image_width}x{image_height}, Proportion: {slide_x_proportion}")
            logger.debug(f"Shrink size: {request.shrinkSize}, Ratio: {original_to_ui_ratio}, marginLeft: {request.marginLeft}")
            logger.debug(f"Original padding - Left: {request.piecePaddingLeft}, Right: {request.piecePaddingRight}")
            logger.debug(f"Final slide distance: {slide_distance}")
        
        # Log detected gap box coordinates and confidence
        logger.debug(f"Detected gap box: {box}, confidence: {confidence}")
        return SlideResponseModel(
            box=box,
            x=box[0],
            x1=x1,
            confidence=confidence,
            slideXProportion=slide_x_proportion,
            slideDistance=slide_distance,
            imageWidth=image_width,
            imageHeight=image_height,
            status="success" if confidence > 0.5 else "failed"
        )
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            logger.debug(f"Temporary file removed: {temp_file_path}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    app.state.dishka_container.close()

app = FastAPI(lifespan=lifespan)
app.include_router(router)
container = make_container(RecognizerProvider(), FastapiProvider())
setup_dishka(container=container, app=app)
