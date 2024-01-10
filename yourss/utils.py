def parse_channel_names(
    text: str, delimiter: str = ",", disabled_prefix: str = "-"
) -> dict[str, bool]:
    return {
        s.removeprefix(disabled_prefix): not s.startswith(disabled_prefix)
        for s in filter(
            lambda x: len(x.removeprefix(disabled_prefix)) > 0, text.split(delimiter)
        )
    }
