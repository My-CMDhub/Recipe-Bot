"""
WhatsApp image handling for receipt processing
Handles downloading images and storing receipt records
"""

import requests
import os
from dotenv import load_dotenv
from handlers.whatsapp_hanlder import send_whatsapp_message
from utils.receipt_storage import (
create_receipt_record, 
update_receipt_extraction_status, 
update_receipt_with_unstract, 
save_receipt_items, 
update_receipt_with_structured_data,
 )
from handlers.feedback_handler import process_feedback_for_receipt
from handlers.unstract_client import process_receipt_with_unstract
from handlers.ai_data_processor import structure_receipt_data
from utils.session_manager import get_active_feedback_session


load_dotenv()

# WhatsApp API version (using v22.0 as per your current setup)
WHATSAPP_API_VERSION = "v22.0"

def download_whatsapp_image(media_id: str) -> tuple:
    """
    Downloads an image from WhatsApp using media ID
    
    Process:
    1. Get temporary URL from WhatsApp using media_id
    2. Download image from that URL
    3. Return image bytes and metadata
    
    Args:
        media_id: The media ID from WhatsApp webhook
        
    Returns:
        tuple: (image_bytes, mime_type, file_size) or (None, None, None) if failed
    """
    access_token = os.getenv('WHATSAPP_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    if not access_token or not phone_number_id:
        raise ValueError("Missing WhatsApp credentials")
    
    try:
        # Step 1: Get temporary download URL
        # According to docs: GET /{MEDIA_ID}?phone_number_id={PHONE_NUMBER_ID}
        url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{media_id}"
        params = {'phone_number_id': phone_number_id}
        headers = {'Authorization': f'Bearer {access_token}'}
        
        print(f"🔗 Getting media URL for media_id: {media_id}")
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Failed to get media URL: {response.status_code} - {response.text}")
            return None, None, None
        
        media_data = response.json()
        media_url = media_data.get('url')
        mime_type = media_data.get('mime_type', 'image/jpeg')
        file_size = media_data.get('file_size', 0)
        
        if not media_url:
            print("❌ No URL in media response")
            return None, None, None
        
        print(f"✅ Got media URL (expires in 5 minutes)")
        
        # Step 2: Download the actual image
        # Important: Must include Authorization header!
        print(f"📥 Downloading image...")
        image_response = requests.get(media_url, headers=headers)
        
        if image_response.status_code != 200:
            print(f"❌ Failed to download image: {image_response.status_code}")
            return None, None, None
        
        image_bytes = image_response.content
        print(f"✅ Image downloaded: {len(image_bytes)} bytes")
        
        return image_bytes, mime_type, file_size
        
    except Exception as e:
        print(f"❌ Error downloading image: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def handle_receipt_image(phone_number: str, message: dict):
    """
    Handles when user sends a receipt image
    
    Process:
    1. Extract image ID from message
    2. Download image from WhatsApp
    3. Store receipt record in database
    4. Send acknowledgment to user
    
    Args:
        phone_number: User's WhatsApp phone number
        message: The message object from webhook
    """
    try:
        # Extract image data from webhook payload
        image_data = message.get('image', {})
        media_id = image_data.get('id')
        mime_type = image_data.get('mime_type', 'image/jpeg')
        
        if not media_id:
            print("❌ No media ID in image message")
            send_whatsapp_message(
                phone_number, 
                "⚠️ Sorry, I couldn't process that image. Please try sending it again."
            )
            return
        
        print(f"📷 Processing receipt image:")
        print(f"   Media ID: {media_id}")
        print(f"   MIME Type: {mime_type}")
        
        # Check for duplicate receipt FIRST (prevent processing same image multiple times)
        # This prevents multiple acknowledgment messages for the same receipt
        from utils.receipt_storage import check_receipt_exists
        image_url_ref = f"whatsapp_media_id:{media_id}"
        existing_receipt_id = check_receipt_exists(image_url_ref, phone_number)
        
        if existing_receipt_id:
            print(f"⚠️ Receipt already processed: ID {existing_receipt_id}")
            # Only send message if this is a new webhook call (not already processing)
            # Check if receipt is still pending (being processed)
            from config.supabase_config import get_supabase_client
            supabase = get_supabase_client()
            receipt_status = supabase.table('receipts')\
                .select('extraction_status')\
                .eq('id', existing_receipt_id)\
                .execute()
            
            if receipt_status.data and receipt_status.data[0].get('extraction_status') == 'pending':
                # Still processing, don't send duplicate message
                print("ℹ️ Receipt is still being processed, skipping duplicate message")
            else:
                send_whatsapp_message(
                    phone_number,
                    "✅ This receipt was already processed earlier. If you need to resubmit, please send a new image."
                )
            return
        
        # Check if this receipt is feedback for an active prediction (check early)
        # Extend session if found to prevent expiration during OCR processing
        # Include recently expired sessions (grace period) in case extension failed
        active_session = get_active_feedback_session(user_phone=phone_number, extend_if_found=True, include_recently_expired=True)
        
        # Download the image
        image_bytes, downloaded_mime_type, file_size = download_whatsapp_image(media_id)
        
        if not image_bytes:
            # Failed to download
            send_whatsapp_message(
                phone_number,
                "❌ Sorry, I couldn't download that image. Please try sending it again."
            )
            return
        
        # Store receipt record in database FIRST (so we can detect batch)
        receipt_id = create_receipt_record(
            user_phone=phone_number,
            image_url=image_url_ref,  # Store media ID reference
            mime_type=downloaded_mime_type or mime_type,
            file_size=file_size,
            image_bytes=image_bytes  # We'll store this or process it
        )
        
        if not receipt_id:
            send_whatsapp_message(
                phone_number,
                "❌ Sorry, I couldn't save that receipt. Please try again."
            )
            return
        
        # Check for batch receipts (multiple receipts sent at once)
        from utils.receipt_storage import get_recent_pending_receipts_count
        total_pending, receipt_position = get_recent_pending_receipts_count(phone_number, within_seconds=15)
        
        # Send appropriate acknowledgment message
        if total_pending > 1:
            # Batch mode: multiple receipts detected
            send_whatsapp_message(
                phone_number,
                f"📸 {total_pending} receipts received! Processing all receipts...\n\nI'll update you as each one completes."
            )
        else:
            # Single receipt
            send_whatsapp_message(
                phone_number,
                "📸 Receipt received, processing..."
            )
        
        print(f"✅ Receipt stored with ID: {receipt_id}")
        
        # Store receipt position for progress updates (if batch)
        receipt_position_for_update = receipt_position if total_pending > 1 else None
        
        try:
            print(f"🔍 Starting OCR processing with Unstract...")
            unstract_result = process_receipt_with_unstract(image_bytes)

            if unstract_result:
                update_receipt_with_unstract(
                    receipt_id=receipt_id,
                    unstract_response=unstract_result,
                    extraction_status='success'
                )
                print(f"✅ OCR completed! Extracted {len(unstract_result.get('extracted_text', ''))} characters")
                # Don't send message here - we'll send after items are saved to avoid duplicate messages
                structured_data = structure_receipt_data(unstract_result.get('extracted_text', ''))
                if structured_data:
                    update_receipt_with_structured_data(receipt_id, structured_data)

                    items_list = structured_data.get('items', [])
                    if items_list:
                        saved_count = save_receipt_items(receipt_id, items_list, normalization_model='mistral')
                        print(f"✅ Saved {saved_count} items to database")

                        if saved_count > 0:
                            # Re-check for active session right before processing feedback
                            # (session might have been created after initial check)
                            # Include recently expired sessions as grace period
                            current_session = get_active_feedback_session(user_phone=phone_number, extend_if_found=False, include_recently_expired=True)
                            
                            # Format completion message based on batch or single mode
                            store_name = structured_data.get('store_name', 'the store')
                            
                            if receipt_position_for_update and total_pending > 1:
                                # Batch mode: include receipt number
                                completion_msg = f"✅ Receipt {receipt_position_for_update}/{total_pending} completed: Found {saved_count} items from {store_name}."
                            else:
                                # Single receipt mode
                                completion_msg = f"✅ Receipt processed successfully! Found {saved_count} items from {store_name}."
                            
                            # Check if this was feedback and process it
                            if current_session:
                                print(f"📝 Processing feedback for prediction {current_session['prediction_id']}")
                                feedback_success = process_feedback_for_receipt(receipt_id, current_session)
                                if feedback_success:
                                    try:
                                        send_whatsapp_message(
                                            phone_number,
                                            f"{completion_msg}\n\n📊 Feedback recorded!\n\nDo you have any other receipts from this shopping trip? If yes, send them now. If no, reply 'done' or 'no more'."
                                        )
                                        print(f"✅ Feedback message sent to user")
                                    except Exception as msg_error:
                                        print(f"⚠️ Could not send feedback message: {msg_error}")
                                        # Still send basic completion message
                                        try:
                                            send_whatsapp_message(phone_number, completion_msg)
                                        except:
                                            pass
                                else:
                                    try:
                                        send_whatsapp_message(phone_number, completion_msg)
                                    except Exception as msg_error:
                                        print(f"⚠️ Could not send completion message: {msg_error}")
                            else:
                                try:
                                    send_whatsapp_message(phone_number, completion_msg)
                                except Exception as msg_error:
                                    print(f"⚠️ Could not send completion message: {msg_error}")
                            return

                        else:
                            send_whatsapp_message(
                                phone_number,
                                "⚠️ Receipt processed but no items found. Please check the receipt image quality."
                            )
                            return

                    else:
                        update_receipt_extraction_status(receipt_id, 'failed', 'AI structuring failed')
                        send_whatsapp_message(
                            phone_number,
                            "⚠️ Receipt processed but couldn't extract items. Please try sending a clearer image."
                        )
                        return
                        
            else:
                update_receipt_extraction_status(receipt_id, 'failed', 'OCR processing failed')
                send_whatsapp_message(
                    phone_number,
                    "⚠️ Receipt received but OCR processing failed. Please try sending a clearer image."
                )
                return
                    
        except Exception as e:
            print(f"❌ Error during OCR processing: {e}")
            import traceback
            traceback.print_exc()
            update_receipt_extraction_status(receipt_id, 'failed', 'Exception during OCR processing')
            send_whatsapp_message(
                phone_number,
                "❌ Sorry, something went wrong processing your receipt. Please try again later."
            )
            
    except Exception as e:
        print(f"❌ Error handling receipt image: {e}")
        import traceback
        traceback.print_exc()
        send_whatsapp_message(
            phone_number,
            "❌ Sorry, something went wrong processing your receipt. Please try again later."
        ) 