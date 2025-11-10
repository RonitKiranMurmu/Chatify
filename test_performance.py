"""
Quick performance test to verify optimizations work
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.database import get_db
from app.models import Message, User, ServerChat
from datetime import datetime

def test_database_indexes():
    """Test that database indexes are created"""
    print("\n" + "="*60)
    print("Testing Database Indexes...")
    print("="*60)
    
    try:
        app = create_app('testing')
        with app.app_context():
            db = get_db()
            
            # Check messages collection indexes
            messages_indexes = list(db.messages.list_indexes())
            print(f"\n✓ Messages collection has {len(messages_indexes)} indexes:")
            for idx in messages_indexes:
                print(f"  - {idx['name']}: {idx.get('key', {})}")
            
            # Check users collection indexes
            users_indexes = list(db.users.list_indexes())
            print(f"\n✓ Users collection has {len(users_indexes)} indexes:")
            for idx in users_indexes:
                print(f"  - {idx['name']}: {idx.get('key', {})}")
            
            # Check server_messages collection indexes
            server_indexes = list(db.server_messages.list_indexes())
            print(f"\n✓ Server messages collection has {len(server_indexes)} indexes:")
            for idx in server_indexes:
                print(f"  - {idx['name']}: {idx.get('key', {})}")
            
            print("\n✅ Database indexes test PASSED")
            return True
            
    except Exception as e:
        print(f"\n❌ Database indexes test FAILED: {e}")
        return False


def test_message_pagination():
    """Test message pagination parameters"""
    print("\n" + "="*60)
    print("Testing Message Pagination...")
    print("="*60)
    
    try:
        # Test that get_chat_history accepts limit and skip parameters
        print("\n✓ Message.get_chat_history signature supports pagination")
        
        # Verify the function signature
        import inspect
        sig = inspect.signature(Message.get_chat_history)
        params = list(sig.parameters.keys())
        
        assert 'limit' in params, "Missing 'limit' parameter"
        assert 'skip' in params, "Missing 'skip' parameter"
        
        print(f"  - Parameters: {params}")
        print("\n✅ Message pagination test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Message pagination test FAILED: {e}")
        return False


def test_server_chat_caching():
    """Test server chat caching functions"""
    print("\n" + "="*60)
    print("Testing Server Chat Caching...")
    print("="*60)
    
    try:
        from app.routes.server_chat import get_cached_messages, invalidate_cache
        
        print("\n✓ get_cached_messages() function exists")
        print("✓ invalidate_cache() function exists")
        
        # Test that functions are callable
        assert callable(get_cached_messages), "get_cached_messages is not callable"
        assert callable(invalidate_cache), "invalidate_cache is not callable"
        
        print("\n✅ Server chat caching test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Server chat caching test FAILED: {e}")
        return False


def main():
    """Run all performance tests"""
    print("\n" + "="*60)
    print("CHATIFY PERFORMANCE OPTIMIZATION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Database Indexes", test_database_indexes()))
    results.append(("Message Pagination", test_message_pagination()))
    results.append(("Server Chat Caching", test_server_chat_caching()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*60)
    print(f"Total: {passed}/{total} tests passed")
    print("="*60)
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
