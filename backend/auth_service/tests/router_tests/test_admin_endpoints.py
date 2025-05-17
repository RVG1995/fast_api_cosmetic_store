"""Tests for the admin endpoints using the TestClient approach."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock


# Import the FastAPI app and necessary modules
from main import app
import auth_utils
import admin_router

# Create a mock user for tests
def create_mock_user(id=1, email="user@example.com", is_active=True, is_admin=False, is_super_admin=False):
    """Create a mock user with specified attributes."""
    user = MagicMock()
    user.id = id
    user.email = email
    user.first_name = "Test"
    user.last_name = "User"
    user.is_active = is_active
    user.is_admin = is_admin
    user.is_super_admin = is_super_admin
    return user

# Create a mock admin user for tests
def create_mock_admin():
    """Create a mock admin user."""
    return create_mock_user(id=2, email="admin@example.com", is_admin=True)

# Create a mock super admin user for tests
def create_mock_super_admin():
    """Create a mock super admin user."""
    return create_mock_user(id=3, email="superadmin@example.com", is_admin=True, is_super_admin=True)

# Create a mock session factory
def create_mock_session():
    """Create a mock database session."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session

# Override dependencies for tests
@pytest.fixture
def test_client():
    """Create a test client with overridden dependencies."""
    # Create mock dependencies
    mock_user = create_mock_user()
    mock_admin = create_mock_admin()
    mock_super_admin = create_mock_super_admin()
    mock_session = create_mock_session()
    
    # Define async dependency functions that return mocks
    async def get_current_user_override():
        return mock_user
        
    async def get_admin_user_override():
        return mock_admin
    
    async def get_super_admin_user_override():
        return mock_super_admin
    
    async def get_session_override():
        return mock_session
    
    # Override service-key verification
    async def verify_service_key_override():
        return True
        
    # Override service JWT verification
    async def verify_service_jwt_override():
        return True
    
    # Save original dependencies
    original_dependencies = {}
    
    # Override dependencies
    app.dependency_overrides[auth_utils.get_current_user] = get_current_user_override
    app.dependency_overrides[auth_utils.get_admin_user] = get_admin_user_override
    app.dependency_overrides[auth_utils.get_super_admin_user] = get_super_admin_user_override
    app.dependency_overrides[admin_router.get_session] = get_session_override
    app.dependency_overrides[admin_router.verify_service_key] = verify_service_key_override
    app.dependency_overrides[admin_router.verify_service_jwt] = verify_service_jwt_override
    
    # Create test client
    client = TestClient(app)
    
    yield client, mock_session, mock_user, mock_admin, mock_super_admin
    
    # Restore original dependencies
    app.dependency_overrides.clear()

# Tests for admin endpoints
def test_get_all_users(test_client):
    """Test getting all users (admin access)."""
    client, mock_session, _, _, _ = test_client
    
    # Setup mock users for the response
    user1 = create_mock_user(id=1, email="user1@example.com")
    user2 = create_mock_admin()
    
    # Configure mock session to return users
    execute_result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = [user1, user2]
    execute_result.scalars.return_value = scalars_result
    mock_session.execute.return_value = execute_result
    
    # Make the request
    response = client.get(
        "/admin/users",
        headers={"Authorization": "Bearer fake_token"}
    )
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[0]["email"] == "user1@example.com"
    assert data[1]["id"] == 2
    assert data[1]["email"] == "admin@example.com"

