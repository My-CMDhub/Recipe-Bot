

import os
import requests
from dotenv import load_dotenv
import json
from utils.prompt_tracking import save_prompt_metric, is_context_limit_error



load_dotenv()

def call_mistral_api(prompt: str, prediction_id: int = None, user_phone: str = None) -> str | None:

    MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
    if not MISTRAL_API_KEY:
        raise ValueError("MISTRAL_API_KEY not set in environment")
    
    # Track prompt size before sending
    save_prompt_metric(
        prompt=prompt,
        llm_used='mistral',
        prediction_id=prediction_id,
        user_phone=user_phone,
        request_successful=True  # Will update if error occurs
    )
        
    try:
        url = f"https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}"
        }
        data = {
            "model": "mistral-large-latest",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            response_data = response.json()
            content = response_data['choices'][0]['message']['content']
            return content
        else:
            error_msg = f"Mistral API error: {response.status_code} - {response.text}"
            # Check if context limit error
            is_context_error = is_context_limit_error(response.text, response.status_code)
            if is_context_error:
                save_prompt_metric(
                    prompt=prompt,
                    llm_used='mistral',
                    prediction_id=prediction_id,
                    user_phone=user_phone,
                    context_limit_hit=True,
                    error_message=error_msg,
                    error_code=str(response.status_code),
                    request_successful=False
                )
            raise Exception(error_msg)
    except Exception as e:
        error_msg = str(e)
        is_context_error = is_context_limit_error(error_msg)
        if is_context_error:
            save_prompt_metric(
                prompt=prompt,
                llm_used='mistral',
                prediction_id=prediction_id,
                user_phone=user_phone,
                context_limit_hit=True,
                error_message=error_msg,
                request_successful=False
            )
        print(f"❌ Error calling Mistral API: {e}")
        return None

def call_gemini_api(prompt: str, prediction_id: int = None, user_phone: str = None) -> str | None:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in environment")

    # Track prompt size before sending
    save_prompt_metric(
        prompt=prompt,
        llm_used='gemini',
        prediction_id=prediction_id,
        user_phone=user_phone,
        request_successful=True  # Will update if error occurs
    )

    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            "x-goog-api-key": GEMINI_API_KEY
        }

        data = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            response_data = response.json()

            content = response_data['candidates'][0]['content']['parts'][0]['text']
            return content

        else:
            error_msg = f"Gemini API error: {response.status_code} - {response.text}"
            # Check if context limit error
            is_context_error = is_context_limit_error(response.text, response.status_code)
            if is_context_error:
                save_prompt_metric(
                    prompt=prompt,
                    llm_used='gemini',
                    prediction_id=prediction_id,
                    user_phone=user_phone,
                    context_limit_hit=True,
                    error_message=error_msg,
                    error_code=str(response.status_code),
                    request_successful=False
                )
            raise Exception(error_msg)
    except Exception as e:
        error_msg = str(e)
        is_context_error = is_context_limit_error(error_msg)
        if is_context_error:
            save_prompt_metric(
                prompt=prompt,
                llm_used='gemini',
                prediction_id=prediction_id,
                user_phone=user_phone,
                context_limit_hit=True,
                error_message=error_msg,
                request_successful=False
            )
        print(f"❌ Error calling Gemini API: {e}")
        return None

def call_deepseek_api(prompt: str, prediction_id: int = None, user_phone: str = None) -> str | None:

    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not set in environment")

    # Track prompt size before sending
    from utils.prompt_tracking import save_prompt_metric, is_context_limit_error
    save_prompt_metric(
        prompt=prompt,
        llm_used='deepseek',
        prediction_id=prediction_id,
        user_phone=user_phone,
        request_successful=True  # Will update if error occurs
    )

    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            'model': 'deepseek-reasoner',
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            response_data = response.json()
            content = response_data['choices'][0]['message']['content']
            return content
        else:
            error_msg = f"DeepSeek API error: {response.status_code} - {response.text}"
            # Check if context limit error
            is_context_error = is_context_limit_error(response.text, response.status_code)
            if is_context_error:
                save_prompt_metric(
                    prompt=prompt,
                    llm_used='deepseek',
                    prediction_id=prediction_id,
                    user_phone=user_phone,
                    context_limit_hit=True,
                    error_message=error_msg,
                    error_code=str(response.status_code),
                    request_successful=False
                )
            raise Exception(error_msg)
    except Exception as e:
        error_msg = str(e)
        is_context_error = is_context_limit_error(error_msg)
        if is_context_error:
            save_prompt_metric(
                prompt=prompt,
                llm_used='deepseek',
                prediction_id=prediction_id,
                user_phone=user_phone,
                context_limit_hit=True,
                error_message=error_msg,
                request_successful=False
            )
        print(f"❌ Error calling DeepSeek API: {e}")
        return None

