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

# Backwards-compatible alias (in case any old code still calls it)
def fmt_weight(value) -> str:
    return fmt_int_up(value)
