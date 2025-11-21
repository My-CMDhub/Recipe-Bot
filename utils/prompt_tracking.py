"""
Prompt Tracking Utilities
Tracks prompt size and context limit errors for monitoring
"""

from config.supabase_config import get_supabase_client
from datetime import datetime


def estimate_tokens(text: str) -> int:
    """
    Estimates token count from text
    Simple estimation: ~4 characters per token (varies by model)
    
    Args:
        text: The prompt text
        
    Returns:
        int: Estimated token count
    """
    # Rough estimate: 1 token ≈ 4 characters
    # This is a simple approximation, actual tokenization varies by model
    return len(text) // 4


def calculate_prompt_size(prompt: str) -> dict:
    """
    Calculates prompt size metrics
    
    Args:
        prompt: The prompt text
        
    Returns:
        dict: {
            'chars': int,
            'estimated_tokens': int
        }
    """
    chars = len(prompt)
    tokens = estimate_tokens(prompt)
    
    return {
        'chars': chars,
        'estimated_tokens': tokens
    }


def save_prompt_metric(
    prompt: str,
    llm_used: str,
    prediction_id: int = None,
    user_phone: str = None,
    context_limit_hit: bool = False,
    error_message: str = None,
    error_code: str = None,
    request_successful: bool = True
) -> int:
    """
    Saves prompt metrics to database for monitoring
    
    Args:
        prompt: The prompt text
        llm_used: Which LLM was used ('gemini', 'mistral', 'deepseek', 'openai')
        prediction_id: Optional prediction ID
        user_phone: Optional user phone number
        context_limit_hit: Whether context limit was hit
        error_message: Error message if any
        error_code: Error code from API if any
        request_successful: Whether request was successful
        
    Returns:
        int: Metric ID if successful, None if failed
    """
    try:
        supabase = get_supabase_client()
        
        # Calculate prompt size
        size_metrics = calculate_prompt_size(prompt)
        
        metric_data = {
            'prediction_id': prediction_id,
            'user_phone': user_phone,
            'prompt_size_chars': size_metrics['chars'],
            'estimated_tokens': size_metrics['estimated_tokens'],
            'llm_used': llm_used,
            'context_limit_hit': context_limit_hit,
            'error_message': error_message,
            'error_code': error_code,
            'request_successful': request_successful
        }
        
        result = supabase.table('prompt_metrics').insert(metric_data).execute()
        
        if result.data and len(result.data) > 0:
            metric_id = result.data[0]['id']
            print(f"📊 Prompt metric saved: {size_metrics['chars']} chars, ~{size_metrics['estimated_tokens']} tokens, LLM: {llm_used}")
            if context_limit_hit:
                print(f"⚠️ Context limit hit! Error: {error_message}")
            return metric_id
        else:
            print("❌ Failed to save prompt metric")
            return None
            
    except Exception as e:
        print(f"❌ Error saving prompt metric: {e}")
        import traceback
        traceback.print_exc()
        return None


def is_context_limit_error(error_message: str, status_code: int = None) -> bool:
    """
    Detects if an error is related to context limit
    
    Common context limit error patterns:
    - "context_length_exceeded"
    - "maximum context length"
    - "token limit"
    - "too many tokens"
    - HTTP 400/413 with context-related messages
    
    Args:
        error_message: Error message from API
        status_code: HTTP status code (optional)
        
    Returns:
        bool: True if likely a context limit error
    """
    if not error_message:
        return False
    
    error_lower = error_message.lower()
    
    # Common context limit keywords
    context_keywords = [
        'context_length',
        'context length',
        'maximum context',
        'max context',
        'token limit',
        'token_limit',
        'too many tokens',
        'exceeded.*token',
        'input.*too long',
        'prompt.*too long'
    ]
    
    # Check for keywords
    for keyword in context_keywords:
        if keyword.replace('.*', '') in error_lower:
            return True
    
    # HTTP 413 (Payload Too Large) often indicates context limit
    if status_code == 413:
        return True
    
    # HTTP 400 with context-related message
    if status_code == 400 and any(kw in error_lower for kw in ['context', 'token', 'length']):
        return True
    
    return False

