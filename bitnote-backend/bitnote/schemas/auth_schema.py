from pydantic import BaseModel, EmailStr

class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class google_LoginRequest(BaseModel):
    id_token: str