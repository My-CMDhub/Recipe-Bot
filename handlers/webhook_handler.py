"""
Webhook handler for processing incoming WhatsApp messages
Handles message parsing and "not today" detection
"""

from utils.recipe_utils import get_random_recipe_not_sent_today, record_recipe_sent, get_all_recipe_names
from handlers.whatsapp_hanlder import send_alternative_recipe, send_all_recipes_message, send_whatsapp_message
import traceback
def process_incoming_message(webhook_data: dict):
    """
    Processes incoming WhatsApp webhook data
    
    Args:
        webhook_data: The JSON payload sent by WhatsApp webhook
    """
    # WhatsApp sends data in a nested structure:
    # webhook_data['entry'][0]['changes'][0]['value']['messages'][0]
    
    # Extract the message data from nested structure
    try:
        entry = webhook_data.get('entry', [])
        if not entry:
            print("No entry found in webhook data")

            return
        
        changes = entry[0].get('changes', [])
        if not changes:
            print("No changes found in webhook data")

            return
        
        value = changes[0].get('value', {})
        messages = value.get('messages', [])
        
        if not messages:
            print("No messages found in webhook data")
            return
        
        # Get the first message (usually there's only one)
        message = messages[0]
        
        # Extract phone number and message text
        sender_phone = message.get('from')  # Phone number of sender
        message_type = message.get('type')   # Usually 'text'

        print(f"Received message from: {sender_phone}")
        print(f"Message type: {message_type}")
        
        # Only process text messages
        if message_type != 'text':
            print(f"Non-text message received: {message_type}")
            return
        
        # Get the actual message text
        message_text = message.get('text', {}).get('body', '').lower().strip()
        print(f"📝 Message text: '{message_text}'")
        
        # Check for different message types and respond accordingly
        if 'not today' in message_text:
            print("✅ Detected 'not today' - sending alternative recipe")
            handle_not_today_response(sender_phone)
        elif is_greeting(message_text):
            print("👋 Detected greeting - sending friendly response")
            handle_greeting(sender_phone)
        elif is_farewell(message_text):
            print("👋 Detected farewell - sending goodbye message")
            handle_farewell(sender_phone)
        else:
            print(f"ℹ️ Message doesn't match known patterns. Ignoring.")
            
    except (KeyError, IndexError, TypeError) as e:
        # If webhook structure is unexpected, log error but don't crash
        print(f"Error processing webhook: {e}")
        traceback.print_exc()
        return

def handle_not_today_response(phone_number: str):
    """
    Handles when user replies "not today"
    Sends an alternative recipe or full list if all sent
    
    Args:
        phone_number: User's phone number
    """
    print(f"\n🍽️ Handling 'not today' response from {phone_number}")
    
    try:
        # Try to get a random recipe not sent today
        print("🔍 Looking for available recipe...")
        recipe = get_random_recipe_not_sent_today()
        
        if recipe:
            # Found an available recipe - send it
            recipe_id = recipe['id']
            recipe_name = recipe['name']
            
            print(f"✅ Found recipe: {recipe_name} (ID: {recipe_id})")
            print(f"📤 Sending alternative recipe to {phone_number}...")
            
            # Send alternative recipe
            result = send_alternative_recipe(phone_number, recipe_name)
            print(f"✅ Recipe sent successfully: {result}")
            
            # Record that we sent this recipe
            print(f"💾 Recording recipe {recipe_id} as sent...")
            record_recipe_sent(recipe_id)
            print("✅ Recipe recorded in history")
        else:
            # All recipes sent today - send full list
            print("⚠️ All recipes have been sent today")
            print("📋 Getting full recipe list...")
            all_recipes = get_all_recipe_names()
            print(f"📤 Sending full list ({len(all_recipes)} recipes) to {phone_number}...")
            result = send_all_recipes_message(phone_number, all_recipes)
            print(f"✅ Full list sent successfully: {result}")
            
    except Exception as e:
        print(f"❌ Error in handle_not_today_response: {e}")
        traceback.print_exc()

def is_greeting(message_text: str) -> bool:
    """
    Checks if the message is a greeting
    
    Args:
        message_text: Lowercased and stripped message text
        
    Returns:
        bool: True if message is a greeting
    """
    greetings = [
        'hi', 'hello', 'hey', 'hey there', 'hi there',
        'good morning', 'good afternoon', 'good evening',
        'gm', 'morning', 'afternoon', 'evening',
        'what\'s up', 'whats up', 'sup', 'yo'
    ]
    
    # Check if message starts with or contains a greeting
    for greeting in greetings:
        if message_text.startswith(greeting) or message_text == greeting:
            return True
    return False

def is_farewell(message_text: str) -> bool:
    """
    Checks if the message is a farewell
    
    Args:
        message_text: Lowercased and stripped message text
        
    Returns:
        bool: True if message is a farewell
    """
    farewells = [
        'bye', 'goodbye', 'see you', 'see ya', 'cya',
        'take care', 'talk later', 'later', 'bye bye',
        'good night', 'gn', 'night', 'ttyl'
    ]
    
    # Check if message contains a farewell
    for farewell in farewells:
        if farewell in message_text:
            return True
    return False

def handle_greeting(phone_number: str):
    """
    Handles greeting messages with a friendly response
    
    Args:
        phone_number: User's phone number
    """
    greetings_responses = [
        "Hey there! 👋 Ready for today's recipe suggestion?",
        "Hello! 😊 I'm your recipe bot. Want a dinner idea?",
        "Hi! 🍽️ I'm here to help with recipe suggestions!",
        "Hey! 👋 What's cooking? Need a recipe idea?"
    ]
    
    import random
    response = random.choice(greetings_responses)
    
    try:
        send_whatsapp_message(phone_number, response)
        print(f"✅ Greeting sent to {phone_number}")
    except Exception as e:
        print(f"❌ Error sending greeting: {e}")
        traceback.print_exc()

def handle_farewell(phone_number: str):
    """
    Handles farewell messages with a friendly goodbye
    
    Args:
        phone_number: User's phone number
    """
    farewell_responses = [
        "Take care! 👋 See you tomorrow for another recipe!",
        "Goodbye! 😊 Have a great day!",
        "Bye! 👋 Don't forget to check tomorrow's recipe suggestion!",
        "See you later! 🍽️ Enjoy your cooking!"
    ]
    
    import random
    response = random.choice(farewell_responses)
    
    try:
        send_whatsapp_message(phone_number, response)
        print(f"✅ Farewell sent to {phone_number}")
    except Exception as e:
        print(f"❌ Error sending farewell: {e}")
        traceback.print_exc()