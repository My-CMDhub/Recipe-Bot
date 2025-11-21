"""
Learning Engine
Handles batch learning from feedback to improve prediction accuracy
"""

from config.supabase_config import get_supabase_client
from datetime import datetime, timedelta
from collections import defaultdict


def get_pending_feedbacks_count() -> int:
    """
    Gets count of feedbacks that haven't been used for learning yet
    
    Returns:
        int: Number of pending feedbacks
    """
    try:
        supabase = get_supabase_client()
        
        # Count feedbacks that don't have a learning update yet
        # We'll check by looking at feedbacks without a learning_update_id reference
        # For simplicity, we'll count all feedbacks and check if we have enough
        result = supabase.table('prediction_feedback')\
            .select('id', count='exact')\
            .execute()
        
        return result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
        
    except Exception as e:
        print(f"❌ Error getting feedback count: {e}")
        return 0


def get_recent_feedbacks(limit: int = 10) -> list:
    """
    Gets recent feedbacks for batch learning
    
    Args:
        limit: Maximum number of feedbacks to get
        
    Returns:
        list: List of feedback dictionaries
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('prediction_feedback')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"❌ Error getting recent feedbacks: {e}")
        import traceback
        traceback.print_exc()
        return []


def analyze_feedback_patterns(feedbacks: list) -> dict:
    """
    Analyzes feedback patterns to identify learning opportunities
    
    Process:
    1. Calculate average accuracy
    2. Identify commonly missing items (predicted but not bought)
    3. Identify commonly extra items (bought but not predicted)
    4. Calculate accuracy trends
    
    Args:
        feedbacks: List of feedback dictionaries
        
    Returns:
        dict: Analysis results
    """
    try:
        if not feedbacks:
            return {}
        
        # Calculate average accuracy
        accuracies = [fb.get('match_percentage', 0) for fb in feedbacks if fb.get('match_percentage')]
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
        
        # Collect all missing items (predicted but not bought)
        all_missing_items = {}
        for fb in feedbacks:
            missing = fb.get('missing_items', [])
            for item in missing:
                all_missing_items[item] = all_missing_items.get(item, 0) + 1
        
        # Collect all extra items (bought but not predicted)
        all_extra_items = {}
        for fb in feedbacks:
            extra = fb.get('extra_items', [])
            for item in extra:
                all_extra_items[item] = all_extra_items.get(item, 0) + 1
        
        # Sort by frequency
        top_missing = sorted(all_missing_items.items(), key=lambda x: x[1], reverse=True)[:5]
        top_extra = sorted(all_extra_items.items(), key=lambda x: x[1], reverse=True)[:5]
        
        analysis = {
            'feedback_count': len(feedbacks),
            'average_accuracy': round(avg_accuracy, 2),
            'top_missing_items': [{'item': item, 'frequency': freq} for item, freq in top_missing],
            'top_extra_items': [{'item': item, 'frequency': freq} for item, freq in top_extra],
            'accuracy_trend': 'improving' if len(accuracies) > 1 and accuracies[0] > accuracies[-1] else 'stable'
        }
        
        print(f"📊 Analyzed {len(feedbacks)} feedbacks: Avg accuracy {avg_accuracy:.1f}%")
        return analysis
        
    except Exception as e:
        print(f"❌ Error analyzing feedback patterns: {e}")
        import traceback
        traceback.print_exc()
        return {}


def save_learning_update(analysis: dict, feedback_count: int) -> int:
    """
    Saves learning update to learning_updates table
    
    Args:
        analysis: Analysis results from analyze_feedback_patterns()
        feedback_count: Number of feedbacks used
        
    Returns:
        int: Learning update ID if successful, None if failed
    """
    try:
        supabase = get_supabase_client()
        
        learning_data = {
            'update_type': 'batch_learning',
            'feedback_count': feedback_count,
            'update_summary': analysis,
            'accuracy_improvement': None  # We'll calculate this when we have historical data
        }
        
        result = supabase.table('learning_updates').insert(learning_data).execute()
        
        if result.data and len(result.data) > 0:
            update_id = result.data[0]['id']
            print(f"💾 Learning update saved: ID {update_id}")
            return update_id
        else:
            print("❌ Failed to save learning update")
            return None
            
    except Exception as e:
        print(f"❌ Error saving learning update: {e}")
        import traceback
        traceback.print_exc()
        return None


def trigger_batch_learning_if_needed() -> bool:
    """
    Triggers batch learning if we have enough feedbacks (threshold: 5)
    
    Process:
    1. Check feedback count
    2. If >= 5, get recent feedbacks
    3. Analyze patterns
    4. Save learning update
    
    Returns:
        bool: True if learning was triggered, False otherwise
    """
    try:
        BATCH_LEARNING_THRESHOLD = 5
        
        # Get feedback count
        feedback_count = get_pending_feedbacks_count()
        
        if feedback_count < BATCH_LEARNING_THRESHOLD:
            print(f"ℹ️ Not enough feedbacks for batch learning ({feedback_count}/{BATCH_LEARNING_THRESHOLD})")
            return False
        
        print(f"🧠 Triggering batch learning with {feedback_count} feedbacks...")
        
        # Get recent feedbacks
        feedbacks = get_recent_feedbacks(limit=BATCH_LEARNING_THRESHOLD)
        
        if not feedbacks:
            print("⚠️ No feedbacks found for learning")
            return False
        
        # Analyze patterns
        analysis = analyze_feedback_patterns(feedbacks)
        
        if not analysis:
            print("⚠️ Couldn't analyze feedback patterns")
            return False
        
        # Save learning update
        update_id = save_learning_update(analysis, len(feedbacks))
        
        if update_id:
            print(f"✅ Batch learning completed! Update ID: {update_id}")
            print(f"   📊 Average accuracy: {analysis.get('average_accuracy', 0):.1f}%")
            print(f"   📝 Top missing items: {len(analysis.get('top_missing_items', []))}")
            print(f"   📝 Top extra items: {len(analysis.get('top_extra_items', []))}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error triggering batch learning: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_aggregated_learning_summary(user_phone: str = None, days_back: int = 60, max_updates: int = 10) -> dict:
    """
    Gets aggregated learning insights from recent learning updates
    
    Strategy:
    1. Fetch last N learning updates (default: 10)
    2. Filter by recency (default: last 60 days)
    3. Aggregate patterns across all updates
    4. Only include items appearing in 2+ updates (signal strength)
    5. Limit to top 5 missing + top 5 extra items
    
    This keeps the learning section small (~150 tokens max) and focused on
    recent, relevant patterns that appear consistently.
    
    Args:
        user_phone: Optional user phone to filter by user (not implemented yet)
        days_back: How many days back to look (default: 60)
        max_updates: Maximum number of learning updates to fetch (default: 10)
        
    Returns:
        dict: Aggregated learning summary with:
            - top_missing_items: List of items often predicted but not bought
            - top_extra_items: List of items often bought but not predicted
            - average_accuracy: Average accuracy across all updates
            - accuracy_trend: 'improving', 'stable', or 'declining'
            - update_count: Number of learning updates used
            - has_learning: Boolean indicating if learning data exists
    """
    try:
        supabase = get_supabase_client()
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Fetch recent learning updates
        result = supabase.table('learning_updates')\
            .select('*')\
            .gte('created_at', cutoff_date.isoformat())\
            .order('created_at', desc=True)\
            .limit(max_updates)\
            .execute()
        
        updates = result.data if result.data else []
        
        if not updates:
            print(f"ℹ️ No learning updates found in last {days_back} days")
            return {
                'has_learning': False,
                'top_missing_items': [],
                'top_extra_items': [],
                'average_accuracy': 0,
                'accuracy_trend': 'stable',
                'update_count': 0
            }
        
        # Aggregate patterns across all updates
        all_missing_items = defaultdict(int)
        all_extra_items = defaultdict(int)
        all_accuracies = []
        
        for update in updates:
            summary = update.get('update_summary', {})
            
            # Collect missing items
            missing_items = summary.get('top_missing_items', [])
            for item_data in missing_items:
                item_name = item_data.get('item', '')
                frequency = item_data.get('frequency', 1)
                if item_name:
                    all_missing_items[item_name] += frequency
            
            # Collect extra items
            extra_items = summary.get('top_extra_items', [])
            for item_data in extra_items:
                item_name = item_data.get('item', '')
                frequency = item_data.get('frequency', 1)
                if item_name:
                    all_extra_items[item_name] += frequency
            
            # Collect accuracies
            avg_acc = summary.get('average_accuracy', 0)
            if avg_acc:
                all_accuracies.append(avg_acc)
        
        # Filter: Only include items appearing in 2+ updates (signal strength)
        # Count how many updates mentioned each item
        missing_item_counts = defaultdict(int)
        extra_item_counts = defaultdict(int)
        
        for update in updates:
            summary = update.get('update_summary', {})
            missing_items = summary.get('top_missing_items', [])
            extra_items = summary.get('top_extra_items', [])
            
            for item_data in missing_items:
                item_name = item_data.get('item', '')
                if item_name:
                    missing_item_counts[item_name] += 1
            
            for item_data in extra_items:
                item_name = item_data.get('item', '')
                if item_name:
                    extra_item_counts[item_name] += 1
        
        # Filter and sort missing items (must appear in 2+ updates)
        filtered_missing = {
            item: freq for item, freq in all_missing_items.items()
            if missing_item_counts[item] >= 2
        }
        top_missing = sorted(filtered_missing.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Filter and sort extra items (must appear in 2+ updates)
        filtered_extra = {
            item: freq for item, freq in all_extra_items.items()
            if extra_item_counts[item] >= 2
        }
        top_extra = sorted(filtered_extra.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calculate average accuracy
        avg_accuracy = sum(all_accuracies) / len(all_accuracies) if all_accuracies else 0
        
        # Determine accuracy trend (compare first half vs second half)
        accuracy_trend = 'stable'
        if len(all_accuracies) >= 4:
            mid_point = len(all_accuracies) // 2
            first_half_avg = sum(all_accuracies[:mid_point]) / mid_point
            second_half_avg = sum(all_accuracies[mid_point:]) / (len(all_accuracies) - mid_point)
            
            if second_half_avg > first_half_avg + 2:  # 2% improvement threshold
                accuracy_trend = 'improving'
            elif second_half_avg < first_half_avg - 2:  # 2% decline threshold
                accuracy_trend = 'declining'
        
        summary = {
            'has_learning': True,
            'top_missing_items': [item for item, freq in top_missing],
            'top_extra_items': [item for item, freq in top_extra],
            'average_accuracy': round(avg_accuracy, 2),
            'accuracy_trend': accuracy_trend,
            'update_count': len(updates)
        }
        
        print(f"📊 Aggregated learning from {len(updates)} updates: {len(top_missing)} missing, {len(top_extra)} extra items")
        return summary
        
    except Exception as e:
        print(f"❌ Error getting aggregated learning summary: {e}")
        import traceback
        traceback.print_exc()
        return {
            'has_learning': False,
            'top_missing_items': [],
            'top_extra_items': [],
            'average_accuracy': 0,
            'accuracy_trend': 'stable',
            'update_count': 0
        }


def get_learning_analytics(days_back: int = 90) -> dict:
    """
    Gets comprehensive analytics about the learning system for monitoring
    
    This function provides insights you can check in Supabase to see if
    the system is improving over time.
    
    Args:
        days_back: How many days back to analyze (default: 90)
        
    Returns:
        dict: Analytics including:
            - total_learning_updates: Total number of learning updates
            - learning_updates_by_period: Count by time period
            - accuracy_over_time: Accuracy trends
            - most_common_missing_items: Items most often predicted but not bought
            - most_common_extra_items: Items most often bought but not predicted
            - average_accuracy: Overall average accuracy
            - accuracy_trend: Trend direction
    """
    try:
        supabase = get_supabase_client()
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Fetch all learning updates in the period
        result = supabase.table('learning_updates')\
            .select('*')\
            .gte('created_at', cutoff_date.isoformat())\
            .order('created_at', desc=True)\
            .execute()
        
        updates = result.data if result.data else []
        
        if not updates:
            return {
                'total_learning_updates': 0,
                'learning_updates_by_period': {},
                'accuracy_over_time': [],
                'most_common_missing_items': [],
                'most_common_extra_items': [],
                'average_accuracy': 0,
                'accuracy_trend': 'insufficient_data'
            }
        
        # Group by time periods (weekly)
        updates_by_week = defaultdict(int)
        accuracy_by_week = defaultdict(list)
        all_missing_items = defaultdict(int)
        all_extra_items = defaultdict(int)
        all_accuracies = []
        
        for update in updates:
            created_at = update.get('created_at', '')
            summary = update.get('update_summary', {})
            
            # Parse date and group by week
            try:
                update_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                week_key = update_date.strftime('%Y-W%W')
                updates_by_week[week_key] += 1
                
                avg_acc = summary.get('average_accuracy', 0)
                if avg_acc:
                    accuracy_by_week[week_key].append(avg_acc)
                    all_accuracies.append(avg_acc)
            except:
                pass
            
            # Aggregate items
            missing_items = summary.get('top_missing_items', [])
            for item_data in missing_items:
                item_name = item_data.get('item', '')
                freq = item_data.get('frequency', 1)
                if item_name:
                    all_missing_items[item_name] += freq
            
            extra_items = summary.get('top_extra_items', [])
            for item_data in extra_items:
                item_name = item_data.get('item', '')
                freq = item_data.get('frequency', 1)
                if item_name:
                    all_extra_items[item_name] += freq
        
        # Calculate weekly average accuracies
        accuracy_over_time = []
        for week in sorted(updates_by_week.keys()):
            week_accuracies = accuracy_by_week[week]
            if week_accuracies:
                avg_acc = sum(week_accuracies) / len(week_accuracies)
                accuracy_over_time.append({
                    'period': week,
                    'average_accuracy': round(avg_acc, 2),
                    'update_count': updates_by_week[week]
                })
        
        # Get top items
        top_missing = sorted(all_missing_items.items(), key=lambda x: x[1], reverse=True)[:10]
        top_extra = sorted(all_extra_items.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Calculate overall average and trend
        overall_avg = sum(all_accuracies) / len(all_accuracies) if all_accuracies else 0
        
        # Determine trend (compare first third vs last third)
        trend = 'stable'
        if len(all_accuracies) >= 6:
            third = len(all_accuracies) // 3
            first_third_avg = sum(all_accuracies[:third]) / third
            last_third_avg = sum(all_accuracies[-third:]) / third
            
            if last_third_avg > first_third_avg + 3:
                trend = 'improving'
            elif last_third_avg < first_third_avg - 3:
                trend = 'declining'
        
        analytics = {
            'total_learning_updates': len(updates),
            'learning_updates_by_period': dict(updates_by_week),
            'accuracy_over_time': accuracy_over_time,
            'most_common_missing_items': [{'item': item, 'frequency': freq} for item, freq in top_missing],
            'most_common_extra_items': [{'item': item, 'frequency': freq} for item, freq in top_extra],
            'average_accuracy': round(overall_avg, 2),
            'accuracy_trend': trend,
            'analysis_period_days': days_back
        }
        
        print(f"📊 Learning analytics: {len(updates)} updates, avg accuracy {overall_avg:.1f}%, trend: {trend}")
        return analytics
        
    except Exception as e:
        print(f"❌ Error getting learning analytics: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_learning_updates': 0,
            'error': str(e)
        }

