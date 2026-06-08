from html import escape


def admin_select2_text(value: object) -> str:
    return f"<span>{escape(str(value))}</span>"
