from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None

class LoginResponse(BaseModel):
    success: bool
    message: str
    requires_mfa: bool = False

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str
