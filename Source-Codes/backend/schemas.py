"""Pydantic request schemas for backend API payload validation."""

from pydantic import BaseModel, Field, model_validator


class LoginRequest(BaseModel):
    """Login payload supporting username or email identifiers."""

    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    password: str = Field(min_length=3, max_length=128)
    captcha_id: str | None = Field(default=None, min_length=8, max_length=64)
    captcha_answer: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_identifier(self):
        """Ensure at least one login identifier is provided."""
        if not self.username and not self.email:
            raise ValueError("Either username or email is required")
        return self


class RegisterRequest(BaseModel):
    """Registration payload supporting username or email sign-up."""

    username: str | None = Field(default=None, min_length=3, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    agree_terms: bool = Field(default=False)
    captcha_id: str | None = Field(default=None, min_length=8, max_length=64)
    captcha_answer: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_identifier(self):
        """Ensure at least one registration identifier is provided."""
        if not self.username and not self.email:
            raise ValueError("Either username or email is required")
        if not self.agree_terms:
            raise ValueError("Please agree to the terms and conditions")
        return self


class OtpVerifyRequest(BaseModel):
    """OTP verification request payload."""

    otp_session: str = Field(min_length=8, max_length=64)
    otp_code: str = Field(min_length=4, max_length=12)


class OtpResendRequest(BaseModel):
    """OTP resend request payload."""

    otp_session: str = Field(min_length=8, max_length=64)


class ProfileUpdateRequest(BaseModel):
    """User profile update payload."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    avatar: str | None = Field(default=None, min_length=1, max_length=512)


class PasswordChangeRequest(BaseModel):
    """Password change payload."""

    current_password: str = Field(min_length=3, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordForgotRequest(BaseModel):
    """Password reset-link request payload."""

    email: str = Field(min_length=5, max_length=255)


class PasswordResetRequest(BaseModel):
    """Password reset completion payload."""

    reset_token: str = Field(min_length=8, max_length=128)
    reset_code: str = Field(min_length=8, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)
