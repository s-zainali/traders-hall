from pydantic import BaseModel, ConfigDict, EmailStr, Field
import uuid


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=24, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, max_length=64)


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str          # username or email
    password: str


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    status: str