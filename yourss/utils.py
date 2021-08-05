from re import fullmatch


def validate_email(value: str):
    if (
        isinstance(value, str)
        and fullmatch(r"[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+", value) is not None
    ):
        return value
    raise ValueError("Invalid email")


def validate_password(value: str):
    if isinstance(value, str) and len(value) > 8 and len(set(value)) > 6:
        return value
    raise ValueError("Invalid password")
