## Your Continuation Application Details
**Previous Jurisdiction:** {{ foreign_jurisdiction }}
**Name in Previous Jurisdiction:** {{ filing.foreignJurisdiction.legalName }}
**Number in Previous Jurisdiction:** {{ filing.foreignJurisdiction.identifier }}
{% if filing.business %}
**Extraprovincial Registration Number in BC:** {{ filing.business.identifier }}
{% endif %}
