"""
WhatsApp image handling for receipt processing
Handles downloading images and storing receipt records
"""

import requests
import os
from dotenv import load_dotenv
from handlers.whatsapp_hanlder import send_whatsapp_message
from utils.receipt_storage import create_receipt_record

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
        
        # Send immediate acknowledgment
        send_whatsapp_message(
            phone_number,
            "� receipt received, processing..."
        )
        
        # Download the image
        image_bytes, downloaded_mime_type, file_size = download_whatsapp_image(media_id)
        
        if not image_bytes:
            # Failed to download
            send_whatsapp_message(
                phone_number,
                "❌ Sorry, I couldn't download that image. Please try sending it again."
            )
            return
        
        # Store receipt record in database
        # We'll create this function next
        receipt_id = create_receipt_record(
            user_phone=phone_number,
            image_url=f"whatsapp_media_id:{media_id}",  # Store media ID reference
            mime_type=downloaded_mime_type or mime_type,
            file_size=file_size,
            image_bytes=image_bytes  # We'll store this or process it
        )
        
        if receipt_id:
            print(f"✅ Receipt stored with ID: {receipt_id}")
            send_whatsapp_message(
                phone_number,
                "✅ Receipt processed successfully! I'll extract the details now. This may take a moment..."
            )
        else:
            send_whatsapp_message(
                phone_number,
                "⚠️ Receipt received but there was an issue saving it. Please try again."
            )
            
    except Exception as e:
        print(f"❌ Error handling receipt image: {e}")
        import traceback
        traceback.print_exc()
        send_whatsapp_message(
            phone_number,
            "❌ Sorry, something went wrong processing your receipt. Please try again later."
        )