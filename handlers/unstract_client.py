"""
Unstract LLMWhisper API client
Handles image upload, polling, and text retrieval
"""

import requests
import os
import time
from dotenv import load_dotenv


load_dotenv()

# Unstract API base URL
UNSTRACT_API_BASE = os.getenv('UNSTRACT_API_URL', 'https://llmwhisperer-api.us-central.unstract.com/api/v2')
UNSTRACT_API_KEY = os.getenv('UNSTRACT_API_KEY')

# Polling configuration
POLL_INTERVAL = 5  # Check every 5 seconds
MAX_POLL_ATTEMPTS = 60  # Max 5 minutes (60 * 5 seconds)

def upload_image_to_unstract(image_bytes: bytes, filename: str = "receipt.jpg") -> dict:
    """
    Uploads an image to Unstract for OCR processing
    
    Process:
    1. POST image as binary data to /whisper endpoint
    2. Get whisper_hash immediately
    3. Return hash for polling
    
    Args:
        image_bytes: Raw image file bytes
        filename: Name for the file (optional)
        
    Returns:
        dict: Response with 'whisper_hash' and 'status', or None if failed
    """
    if not UNSTRACT_API_KEY:
        raise ValueError("UNSTRACT_API_KEY not set in environment")
    
    try:
        url = f"{UNSTRACT_API_BASE}/whisper"
        
        # Query parameters as per documentation
        params = {
            'mode': 'form',
            'output_mode': 'layout_preserving'
        }
        
        headers = {
            'unstract-key': UNSTRACT_API_KEY
        }
        
        # Upload binary data
        # Note: requests will set Content-Type automatically for binary data
        print(f"📤 Uploading image to Unstract ({len(image_bytes)} bytes)...")
        response = requests.post(
            url,
            params=params,
            headers=headers,
            data=image_bytes  # Binary upload
        )
        
        if response.status_code in [200, 202]:
            result = response.json()
            whisper_hash = result.get('whisper_hash')
            status = result.get('status', 'processing')
            
            print(f"✅ Image uploaded successfully!")
            print(f"   Whisper Hash: {whisper_hash}")
            print(f"   Status: {status}")
            
            return {
                'whisper_hash': whisper_hash,
                'status': status,
                'message': result.get('message', 'Whisper Job Accepted')
            }
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error uploading to Unstract: {e}")
        import traceback
        traceback.print_exc()
        return None

def poll_unstract_status(whisper_hash: str) -> dict:
    """
    Polls Unstract to check if processing is complete
    
    Process:
    1. GET /whisper-detail with whisper_hash
    2. Check if status is "completed"
    3. Return status and metadata
    
    Args:
        whisper_hash: Hash returned from upload
        
    Returns:
        dict: Status info with 'completed_at' when done, or None if failed
    """
    if not UNSTRACT_API_KEY:
        raise ValueError("UNSTRACT_API_KEY not set in environment")
    
    try:
        url = f"{UNSTRACT_API_BASE}/whisper-detail"
        params = {'whisper_hash': whisper_hash}
        headers = {'unstract-key': UNSTRACT_API_KEY}
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"⚠️ Whisper hash not found: {whisper_hash}")
            return None
        else:
            print(f"❌ Status check failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return None

def wait_for_unstract_completion(whisper_hash: str) -> dict:
    """
    Waits for Unstract processing to complete by polling
    
    Process:
    1. Poll every 5 seconds
    2. Check up to 60 times (5 minutes max)
    3. Return when completed or timeout
    
    Args:
        whisper_hash: Hash from upload
        
    Returns:
        dict: Final status with 'completed_at', or None if timeout/failed
    """
    print(f"⏳ Waiting for Unstract processing to complete...")
    
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        status_data = poll_unstract_status(whisper_hash)
        
        if not status_data:
            print(f"❌ Failed to get status on attempt {attempt}")
            return None
        
        # Check if completed
        if status_data.get('completed_at'):
            print(f"✅ Processing completed!")
            print(f"   Processing time: {status_data.get('processing_time_in_seconds', 0)} seconds")
            return status_data
        
        # Still processing
        if attempt % 6 == 0:  # Log every 30 seconds
            print(f"   Still processing... (attempt {attempt}/{MAX_POLL_ATTEMPTS})")
        
        # Wait before next poll
        time.sleep(POLL_INTERVAL)
    
    print(f"⏰ Timeout: Processing took longer than {MAX_POLL_ATTEMPTS * POLL_INTERVAL} seconds")
    return None

def retrieve_unstract_text(whisper_hash: str) -> dict:
    """
    Retrieves the extracted text from Unstract
    
    Process:
    1. GET /whisper-retrieve with whisper_hash
    2. Get result_text (unstructured text)
    3. Return text and metadata
    
    Args:
        whisper_hash: Hash from upload
        
    Returns:
        dict: Extracted text data with 'result_text', or None if failed
    """
    if not UNSTRACT_API_KEY:
        raise ValueError("UNSTRACT_API_KEY not set in environment")
    
    try:
        url = f"{UNSTRACT_API_BASE}/whisper-retrieve"
        params = {
            'whisper_hash': whisper_hash,
            'text_only': 'false'  # Get full data including metadata
        }
        headers = {'unstract-key': UNSTRACT_API_KEY}
        
        print(f"📥 Retrieving extracted text from Unstract...")
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            result_text = result.get('result_text', '')
            confidence_metadata = result.get('confidence_metadata', [])
            
            print(f"✅ Text retrieved: {len(result_text)} characters")
            
            return {
                'result_text': result_text,
                'confidence_metadata': confidence_metadata,
                'metadata': result.get('metadata', {})
            }
        else:
            print(f"❌ Retrieve failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error retrieving text: {e}")
        import traceback
        traceback.print_exc()
        return None

def process_receipt_with_unstract(image_bytes: bytes) -> dict:
    """
    Complete Unstract OCR processing pipeline
    
    Process:
    1. Upload image → Get whisper_hash
    2. Poll until complete → Wait for processing
    3. Retrieve text → Get extracted text
    4. Return all data
    
    Args:
        image_bytes: Raw image file bytes
        
    Returns:
        dict: Complete extraction data, or None if failed
    """
    # Step 1: Upload
    upload_result = upload_image_to_unstract(image_bytes)
    if not upload_result:
        return None
    
    whisper_hash = upload_result['whisper_hash']
    
    # Step 2: Wait for completion
    status_result = wait_for_unstract_completion(whisper_hash)
    if not status_result:
        return None
    
    # Step 3: Retrieve text
    text_result = retrieve_unstract_text(whisper_hash)
    if not text_result:
        return None

    
    # Combine all results
    return {
        'whisper_hash': whisper_hash,
        'status': status_result,
        'extracted_text': text_result['result_text'],
        'confidence_metadata': text_result.get('confidence_metadata', []),
        'metadata': text_result.get('metadata', {})
    }