"""
Webhook handler for processing incoming WhatsApp messages
Handles message parsing and "not today" detection
"""

from utils.recipe_utils import get_random_recipe_not_sent_today, record_recipe_sent, get_all_recipe_names
from handlers.whatsapp_hanlder import send_alternative_recipe, send_all_recipes_message, send_whatsapp_message
from handlers.image_handler import handle_receipt_image
from utils.receipt_storage import get_receipt_count, save_prediction
from utils.grocery_prediction_utils import get_recent_receipts, receipt_items_from_receipts, aggregate_purchase_patterns, format_data_for_llm
from handlers.prediction_handler import generate_grocery_prediction
from utils.session_manager import create_feedback_session
from datetime import date, datetime, timedelta
import os
import traceback
from typing import Optional

# In-memory cache for processed message IDs (prevents duplicate processing)
# Format: {message_id: timestamp}
# Auto-cleanup: messages older than 24 hours are removed
_processed_messages_cache = {}
_cache_cleanup_interval = timedelta(hours=24)

def _cleanup_old_messages():
    """Remove message IDs older than 24 hours from cache"""
    now = datetime.now()
    expired_ids = [
        msg_id for msg_id, timestamp in _processed_messages_cache.items()
        if now - timestamp > _cache_cleanup_interval
    ]
    for msg_id in expired_ids:
        del _processed_messages_cache[msg_id]
    if expired_ids:
        print(f"🧹 Cleaned up {len(expired_ids)} old message IDs from cache")

def _is_message_processed(message_id: str) -> bool:
    """Check if message has already been processed"""
    if message_id in _processed_messages_cache:
        return True
    return False

def _mark_message_processed(message_id: str):
    """Mark a message as processed"""
    _processed_messages_cache[message_id] = datetime.now()
    # Periodic cleanup (every 100 messages)
    if len(_processed_messages_cache) % 100 == 0:
        _cleanup_old_messages()

