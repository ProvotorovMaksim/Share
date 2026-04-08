from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    telegram_id: int
    username: str | None = None
    password: str

class UserLogin(BaseModel):
    telegram_id: int
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"