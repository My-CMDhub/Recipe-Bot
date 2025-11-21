"""
Learning Analytics Utilities
Provides functions to monitor and analyze learning system performance
Use these functions to check if the AI is improving over time in Supabase
"""

from handlers.learning_engine import get_learning_analytics
import json


def print_learning_analytics(days_back: int = 90):
    """
    Prints comprehensive learning analytics to console
    
    Use this function to monitor:
    - Whether accuracy is improving over time
    - Most common prediction mistakes
    - Learning update frequency
    - Overall system performance
    
    Args:
        days_back: How many days back to analyze (default: 90)
    """
    print("\n" + "="*60)
    print("📊 LEARNING SYSTEM ANALYTICS")
    print("="*60)
    
    analytics = get_learning_analytics(days_back=days_back)
    
    if analytics.get('total_learning_updates') == 0:
        print("\n⚠️  No learning updates found in the specified period")
        print(f"   Analysis period: Last {days_back} days")
        print("\n💡 Tip: Learning updates are created after every 5 feedbacks")
        return
    
    print(f"\n📈 OVERVIEW")
    print(f"   Total Learning Updates: {analytics['total_learning_updates']}")
    print(f"   Analysis Period: Last {analytics.get('analysis_period_days', days_back)} days")
    print(f"   Average Accuracy: {analytics['average_accuracy']}%")
    
    trend = analytics.get('accuracy_trend', 'stable')
    trend_emoji = "📈" if trend == 'improving' else "📉" if trend == 'declining' else "➡️"
    print(f"   Accuracy Trend: {trend_emoji} {trend.upper()}")
    
    # Accuracy over time
    accuracy_over_time = analytics.get('accuracy_over_time', [])
    if accuracy_over_time:
        print(f"\n📅 ACCURACY OVER TIME (by week)")
        for period_data in accuracy_over_time[:10]:  # Show last 10 weeks
            period = period_data['period']
            acc = period_data['average_accuracy']
            count = period_data['update_count']
            print(f"   {period}: {acc}% ({count} updates)")
    
    # Most common mistakes
    missing_items = analytics.get('most_common_missing_items', [])
    if missing_items:
        print(f"\n❌ TOP ITEMS PREDICTED BUT NOT BOUGHT")
        print(f"   (Items the AI should predict less often)")
        for i, item_data in enumerate(missing_items[:10], 1):
            item = item_data['item']
            freq = item_data['frequency']
            print(f"   {i}. {item} (missed {freq} times)")
    
    extra_items = analytics.get('most_common_extra_items', [])
    if extra_items:
        print(f"\n➕ TOP ITEMS BOUGHT BUT NOT PREDICTED")
        print(f"   (Items the AI should predict more often)")
        for i, item_data in enumerate(extra_items[:10], 1):
            item = item_data['item']
            freq = item_data['frequency']
            print(f"   {i}. {item} (missed {freq} times)")
    
    # Learning update frequency
    updates_by_period = analytics.get('learning_updates_by_period', {})
    if updates_by_period:
        print(f"\n🔄 LEARNING UPDATE FREQUENCY")
        total_weeks = len(updates_by_period)
        avg_per_week = analytics['total_learning_updates'] / total_weeks if total_weeks > 0 else 0
        print(f"   Average updates per week: {avg_per_week:.1f}")
        print(f"   Active weeks: {total_weeks}")
    
    print("\n" + "="*60)
    print("💡 INTERPRETATION GUIDE")
    print("="*60)
    print("   • Improving trend = AI is learning and getting better")
    print("   • Declining trend = May need to review prediction logic")
    print("   • Missing items = Items predicted too often (reduce predictions)")
    print("   • Extra items = Items not predicted enough (increase predictions)")
    print("   • More learning updates = More feedback = Better learning")
    print("="*60 + "\n")


def get_learning_summary_for_dashboard() -> dict:
    """
    Gets a concise summary suitable for dashboard display
    
    Returns:
        dict: Summary with key metrics
    """
    analytics = get_learning_analytics(days_back=90)
    
    return {
        'total_updates': analytics.get('total_learning_updates', 0),
        'average_accuracy': analytics.get('average_accuracy', 0),
        'trend': analytics.get('accuracy_trend', 'stable'),
        'top_missing_count': len(analytics.get('most_common_missing_items', [])),
        'top_extra_count': len(analytics.get('most_common_extra_items', [])),
        'has_data': analytics.get('total_learning_updates', 0) > 0
    }


def export_learning_data_to_json(output_file: str = 'learning_analytics.json', days_back: int = 90):
    """
    Exports learning analytics to a JSON file for external analysis
    
    Args:
        output_file: Path to output JSON file
        days_back: How many days back to analyze
    """
    analytics = get_learning_analytics(days_back=days_back)
    
    with open(output_file, 'w') as f:
        json.dump(analytics, f, indent=2, default=str)
    
    print(f"✅ Learning analytics exported to {output_file}")


if __name__ == "__main__":
    # Run analytics when script is executed directly
    print_learning_analytics(days_back=90)

