import math

def fmt_int_up(value) -> str:
    """Round UP to a whole number string (no decimals)."""
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "0"
        return str(int(math.ceil(v))) if v >= 0 else str(int(math.floor(v)))
    except Exception:
        return "0"

def fmt_qty(value, max_dp: int = 3) -> str:
    """Format per-unit quantities EXACTLY (allow decimals), trimming trailing zeros.

    Use this for any 'per meal', 'per batch', 'recipe qty', etc.
    Only calculated totals should ever be rounded.

    Examples:
      0.5   -> "0.5"
      1.0   -> "1"
      1.62  -> "1.62"
      5.270 -> "5.27"
    """
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "0"

        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))

        return f"{v:.{max_dp}f}".rstrip("0").rstrip(".")
    except Exception:
        return "0"

def fmt_weight(value) -> str:
    """Backwards compatible alias: weights/totals should be whole numbers."""
    return fmt_int_up(value)
