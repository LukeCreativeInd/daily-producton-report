def fmt_weight(value) -> str:
    """Format weights/totals to exactly 2 decimal places.

    - Prevents floating point artifacts (e.g. 1.3999999996)
    - Always returns a string like '2451.40'
    """
    try:
        return f"{round(float(value), 2):.2f}"
    except Exception:
        return "0.00"
