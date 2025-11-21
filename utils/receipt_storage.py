"""
Receipt storage utilities
Handles saving receipt data to Supabase database
"""

from config.supabase_config import get_supabase_client
from utils.grocery_prediction_utils import receipt_items_from_receipts, aggregate_purchase_patterns, format_data_for_llm
from datetime import date, datetime, timedelta
import os

def check_receipt_exists(image_url: str, user_phone: str) -> int | None:
    """
    Checks if a receipt with the same image_url already exists
    
    Args:
        image_url: The image URL or media ID reference
        user_phone: User's phone number
        
    Returns:
        int: Existing receipt ID if found, None otherwise
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('receipts')\
            .select('id')\
            .eq('user_phone', user_phone)\
            .eq('image_url', image_url)\
            .limit(1)\
            .execute()
        
        if result.data and len(result.data) > 0:
            existing_id = result.data[0]['id']
            print(f"⚠️ Receipt with this image already exists: ID {existing_id}")
            return existing_id
        
        return None
        
    except Exception as e:
        print(f"❌ Error checking receipt existence: {e}")
        return None


def get_recent_pending_receipts_count(user_phone: str, within_seconds: int = 15) -> tuple[int, int]:
    """
    Gets count of pending receipts created recently (for batch detection)
    
    Args:
        user_phone: User's phone number
        within_seconds: How many seconds back to check (default: 15)
        
    Returns:
        tuple: (total_count, receipt_position) - total pending receipts and position of most recent
    """
    try:
        supabase = get_supabase_client()
        now = datetime.now()
        threshold = now - timedelta(seconds=within_seconds)
        
        # Get all pending receipts created in the last N seconds, ordered by creation time
        result = supabase.table('receipts')\
            .select('id, created_at')\
            .eq('user_phone', user_phone)\
            .eq('extraction_status', 'pending')\
            .gte('created_at', threshold.isoformat())\
            .order('created_at', desc=False)\
            .execute()
        
        receipts = result.data if result.data else []
        total_count = len(receipts)
        
        # Find position of most recent receipt (if it exists in the list)
        receipt_position = None
        if receipts:
            # Get the most recent receipt ID to find its position
            most_recent = supabase.table('receipts')\
                .select('id, created_at')\
                .eq('user_phone', user_phone)\
                .eq('extraction_status', 'pending')\
                .gte('created_at', threshold.isoformat())\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if most_recent.data:
                most_recent_id = most_recent.data[0]['id']
                # Find position in ordered list
                for idx, receipt in enumerate(receipts, start=1):
                    if receipt['id'] == most_recent_id:
                        receipt_position = idx
                        break
        
        return total_count, receipt_position or total_count
        
    except Exception as e:
        print(f"❌ Error getting recent pending receipts count: {e}")
        return 0, 0


def create_receipt_record(
    user_phone: str,
    image_url: str,
    mime_type: str = None,
    file_size: int = None,
    image_bytes: bytes = None,
    store_name: str = None,
    purchase_date: date = None,
    date_is_estimated: bool = False
) -> int:
    """
    Creates a new receipt record in the database
    
    Args:
        user_phone: WhatsApp phone number
        image_url: URL or reference to the image
        mime_type: Image MIME type (e.g., 'image/jpeg')
        file_size: Size of image in bytes
        image_bytes: Raw image data (optional, for future processing)
        store_name: Store name if known (default: None)
        purchase_date: Purchase date (default: today)
        date_is_estimated: Whether date is estimated (default: False)
        
    Returns:
        int: Receipt ID if successful, None if failed
    """
    try:
        supabase = get_supabase_client()
        
        # Use today's date if not provided
        if purchase_date is None:
            purchase_date = date.today()
            date_is_estimated = True  # Mark as estimated since we don't have receipt date
        
        # Prepare receipt data
        receipt_data = {
            'user_phone': user_phone,
            'image_url': image_url,
            'store_name': store_name or 'Unknown Store',
            'purchase_date': purchase_date.isoformat(),
            'date_is_estimated': date_is_estimated,
            'extraction_status': 'pending',  # Will be updated when OCR completes
            'mime_type': mime_type,
            'file_size': file_size
        }
        
        # Insert into database
        result = supabase.table('receipts').insert(receipt_data).execute()
        
        if result.data and len(result.data) > 0:
            receipt_id = result.data[0]['id']
            print(f"💾 Receipt saved: ID {receipt_id}")
            return receipt_id
        else:
            print("❌ Failed to save receipt - no data returned")
            return None
            
    except Exception as e:
        print(f"❌ Error creating receipt record: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_receipt_count(user_phone: str = None) -> int:
    """
    Gets total count of receipts (for all users or specific user)
    
    Args:
        user_phone: Optional phone number to filter by
        
    Returns:
        int: Number of receipts
    """
    try:
        supabase = get_supabase_client()
        
        if user_phone:
            result = supabase.table('receipts').select('id', count='exact').eq('user_phone', user_phone).execute()
        else:
            result = supabase.table('receipts').select('id', count='exact').execute()
        
        return result.count if hasattr(result, 'count') else len(result.data)
        
    except Exception as e:
        print(f"❌ Error getting receipt count: {e}")
        return 0

def update_receipt_with_unstract(receipt_id: int, unstract_response: dict, extraction_status: str = 'success'):
    """
    Updates receipt record with Unstract OCR results
    
    Args:
        receipt_id: Receipt ID to update
        unstract_response: Full Unstract API response
        extraction_status: 'success' or 'failed'
    """
    try:
        supabase = get_supabase_client()
        
        update_data = {
            'unstract_response': unstract_response,
            'extraction_status': extraction_status,
            'updated_at': datetime.now().isoformat()
        }
        
        supabase.table('receipts').update(update_data).eq('id', receipt_id).execute()
        print(f"✅ Receipt {receipt_id} updated with Unstract data")
        
    except Exception as e:
        print(f"❌ Error updating receipt: {e}")
        import traceback
        traceback.print_exc()

def update_receipt_extraction_status(receipt_id: int, status: str, error_message: str = None):
    """
    Updates receipt extraction status
    
    Args:
        receipt_id: Receipt ID
        status: 'pending', 'processing', 'success', 'failed'
        error_message: Error message if failed
    """
    try:
        supabase = get_supabase_client()
        
        update_data = {
            'extraction_status': status,
            'updated_at': datetime.now().isoformat()
        }
        
        if error_message:
            update_data['error_message'] = error_message
        
        supabase.table('receipts').update(update_data).eq('id', receipt_id).execute()
        
    except Exception as e:
        print(f"❌ Error updating status: {e}")

def save_receipt_items(receipt_id: int, items_list: list, normalization_model: str = 'ai_normalized'):

    """
    Saves receipt items to the receipt_items table
    
    Args:
        receipt_id: The receipt ID these items belong to
        items_list: List of item dicts from AI structuring
                   Format: [{"name": "...", "quantity": 2.0, "unit_price": 1.65, "total_price": 3.30}, ...]
        normalization_model: Which AI model normalized these ('mistral', 'gemini', etc.)
    
    Returns:
        int: Number of items saved, or 0 if failed
    """

    try:
        supabase = get_supabase_client()

        items_to_insert = []

        for item in items_list:
            item_data = {
                'receipt_id': receipt_id,
                'item_name_raw': item.get('name', ''),
                'item_name_normalized': item.get('name', ''),
                'quantity': item.get('quantity', 0),
                'unit_price': item.get('unit_price', 0),
                'total_price': item.get('total_price', 0),
                'normalization_status': 'success',
                'normalization_model': normalization_model
            }
            items_to_insert.append(item_data)

        if items_to_insert:
            result = supabase.table('receipt_items').insert(items_to_insert).execute()
            saved_count = len(result.data) if result.data else 0
            print(f"✅ Saved {saved_count} items for receipt {receipt_id}")
            return saved_count
        else:
            print("⚠️ No items to save")
            return 0

    except Exception as e:
        print(f"❌ Error saving receipt items: {e}")
        import traceback
        traceback.print_exc()
        return 0

def update_receipt_with_structured_data(receipt_id: int, structured_data: dict):
    """
    Updates receipt record with AI-structured data (store_name, purchase_date)
    
    Args:
        receipt_id: Receipt ID to update
        structured_data: Dict with 'store_name' and 'purchase_date'
    """
    try:
        supabase = get_supabase_client()
        
        update_data = {
            'store_name': structured_data.get('store_name'),
            'purchase_date': structured_data.get('purchase_date'),
            'date_is_estimated': False,  # AI extracted it from receipt, so it's accurate
            'updated_at': datetime.now().isoformat()
        }
        
        supabase.table('receipts').update(update_data).eq('id', receipt_id).execute()
        print(f"✅ Receipt {receipt_id} updated with structured data")
        
    except Exception as e:
        print(f"❌ Error updating receipt with structured data: {e}")
        import traceback
        traceback.print_exc()

def save_prediction(user_phone: str, prediction_data: dict, llm_prompt: str = None) -> int:
    """
    Saves a grocery prediction to the predictions table
    
    Args:
        user_phone: User's WhatsApp phone number
        prediction_data: Dictionary from generate_grocery_prediction()
                        Must contain: predicted_date_range_start, predicted_date_range_end, 
                                     predicted_items, reasoning (optional), llm_used
        llm_prompt: The prompt sent to LLM (optional, for debugging)
        
    Returns:
        int: Prediction ID if successful, None if failed
    """

    try:
        supabase = get_supabase_client()

         # Calculate expiration time (5 hours from now, or end of day, whichever is later)
        now = datetime.now()
        expires_at = now + timedelta(hours=5)

        # Prepare prediction data
        prediction_record = {
            'user_phone': user_phone,
            'prediction_date': date.today().isoformat(),
            'predicted_date_range_start': prediction_data.get('predicted_date_range_start'),
            'predicted_date_range_end': prediction_data.get('predicted_date_range_end'),
            'predicted_items': prediction_data.get('predicted_items', []),  # JSONB array
            'reasoning': prediction_data.get('reasoning'),
            'llm_used': prediction_data.get('llm_used', 'unknown'),
            'llm_prompt': llm_prompt,
            'llm_response': prediction_data,  # Store full response as JSONB
            'status': 'pending_feedback',
            'expires_at': expires_at.isoformat()
        }

        # Insert into database
        result = supabase.table('predictions').insert(prediction_record).execute()

        if result.data and len(result.data) > 0:
            prediction_id = result.data[0]['id']
            print(f"💾 Prediction saved: ID {prediction_id}")
            return prediction_id
        
        else:
             print("❌ Failed to save prediction - no data returned")
             return None

    except Exception as e:
        print(f"❌ Error saving prediction: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_receipt_items_for_receipts(receipt_ids: list):
    """
    Gets receipt items for a list of receipt IDs
    (This is a wrapper for the function in grocery_prediction_utils)
    """
    from utils.grocery_prediction_utils import receipt_items_from_receipts
    return receipt_items_from_receipts(receipt_ids)