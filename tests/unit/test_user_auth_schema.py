from uuid import uuid4

import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.auth_schema import UserLoginRequest
from sidebrain_back.schemas.user_schema import (
    PasswordUpdateRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)


def test_registration_normalizes_name_and_email():
    payload = UserRegisterRequest(
        name="  Maria Silva  ",
        email="  MARIA@Example.COM ",
        password="12345678",
    )

    assert payload.name == "Maria Silva"
    assert str(payload.email) == "maria@example.com"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": " ", "email": "a@example.com", "password": "12345678"},
        {"name": "A", "email": "inválido", "password": "12345678"},
        {"name": "A", "email": "a@example.com", "password": "curta"},
        {
            "name": "A",
            "email": "a@example.com",
            "password": "12345678",
            "usr_id": str(uuid4()),
        },
    ],
)
def test_registration_rejects_invalid_or_extra_fields(payload):
    with pytest.raises(ValidationError):
        UserRegisterRequest(**payload)


def test_login_normalizes_email_and_forbids_extra_fields():
    payload = UserLoginRequest(email=" A@Example.com ", password="12345678")
    assert str(payload.email) == "a@example.com"
    with pytest.raises(ValidationError):
        UserLoginRequest(
            email="a@example.com",
            password="12345678",
            token="proibido",
        )


def test_profile_update_requires_at_least_one_non_null_field():
    for payload in ({}, {"name": None}, {"email": None}):
        with pytest.raises(ValidationError):
            UserUpdateRequest(**payload)


def test_password_update_uses_public_camel_case_contract():
    payload = PasswordUpdateRequest(
        currentPassword="senha-antiga",
        newPassword="senha-nova-123",
    )
    assert payload.current_password == "senha-antiga"
    assert payload.new_password == "senha-nova-123"


def test_user_response_maps_physical_fields_without_exposing_them():
    user_id = uuid4()

    class UserRecord:
        usr_id = user_id
        usr_name = "Maria"
        usr_email = "maria@example.com"
        usr_password_hash = "não pode aparecer"

    body = UserResponse.model_validate(UserRecord()).model_dump(
        by_alias=True,
        mode="json",
    )
    assert body == {
        "id": str(user_id),
        "name": "Maria",
        "email": "maria@example.com",
    }
