"""
Session management utilities
Handles feedback session tracking for predictions
"""

from config.supabase_config import get_supabase_client
from datetime import datetime, timedelta


def create_feedback_session(prediction_id: int, user_phone: str) -> int:
    """
    Creates a feedback session when prediction is sent
    
    Process:
    1. Calculate expiration time (5 hours from now, or end of day, whichever is earlier)
    2. Create session record in feedback_sessions table
    3. Return session ID
    
    Args:
        prediction_id: The prediction ID this session is for
        user_phone: User's WhatsApp phone number
        
    Returns:
        int: Session ID if successful, None if failed
    """
    try:
        supabase = get_supabase_client()
        
        # Calculate expiration: 5 hours from now, or end of day (midnight), whichever is earlier
        now = datetime.now()
        expires_in_5_hours = now + timedelta(hours=5)
        
        # End of day (midnight)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Use whichever is earlier
        expires_at = min(expires_in_5_hours, end_of_day)
        
        # Create session record
        session_data = {
            'prediction_id': prediction_id,
            'user_phone': user_phone,
            'session_status': 'waiting',
            'expires_at': expires_at.isoformat()
        }
        
        result = supabase.table('feedback_sessions').insert(session_data).execute()
        
        if result.data and len(result.data) > 0:
            session_id = result.data[0]['id']
            print(f"✅ Feedback session created: ID {session_id} (expires at {expires_at})")
            return session_id
        else:
            print("❌ Failed to create feedback session")
            return None
            
    except Exception as e:
        print(f"❌ Error creating feedback session: {e}")
        import traceback
        traceback.print_exc()
        return None

