from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from passlib.context import CryptContext

# Password hashing context with updated configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 72:
            raise ValueError('Password cannot be longer than 72 characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
    @validator('password')
    def validate_password_length(cls, v):
        if len(v) > 72:
            raise ValueError('Password cannot be longer than 72 characters')
        return v

class UserInDB(UserBase):
    id: str = Field(alias="_id")
    hashed_password: str
    date_created: datetime
    is_active: bool = True
    
    class Config:
        populate_by_name = True

class UserResponse(UserBase):
    id: str
    date_created: datetime
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None

# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Truncate password if needed (bcrypt has 72 byte limit)
        if len(plain_password.encode('utf-8')) > 72:
            plain_password = plain_password[:72]
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash a password"""
    try:
        # Truncate password if needed (bcrypt has 72 byte limit)
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Password hashing error: {e}")
        raise ValueError("Failed to hash password")
