from typing import Dict, Any, List

def calculate(operation: str) -> str:
    """Basic arithmetic logic: safe evaluation."""
    try:
        # Use simpler logic or restricted eval
        # For our agent a basic eval on a sanitized string is sufficient
        safe_chars = "0123456789+-*/(). "
        if all(c in safe_chars for c in operation):
            res = eval(operation)
            return f"🔢 Calculated: {res}"
        return "❌ Error: Forbidden characters in calculation."
    except Exception as e:
        return f"❌ Calculation Fault: {str(e)}"
