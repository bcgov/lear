
export class Business {
     typeEnum: string;
     displayName:String;
     flows: Array<Flow>;
}

export class Flow {
     feeCode:String;
     displayName:String;
     certifyText:String;
     // fields:Array<Fields>
}

export const configJson = [{
  typeEnum: 'BC',
  displayName: 'Benefits Company',
  flows: [
    {
      feeCode: 'OTADD',
      displayName: 'Change Of Address',
      certifyText: 'Note: It is an offence to make a false or misleading statement in' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See sections 35 and 36 of the Business Corporations Act.'
    },
    {
      feeCode: 'OTANN',
      displayName: 'Annual Report',
      certifyText: 'Note: It is an offence to make a false or misleading statement in' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See section 51 of the Business Corporations Act.'
    },
    {
      feeCode: 'OTCDR',
      displayName: 'Change Of Directors',
      certifyText: 'Note: It is an offence to make a false or misleading statement in' +
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
      certifyText: 'Note: It is an offence to make a false or misleading statement in' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See section 27 of the Cooperative Associations Act.'
    },
    {
      feeCode: 'OTANN',
      displayName: 'Annual Report',
      certifyText: 'Note: It is an offence to make a false or misleading statement in' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See section 126 of the Cooperative Associations Act.'
    },
    {
      feeCode: 'OTCDR',
      displayName: 'Change Of Directors',
      certifyText: 'Note: It is an offence to make a false or misleading statement in' +
           'respect of a material fact in a record submitted to the Corporate Registry for filing. ' +
           'See section 78 of the Cooperative Associations Act.'
    }
  ]
}]
