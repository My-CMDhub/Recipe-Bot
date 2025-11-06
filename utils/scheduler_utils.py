"""
Scheduler utilities for daily recipe automation
Handles APScheduler setup and daily recipe sending
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import os
from dotenv import load_dotenv
from handlers.whatsapp_hanlder import send_recipe_message
from utils.recipe_utils import get_random_recipe_not_sent_today, record_recipe_sent, get_all_recipe_names, reset_daily_history
from datetime import datetime

load_dotenv()

# Australian timezone (handles both AEST and AEDT automatically)
AUSTRALIA_TZ = pytz.timezone('Australia/Sydney')

def send_daily_recipe():
    """
    Sends daily recipe suggestion to the configured phone number
    This function is called by the scheduler
    """
    try:
        # Get recipient phone number from environment
        recipient_phone = os.getenv('RECIPIENT_PHONE_NUMBER')
        
        if not recipient_phone:
            print("⚠️ WARNING: RECIPIENT_PHONE_NUMBER not set in .env")
            return
        
        print(f"\n🍽️ [{datetime.now(AUSTRALIA_TZ).strftime('%Y-%m-%d %H:%M:%S')}] Sending daily recipe...")
        
        # Get a random recipe not sent today
        recipe = get_random_recipe_not_sent_today()
        
        if recipe:
            recipe_id = recipe['id']
            recipe_name = recipe['name']
            
            print(f"✅ Found recipe: {recipe_name} (ID: {recipe_id})")
            print(f"📤 Sending to {recipient_phone}...")
            
            # Send the recipe
            result = send_recipe_message(recipient_phone, recipe_name)
            print(f"✅ Recipe sent successfully!")
            
            # Record that we sent this recipe
            record_recipe_sent(recipe_id)
            print(f"💾 Recipe recorded in history")
        else:
            # All recipes sent today - send full list
            print("⚠️ All recipes have been sent today")
            all_recipes = get_all_recipe_names()
            
            from handlers.whatsapp_hanlder import send_all_recipes_message
            send_all_recipes_message(recipient_phone, all_recipes)
            print(f"✅ Full recipe list sent")
            
    except Exception as e:
        print(f"❌ Error sending daily recipe: {e}")
        import traceback
        traceback.print_exc()

def reset_daily_history_job():
    """
    Resets daily recipe history at midnight Australian time
    This allows recipes to be sent again the next day
    """
    try:
        print(f"\n🔄 [{datetime.now(AUSTRALIA_TZ).strftime('%Y-%m-%d %H:%M:%S')}] Resetting daily history...")
        reset_daily_history()
        print("✅ Daily history reset complete")
    except Exception as e:
        print(f"❌ Error resetting daily history: {e}")
        import traceback
        traceback.print_exc()

def setup_scheduler():
    """
    Sets up and starts the APScheduler with daily recipe job
    
    Returns:
        BackgroundScheduler: Configured scheduler instance
    """
    # Create scheduler
    scheduler = BackgroundScheduler(timezone=AUSTRALIA_TZ)
    
    # Get recipe send time from environment (default to 22:00)
    recipe_time = os.getenv('RECIPE_SEND_TIME', '22:00')
    hour, minute = map(int, recipe_time.split(':'))
    
    print(f"\n⏰ Setting up scheduler:")
    print(f"   - Daily recipe: {hour:02d}:{minute:02d} Australian time")
    print(f"   - Daily reset: 00:00 Australian time")
    
    # Schedule daily recipe sending
    scheduler.add_job(
        func=send_daily_recipe,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=AUSTRALIA_TZ),
        id='daily_recipe',
        name='Send daily recipe suggestion',
        replace_existing=True
    )
    
    # Schedule daily history reset at midnight
    scheduler.add_job(
        func=reset_daily_history_job,
        trigger=CronTrigger(hour=0, minute=0, timezone=AUSTRALIA_TZ),
        id='daily_reset',
        name='Reset daily recipe history',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    print("✅ Scheduler started successfully!")
    
    return scheduler

