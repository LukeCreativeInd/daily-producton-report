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
    """Format per-meal quantities EXACTLY (allow decimals), trimming trailing zeros.

    Examples:
      0.5  -> "0.5"
      1.0  -> "1"
      1.62 -> "1.62"
      5.270 -> "5.27"
    """
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "0"

        # Show integers without .0
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))

        s = f"{v:.{max_dp}f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "-0.0") else s
    except Exception:
        return "0"

# If other modules rely on fmt_weight, keep it mapped to whole-number rounding
def fmt_weight(value) -> str:
    return fmt_int_up(value)
