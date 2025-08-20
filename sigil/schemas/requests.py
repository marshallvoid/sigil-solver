from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field


class SlideRequestSchema(BaseModel):
    puzzle_image_b64: Optional[str] = Field(default=None, description="Base64 encoded image data")
    piece_image_b64: Optional[str] = Field(default=None, description="Base64 encoded image data")

    puzzle_image_url: Optional[str] = Field(default=None, description="URL to the puzzle image")
    piece_image_url: Optional[str] = Field(default=None, description="URL to the puzzle image")

    shrink_size: Optional[float] = Field(default=340.0, description="Shrink size of the puzzle image")

    def validate_input(self) -> None:
        if not self.puzzle_image_b64 and not self.puzzle_image_url:
            raise HTTPException(status_code=400, detail="Either puzzle_image_b64 or puzzle_image_url must be provided")
