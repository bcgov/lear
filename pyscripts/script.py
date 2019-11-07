#from sqlalchemy import desc, event, inspect
#from sqlalchemy.dialects.postgresql import JSONB
#from sqlalchemy.ext.hybrid import hybrid_property
#from sqlalchemy.orm import backref
from flask import redirect, Flask  # noqa: I001

import legal_api
from legal_api import config
from legal_api.models import Business, Address, Office 
from legal_api.models import db

app = Flask(__name__)
app.config.from_object(config.CONFIGURATION['development'])
db.init_app(app)

def _add_office(num, business: Business):
    office_types =['registeredOffice', 'recordsOffice']
    for i in range(0, num):
        office = Office()
        office.business_id=business.id
        office.office_type = office_types[i]
        yield office

with app.app_context():
    businesses = db.session.query(legal_api.models.Business)
    b_list = businesses.all()

    for x in b_list:
        offices = db.session.query(legal_api.models.Office). \
            filter(Office.business_id == x.id).all()
        
        if len(offices) == 0:
           if x.legal_type == 'CP':
               for _office in _add_office(1, x):
                   db.session.add(_office)
                   db.session.commit()
                   _id = _office.id
                   addresses = db.session.query(legal_api.models.Address).filter(Address.business_id == x.id).all()
                   for address in addresses:
                       address.office_id = _id
                       db.session.add(address)
                       db.session.commit()
           else:
             _add_office(2, x)