def call_openai_api(prompt: str, prediction_id: int = None, user_phone: str = None) -> str | None:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment")

    # Track prompt size before sending
    from utils.prompt_tracking import save_prompt_metric, is_context_limit_error
    save_prompt_metric(
        prompt=prompt,
        llm_used='openai',
        prediction_id=prediction_id,
        user_phone=user_phone,
        request_successful=True  # Will update if error occurs
    )

    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            response_data = response.json()
            content = response_data['choices'][0]['message']['content']
            return content
        else:
            error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
            # Check if context limit error
            is_context_error = is_context_limit_error(response.text, response.status_code)
            if is_context_error:
                save_prompt_metric(
                    prompt=prompt,
                    llm_used='openai',
                    prediction_id=prediction_id,
                    user_phone=user_phone,
                    context_limit_hit=True,
                    error_message=error_msg,
                    error_code=str(response.status_code),
                    request_successful=False
                )
            raise Exception(error_msg)
    except Exception as e:
        error_msg = str(e)
        is_context_error = is_context_limit_error(error_msg)
        if is_context_error:
            save_prompt_metric(
                prompt=prompt,
                llm_used='openai',
                prediction_id=prediction_id,
                user_phone=user_phone,
                context_limit_hit=True,
                error_message=error_msg,
                request_successful=False
            )
        print(f"❌ Error calling OpenAI API: {e}")
        return None

def parse_ai_response(response_text: str) -> dict | None:
    """
    Parses AI response text into structured JSON
    
    Handles:
    - JSON wrapped in markdown: ```json {...} ```
    - Plain JSON: {...}
    """
    try:
        # Check if wrapped in markdown code block
        if "```json" in response_text:
            # Extract JSON from markdown: ```json {...} ```
            json_part = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            # Might be wrapped in just ``` without json label
            json_part = response_text.split("```")[1].split("```")[0].strip()
        else:
            # Plain JSON, use as is
            json_part = response_text.strip()
        
        # Parse JSON string into Python dict
        parsed = json.loads(json_part)
        return parsed
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"   Response text (first 200 chars): {response_text[:200]}...")
        return None
    except Exception as e:
        print(f"❌ Error parsing AI response: {e}")
        return None

        
def structure_receipt_data(extracted_text: str) -> dict | None:

    
    prompt = f"""You are a receipt parser. Extract structured data from this receipt text:
        
        {extracted_text}
        
         Return ONLY valid JSON with this structure:
   {{
     "store_name": "Store name",
     "purchase_date": "YYYY-MM-DD",
     "items": [
       {{
         "name": "Normalized item name",
         "quantity": 2.0,
         "unit_price": 1.65,
         "total_price": 3.30
       }}
     ]
   }}

   Instructions:
   - Normalize item names to common format (e.g., "COLES LEMON JUICE" → "Lemon Juice")
   - Extract date in YYYY-MM-DD format
   - Extract quantities, unit prices, and total prices
   - Return ONLY the JSON, no other text or markdown
        """

    mistral_response = call_mistral_api(prompt)

    if mistral_response:

        structured = parse_ai_response(mistral_response)
        print(structured)
        if structured:
            return structured

    print("⚠️ Mistral failed, trying Gemini...")

    gemini_response = call_gemini_api(prompt)

    if gemini_response:

        structure = parse_ai_response(gemini_response)
        print(structure)
        if structure:
            return structure

    print("❌ Both AI APIs failed")
    return None

