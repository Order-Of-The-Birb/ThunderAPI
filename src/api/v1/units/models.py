from pydantic import BaseModel, Field

class LocalizationModel(BaseModel):
    short: str
    long: str
