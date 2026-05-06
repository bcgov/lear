def colin_oracle_chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[i:i + size] for i in range(0, len(values), size)]

def colin_oracle_corp_num_list_format(corp_nums: list[str]) -> str:
    def q(s: str) -> str:
        return "'" + str(s).replace("'","'") + ""
    return '(' + ','.join(q(c) for c in corp_nums) + ')'