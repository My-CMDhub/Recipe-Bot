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
from utils.session_manager import check_and_send_reminders
from apscheduler.triggers.interval import IntervalTrigger
from utils.recipe_utils import get_random_recipe_not_sent_today, record_recipe_sent, get_all_recipe_names, reset_daily_history
from datetime import datetime

load_dotenv()

# Australian timezone (handles both AEST and AEDT automatically)
AUSTRALIA_TZ = pytz.timezone('Australia/Sydney')

def get_recipient_phone_numbers():
    """
    Gets list of recipient phone numbers from environment variable
    Supports comma-separated phone numbers
    
    Returns:
        list: List of phone numbers (without + sign, trimmed)
    """
    recipient_phones_env = os.getenv('RECIPIENT_PHONE_NUMBER', '')
    
    if not recipient_phones_env:
        return []
    
    # Split by comma and clean up each phone number
    phone_numbers = [phone.strip() for phone in recipient_phones_env.split(',') if phone.strip()]
    
    return phone_numbers

def send_daily_recipe():
    """
    Sends daily recipe suggestion to all configured phone numbers
    This function is called by the scheduler
    
    IMPORTANT: This function is called automatically by APScheduler.
    Make sure scheduler is running and properly configured.
    """
    try:
        print(f"\n{'='*60}")
        print(f"🍽️ SCHEDULER TRIGGERED: Daily Recipe Job")
        print(f"{'='*60}")
        print(f"⏰ Time: {datetime.now(AUSTRALIA_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Get list of recipient phone numbers
        recipient_phones = get_recipient_phone_numbers()
        
        if not recipient_phones:
            print("⚠️ WARNING: RECIPIENT_PHONE_NUMBER not set in .env")
            print("   Cannot send recipes without recipient phone numbers!")
            return
        
        print(f"📱 Recipients: {len(recipient_phones)} phone number(s)")
        for i, phone in enumerate(recipient_phones, 1):
            print(f"   {i}. {phone}")
        
        # Get a random recipe not sent today
        recipe = get_random_recipe_not_sent_today()
        
        if recipe:
            recipe_id = recipe['id']
            recipe_name = recipe['name']
            
            print(f"✅ Found recipe: {recipe_name} (ID: {recipe_id})")
            
            # Send to all recipients
            success_count = 0
            for phone_number in recipient_phones:
                try:
                    print(f"📤 Sending to {phone_number}...")
                    result = send_recipe_message(phone_number, recipe_name)
                    success_count += 1
                    print(f"✅ Sent to {phone_number}")
                except Exception as e:
                    print(f"❌ Failed to send to {phone_number}: {e}")
            
            print(f"✅ Recipe sent to {success_count}/{len(recipient_phones)} recipients")
            
            # Record that we sent this recipe (only once, not per recipient)
            if success_count > 0:
                record_recipe_sent(recipe_id)
                print(f"💾 Recipe recorded in history")
        else:
            # All recipes sent today - send full list to all recipients
            print("⚠️ All recipes have been sent today")
            all_recipes = get_all_recipe_names()
            
            from handlers.whatsapp_hanlder import send_all_recipes_message
            success_count = 0
            for phone_number in recipient_phones:
                try:
                    send_all_recipes_message(phone_number, all_recipes)
                    success_count += 1
                except Exception as e:
                    print(f"❌ Failed to send full list to {phone_number}: {e}")
            
            print(f"✅ Full recipe list sent to {success_count}/{len(recipient_phones)} recipients")
            
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
    
    CRITICAL for Heroku: Uses daemon=False to ensure threads persist
    and survive dyno restarts.
    
    Returns:
        BackgroundScheduler: Configured scheduler instance
    """
    # Create scheduler with daemon=False for Heroku compatibility
    # This ensures threads persist and scheduler survives dyno restarts
    scheduler = BackgroundScheduler(
        timezone=AUSTRALIA_TZ,
        daemon=False,  # CRITICAL: Non-daemon threads persist on Heroku
        job_defaults={
            'coalesce': True,  # Combine multiple pending executions into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 300  # 5 minutes grace period for missed jobs
        }
    )
    
    # Get recipe send time from environment (default to 22:00)
    recipe_time = os.getenv('RECIPE_SEND_TIME', '22:00')
    try:
        hour, minute = map(int, recipe_time.split(':'))
    except ValueError:
        print(f"⚠️ Invalid RECIPE_SEND_TIME format: {recipe_time}. Using default 22:00")
        hour, minute = 22, 0
    
    current_time = datetime.now(AUSTRALIA_TZ)
    print(f"\n⏰ Setting up scheduler:")
    print(f"   - Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   - Daily recipe: {hour:02d}:{minute:02d} Australian time")
    print(f"   - Daily reset: 00:00 Australian time")
    print(f"   - Feedback reminders: Every 30 minutes")
    
    # Schedule daily recipe sending
    try:
        scheduler.add_job(
            func=send_daily_recipe,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=AUSTRALIA_TZ),
            id='daily_recipe',
            name='Send daily recipe suggestion',
            replace_existing=True
        )
        print(f"✅ Scheduled daily recipe job (ID: daily_recipe)")
    except Exception as e:
        print(f"❌ Failed to schedule daily recipe job: {e}")
        import traceback
        traceback.print_exc()
    
    # Schedule daily history reset at midnight
    try:
        scheduler.add_job(
            func=reset_daily_history_job,
            trigger=CronTrigger(hour=0, minute=0, timezone=AUSTRALIA_TZ),
            id='daily_reset',
            name='Reset daily recipe history',
            replace_existing=True
        )
        print(f"✅ Scheduled daily reset job (ID: daily_reset)")
    except Exception as e:
        print(f"❌ Failed to schedule daily reset job: {e}")
        import traceback
        traceback.print_exc()
    
    # Schedule feedback reminder checks every 30 minutes
    try:
        scheduler.add_job(
            func=check_and_send_reminders,
            trigger=IntervalTrigger(minutes=30),
            id='check_feedback_reminders',
            name='Check and send feedback reminders',
            replace_existing=True
        )
        print(f"✅ Scheduled feedback reminders job (ID: check_feedback_reminders)")
    except Exception as e:
        print(f"❌ Failed to schedule feedback reminders job: {e}")
        import traceback
        traceback.print_exc()
    
    # Start the scheduler
    try:
        scheduler.start()
        print("✅ Scheduler started successfully!")
        
        # Verify scheduler is running
        if scheduler.running:
            print(f"✅ Scheduler status: RUNNING")
            print(f"   Active jobs: {len(scheduler.get_jobs())}")
            for job in scheduler.get_jobs():
                next_run = job.next_run_time
                if next_run:
                    print(f"   - {job.name}: Next run at {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                else:
                    print(f"   - {job.name}: No next run scheduled")
        else:
            print("⚠️ WARNING: Scheduler started but status is not RUNNING!")
            
    except Exception as e:
        print(f"❌ Failed to start scheduler: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return scheduler

