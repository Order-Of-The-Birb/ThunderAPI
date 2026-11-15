from pydantic import BaseModel


class LocalizationModel(BaseModel):
    short: str
    long: str
