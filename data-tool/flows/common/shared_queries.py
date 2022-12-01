

def get_corp_comments_data_query(corp_num: str):
    query = f"""
        select to_char(cc.comment_dts, 'YYYY-MM-DD HH24:MI:SS')::timestamp AT time zone 'America/Los_Angeles' as cc_comment_dts_pacific,
               cc.corp_num as cc_corp_num,
               cc.comments as cc_comments
        from corp_comments cc
        where cc.corp_num = '{corp_num}'
        order by cc.comment_dts
        ;
        """
    return query