def extend_feedback_session(session_id: int, additional_seconds: int = 60):
    """
    Extends a feedback session expiration time (useful when receipt is being processed)
    
    Args:
        session_id: Session ID to extend
        additional_seconds: How many seconds to add to expiration
    """
    try:
        supabase = get_supabase_client()
        
        # Get current expiration
        current = supabase.table('feedback_sessions')\
            .select('expires_at')\
            .eq('id', session_id)\
            .execute()
        
        if current.data:
            expires_str = current.data[0]['expires_at']
            # Handle different datetime formats - remove timezone info for parsing
            if 'Z' in expires_str:
                expires_str = expires_str.replace('Z', '')
            if '+' in expires_str:
                expires_str = expires_str.split('+')[0]
            if '.' in expires_str:
                expires_str = expires_str.split('.')[0]
            
            # Parse datetime (format: YYYY-MM-DDTHH:MM:SS)
            try:
                current_expires = datetime.fromisoformat(expires_str)
            except (ValueError, AttributeError):
                # Fallback: try parsing without microseconds
                try:
                    current_expires = datetime.strptime(expires_str, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    print(f"⚠️ Could not parse expiration date: {expires_str}")
                    return
            
            new_expires = current_expires + timedelta(seconds=additional_seconds)
            
            # Only update expires_at - don't update last_updated_at to avoid trigger error
            # NOTE: Database trigger has a bug - it tries to set 'updated_at' but table has 'last_updated_at'
            # This may fail, but we'll handle it gracefully
            try:
                supabase.table('feedback_sessions')\
                    .update({
                        'expires_at': new_expires.isoformat()
                        # Note: Not updating last_updated_at to avoid database trigger error
                    })\
                    .eq('id', session_id)\
                    .execute()
                
                print(f"⏰ Extended session {session_id} expiration by {additional_seconds} seconds (new expires: {new_expires})")
            except Exception as update_error:
                # Update failed due to trigger issue, but session might still be valid
                print(f"⚠️ Could not extend session {session_id} expiration (trigger issue): {update_error}")
                print(f"ℹ️ Session expiration update failed, but session may still be active")
    except Exception as e:
        print(f"⚠️ Could not extend session {session_id}: {e}")
        import traceback
        traceback.print_exc()


def get_active_feedback_session(user_phone: str, extend_if_found: bool = False, include_recently_expired: bool = False) -> dict | None:
    """
    Gets the active feedback session for a user (if any)
    
    Process:
    1. Query feedback_sessions table for this user
    2. Filter by 'waiting' status
    3. Check if session hasn't expired (or recently expired if include_recently_expired=True)
    4. Optionally extend session if found (to prevent expiration during processing)
    5. Return most recent active session
    
    Args:
        user_phone: User's WhatsApp phone number
        extend_if_found: If True, extend session expiration by 120 seconds when found
        include_recently_expired: If True, also check for sessions expired within last 2 minutes
        
    Returns:
        dict: Session data if found, None if no active session
    """
    try:
        supabase = get_supabase_client()
        
        # Get active sessions (waiting status, not expired)
        now = datetime.now()
        now_iso = now.isoformat()
        
        # First try: active (not expired) sessions
        result = supabase.table('feedback_sessions')\
            .select('*')\
            .eq('user_phone', user_phone)\
            .eq('session_status', 'waiting')\
            .gt('expires_at', now_iso)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if result.data and len(result.data) > 0:
            session = result.data[0]
            print(f"✅ Found active feedback session: ID {session['id']} for prediction {session['prediction_id']}")
            
            # Extend session to prevent expiration during OCR processing (extend by 120 seconds for safety)
            if extend_if_found:
                extend_feedback_session(session['id'], additional_seconds=120)
            
            return session
        
        # Second try: recently expired sessions (within last 2 minutes) - for cases where extension failed
        if include_recently_expired:
            two_minutes_ago = (now - timedelta(minutes=2)).isoformat()
            result = supabase.table('feedback_sessions')\
                .select('*')\
                .eq('user_phone', user_phone)\
                .eq('session_status', 'waiting')\
                .gte('expires_at', two_minutes_ago)\
                .lt('expires_at', now_iso)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                session = result.data[0]
                print(f"⚠️ Found recently expired session: ID {session['id']} (expired but within 2 min grace period)")
                # Extend it now
                if extend_if_found:
                    extend_feedback_session(session['id'], additional_seconds=120)
                return session
        
        print(f"ℹ️ No active feedback session for {user_phone}")
        return None
            
    except Exception as e:
        print(f"❌ Error getting active feedback session: {e}")
        import traceback
        traceback.print_exc()
        return None

def close_feedback_session(session_id: int, reason: str = 'completed'):
    """
    Closes a feedback session
    
    Args:
        session_id: Session ID to close
        reason: Reason for closing ('receipt_submitted', 'expired', 'cancelled', 'no_response')
    """
    try:
        supabase = get_supabase_client()
        
        # Map reason to session status
        status_map = {
            'receipt_submitted': 'receipt_submitted',
            'expired': 'expired',
            'cancelled': 'cancelled',
            'no_response': 'no_response'
        }
        
        new_status = status_map.get(reason, 'completed')
        
        # Only update session_status - don't update last_updated_at to avoid trigger error
        # The trigger tries to set 'updated_at' which doesn't exist in this table
        update_data = {
            'session_status': new_status
            # Note: Not updating last_updated_at to avoid database trigger error
        }
        
        try:
            supabase.table('feedback_sessions')\
                .update(update_data)\
                .eq('id', session_id)\
                .execute()
            
            print(f"✅ Session {session_id} closed: {reason}")
        except Exception as update_error:
            # If update fails due to trigger, try with raw SQL or just log
            print(f"⚠️ Could not update session status via Supabase (trigger issue): {update_error}")
            # Session status update failed, but we'll continue
            print(f"ℹ️ Session {session_id} should be marked as {new_status} (update failed due to DB trigger)")
        
    except Exception as e:
        print(f"❌ Error closing session: {e}")
        import traceback
        traceback.print_exc()


def check_and_send_reminders():
    """
    Checks for sessions that need reminders (5 hours passed, no receipt)
    Called by scheduler every 30 minutes
    """
    try:
        from handlers.whatsapp_hanlder import send_whatsapp_message
        
        supabase = get_supabase_client()
        now = datetime.now()
        # Reminder threshold: 5 hours ago
        reminder_threshold = now - timedelta(hours=5)
        
        # Find sessions that:
        # - Status is 'waiting'
        # - Created more than 5 hours ago
        # - Reminder not sent yet
        # - Not expired yet
        result = supabase.table('feedback_sessions')\
            .select('*')\
            .eq('session_status', 'waiting')\
            .lt('created_at', reminder_threshold.isoformat())\
            .is_('reminder_sent_at', 'null')\
            .gt('expires_at', now.isoformat())\
            .execute()
        
        sessions = result.data if result.data else []
        
        for session in sessions:
            user_phone = session['user_phone']
            session_id = session['id']
            
            reminder_message = (
                "⏰ *Reminder*\n\n"
                "Did you go shopping? Send your receipt photo to check my prediction accuracy.\n\n"
                "Not shopping today? Reply 'No' to stop reminders."
            )

            try:
                send_whatsapp_message(user_phone, reminder_message)
                print(f"✅ Reminder sent for session {session_id}")
                
                # Mark reminder as sent (only update reminder_sent_at to avoid trigger error)
                # NOTE: Database trigger has a bug - it tries to set 'updated_at' but table has 'last_updated_at'
                # This update may fail, but reminder was already sent, so we continue
                try:
                    supabase.table('feedback_sessions')\
                        .update({
                            'reminder_sent_at': now.isoformat()
                            # Note: Not updating last_updated_at to avoid database trigger error
                        })\
                        .eq('id', session_id)\
                        .execute()
                    print(f"✅ Reminder marked as sent in database for session {session_id}")
                except Exception as db_error:
                    # Database update failed (likely trigger issue), but reminder was sent
                    print(f"⚠️ Could not update reminder_sent_at in database (trigger issue): {db_error}")
                    print(f"ℹ️ Reminder was sent successfully, but database update failed")
                    
            except Exception as e:
                print(f"❌ Error sending reminder for session {session_id}: {e}")
                import traceback
                traceback.print_exc()
        
        if sessions:
            print(f"📧 Sent {len(sessions)} reminder(s)")
            
    except Exception as e:
        print(f"❌ Error checking reminders: {e}")
        import traceback
        traceback.print_exc()