def process_incoming_message(webhook_data: dict) -> bool:
    """
    Processes incoming WhatsApp webhook data
    
    Args:
        webhook_data: The JSON payload sent by WhatsApp webhook
        
    Returns:
        bool: True if message was processed, False if ignored (status update, duplicate, etc.)
    """
    # WhatsApp sends different types of webhook events:
    # 1. Messages: value.messages[] - actual user messages (we process these)
    # 2. Status updates: value.statuses[] - delivery/read receipts (we ignore these)
    # 3. Account updates: value.contacts[] - account changes (we ignore these)
    
    try:
        entry = webhook_data.get('entry', [])
        if not entry:
            print("⚠️ No entry found in webhook data - ignoring")
            return False
        
        changes = entry[0].get('changes', [])
        if not changes:
            print("⚠️ No changes found in webhook data - ignoring")
            return False
        
        value = changes[0].get('value', {})
        
        # CRITICAL: Filter out status updates (delivered, read, sent notifications)
        # These are NOT messages and should be ignored immediately
        statuses = value.get('statuses', [])
        if statuses:
            print(f"📊 Status update received (delivered/read/sent) - ignoring")
            return False
        
        # Check for account/contact updates (also not messages)
        contacts = value.get('contacts', [])
        if contacts and not value.get('messages'):
            print(f"👤 Contact/account update received - ignoring")
            return False
        
        # Only process if we have actual messages
        messages = value.get('messages', [])
        if not messages:
            print("⚠️ No messages found in webhook data (might be status update) - ignoring")
            return False
        
        # Get the first message (usually there's only one)
        message = messages[0]
        
        # Extract message ID for idempotency check (CRITICAL for preventing duplicate processing)
        message_id = message.get('id')
        if not message_id:
            print("⚠️ No message ID found - cannot verify idempotency, skipping")
            return False
        
        # IDEMPOTENCY CHECK: Prevent processing the same message twice
        # This handles WhatsApp retries and prevents duplicate responses
        if _is_message_processed(message_id):
            print(f"🔄 Duplicate message detected (ID: {message_id[:20]}...) - already processed, ignoring")
            return False
        
        # Extract phone number and message text
        sender_phone = message.get('from')  # Phone number of sender
        message_type = message.get('type')   # Usually 'text'

        print(f"📨 Processing new message from: {sender_phone}")
        print(f"   Message ID: {message_id[:20]}...")
        print(f"   Message type: {message_type}")
        
        # Only process text and image messages
        if message_type != 'text':
            if message_type == 'image':
                print(f"📷 Image message received from {sender_phone}")
                # For images: Don't mark as processed yet - let image handler do it
                # after checking media_id duplicates. This prevents false positives.
                handle_receipt_image(sender_phone, message, message_id)
                return True
            else:    
                print(f"⚠️ Unsupported message type: {message_type} - ignoring")
                return False
        
        # For text messages: Mark as processed immediately (they're fast and synchronous)
        _mark_message_processed(message_id)
        
        # Get the actual message text
        message_text = message.get('text', {}).get('body', '').lower().strip()
        print(f"📝 Message text: '{message_text}'")
        
        # Check for different message types and respond accordingly
        if 'not today' in message_text:
            print("✅ Detected 'not today' - sending alternative recipe")
            handle_not_today_response(sender_phone)
        elif is_full_list(message_text):
            print("📋 Detected 'full list' request - sending all recipes")
            handle_full_list(sender_phone)
        elif is_greeting(message_text):
            print("👋 Detected greeting - sending friendly response")
            handle_greeting(sender_phone)
        elif is_farewell(message_text):
            print("👋 Detected farewell - sending goodbye message")
            handle_farewell(sender_phone)
        elif is_grocery_command(message_text):
                print("🛒 Detected grocery command - handling prediction request")
                handle_grocery_request(sender_phone)
        elif is_no_response(message_text):
            print("❌ Detected 'No' response - checking for active feedback session")
            handle_no_response(sender_phone)
        elif is_no_more_receipts(message_text):
            print("✅ Detected 'No more receipts' - closing feedback session and triggering learning")
            handle_no_more_receipts(sender_phone)
        else:
            send_whatsapp_message(sender_phone, "Sorry, I didn't understand that. Please reply with 'not today', 'full list', a greeting, or a farewell.")
            print(f"❓ Sent feedback for unsupported query from {sender_phone}")
        
        return True
            
    except (KeyError, IndexError, TypeError) as e:
        # If webhook structure is unexpected, log error but don't crash
        # Still return True so webhook returns 200 (prevents retries)
        print(f"⚠️ Error processing webhook structure: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        # Unexpected error - log but don't crash
        # Return False so we know it failed, but webhook will still return 200
        print(f"❌ Unexpected error processing webhook: {e}")
        traceback.print_exc()
        return False

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

def is_full_list(message_text: str) -> bool:
    """
    Checks if the message is a request for the full list of recipes
    
    Args:
        message_text: Lowercased and stripped message text
        
    Returns:
        bool: True if message is a request for the full list of recipes
    """
    full_list_keywords = [
        "full list", 
        "all recipes", 
        "all recipe",
        "show all",
        "list all",
        "all please",
        "show recipes",
        "recipe list"
    ]
    
    # Check if message contains any of the keywords
    for keyword in full_list_keywords:
        if keyword in message_text:
            return True
    return False

def handle_greeting(phone_number: str):
    """
    Handles greeting messages with a friendly response and instructions
    
    Args:
        phone_number: User's phone number
    """
    # Welcome message with instructions
    response = """Hey there! 👋 

I'm your *Daily Recipe Bot - Luca*! *made by @DHRUV PATEL*  I'll send you dinner recipe suggestions every day at 10 PM.

*Here's what you can do:*

🍽️ *Daily Recipe* - I'll send you a recipe automatically at 10 PM

🔄 *"not today"* - Reply with "not today" to get an alternative recipe suggestion

📋 *"full list"* - Reply with "full list" to see all available recipes

👋 *Greetings* - Say "hi", "hello", or "hey" anytime

👋 *Farewell* - Say "bye", "goodbye", or "see you" 

*Note:* You'll receive your first recipe suggestion today at 10 PM Australian time! 😊
_not getting any recipes? contact @DHRUV PATEL to update the list of recipes_"""
    
    try:
        send_whatsapp_message(phone_number, response)
        print(f"✅ Greeting with instructions sent to {phone_number}")
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

def handle_full_list(phone_number: str):
    """
    Handles requests for the full list of recipes
    
    Args:
        phone_number: User's phone number
    """
    all_recipes = get_all_recipe_names()

    try:        
        send_all_recipes_message(phone_number, all_recipes)
        print(f"✅ Full list sent to {phone_number}")
    except Exception as e:
        print(f"❌ Error sending full list: {e}")
        traceback.print_exc()

def is_no_response(message_text: str) -> bool:
    """
    Checks if the message is a "No" response
    
    Args:
        message_text: Lowercased and stripped message text
        
    Returns:
        bool: True if message is a "No" response
    """
    no_responses = [
        'no',
        'nope',
        'nah',
        'not yet',
        "haven't",
        "haven't yet",
        'not shopping',
        'not going',
        'didnt shop',
        "didn't shop"
    ]
    
    # Check if message is exactly one of these or starts with them
    for response in no_responses:
        if message_text == response or message_text.startswith(response + ' '):
            return True
    return False


def handle_no_response(phone_number: str):
    """
    Handles when user replies "No" during feedback window
    
    Process:
    1. Check for active feedback session
    2. If found, close session with 'cancelled' status
    3. Send acknowledgment
    """
    try:
        from utils.session_manager import get_active_feedback_session, close_feedback_session
        
        # Check for active or recently expired sessions
        active_session = get_active_feedback_session(phone_number, extend_if_found=False, include_recently_expired=True)
        
        if active_session:
            # Close the session
            close_feedback_session(active_session['id'], 'cancelled')
            
            send_whatsapp_message(
                phone_number,
                "👍 Got it! I've cancelled the feedback session. Feel free to send your receipt later if you change your mind."
            )
            print(f"✅ Session {active_session['id']} cancelled by user")
        else:
            # No active session, just acknowledge
            send_whatsapp_message(
                phone_number,
                "👍 No problem! Let me know when you're ready."
            )
            
    except Exception as e:
        print(f"❌ Error handling 'No' response: {e}")
        import traceback
        traceback.print_exc()


def is_no_more_receipts(message_text: str) -> bool:
    """
    Checks if the message indicates no more receipts to send
    
    Args:
        message_text: Lowercased and stripped message text
        
    Returns:
        bool: True if message indicates no more receipts
    """
    no_more_keywords = [
        'done',
        'no more',
        "that's all",
        "that's it",
        'finished',
        'all done',
        'no more receipts',
        'no other receipts',
        "don't have",
        "don't have any",
        'none',
        'no others'
    ]
    
    # Check if message matches any of these keywords
    for keyword in no_more_keywords:
        if keyword in message_text:
            return True
    return False


def handle_no_more_receipts(phone_number: str):
    """
    Handles when user confirms no more receipts during feedback window
    
    Process:
    1. Check for active feedback session
    2. If found, close session with 'receipt_submitted' status
    3. Trigger batch learning
    4. Send confirmation message
    """
    try:
        from utils.session_manager import get_active_feedback_session, close_feedback_session
        from handlers.learning_engine import trigger_batch_learning_if_needed
        
        # Check for active or recently expired sessions
        active_session = get_active_feedback_session(phone_number, extend_if_found=False, include_recently_expired=True)
        
        if active_session:
            # Close the session
            close_feedback_session(active_session['id'], 'receipt_submitted')
            
            # Trigger batch learning
            learning_triggered = trigger_batch_learning_if_needed()
            
            if learning_triggered:
                send_whatsapp_message(
                    phone_number,
                    "✅ Got it! I've closed the feedback session and started learning from your feedback. Thanks for helping me improve! 🎓"
                )
            else:
                send_whatsapp_message(
                    phone_number,
                    "✅ Got it! I've closed the feedback session. Thanks for your feedback! I'll use it to improve my predictions. 📊"
                )
            
            print(f"✅ Session {active_session['id']} closed - no more receipts")
        else:
            # No active session, just acknowledge
            send_whatsapp_message(
                phone_number,
                "👍 No problem! Let me know if you need anything else."
            )
            
    except Exception as e:
        print(f"❌ Error handling 'No more receipts': {e}")
        import traceback
        traceback.print_exc()

def is_grocery_command(command: str) -> bool:

    grocery_keywords = [
        'grocery',
        'groceries',
        'next shop',
        'shop list',
        'predict',
        'shopping list',
        'what should i buy',
        'what to buy'
    ]

    for commands in grocery_keywords:
        if commands in command:
            return True
    return False



def handle_grocery_request(phone_number: str):
    """
    Handles grocery prediction requests
    
    Args:
        phone_number: User's phone number
    """
    # TODO: Check receipt count and generate prediction

    receipt_count = get_receipt_count(user_phone=phone_number)
    print(f"📊 User {phone_number} has {receipt_count} receipts")

    MIN_RECEIPTS_NEEDED = int(os.getenv('MIN_RECEIPTS_NEEDED', '25'))

    if receipt_count < MIN_RECEIPTS_NEEDED:

        receipt_needed = MIN_RECEIPTS_NEEDED - receipt_count
        message = f"📊 You have {receipt_count} receipt(s) saved.\n\n"
        message += f"I need at least {MIN_RECEIPTS_NEEDED} receipts to make accurate predictions for your next purchase list.\n\n"
        message += f"So, once you have {receipt_needed} more receipts, I'll be able to generate a prediction for you with better accuracy."

        send_whatsapp_message(phone_number, message)
        print(f"⚠️ Not enough receipts ({receipt_count}/{MIN_RECEIPTS_NEEDED})")

    else:
        # Enough receipts! Ready for prediction

        try:
            send_whatsapp_message(phone_number, f"✅ Great! You have {receipt_count} receipt(s).\n\n🔄 Analyzing your shopping patterns... This may take a moment.")
            print(f"✅ Enough receipts ({receipt_count}) - ready for prediction")

            # Step 1: Fetch recent receipts

            print("📊 Fetching recent receipts...")

            recent_receipts = get_recent_receipts(user_phone=phone_number, limit=50)
            if not recent_receipts:
                send_whatsapp_message(phone_number, "⚠️ Couldn't fetch your receipts. Please try again later.")
                return


            # Step 2: Get receipt IDs
            receipt_ids = [receipt['id'] for receipt in recent_receipts]
            print(f"📦 Fetching items from {len(receipt_ids)} receipts...")


             # Step 3: Get all receipt items
            items = receipt_items_from_receipts(receipt_ids)
            
            if not items:
                send_whatsapp_message(phone_number, "⚠️ No items found in your receipts. Please try again later.")
                return

            # Step 4: Aggregate purchase patterns
            print("🔍 Analyzing purchase patterns...")
            patterns = aggregate_purchase_patterns(items)
            
            if not patterns:
                send_whatsapp_message(phone_number, "⚠️ Couldn't analyze your purchase patterns. Please try again later.")
                return

             # Step 5: Format data for LLM (includes learning insights if available)
            print("📝 Formatting data for AI...")
            prompt = format_data_for_llm(patterns, current_date=date.today(), user_phone=phone_number)
            
            if not prompt:
                send_whatsapp_message(phone_number, "⚠️ Error preparing prediction. Please try again later.")
                return

            
            # Step 6: Generate prediction with AI
            # Note: prediction_id will be None initially, created after prediction succeeds
            print("🤖 Generating prediction with AI...")
            prediction = generate_grocery_prediction(prompt, prediction_id=None, user_phone=phone_number)
            
            if not prediction:
                send_whatsapp_message(phone_number, "⚠️ Couldn't generate prediction. Please try again later.")
                return
            
            # Step 7: Save prediction to database
            print("💾 Saving prediction to database...")
            prediction_id = save_prediction(phone_number, prediction, llm_prompt=prompt)
            
            if not prediction_id:
                print("⚠️ Prediction generated but couldn't save to database")
                # Still send the message even if save failed
            else:
                # Step 7.5: Create feedback session only if prediction was saved
                session_id = create_feedback_session(prediction_id, phone_number)
                if session_id:
                    print(f"✅ Feedback session created: ID {session_id}")
                else:
                    print("⚠️ Failed to create feedback session")
            
            # Step 8: Format and send prediction message
            items_list = prediction.get('predicted_items', [])
            date_start = prediction.get('predicted_date_range_start', 'soon')
            date_end = prediction.get('predicted_date_range_end', 'soon')
            reasoning = prediction.get('reasoning', '')
            
            # Clean, concise prediction message
            message = f"🛒 *Shopping List*\n\n"
            message += f"*When:* {date_start} - {date_end}\n\n"
            message += f"*Items:*\n"
            
            for i, item in enumerate(items_list, 1):
                message += f"{i}. {item}\n"
            
            if reasoning:
                # Keep reasoning brief if it's too long
                brief_reasoning = reasoning[:150] + "..." if len(reasoning) > 150 else reasoning
                message += f"\n💡 {brief_reasoning}"
            
            message += f"\n\n📸 Send your receipt after shopping!"
            
            send_whatsapp_message(phone_number, message)
            print(f"✅ Prediction sent successfully! Prediction ID: {prediction_id}")


        except Exception as e:
            print(f"❌ Error generating prediction: {e}")
            import traceback
            traceback.print_exc()
            send_whatsapp_message(phone_number, "❌ Sorry, something went wrong generating your prediction. Please try again later.")
            





        




