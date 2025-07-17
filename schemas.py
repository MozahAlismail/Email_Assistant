from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


# ------- email log -------
class EmailLogCreate(SQLModel):
    user_input: str
    reply_to: Optional[str] = None
    context: Optional[str] = None
    length: Optional[int] = None
    tone: Optional[str] = None
    generated_email: str


class EmailLogRead(SQLModel):
    user_input: str
    reply_to: Optional[str]
    context: Optional[str]
    length: Optional[int]
    tone: Optional[str]
    generated_email: str

# ------- email -------
class EmailRequest(SQLModel):
    user_input: str
    reply_to: Optional[str] = None
    context: Optional[str] = None
    length: int = 120
    tone: str = "formal"

class EmailResponse(SQLModel):
    generated_email: str


