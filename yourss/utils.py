from re import fullmatch


def validate_email(value: str):
    return (
        isinstance(value, str)
        and fullmatch(r"[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+", value) is not None
    )


def validate_password(value: str):
    return isinstance(value, str) and len(value) > 8 and len(set(value)) > 6
