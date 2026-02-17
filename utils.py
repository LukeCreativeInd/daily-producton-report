import math

def fmt_int_up(value) -> str:
    """Round UP to a whole number string.

    - Used for ALL weights/totals/amounts in the PDF (no decimals).
    - Prevents float artifacts.
    """
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "0"
        # Ceil for positives; for negatives (unlikely), use floor to keep "up" meaning consistent
        return str(int(math.ceil(v))) if v >= 0 else str(int(math.floor(v)))
    except Exception:
        return "0"

def fmt_qty(value, max_dp: int = 2) -> str:
    """Format a 'Qty/Meal' value EXACTLY (allow decimals), trimming trailing zeros.

    Examples:
    - 0.5 -> "0.5"
    - 1.0 -> "1"
    - 1.8 -> "1.8"
    - 103.5 -> "103.5"
    - 7.21 -> "7.21"
    """
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "0"

        # If it's effectively an integer, show as int
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))

        # Otherwise show up to max_dp decimals, trimming zeros
        s = f"{v:.{max_dp}f}".rstrip("0").rstrip(".")
        # Handle cases like "-0"
        return "0" if s in ("-0", "-0.0") else s
    except Exception:
        return "0"

# Backwards-compatible alias (in case any old code still calls it)
def fmt_weight(value) -> str:
    return fmt_int_up(value)
