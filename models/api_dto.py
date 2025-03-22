from pydantic import BaseModel
from typing import List

class DomainRegistrationRequest(BaseModel):
    domain: str
    years: int = 1

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class DomainsCheckRequest(BaseModel):
    domain: str