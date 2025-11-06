"""
Recipe-related utility functions
Handles recipe selection, history tracking, and daily reset
"""

from config.supabase_config import get_supabase_client
from datetime import datetime, date
import random

def seed_initial_recipes():
    """
    Seeds the database with initial recipe names
    This should be run once to populate your recipes table
    """
    # List of recipe names - you can customize this!
    recipe_names = [
        "Pasta Carbonara",
        "Chicken Tikka Masala",
        "Vegetable Stir Fry",
        "Beef Tacos",
        "Margherita Pizza",
        "Fish Curry",
        "Caesar Salad",
        "Chicken Fried Rice",
        "Vegetable Soup",
        "Grilled Salmon",
        "Beef Burger",
        "Chicken Noodles",
        "Tomato Pasta",
        "Vegetable Lasagna",
        "Chicken Biryani"
    ]
    
    supabase = get_supabase_client()
    
    # Check if recipes already exist
    existing = supabase.table('recipes').select('*').execute()
    
    if len(existing.data) > 0:
        print("Recipes already exist in database. Skipping seed.")
        return
    
    # Insert recipes one by one
    for recipe_name in recipe_names:
        supabase.table('recipes').insert({
            'name': recipe_name
        }).execute()
    
    print(f"Successfully seeded {len(recipe_names)} recipes!")

def get_random_recipe_not_sent_today():
    """
    Gets a random recipe that hasn't been sent today
    
    Returns:
        dict: Recipe data with 'id' and 'name', or None if all sent
    """
    supabase = get_supabase_client()
    today = date.today().isoformat()  # Format: "2024-01-15"
    
    # Get all recipe IDs sent today
    history_today = supabase.table('recipe_history').select('recipe_id').eq('sent_date', today).execute()
    sent_ids = [record['recipe_id'] for record in history_today.data]
    
    # Get all recipes
    all_recipes = supabase.table('recipes').select('id, name').execute()
    
    # Filter out recipes sent today
    available_recipes = [recipe for recipe in all_recipes.data if recipe['id'] not in sent_ids]
    
    # If no recipes available, return None
    if not available_recipes:
        return None
    
    # Return a random recipe from available ones
    return random.choice(available_recipes)

def record_recipe_sent(recipe_id: int):
    """
    Records that a recipe was sent (adds to history)
    
    Args:
        recipe_id: The ID of the recipe that was sent
    """
    supabase = get_supabase_client()
    today = date.today().isoformat()
    
    supabase.table('recipe_history').insert({
        'recipe_id': recipe_id,
        'sent_date': today
    }).execute()

def get_all_recipe_names():
    """
    Gets a list of all recipe names
    
    Returns:
        list: List of recipe name strings
    """
    supabase = get_supabase_client()
    recipes = supabase.table('recipes').select('name').execute()
    return [recipe['name'] for recipe in recipes.data]

def reset_daily_history():
    """
    Clears today's recipe history (called at midnight or start of day)
    This allows recipes to be sent again the next day
    """
    supabase = get_supabase_client()
    today = date.today().isoformat()
    
    # Delete all history records for today
    supabase.table('recipe_history').delete().eq('sent_date', today).execute()
    print(f"Reset daily history for {today}")