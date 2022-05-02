import pandas as pd

def convert_result_set_to_dict(rs):
    df = pd.DataFrame(rs, columns=rs.keys())
    result_dict = df.to_dict('records')
    return result_dict
