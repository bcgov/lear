def colin_oracle_chunks(items: list[str], size: int = 999):
    for i in range(0, len(items), size):
        yield items[i:1 + size]