"""
Grocery prediction utilities
Handles receipt aggregation and pattern analysis for predictions
"""

from config.supabase_config import get_supabase_client
from datetime import date, datetime


def get_recent_receipts(user_phone: str, limit: int = 50):
    """
    Fetches the most recent receipts for a user
    
    Process:
    1. Query receipts table for this user
    2. Order by purchase_date (most recent first)
    3. Limit to last N receipts
    4. Return list of receipt records
    
    Args:
        user_phone: User's WhatsApp phone number
        limit: Maximum number of receipts to fetch (default: 50)
        
    Returns:
        list: List of receipt dictionaries, or empty list if failed
    """

    try:
        supabase = get_supabase_client()

        result = supabase.table('receipts')\
            .select('*')\
            .eq('user_phone', user_phone)\
            .order('purchase_date', desc=True)\
            .limit(limit)\
            .execute()
            
        receipts = result.data if result.data else []
        print(f"📊 Fetched {len(receipts)} recent receipts for {user_phone}")

        return receipts
    except Exception as e:
        print(f"❌ Error fetching recent receipts: {e}")
        import traceback
        traceback.print_exc()
        return []

def receipt_items_from_receipts(receipt_ids: list):
    """
    Fetches all receipt items for a list of receipt IDs
    
    Process:
    1. Query receipt_items table for all items in these receipts
    2. Include purchase_date from receipts table (via join or separate query)
    3. Return list of items with their purchase dates
    
    Args:
        receipt_ids: List of receipt IDs to fetch items for
        
    Returns:
        list: List of item dictionaries with receipt info, or empty list if failed
    """

    try:
        if not receipt_ids:
            return []

        supabase = get_supabase_client()

        # Get items and include purchase date from receipts table
        result = supabase.table('receipt_items')\
            .select('*, receipts(purchase_date)')\
            .in_('receipt_id', receipt_ids)\
            .execute()

        items = result.data if result.data else []
        print(f"📦 Fetched {len(items)} items from {len(receipt_ids)} receipts")

        return items

    except Exception as e:
        print(f"❌ Error fetching receipt items: {e}")
        import traceback
        traceback.print_exc()
        return []


def aggregate_purchase_patterns(items: list):
    """
    Analyzes purchase patterns from receipt items
    
    Process:
    1. Group items by normalized name
    2. Count frequency (how many times purchased)
    3. Find last purchase date
    4. Calculate average days between purchases
    5. Return aggregated patterns
    
    Args:
        items: List of item dictionaries with purchase_date
        
    Returns:
        dict: Dictionary mapping item_name -> pattern data
              Format: {
                  "Milk": {
                      "frequency": 5,
                      "last_purchase_date": "2024-11-15",
                      "avg_days_between": 7.5,
                      "purchase_dates": ["2024-11-15", "2024-11-08", ...]
                  },
                  ...
              }
    """
    try:
        from collections import defaultdict
        
        # Step 1: Group items by normalized name
        item_groups = defaultdict(list)
        
        for item in items:
            item_name = item.get('item_name_normalized', '').strip()
            purchase_date = item.get('purchase_date') or item.get('receipts', {}).get('purchase_date')
            
            if item_name and purchase_date:
                item_groups[item_name].append(purchase_date)
        
        # Step 2: Calculate patterns for each item
        patterns = {}
        
        for item_name, purchase_dates in item_groups.items():
            # Remove duplicates and sort (most recent first)
            unique_dates = sorted(set(purchase_dates), reverse=True)
            
            # Calculate average days between purchases
            avg_days = None
            if len(unique_dates) > 1:
                # Calculate days between consecutive purchases
                days_between = []
                for i in range(len(unique_dates) - 1):
                    date1 = datetime.fromisoformat(unique_dates[i].replace('Z', '+00:00') if 'T' in unique_dates[i] else unique_dates[i])
                    date2 = datetime.fromisoformat(unique_dates[i+1].replace('Z', '+00:00') if 'T' in unique_dates[i+1] else unique_dates[i+1])
                    days_diff = (date1 - date2).days
                    days_between.append(days_diff)
                
                if days_between:
                    avg_days = sum(days_between) / len(days_between)
            
            patterns[item_name] = {
                'frequency': len(unique_dates),
                'last_purchase_date': unique_dates[0] if unique_dates else None,
                'avg_days_between': round(avg_days, 1) if avg_days else None,
                'purchase_dates': unique_dates
            }
        
        print(f"📊 Analyzed patterns for {len(patterns)} unique items")
        return patterns
        
    except Exception as e:
        print(f"❌ Error aggregating patterns: {e}")
        import traceback
        traceback.print_exc()
        return {}


