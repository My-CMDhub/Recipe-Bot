"""
Feedback processing handler
Handles comparing predictions with actual purchases and calculating accuracy
"""

from config.supabase_config import get_supabase_client
from utils.receipt_storage import get_receipt_items_for_receipts




def calculate_accuracy(predicted_items: list, actual_items: list) -> dict:
    """
    Calculates accuracy by comparing predicted items with actual purchased items
    
    Process:
    1. Normalize item names (case-insensitive comparison)
    2. Find matched items (in both lists)
    3. Find missing items (predicted but not bought)
    4. Find extra items (bought but not predicted)
    5. Calculate match percentage
    
    Args:
        predicted_items: List of predicted item names
        actual_items: List of actual purchased item names
        
    Returns:
        dict: {
            'match_percentage': 85.5,
            'matched_items': ['Milk', 'Bread'],
            'missing_items': ['Eggs'],
            'extra_items': ['Cheese']
        }
    """
    try:
        # Normalize items (lowercase for comparison)
        predicted_normalized = [item.lower().strip() for item in predicted_items]
        actual_normalized = [item.lower().strip() for item in actual_items]
        
        # Find matches (items in both lists)
        matched_items = []
        for pred_item in predicted_items:
            if pred_item.lower().strip() in actual_normalized:
                matched_items.append(pred_item)
        
        # Find missing items (predicted but not bought)
        missing_items = []
        for pred_item in predicted_items:
            if pred_item.lower().strip() not in actual_normalized:
                missing_items.append(pred_item)
        
        # Find extra items (bought but not predicted)
        extra_items = []
        for actual_item in actual_items:
            if actual_item.lower().strip() not in predicted_normalized:
                extra_items.append(actual_item)
        
        # Calculate match percentage
        # Formula: (matched items / predicted items) * 100
        if len(predicted_items) > 0:
            match_percentage = (len(matched_items) / len(predicted_items)) * 100
        else:
            match_percentage = 0.0
        
        result = {
            'match_percentage': round(match_percentage, 2),
            'matched_items': matched_items,
            'missing_items': missing_items,
            'extra_items': extra_items
        }
        
        print(f"📊 Accuracy calculated: {match_percentage:.1f}% ({len(matched_items)}/{len(predicted_items)} matched)")
        return result
        
    except Exception as e:
        print(f"❌ Error calculating accuracy: {e}")
        import traceback
        traceback.print_exc()
        return {
            'match_percentage': 0.0,
            'matched_items': [],
            'missing_items': [],
            'extra_items': []
        }


def save_prediction_feedback(prediction_id: int, receipt_id: int, actual_items: list, accuracy_data: dict) -> int:
    """
    Saves feedback to prediction_feedback table
    
    Args:
        prediction_id: The prediction ID this feedback is for
        receipt_id: The receipt ID submitted as feedback
        actual_items: List of actual purchased items
        accuracy_data: Dictionary from calculate_accuracy()
        
    Returns:
        int: Feedback ID if successful, None if failed
    """
    try:
        supabase = get_supabase_client()
        
        feedback_data = {
            'prediction_id': prediction_id,
            'feedback_receipt_id': receipt_id,
            'actual_items_purchased': actual_items,
            'match_percentage': accuracy_data.get('match_percentage', 0.0),
            'matched_items': accuracy_data.get('matched_items', []),
            'missing_items': accuracy_data.get('missing_items', []),
            'extra_items': accuracy_data.get('extra_items', []),
            'feedback_status': 'submitted'
        }
        
        result = supabase.table('prediction_feedback').insert(feedback_data).execute()
        
        if result.data and len(result.data) > 0:
            feedback_id = result.data[0]['id']
            print(f"💾 Feedback saved: ID {feedback_id} (Accuracy: {accuracy_data.get('match_percentage', 0):.1f}%)")
            return feedback_id
        else:
            print("❌ Failed to save feedback")
            return None
            
    except Exception as e:
        print(f"❌ Error saving feedback: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_feedback_for_receipt(receipt_id: int, session: dict) -> bool:
    """
    Processes feedback when a receipt is submitted during an active session
    
    Process:
    1. Get prediction data
    2. Get receipt items
    3. Calculate accuracy
    4. Save feedback
    5. Close session
    
    Args:
        receipt_id: The receipt ID that was just processed
        session: The active feedback session dictionary
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        
        prediction_id = session['prediction_id']
        
        # Step 1: Get prediction data
        supabase = get_supabase_client()
        prediction_result = supabase.table('predictions')\
            .select('predicted_items')\
            .eq('id', prediction_id)\
            .execute()
        
        if not prediction_result.data:
            print(f"❌ Prediction {prediction_id} not found")
            return False
        
        predicted_items = prediction_result.data[0].get('predicted_items', [])
        
        # Step 2: Get receipt items
        receipt_items = get_receipt_items_for_receipts([receipt_id])
        actual_items = [item.get('item_name_normalized', '') for item in receipt_items if item.get('item_name_normalized')]
        
        if not actual_items:
            print("⚠️ No items found in receipt")
            return False
        
        # Step 3: Calculate accuracy
        accuracy_data = calculate_accuracy(predicted_items, actual_items)
        
        # Step 4: Save feedback
        feedback_id = save_prediction_feedback(prediction_id, receipt_id, actual_items, accuracy_data)
        
        if not feedback_id:
            return False
        
        # Step 5: Keep session open and ask if there are more receipts
        # Session will be closed when user confirms "no more receipts"
        # This allows user to submit multiple receipts from same shopping trip
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing feedback: {e}")
        import traceback
        traceback.print_exc()
        return False