def test_activate_user(test_client):
    """Test activating a user."""
    client, mock_session, _, _, _ = test_client
    
    # Create inactive user
    inactive_user = create_mock_user(is_active=False)
    
    # Mock UserModel.get_by_id to return the inactive user
    with patch("models.UserModel.get_by_id", return_value=inactive_user):
        # Make the request
        response = client.patch(
            "/admin/users/1/activate",
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Check the response
        assert response.status_code == 200
        assert "message" in response.json()
        assert inactive_user.email in response.json()["message"]
        
        # Check that the user was updated
        assert inactive_user.is_active is True
        assert inactive_user.activation_token is None
        mock_session.commit.assert_called_once()

def test_activate_user_not_found(test_client):
    """Test activating a non-existent user."""
    client, _, _, _, _ = test_client
    
    # Mock UserModel.get_by_id to return None (user not found)
    with patch("models.UserModel.get_by_id", return_value=None):
        # Make the request
        response = client.patch(
            "/admin/users/999/activate",
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Check the response
        assert response.status_code == 404
        assert response.json() == {"detail": "Пользователь не найден"}

def test_make_user_admin(test_client):
    """Test making a user an admin."""
    client, mock_session, _, _, _ = test_client
    
    # Create regular user
    regular_user = create_mock_user()
    
    # Mock UserModel.get_by_id to return the regular user
    with patch("models.UserModel.get_by_id", return_value=regular_user):
        # Make the request
        response = client.patch(
            "/admin/users/1/make-admin",
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Check the response
        assert response.status_code == 200
        assert "message" in response.json()
        assert regular_user.email in response.json()["message"]
        
        # Check that the user was updated
        assert regular_user.is_admin is True
        mock_session.commit.assert_called_once()

def test_remove_admin_rights(test_client):
    """Test removing admin rights from a user."""
    client, mock_session, _, _, _ = test_client
    
    # Create admin user who is not super admin
    admin_user = create_mock_admin()
    
    # Mock UserModel.get_by_id to return the admin user
    with patch("models.UserModel.get_by_id", return_value=admin_user):
        # Make the request
        response = client.patch(
            "/admin/users/2/remove-admin",
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Check the response
        assert response.status_code == 200
        assert "message" in response.json()
        assert admin_user.email in response.json()["message"]
        
        # Check that the user was updated
        assert admin_user.is_admin is False
        mock_session.commit.assert_called_once()

def test_remove_admin_rights_from_super_admin(test_client):
    """Test removing admin rights from a super admin (should fail)."""
    client, _, _, _, _ = test_client
    
    # Create super admin user
    super_admin = create_mock_super_admin()
    
    # Mock UserModel.get_by_id to return the super admin user
    with patch("models.UserModel.get_by_id", return_value=super_admin):
        # Make the request
        response = client.patch(
            "/admin/users/3/remove-admin",
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Check the response
        assert response.status_code == 400
        assert response.json() == {"detail": "Невозможно отозвать права администратора у суперадминистратора"}

def test_delete_user(test_client):
    """Test deleting a user."""
    client, mock_session, _, _, _ = test_client
    
    # Create regular user
    regular_user = create_mock_user()
    
    # Mock UserModel.get_by_id to return the regular user
    with patch("models.UserModel.get_by_id", return_value=regular_user):
        # Make the request
        response = client.delete(
            "/admin/users/1",
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Check the response
        assert response.status_code == 200
        assert "message" in response.json()
        assert regular_user.email in response.json()["message"]
        
        # Check that the user was deleted
        mock_session.delete.assert_called_once_with(regular_user)
        mock_session.commit.assert_called_once()

def test_check_admin_access(test_client):
    """Test checking admin access."""
    client, _, _, _, _ = test_client
    
    # Make the request
    response = client.get(
        "/admin/check-access",
        headers={"Authorization": "Bearer fake_token"}
    )
    
    # Check the response
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "У вас есть права администратора"}

def test_check_super_admin_access(test_client):
    """Test checking super admin access."""
    client, _, _, _, _ = test_client
    
    # Make the request
    response = client.get(
        "/admin/check-super-access",
        headers={"Authorization": "Bearer fake_token"}
    )
    
    # Check the response
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "У вас есть права суперадминистратора"}

def test_get_user_by_id(test_client):
    """Test getting a user by ID with service JWT."""
    client, _, _, _, _ = test_client
    
    # Create regular user
    user = create_mock_user()
    
    # Mock UserModel.get_by_id to return the user
    with patch("models.UserModel.get_by_id", return_value=user):
        # Make the request
        response = client.get(
            "/admin/users/1",
            headers={"Authorization": "Bearer service_token"}
        )
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["email"] == "user@example.com"

def test_get_user_by_id_not_found(test_client):
    """Test getting a non-existent user by ID."""
    client, _, _, _, _ = test_client
    
    # Mock UserModel.get_by_id to return None (user not found)
    with patch("models.UserModel.get_by_id", return_value=None):
        # Make the request
        response = client.get(
            "/admin/users/999",
            headers={"Authorization": "Bearer service_token"}
        )
        
        # Check the response
        assert response.status_code == 404
        assert response.json() == {"detail": "Пользователь не найден"} 