from pydantic import BaseModel


class SlideResponseSchema(BaseModel):
    status: str
    x: float
