# query = db.session.query(Business.identifier).limit(5000)
# businesses = [x[0] for x in query.all()]
# filing_query = db.session.query(Filing.temp_reg).filter(Filing._status == Filing.Status.DRAFT.value).filter(Filing.temp_reg != None).filter(Filing._filing_type.in_(['incorporationApplication', 'registration'])).limit(5000)
# filings = [x[0] for x in filing_query.all()]
# print(businesses + filings)
