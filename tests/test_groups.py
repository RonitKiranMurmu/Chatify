"""
Group chat tests
"""
import pytest
from app.models import Group, User


@pytest.fixture
def test_users(client):
    """Create multiple test users"""
    users = [
        {
            'username': 'alice',
            'password': 'Alice1234',
            'identity_pub': 'alice_identity_pub',
            'signed_prekey_pub': 'alice_signed_prekey',
            'signed_prekey_sig': 'alice_signature',
            'one_time_prekeys': [{'id': 'opk1', 'publicKey': 'alice_opk_1'}]
        },
        {
            'username': 'bob',
            'password': 'Bob1234',
            'identity_pub': 'bob_identity_pub',
            'signed_prekey_pub': 'bob_signed_prekey',
            'signed_prekey_sig': 'bob_signature',
            'one_time_prekeys': [{'id': 'opk1', 'publicKey': 'bob_opk_1'}]
        },
        {
            'username': 'charlie',
            'password': 'Charlie1234',
            'identity_pub': 'charlie_identity_pub',
            'signed_prekey_pub': 'charlie_signed_prekey',
            'signed_prekey_sig': 'charlie_signature',
            'one_time_prekeys': [{'id': 'opk1', 'publicKey': 'charlie_opk_1'}]
        }
    ]
    
    for user in users:
        client.post('/auth/register', json=user)
    
    return users


class TestGroupCreation:
    """Test group creation"""
    
    def test_create_group(self, client, test_users):
        """Test creating a new group"""
        admin = test_users[0]
        
        # Login as admin
        client.post('/auth/login', json={
            'username': admin['username'],
            'password': admin['password']
        })
        
        # Create group
        group_data = {
            'name': 'Test Group',
            'members': [test_users[1]['username'], test_users[2]['username']],
            'encrypted_group_keys': {
                test_users[1]['username']: {'ciphertext': 'enc_key_bob', 'iv': 'iv_bob'},
                test_users[2]['username']: {'ciphertext': 'enc_key_charlie', 'iv': 'iv_charlie'}
            }
        }
        
        response = client.post('/group/create', json=group_data)
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'group_id' in data
        assert data['name'] == 'Test Group'
    
    def test_create_group_empty_name(self, client, test_users):
        """Test creating group with empty name"""
        admin = test_users[0]
        
        # Login
        client.post('/auth/login', json={
            'username': admin['username'],
            'password': admin['password']
        })
        
        # Create group with empty name
        group_data = {
            'name': '',
            'members': [test_users[1]['username']],
            'encrypted_group_keys': {
                test_users[1]['username']: {'ciphertext': 'enc_key', 'iv': 'iv'}
            }
        }
        
        response = client.post('/group/create', json=group_data)
        assert response.status_code == 400
    
    def test_create_group_no_members(self, client, test_users):
        """Test creating group with no members"""
        admin = test_users[0]
        
        # Login
        client.post('/auth/login', json={
            'username': admin['username'],
            'password': admin['password']
        })
        
        # Create group with no members
        group_data = {
            'name': 'Empty Group',
            'members': [],
            'encrypted_group_keys': {}
        }
        
        response = client.post('/group/create', json=group_data)
        assert response.status_code == 400


class TestGroupMembership:
    """Test group membership operations"""
    
    def test_get_user_groups(self, client, test_users):
        """Test retrieving user's groups"""
        admin = test_users[0]
        
        # Login as admin
        client.post('/auth/login', json={
            'username': admin['username'],
            'password': admin['password']
        })
        
        # Create a group
        group_data = {
            'name': 'My Group',
            'members': [test_users[1]['username']],
            'encrypted_group_keys': {
                test_users[1]['username']: {'ciphertext': 'enc_key', 'iv': 'iv'}
            }
        }
        client.post('/group/create', json=group_data)
        
        # Get groups
        response = client.get('/group/list')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'groups' in data
        assert len(data['groups']) > 0
    
    def test_add_member_to_group(self, client, test_users):
        """Test adding a member to existing group"""
        admin = test_users[0]
        
        # Login and create group
        client.post('/auth/login', json={
            'username': admin['username'],
            'password': admin['password']
        })
        
        group_data = {
            'name': 'Test Group',
            'members': [test_users[1]['username']],
            'encrypted_group_keys': {
                test_users[1]['username']: {'ciphertext': 'enc_key', 'iv': 'iv'}
            }
        }
        response = client.post('/group/create', json=group_data)
        group_id = response.get_json()['group_id']
        
        # Add new member
        add_member_data = {
            'username': test_users[2]['username'],
            'encrypted_group_key': {'ciphertext': 'enc_key_charlie', 'iv': 'iv_charlie'}
        }
        
        response = client.post(f'/group/{group_id}/add-member', json=add_member_data)
        assert response.status_code == 200
    
    def test_remove_member_from_group(self, client, test_users):
        """Test removing a member from group"""
        admin = test_users[0]
        
        # Login and create group
        client.post('/auth/login', json={
            'username': admin['username'],
            'password': admin['password']
        })
        
        group_data = {
            'name': 'Test Group',
            'members': [test_users[1]['username'], test_users[2]['username']],
            'encrypted_group_keys': {
                test_users[1]['username']: {'ciphertext': 'enc_key_bob', 'iv': 'iv_bob'},
                test_users[2]['username']: {'ciphertext': 'enc_key_charlie', 'iv': 'iv_charlie'}
            }
        }
        response = client.post('/group/create', json=group_data)
        group_id = response.get_json()['group_id']
        
        # Remove member
        remove_data = {
            'username': test_users[2]['username'],
            'new_encrypted_keys': {
                test_users[1]['username']: {'ciphertext': 'new_key_bob', 'iv': 'new_iv_bob'}
            }
        }
        
        response = client.post(f'/group/{group_id}/remove-member', json=remove_data)
        assert response.status_code == 200


class TestGroupPermissions:
    """Test group admin permissions"""
    
    def test_non_admin_cannot_add_member(self, client, test_users):
        """Test that non-admin cannot add members"""
        admin = test_users[0]
        member = test_users[1]
        
        # Login as admin and create group
        client.post('/auth/login', json={
            'username': admin['username'],
            'password': admin['password']
        })
        
        group_data = {
            'name': 'Test Group',
            'members': [member['username']],
            'encrypted_group_keys': {
                member['username']: {'ciphertext': 'enc_key', 'iv': 'iv'}
            }
        }
        response = client.post('/group/create', json=group_data)
        group_id = response.get_json()['group_id']
        
        # Logout and login as member
        client.post('/auth/logout')
        client.post('/auth/login', json={
            'username': member['username'],
            'password': member['password']
        })
        
        # Try to add member (should fail)
        add_member_data = {
            'username': test_users[2]['username'],
            'encrypted_group_key': {'ciphertext': 'enc_key', 'iv': 'iv'}
        }
        
        response = client.post(f'/group/{group_id}/add-member', json=add_member_data)
        assert response.status_code == 403


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
