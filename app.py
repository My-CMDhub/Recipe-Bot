
"""Main Flask application for WhatsApp Recipe Bot
This is the entry point that ties everything together"""

from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import json
import traceback
from datetime import datetime
from handlers.whatsapp_hanlder import send_recipe_message
from handlers.webhook_handler import process_incoming_message
from utils.recipe_utils import seed_initial_recipes
from utils.scheduler_utils import setup_scheduler, send_daily_recipe

load_dotenv()

app = Flask(__name__)

# Check if debug mode is enabled
DEBUG_MODE = os.getenv('DEBUG', 'False').lower() == 'true'

# Setup and start the scheduler for daily recipe automation
print("\n🚀 Initializing Recipe Bot...")
scheduler = setup_scheduler()

# Add logging for all requests (only in debug mode)
@app.before_request
def log_request_info():
    """Log all incoming requests for debugging (only in debug mode)"""
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] {request.method} {request.path}")
        if request.is_json:
            print(f"JSON Body: {json.dumps(request.get_json(), indent=2)}")
        elif request.form:
            print(f"Form Data: {dict(request.form)}")
        elif request.args:
            print(f"Query Params: {dict(request.args)}")
        print("-" * 50)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'WhatsApp Recipe Bot is running!'
    }), 200

@app.route('/test-webhook', methods=['GET', 'POST'])
def test_webhook():
    """Test endpoint to verify webhook is reachable (development only)"""
    if not DEBUG_MODE:
        return jsonify({'error': 'Not available in production'}), 403
    
    if DEBUG_MODE:
        print("\n🧪 TEST WEBHOOK ENDPOINT CALLED")
        print(f"Method: {request.method}")
    
    return jsonify({
        'status': 'success',
        'message': 'Webhook endpoint is reachable!',
        'method': request.method,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/seed-recipes', methods=['POST'])
def seed_recipes():

    try:
        seed_initial_recipes()
        return jsonify({
            'status': 'success',
            'message': 'Recipes seeded successfully'
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/test-recipe', methods=['POST'])
def send_recipe():
    """Test endpoint to manually send a recipe (development only)"""
    if not DEBUG_MODE:
        return jsonify({'error': 'Not available in production'}), 403
    
    try:
        data = request.get_json()
        recipient_phone = data.get('phone_number')

        if not recipient_phone:
            return jsonify({
                'status': 'error',
                'message': 'Recipient phone number is required'
            }), 400
            
        result = send_recipe_message(recipient_phone, 'Pasta Carbonara')
        return jsonify({
            'status': 'success',
            'message': 'Recipe sent successfully',
            'result': result
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/test-scheduler', methods=['POST'])
def test_scheduler():
    """
    Test endpoint to trigger the daily recipe scheduler function immediately (development only)
    """
    if not DEBUG_MODE:
        return jsonify({'error': 'Not available in production'}), 403
    
    try:
        if DEBUG_MODE:
            print("\n🧪 TESTING SCHEDULER - Triggering send_daily_recipe()...")
        
        send_daily_recipe()
        
        return jsonify({
            'status': 'success',
            'message': 'Scheduler function executed! Check your WhatsApp and Flask console for results.'
        }), 200
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"❌ Scheduler test error: {e}")
            traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Webhook verification endpoint - WhatsApp calls this to verify your webhook"""
    if DEBUG_MODE:
        print("\n🔍 WEBHOOK VERIFICATION REQUEST")
        print(f"Mode: {request.args.get('hub.mode')}")
    
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN')
    
    # Check if mode is 'subscribe' and token matches
    if mode == 'subscribe' and token == verify_token:
        if DEBUG_MODE:
            print("✅ Verification successful! Returning challenge.")
        return challenge, 200
    else:
        if DEBUG_MODE:
            print("❌ Verification failed!")
        return jsonify({'error': 'Verification failed'}), 403

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Main webhook endpoint - receives incoming messages
    WhatsApp calls this whenever you receive a message
    """
    if DEBUG_MODE:
        print("\n📨 POST WEBHOOK REQUEST RECEIVED")
    
    try:
        webhook_data = request.get_json()
        
        if webhook_data is None:
            if DEBUG_MODE:
                print("⚠️ WARNING: No JSON data received!")
            return jsonify({'status': 'error', 'message': 'No JSON data'}), 200

        if DEBUG_MODE:
            print("\n" + "="*60)
            print("INCOMING WEBHOOK DATA:")
            print("="*60)
            print(json.dumps(webhook_data, indent=2))
            print("="*60 + "\n")
            print("🔄 Processing incoming message...")
        
        process_incoming_message(webhook_data)
        
        if DEBUG_MODE:
            print("✅ Processing complete")
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"\n❌ WEBHOOK ERROR: {e}")
            traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 200


if __name__ == "__main__":
    try:
        port = int(os.getenv('PORT', 5001))
        debug = DEBUG_MODE
        
        print("\n✅ Flask app starting...")
        print(f"📱 Webhook endpoint: /webhook")
        print(f"⏰ Daily recipe scheduled at configured time")
        print(f"🌏 Timezone: Australia/Sydney")
        print(f"🔧 Debug mode: {debug}")
        print(f"🌐 Port: {port}")
        
        app.run(debug=debug, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        scheduler.shutdown()
        print("✅ Scheduler stopped")