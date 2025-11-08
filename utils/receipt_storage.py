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