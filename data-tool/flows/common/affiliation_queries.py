def get_unaffiliated_firms_query(data_load_env: str):
    query = f"""
            select ap.account_id, ap.corp_num, ap.contact_email, c.admin_email
            from affiliation_processing ap
                     join corporation c on ap.corp_num = c.corp_num
            where environment = '{data_load_env}'
              -- and processed_status is null
              --or processed_status <> 'COMPLETED'
              and (processed_status is null or processed_status not in ('COMPLETED', 'FAILED'))
            limit 5
            ;
        """
    return query
