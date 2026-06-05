from pydantic import BaseModel, Field, field_validator


class AuthCredentials(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=255)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("Username is required.")
        return username

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value:
            raise ValueError("Password is required.")
        return value


class AuthUserResponse(BaseModel):
    id: int
    username: str
    is_active: bool


class AuthResponse(BaseModel):
    user: AuthUserResponse
