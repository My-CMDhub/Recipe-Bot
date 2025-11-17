"""
Receipt storage utilities
Handles saving receipt data to Supabase database
"""

from config.supabase_config import get_supabase_client
from datetime import date, datetime
import os

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


            