def parse_channel_names(text: str, delimiter: str = ",") -> set[str]:
    return set(filter(None, text.split(delimiter)))
