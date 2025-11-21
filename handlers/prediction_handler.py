"""
Grocery prediction handler
Handles AI-powered grocery predictions based on purchase history
"""

from handlers.ai_data_processor import call_gemini_api, call_mistral_api, parse_ai_response, call_deepseek_api, call_openai_api
from datetime import datetime

def generate_grocery_prediction(prompt: str, prediction_id: int = None, user_phone: str = None) -> dict | None:
    """
    Generates grocery prediction using AI (LLM chain with fallback)
    
    Process:
    1. Try Gemini API first
    2. If fails, try Mistral API
    3. If fails, try DeepSeek API
    4. If fails, try OpenAI API
    5. Parse JSON response
    6. Return structured prediction
    
    Args:
        prompt: Formatted prompt string from format_data_for_llm()
        
    Returns:
        dict: Prediction data with date range and items, or None if failed
              Format: {
                  "predicted_date_range_start": "2024-11-20",
                  "predicted_date_range_end": "2024-11-27",
                  "predicted_items": ["Milk", "Bread", "Eggs"],
                  "reasoning": "These items are frequently purchased...",
                  "llm_used": "gemini" | "mistral" | "deepseek" | "openai"
              }
    """

    try:
        print("🤖 Generating prediction with Gemini...")

        gemini_response = call_gemini_api(prompt, prediction_id=prediction_id, user_phone=user_phone)

        if gemini_response:
            print("✅ Gemini responded, parsing...")
            prediction = parse_ai_response(gemini_response)
            
            if prediction and _validate_prediction(prediction):
                print(f"✅ Prediction generated: {len(prediction.get('predicted_items', []))} items")
                prediction['llm_used'] = 'gemini'
                return prediction
            else:
                print("⚠️ Gemini response invalid, trying Mistral...")
        else:
            print("⚠️ Gemini failed, trying Mistral...")

        print("🤖 Generating prediction with Mistral...")

        mistral_response = call_mistral_api(prompt, prediction_id=prediction_id, user_phone=user_phone)

        if mistral_response:
            print("✅ Mistral responded, parsing...")
            prediction = parse_ai_response(mistral_response)
            
            if prediction and _validate_prediction(prediction):
                print(f"✅ Prediction generated: {len(prediction.get('predicted_items', []))} items")
                prediction['llm_used'] = 'mistral'
                return prediction
            else:
                print("⚠️ Mistral response invalid, trying DeepSeek...")
        else:
            print("⚠️ Mistral failed, trying DeepSeek...")

        print("🤖 Generating prediction with DeepSeek...")

        deepseek_response = call_deepseek_api(prompt, prediction_id=prediction_id, user_phone=user_phone)

        if deepseek_response:
            print("✅ DeepSeek responded, parsing...")
            prediction = parse_ai_response(deepseek_response)
            
            if prediction and _validate_prediction(prediction):
                print(f"✅ Prediction generated: {len(prediction.get('predicted_items', []))} items")
                prediction['llm_used'] = 'deepseek'
                return prediction
            else:
                print("⚠️ DeepSeek response invalid, trying OpenAI...")
        else:
            print("⚠️ DeepSeek failed, trying OpenAI...")

        print("🤖 Generating prediction with OpenAI...")

        openai_response = call_openai_api(prompt, prediction_id=prediction_id, user_phone=user_phone)
            
        if openai_response:
            print("✅ OpenAI responded, parsing...")
            prediction = parse_ai_response(openai_response)
            
            if prediction and _validate_prediction(prediction):
                print(f"✅ Prediction generated: {len(prediction.get('predicted_items', []))} items")
                prediction['llm_used'] = 'openai'
                return prediction
            else:
                print("⚠️ OpenAI response invalid")
        else:
            print("⚠️ OpenAI failed")
            
        print("❌ All AI APIs failed or returned invalid responses")
        return None

    except Exception as e:
            print(f"❌ Error generating prediction: {e}")
            import traceback
            traceback.print_exc()
            return None

def _validate_prediction(prediction: dict) -> bool:
    """
    Validates that prediction has required fields
    
    Args:
        prediction: Parsed prediction dictionary
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ['predicted_date_range_start', 'predicted_date_range_end', 'predicted_items']
    
    # Check all required fields exist
    for field in required_fields:
        if field not in prediction:
            print(f"⚠️ Missing required field: {field}")
            return False
    
    # Check predicted_items is a list and not empty
    if not isinstance(prediction['predicted_items'], list) or len(prediction['predicted_items']) == 0:
        print("⚠️ predicted_items must be a non-empty list")
        return False
    
    # Check dates are valid format
    try:
        datetime.fromisoformat(prediction['predicted_date_range_start'])
        datetime.fromisoformat(prediction['predicted_date_range_end'])
    except (ValueError, TypeError):
        print("⚠️ Invalid date format")
        return False
    
    return True