def format_data_for_llm(patterns: dict, current_date: date = None, user_phone: str = None) -> str:
    """
    Formats purchase patterns into a prompt for the LLM
    
    Process:
    1. Sort items by frequency and recency
    2. Format each item's pattern clearly
    3. Include current date context
    4. Include aggregated learning insights (if available)
    5. Create a clear, structured prompt
    
    Args:
        patterns: Dictionary from aggregate_purchase_patterns()
        current_date: Today's date (defaults to date.today())
        user_phone: User's phone number (optional, for future user-specific learning)
        
    Returns:
        str: Formatted prompt string for LLM
    """
    try:
        if current_date is None:
            current_date = date.today()
        
        # Sort items by frequency (most frequent first), then by recency
        sorted_items = sorted(
            patterns.items(),
            key=lambda x: (x[1]['frequency'], x[1]['last_purchase_date'] or ''),
            reverse=True
        )
        
        # Build the prompt
        prompt = f"""You are a grocery shopping prediction assistant. Based on the user's purchase history, predict what items they should buy in the next 3-7 days.

Today's date: {current_date.isoformat()}

Purchase History (last receipts):
"""
        
        # Add each item's pattern
        for item_name, pattern_data in sorted_items[:30]:  # Top 30 most frequent items
            frequency = pattern_data['frequency']
            last_date = pattern_data['last_purchase_date']
            avg_days = pattern_data['avg_days_between']
            
            # Calculate days since last purchase
            days_since = None
            if last_date:
                try:
                    last_purchase = datetime.fromisoformat(last_date.replace('Z', '+00:00') if 'T' in last_date else last_date).date()
                    days_since = (current_date - last_purchase).days
                except:
                    pass
            
            prompt += f"\n- {item_name}:"
            prompt += f"\n  • Purchased {frequency} time{'s' if frequency > 1 else ''} in last receipts"
            if last_date:
                prompt += f"\n  • Last purchased: {last_date}"
                if days_since is not None:
                    prompt += f" ({days_since} days ago)"
            if avg_days:
                prompt += f"\n  • Average time between purchases: {avg_days} days"
            
            # Add prediction hint
            if days_since is not None and avg_days:
                if days_since >= avg_days * 0.8:  # 80% of average time has passed
                    prompt += f"\n  → Likely needs soon (past {avg_days * 0.8:.0f} days)"
            prompt += "\n"
        
        # Add learning insights if available
        try:
            from handlers.learning_engine import get_aggregated_learning_summary
            learning_summary = get_aggregated_learning_summary(user_phone=user_phone, days_back=60, max_updates=10)
            
            if learning_summary.get('has_learning'):
                prompt += "\n\nLearning Insights (from recent feedback analysis):\n"
                
                missing_items = learning_summary.get('top_missing_items', [])
                extra_items = learning_summary.get('top_extra_items', [])
                avg_acc = learning_summary.get('average_accuracy', 0)
                trend = learning_summary.get('accuracy_trend', 'stable')
                
                if missing_items:
                    prompt += f"- Items often predicted but not bought: {', '.join(missing_items[:5])}\n"
                    prompt += "  → Consider reducing predictions for these items unless purchase pattern strongly suggests otherwise\n"
                
                if extra_items:
                    prompt += f"- Items often bought but not predicted: {', '.join(extra_items[:5])}\n"
                    prompt += "  → Consider including these items more often in predictions\n"
                
                if avg_acc > 0:
                    trend_emoji = "📈" if trend == 'improving' else "📉" if trend == 'declining' else "➡️"
                    prompt += f"- Average prediction accuracy: {avg_acc}% {trend_emoji} ({trend})\n"
        except Exception as e:
            print(f"⚠️ Could not include learning insights: {e}")
            # Continue without learning insights if there's an error
        
        prompt += f"""
Instructions:
1. Analyze the purchase patterns above
2. Consider the learning insights (if provided) to improve prediction accuracy
3. Predict which items the user should buy in the next 3-7 days (from {current_date.isoformat()})
4. Consider:
   - Items purchased frequently but not recently
   - Items approaching their average purchase interval
   - Items that haven't been bought in a while
   - Learning insights about commonly missed or extra items
5. Return ONLY valid JSON with this structure:
{{
  "predicted_date_range_start": "YYYY-MM-DD",
  "predicted_date_range_end": "YYYY-MM-DD",
  "predicted_items": ["Item 1", "Item 2", "Item 3"],
  "reasoning": "Brief explanation of why these items were predicted"
}}

Return ONLY the JSON, no other text or markdown.
"""
        
        return prompt

        
    except Exception as e:
        print(f"❌ Error formatting data for LLM: {e}")
        import traceback
        traceback.print_exc()
        return ""
