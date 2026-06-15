"""Tests para value objects del dominio."""
import pytest
from domain.value_objects.email import Email
from domain.value_objects.password import PasswordHash, PasswordPolicy
from domain.value_objects.oauth import OAuthProvider, OAuthLink


class TestEmail:
    def test_valid_email(self):
        email = Email("User@Example.com")
        assert email.value == "user@example.com"  # normalizado a lowercase

    def test_valid_email_with_plus(self):
        email = Email("user+tag@gmail.com")
        assert email.value == "user+tag@gmail.com"

    def test_invalid_email_no_at(self):
        with pytest.raises(ValueError, match="Invalid email"):
            Email("notanemail")

    def test_invalid_email_empty(self):
        with pytest.raises(ValueError):
            Email("")

    def test_invalid_email_spaces(self):
        with pytest.raises(ValueError):
            Email("user @example.com")

    def test_emails_equal(self):
        e1 = Email("test@example.com")
        e2 = Email("Test@Example.com")
        assert e1 == e2

    def test_email_hashable(self):
        s = {Email("a@b.com"), Email("a@b.com")}
        assert len(s) == 1

    def test_email_repr(self):
        email = Email("a@b.com")
        assert repr(email) == "Email(a@b.com)"


class TestPasswordPolicy:
    def test_valid_password(self):
        assert PasswordPolicy.validate("Str0ng!Pass") is True

    def test_too_short(self):
        assert PasswordPolicy.validate("Ab1!") is False

    def test_no_uppercase(self):
        assert PasswordPolicy.validate("str0ng!pass") is False  # needs uppercase

    def test_no_lowercase(self):
        assert PasswordPolicy.validate("STR0NG!PASS") is False  # needs lowercase

    def test_no_digit(self):
        assert PasswordPolicy.validate("Strong!Pass") is False

    def test_no_special_char(self):
        assert PasswordPolicy.validate("Str0ngPass") is False

    def test_minimum_valid(self):
        assert PasswordPolicy.validate("Abc1!def") is True  # 8 chars, has all


class TestPasswordHash:
    def test_create_and_verify(self):
        pw = PasswordHash.from_plain("Str0ng!Pass")
        assert isinstance(pw.value, str)
        assert len(pw.value) > 20
        assert pw.verify("Str0ng!Pass") is True

    def test_wrong_password(self):
        pw = PasswordHash.from_plain("Str0ng!Pass")
        assert pw.verify("WrongPass1!") is False

    def test_from_string(self):
        pw = PasswordHash("$2b$12$abcdefghijklmnopqrstuv")
        assert pw.value == "$2b$12$abcdefghijklmnopqrstuv"
        assert pw.verify("anything") is False  # hash inválido, no matchea


class TestOAuthProvider:
    def test_google_provider(self):
        assert OAuthProvider.GOOGLE.value == "google"

    def test_github_provider(self):
        assert OAuthProvider.GITHUB.value == "github"

    def test_from_string(self):
        assert OAuthProvider.from_string("google") == OAuthProvider.GOOGLE
        assert OAuthProvider.from_string("github") == OAuthProvider.GITHUB

    def test_from_string_invalid(self):
        with pytest.raises(ValueError):
            OAuthProvider.from_string("twitter")


class TestOAuthLink:
    def test_create_link(self):
        link = OAuthLink(provider=OAuthProvider.GOOGLE, provider_user_id="12345")
        assert link.provider == OAuthProvider.GOOGLE
        assert link.provider_user_id == "12345"

    def test_link_equality(self):
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc)
        l1 = OAuthLink(OAuthProvider.GOOGLE, "123", created_at=ts)
        l2 = OAuthLink(OAuthProvider.GOOGLE, "123", created_at=ts)
        assert l1 == l2
