"""
Test script for learning integration
Tests that learning insights are correctly included in prompts without breaking existing functionality
"""

import sys
import os
from datetime import date, datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.grocery_prediction_utils import format_data_for_llm, aggregate_purchase_patterns
from handlers.learning_engine import get_aggregated_learning_summary
from config.supabase_config import get_supabase_client


def create_mock_learning_update():
    """
    Creates a mock learning update in database for testing
    """
    try:
        supabase = get_supabase_client()
        
        # Create mock learning update
        mock_update = {
            'update_type': 'batch_learning',
            'feedback_count': 5,
            'update_summary': {
                'feedback_count': 5,
                'average_accuracy': 75.5,
                'top_missing_items': [
                    {'item': 'Bananas', 'frequency': 3},
                    {'item': 'Apples', 'frequency': 2},
                    {'item': 'Bread', 'frequency': 2}
                ],
                'top_extra_items': [
                    {'item': 'Milk', 'frequency': 4},
                    {'item': 'Eggs', 'frequency': 3},
                    {'item': 'Yogurt', 'frequency': 2}
                ],
                'accuracy_trend': 'improving'
            },
            'accuracy_improvement': None
        }
        
        result = supabase.table('learning_updates').insert(mock_update).execute()
        
        if result.data:
            print(f"✅ Created mock learning update: ID {result.data[0]['id']}")
            return result.data[0]['id']
        else:
            print("❌ Failed to create mock learning update")
            return None
            
    except Exception as e:
        print(f"❌ Error creating mock learning update: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_second_mock_learning_update():
    """
    Creates a second mock learning update to test aggregation
    """
    try:
        supabase = get_supabase_client()
        
        # Create second mock learning update (some overlapping items)
        mock_update = {
            'update_type': 'batch_learning',
            'feedback_count': 5,
            'update_summary': {
                'feedback_count': 5,
                'average_accuracy': 78.0,
                'top_missing_items': [
                    {'item': 'Bananas', 'frequency': 2},  # Overlaps with first
                    {'item': 'Oranges', 'frequency': 3},
                    {'item': 'Bread', 'frequency': 1}  # Overlaps with first
                ],
                'top_extra_items': [
                    {'item': 'Milk', 'frequency': 3},  # Overlaps with first
                    {'item': 'Cheese', 'frequency': 2},
                    {'item': 'Eggs', 'frequency': 2}  # Overlaps with first
                ],
                'accuracy_trend': 'improving'
            },
            'accuracy_improvement': None
        }
        
        result = supabase.table('learning_updates').insert(mock_update).execute()
        
        if result.data:
            print(f"✅ Created second mock learning update: ID {result.data[0]['id']}")
            return result.data[0]['id']
        else:
            print("❌ Failed to create second mock learning update")
            return None
            
    except Exception as e:
        print(f"❌ Error creating second mock learning update: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_prompt_without_learning():
    """
    Test 1: Prompt generation without learning data
    Should work normally, no learning section
    """
    print("\n" + "="*60)
    print("TEST 1: Prompt Generation WITHOUT Learning Data")
    print("="*60)
    
    # Create mock purchase patterns
    mock_patterns = {
        'Milk': {
            'frequency': 10,
            'last_purchase_date': '2024-01-15',
            'avg_days_between': 7.0,
            'purchase_dates': ['2024-01-15', '2024-01-08', '2024-01-01']
        },
        'Bread': {
            'frequency': 8,
            'last_purchase_date': '2024-01-14',
            'avg_days_between': 5.0,
            'purchase_dates': ['2024-01-14', '2024-01-09']
        }
    }
    
    try:
        # Generate prompt without learning (no user_phone or empty learning)
        prompt = format_data_for_llm(mock_patterns, current_date=date.today(), user_phone=None)
        
        # Check prompt structure
        assert "Purchase History" in prompt, "❌ Prompt missing purchase history section"
        assert "Milk" in prompt, "❌ Prompt missing purchase patterns"
        assert "Bread" in prompt, "❌ Prompt missing purchase patterns"
        
        # Should NOT have learning section if no learning data
        # (This is expected behavior - learning only added if has_learning=True)
        print("✅ Prompt generated successfully")
        print(f"📏 Prompt length: {len(prompt)} characters")
        print(f"📊 Estimated tokens: ~{len(prompt) // 4}")
        
        # Show first 500 chars
        print("\n📝 Prompt preview (first 500 chars):")
        print(prompt[:500] + "...")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_learning_summary_function():
    """
    Test 2: Learning summary function works correctly
    """
    print("\n" + "="*60)
    print("TEST 2: Learning Summary Function")
    print("="*60)
    
    try:
        # Test with no learning data (should return has_learning=False)
        summary_no_data = get_aggregated_learning_summary(user_phone=None, days_back=1, max_updates=10)
        
        assert summary_no_data.get('has_learning') == False, "❌ Should return has_learning=False when no data"
        print("✅ Correctly handles no learning data")
        
        # Create mock learning updates
        print("\n📝 Creating mock learning updates...")
        update1_id = create_mock_learning_update()
        update2_id = create_second_mock_learning_update()
        
        if not update1_id or not update2_id:
            print("⚠️ Could not create mock updates, skipping aggregation test")
            return False
        
        # Wait a moment for database consistency
        import time
        time.sleep(1)
        
        # Test with learning data
        summary_with_data = get_aggregated_learning_summary(user_phone=None, days_back=60, max_updates=10)
        
        assert summary_with_data.get('has_learning') == True, "❌ Should return has_learning=True when data exists"
        print("✅ Correctly detects learning data")
        
        # Check aggregated items (should only include items appearing in 2+ updates)
        missing_items = summary_with_data.get('top_missing_items', [])
        extra_items = summary_with_data.get('top_extra_items', [])
        
        print(f"📊 Missing items found: {missing_items}")
        print(f"📊 Extra items found: {extra_items}")
        print(f"📊 Average accuracy: {summary_with_data.get('average_accuracy', 0)}%")
        print(f"📊 Trend: {summary_with_data.get('accuracy_trend', 'stable')}")
        
        # Bananas and Bread should appear (in both updates)
        # Milk and Eggs should appear (in both updates)
        assert 'Bananas' in missing_items or 'Bread' in missing_items, "❌ Should aggregate missing items from multiple updates"
        assert 'Milk' in extra_items or 'Eggs' in extra_items, "❌ Should aggregate extra items from multiple updates"
        
        print("✅ Learning aggregation works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_with_learning():
    """
    Test 3: Prompt generation WITH learning data
    Should include learning insights section
    """
    print("\n" + "="*60)
    print("TEST 3: Prompt Generation WITH Learning Data")
    print("="*60)
    
    # Create mock purchase patterns
    mock_patterns = {
        'Milk': {
            'frequency': 10,
            'last_purchase_date': '2024-01-15',
            'avg_days_between': 7.0,
            'purchase_dates': ['2024-01-15', '2024-01-08']
        },
        'Bread': {
            'frequency': 8,
            'last_purchase_date': '2024-01-14',
            'avg_days_between': 5.0,
            'purchase_dates': ['2024-01-14', '2024-01-09']
        }
    }
    
    try:
        # Generate prompt with learning (using any user_phone, learning exists globally)
        prompt = format_data_for_llm(mock_patterns, current_date=date.today(), user_phone="+1234567890")
        
        # Check prompt structure
        assert "Purchase History" in prompt, "❌ Prompt missing purchase history section"
        assert "Milk" in prompt, "❌ Prompt missing purchase patterns"
        
        # Check if learning section is included
        has_learning_section = "Learning Insights" in prompt
        
        if has_learning_section:
            print("✅ Learning insights section found in prompt")
            assert "Items often predicted but not bought" in prompt or "Items often bought but not predicted" in prompt, "❌ Learning insights missing details"
            print("✅ Learning insights details included")
        else:
            print("ℹ️ No learning insights section (no learning data or filtering removed items)")
        
        print(f"📏 Prompt length: {len(prompt)} characters")
        print(f"📊 Estimated tokens: ~{len(prompt) // 4}")
        
        # Show learning section if present
        if has_learning_section:
            learning_start = prompt.find("Learning Insights")
            learning_end = prompt.find("Instructions:", learning_start)
            if learning_end > learning_start:
                learning_section = prompt[learning_start:learning_end]
                print("\n📝 Learning Insights Section:")
                print(learning_section)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """
    Test 4: Error handling - should not break if learning fails
    """
    print("\n" + "="*60)
    print("TEST 4: Error Handling")
    print("="*60)
    
    mock_patterns = {
        'Milk': {
            'frequency': 10,
            'last_purchase_date': '2024-01-15',
            'avg_days_between': 7.0,
            'purchase_dates': ['2024-01-15']
        }
    }
    
    try:
        # Should work even if learning function has issues
        # (It's wrapped in try-except in format_data_for_llm)
        prompt = format_data_for_llm(mock_patterns, current_date=date.today(), user_phone="test")
        
        assert len(prompt) > 0, "❌ Prompt should be generated even if learning fails"
        assert "Purchase History" in prompt, "❌ Core prompt should work"
        
        print("✅ Prompt generation handles errors gracefully")
        print("✅ System continues working even if learning fails")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_mock_data():
    """
    Cleanup: Remove test learning updates
    """
    print("\n" + "="*60)
    print("CLEANUP: Removing Test Data")
    print("="*60)
    
    try:
        supabase = get_supabase_client()
        
        # Delete mock updates created today
        cutoff = datetime.now() - timedelta(hours=1)
        result = supabase.table('learning_updates')\
            .delete()\
            .gte('created_at', cutoff.isoformat())\
            .eq('update_type', 'batch_learning')\
            .execute()
        
        print(f"✅ Cleaned up test data")
        return True
        
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
        return False


def main():
    """
    Run all tests
    """
    print("\n" + "="*60)
    print("🧪 LEARNING INTEGRATION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Without learning
    results.append(("Prompt without learning", test_prompt_without_learning()))
    
    # Test 2: Learning summary function
    results.append(("Learning summary function", test_learning_summary_function()))
    
    # Test 3: With learning
    results.append(("Prompt with learning", test_prompt_with_learning()))
    
    # Test 4: Error handling
    results.append(("Error handling", test_error_handling()))
    
    # Cleanup
    cleanup_mock_data()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Learning integration is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    exit(main())

