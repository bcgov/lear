export class Flow {
  feeCode: string
  displayName: string
  certifyText: string
}

export class Business {
  typeEnum: string
  displayName: string
  flows: Array<Flow>
}

export const configJson = [{
  typeEnum: 'BC',
  displayName: 'Benefit Company',
  flows: [
    {
      feeCode: 'OTADD',
      displayName: 'Change Of Address',
      certifyText: 'Note: It is an offence to make a false or misleading statement in ' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See sections 35 and 36 of the Business Corporations Act.'
    },
    {
      feeCode: 'OTANN',
      displayName: 'Annual Report',
      certifyText: 'Note: It is an offence to make a false or misleading statement in ' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See section 51 of the Business Corporations Act.'
    },
    {
      feeCode: 'OTCDR',
      displayName: 'Change Of Directors',
      certifyText: 'Note: It is an offence to make a false or misleading statement in ' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See section 127 of the Business Corporations Act.'
    }
  ]
},
{
  typeEnum: 'CP',
  displayName: 'Cooperative',
  flows: [
    {
      feeCode: 'OTADD',
      displayName: 'Change Of Address',
      certifyText: 'Note: It is an offence to make a false or misleading statement in ' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See section 27 of the Cooperative Association Act.'
    },
    {
      feeCode: 'OTANN',
      displayName: 'Annual Report',
      certifyText: 'Note: It is an offence to make a false or misleading statement in ' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See section 126 of the Cooperative Association Act.'
    },
    {
      feeCode: 'OTCDR',
      displayName: 'Change Of Directors',
      certifyText: 'Note: It is an offence to make a false or misleading statement in ' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See section 78 of the Cooperative Association Act.'
    }
  ]
}]
