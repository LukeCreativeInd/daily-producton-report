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

def fmt_qty(value, max_dp: int = 3) -> str:
    """Format per-unit quantities EXACTLY as listed (allow decimals).

    Use this for:
    - Qty/Meal
    - Qty/Batch
    - Meal Amount
    - Any other per-unit recipe-defined quantity

    Calculated totals should use fmt_int_up().
    """
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "0"

        # If effectively integer, show without decimals
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))

        # Otherwise show up to max_dp, trimming trailing zeros
        return f"{v:.{max_dp}f}".rstrip("0").rstrip(".")
    except Exception:
        return "0"

# Backwards-compatible alias (in case any old code still calls it)
def fmt_weight(value) -> str:
    return fmt_int_up(value)
