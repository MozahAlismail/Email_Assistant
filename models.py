from sqlmodel import SQLModel, Field
from typing import Optional

class EmailLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_input: str
    reply_to: Optional[str] = Field(default=None)
    context: Optional[str] = Field(default=None)
    length: Optional[int] = Field(default=None)
    tone: str
    generated_email: str
