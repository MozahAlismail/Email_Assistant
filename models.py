from sqlmodel import SQLModel, Field
from typing import Optional

class EmailLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_input: str = Field(max_length=1000)
    reply_to: Optional[str] = Field(default=None, max_length=500)
    context: Optional[str] = Field(default=None, max_length=1000)
    length: Optional[int] = Field(default=None)
    tone: str = Field(max_length=100)
    generated_email: str = Field(max_length=5000)  # Allow up to 5000 characters for email content
