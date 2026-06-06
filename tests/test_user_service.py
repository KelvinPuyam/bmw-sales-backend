"""
Unit tests for app/services/user_service.py
Tests profile update, password change, role assignment.
"""

import pytest

from app.services.user_service import update_profile, change_password, assign_role, get_all_users
from app.schemas import UserUpdateRequest, ChangePasswordRequest, AssignRoleRequest
from app.models import RoleEnum
from app.exceptions.base import EmailTakenError, InvalidCredentialsError, UserNotFoundError


class TestGetAllUsers:
    def test_returns_empty_list_when_no_users(self, db):
        assert get_all_users(db) == []

    def test_returns_all_users(self, db, seed_user, seed_admin):
        users = get_all_users(db)
        usernames = {u.username for u in users}
        assert "testuser" in usernames
        assert "adminuser" in usernames

    def test_ordered_newest_first(self, db, seed_user, seed_admin):
        users = get_all_users(db)
        # admin was seeded after user, so admin should be first
        assert users[0].username == "adminuser"


class TestUpdateProfile:
    def test_updates_fields(self, db, seed_user):
        user, _ = seed_user
        payload = UserUpdateRequest(
            first_name="Updated",
            last_name="Name",
            email="updated@example.com",
        )
        updated = update_profile(payload, user, db)
        assert updated.first_name == "Updated"
        assert updated.email == "updated@example.com"

    def test_email_conflict_with_other_user_raises(self, db, seed_user, seed_admin):
        user, _ = seed_user
        admin, _ = seed_admin
        # Try to take the admin's email
        payload = UserUpdateRequest(
            first_name="Test",
            last_name="User",
            email=admin.email,
        )
        with pytest.raises(EmailTakenError):
            update_profile(payload, user, db)

    def test_keeping_own_email_does_not_raise(self, db, seed_user):
        user, _ = seed_user
        payload = UserUpdateRequest(
            first_name="Same",
            last_name="Email",
            email=user.email,  # same as current
        )
        updated = update_profile(payload, user, db)
        assert updated.email == user.email


class TestChangePassword:
    def test_valid_password_change(self, db, seed_user):
        user, old_pass = seed_user
        payload = ChangePasswordRequest(old_password=old_pass, new_password="newpass456")
        change_password(payload, user, db)  # should not raise

    def test_new_password_is_stored_hashed(self, db, seed_user):
        from app.security import verify_password
        user, old_pass = seed_user
        payload = ChangePasswordRequest(old_password=old_pass, new_password="newpass456")
        change_password(payload, user, db)
        assert verify_password("newpass456", user.hashed_password)

    def test_wrong_old_password_raises(self, db, seed_user):
        user, _ = seed_user
        payload = ChangePasswordRequest(old_password="wrongpass", new_password="newpass456")
        with pytest.raises(InvalidCredentialsError):
            change_password(payload, user, db)


class TestAssignRole:
    def test_promotes_user_to_admin(self, db, seed_user):
        user, _ = seed_user
        payload = AssignRoleRequest(role=RoleEnum.admin)
        updated = assign_role(user.id, payload, db)
        assert updated.role == RoleEnum.admin

    def test_demotes_admin_to_user(self, db, seed_admin):
        admin, _ = seed_admin
        payload = AssignRoleRequest(role=RoleEnum.user)
        updated = assign_role(admin.id, payload, db)
        assert updated.role == RoleEnum.user

    def test_nonexistent_user_raises(self, db):
        payload = AssignRoleRequest(role=RoleEnum.admin)
        with pytest.raises(UserNotFoundError):
            assign_role(99999, payload, db)