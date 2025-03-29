from pydantic import BaseModel
from typing import List

class DomainRegisterUserDetails(BaseModel):
    phone_number: str
    first_name: str
    last_name: str
    address: str
    city: str
    state: str
    zip_code: str
    country: str

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