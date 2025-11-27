"""
WhatsApp Cloud API handler functions
Handles sending messages and formatting recipe messages
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

# WhatsApp Cloud API endpoint
WHATSAPP_API_URL = "https://graph.facebook.com/v22.0"

def send_whatsapp_message(phone_number: str, message: str) -> dict:
    """
    Sends a text message via WhatsApp Cloud API
    
    Args:
        phone_number: Recipient's phone number (with country code, no +)
                     Example: "1234567890" for US number
        message: The text message to send
        
    Returns:
        dict: API response with message_id if successful
        
    Raises:
        Exception: If API call fails
    """
    # Get credentials from environment
    access_token = os.getenv('WHATSAPP_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    if not access_token or not phone_number_id:
        raise ValueError("Missing WhatsApp credentials in .env file")
    
    # Construct the API endpoint
    url = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"
    
    # Headers required by WhatsApp API
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Request body structure required by WhatsApp API
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,  # Phone number without + sign
        "type": "text",
        "text": {
            "preview_url": False,  # Set to True if you want link previews
            "body": message
        }
    }
    
    # Make the API request
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check if request was successful
        if response.status_code == 200:
            result = response.json()
            print(f"📤 WhatsApp message sent to {phone_number}: {message[:50]}...")
            return result
        else:
            # If failed, raise error with details
            error_msg = f"WhatsApp API error: {response.status_code} - {response.text}"
            print(f"❌ Failed to send WhatsApp message: {error_msg}")
            raise Exception(error_msg)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error sending WhatsApp message: {e}")
        raise

def send_recipe_message(phone_number: str, recipe_name: str) -> dict:
    """
    Sends a formatted recipe suggestion message
    
    Args:
        phone_number: Recipient's phone number
        recipe_name: Name of the recipe to suggest
        
    Returns:
        dict: API response
    """
    # Format the message nicely
    message = f"🍽️ *Daily Recipe Suggestion*\n\n"
    message += f"Tomorrow's dinner idea: *{recipe_name}*\n\n"
    message += f"Reply 'not today' if you'd like a different suggestion!"
    
    return send_whatsapp_message(phone_number, message)

def send_all_recipes_message(phone_number: str, recipe_list: list) -> dict:
    """
    Sends a message listing all recipes (when all have been sent)
    
    Args:
        phone_number: Recipient's phone number
        recipe_list: List of all recipe names
        
    Returns:
        dict: API response
    """
    # Format message with all recipes
    message = "📋 *All Recipes Sent!*\n\n"
    message += "You've seen all recipes today. Here's the full list:\n\n"
    
    # Add each recipe as a numbered list
    for i, recipe in enumerate(recipe_list, 1):
        message += f"{i}. {recipe}\n"
    
    message += "\nTomorrow you'll get fresh suggestions! 😊"
    
    return send_whatsapp_message(phone_number, message)

def send_alternative_recipe(phone_number: str, recipe_name: str) -> dict:
    """
    Sends an alternative recipe when user says "not today"
    
    Args:
        phone_number: Recipient's phone number
        recipe_name: Name of the alternative recipe
        
    Returns:
        dict: API response
    """
    message = f"🔄 *Alternative Suggestion*\n\n"
    message += f"How about: *{recipe_name}*?\n\n"
    message += f"Reply 'not today' for another option!"
    
    return send_whatsapp_message(phone_number, message)