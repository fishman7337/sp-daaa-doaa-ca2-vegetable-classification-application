"""WTForms definitions for server-rendered routes."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import BooleanField, PasswordField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ApiForm(FlaskForm):
    """Base form class for API payload validation."""

    class Meta:
        """Disable CSRF for JSON/multipart API validation."""

        csrf = False


class LoginForm(ApiForm):
    """Login payload form for API validation."""

    username = StringField("Username", validators=[Optional(), Length(min=3, max=50)])
    email = StringField("Email", validators=[Optional(), Length(min=5, max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=3, max=128)])
    captcha_id = StringField("CaptchaId", validators=[Optional(), Length(min=8, max=64)])
    captcha_answer = StringField("CaptchaAnswer", validators=[Optional(), Length(min=1, max=64)])

    def validate(self, extra_validators=None):
        """Require at least one identifier and basic email shape when provided."""
        is_valid = super().validate(extra_validators=extra_validators)
        username = (self.username.data or "").strip()
        email = (self.email.data or "").strip()
        if not username and not email:
            self.username.errors.append("Either username or email is required")
            is_valid = False
        if email and "@" not in email:
            self.email.errors.append("Email is invalid")
            is_valid = False
        return is_valid


class RegisterForm(ApiForm):
    """Registration payload form for API validation."""

    username = StringField("Username", validators=[Optional(), Length(min=3, max=50)])
    name = StringField("Name", validators=[Optional(), Length(min=1, max=120)])
    email = StringField("Email", validators=[Optional(), Length(min=5, max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    agree_terms = BooleanField("AgreeTerms")
    captcha_id = StringField("CaptchaId", validators=[Optional(), Length(min=8, max=64)])
    captcha_answer = StringField("CaptchaAnswer", validators=[Optional(), Length(min=1, max=64)])

    def validate(self, extra_validators=None):
        """Require username/email and explicit terms agreement."""
        is_valid = super().validate(extra_validators=extra_validators)
        username = (self.username.data or "").strip()
        email = (self.email.data or "").strip()
        if not username and not email:
            self.username.errors.append("Either username or email is required")
            is_valid = False
        if email and "@" not in email:
            self.email.errors.append("Email is invalid")
            is_valid = False
        if not bool(self.agree_terms.data):
            self.agree_terms.errors.append("Please agree to the terms and conditions")
            is_valid = False
        return is_valid


class PredictForm(ApiForm):
    """Prediction payload form for API validation."""

    model_name = StringField("Model", validators=[DataRequired(), Length(min=1, max=120)])
    image = FileField("Image", validators=[FileRequired()])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=500)])
