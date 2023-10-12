param location string = resourceGroup().location
param vnetRG string
param vnetName string
param vnetAddressPrefix string
param subnet1Name string
param subnet2Name string
param subnet1Prefix string
param subnet2Prefix string
param subnet1nsgname string
param subnet2nsgname string
param subnet1routetablename string
param subnet2routetablename string

@allowed([
  'new'
  'existing'
])
param newOrExisting string

resource newvnet 'Microsoft.Network/virtualNetworks@2019-11-01' = if (newOrExisting == 'new') {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: subnet1Name
        properties: {
          addressPrefix: subnet1Prefix
          networkSecurityGroup: {
            id: subnet1nsg.id
          }
          routeTable: {
            id: subnet1routetable.id
          }
        }
      }
      {
        name: subnet2Name
        properties: {
          addressPrefix: subnet2Prefix
          delegations: [
            {
              name: 'delegation'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
          networkSecurityGroup: {
            id: subnet2nsg.id
          }
          routeTable: {
            id: subnet2routetable.id
          }
        }
      }
    ]
  }
  resource subnet1 'subnets' existing = {
    name: subnet1Name
  }
  resource subnet2 'subnets' existing = {
    name: subnet2Name
  }

}

//NSGs

resource subnet1nsg 'Microsoft.Network/networkSecurityGroups@2022-07-01' = if (newOrExisting == 'new')  {
  name: subnet1nsgname
  location: location
//  properties: {
   // securityRules: [
     // {}
   // ]
 // }
}

resource subnet2nsg 'Microsoft.Network/networkSecurityGroups@2022-07-01' = if (newOrExisting == 'new')  {
  name: subnet2nsgname
  location: location
 // properties: {
  //  securityRules: [
   //   {}
   // ]
 // }
}

resource subnet1routetable 'Microsoft.Network/routeTables@2022-07-01' = if (newOrExisting == 'new') {
  name: subnet1routetablename
  location: location
  properties: {
    disableBgpRoutePropagation: false
   // routes: [
   //   {}
  //  ]
  }
}

resource subnet2routetable 'Microsoft.Network/routeTables@2022-07-01' = if (newOrExisting == 'new') {
  name: subnet2routetablename
  location: location
  properties: {
    disableBgpRoutePropagation: false
 //   routes: [
   //   {}
  //  ]
  }
}

//Get existing VNET for private endpoint
resource existingvnet 'Microsoft.Network/virtualNetworks@2021-05-01' existing = if (newOrExisting == 'existing') {
  name: vnetName
  scope: az.resourceGroup('${vnetRG}')
}

//Get existing subnet for private endpoint
resource existingsubnet1 'Microsoft.Network/virtualNetworks/subnets@2021-05-01' existing = if (newOrExisting == 'existing') {
  parent: existingvnet
  name: subnet1Name
}

//Get existing subnet for vnet integration
resource existingsubnet2 'Microsoft.Network/virtualNetworks/subnets@2021-05-01' existing = if (newOrExisting == 'existing') {
  parent: existingvnet
  name: subnet2Name
}

output vnetid string = ((newOrExisting == 'new') ? newvnet.id : existingvnet.id)
output subnet1Resourceid string = ((newOrExisting == 'new') ? newvnet::subnet1.id : existingsubnet1.id)
output subnet2Resourceid string = ((newOrExisting == 'new') ? newvnet::subnet2.id : existingsubnet2.id)


