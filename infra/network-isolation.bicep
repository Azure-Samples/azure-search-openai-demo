metadata description = 'Sets up private networking for all resources, using VNet, private endpoints, and DNS zones.'

@description('The name of the VNet to create')
param vnetName string

@description('The location to create the VNet and private endpoints')
param location string = resourceGroup().location

@description('The tags to apply to all resources')
param tags object = {}

@allowed(['appservice', 'containerapps'])
param deploymentTarget string

param useVpnGateway bool = false

param vpnGatewayName string = '${vnetName}-vpn-gateway'
param dnsResolverName string = '${vnetName}-dns-resolver'

module containerAppsNSG 'br/public:avm/res/network/network-security-group:0.5.1' = if (deploymentTarget == 'containerapps') {
  name: 'container-apps-nsg'
  params: {
    name: '${vnetName}-container-apps-nsg'
    location: location
    tags: tags
    securityRules: [
      {
        name: 'AllowHttpsInbound'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          sourceAddressPrefix: 'Internet'
          destinationPortRange: '443'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        // TODO: Were any of these rules really needed??
        name: 'AllowPrivateEndpointsOutbound'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          sourceAddressPrefix: '10.0.0.0/21'
          destinationPortRange: '443'
          destinationAddressPrefix: '10.0.8.0/24'
          access: 'Allow'
          priority: 200
          direction: 'Outbound'
        }
      }
      {
        name: 'AllowDnsOutbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '53'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 210
          direction: 'Outbound'
        }
      }
      {
        name: 'AllowVNetOutbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          access: 'Allow'
          priority: 220
          direction: 'Outbound'
        }
      }
    ]
  }
}

module privateEndpointsNSG 'br/public:avm/res/network/network-security-group:0.5.1' = if (deploymentTarget == 'containerapps') {
  name: 'private-endpoints-nsg'
  params: {
    name: '${vnetName}-private-endpoints-nsg'
    location: location
    tags: tags
    securityRules: [
      {
        name: 'AllowVnetInBound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowAzureLoadBalancerInbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: 'AzureLoadBalancer'
          destinationPortRange: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 110
          direction: 'Inbound'
        }
      }
      {
        name: 'DenyInternetInbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: 'Internet'
          destinationPortRange: '*'
          destinationAddressPrefix: '*'
          access: 'Deny'
          priority: 4096
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowVnetOutbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          access: 'Allow'
          priority: 100
          direction: 'Outbound'
        }
      }
      {
        name: 'AllowAzureCloudOutbound'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '443'
          destinationAddressPrefix: 'AzureCloud'
          access: 'Allow'
          priority: 110
          direction: 'Outbound'
        }
      }
      {
        name: 'AllowDnsOutbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '53'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 120
          direction: 'Outbound'
        }
      }
      {
        name: 'DenyInternetOutbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '*'
          destinationAddressPrefix: 'Internet'
          access: 'Deny'
          priority: 4096
          direction: 'Outbound'
        }
      }
    ]
  }
}

module vnet 'br/public:avm/res/network/virtual-network:0.6.1' = {
  name: 'vnet'
  params: {
    name: vnetName
    location: location
    tags: tags
    addressPrefixes: [
      '10.0.0.0/16'
    ]
    subnets: union(
      [
        {
          name: 'backend-subnet'
          addressPrefix: '10.0.8.0/24'
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          networkSecurityGroupResourceId: privateEndpointsNSG.outputs.resourceId
        }
        {
          name: 'GatewaySubnet' // Required name for Gateway subnet
          addressPrefix: '10.0.255.0/27' // Using a /27 subnet size which is minimal required size for gateway subnet
        }
        {
          name: 'dns-resolver-subnet' // Dedicated subnet for Azure Private DNS Resolver
          addressPrefix: '10.0.11.0/28'
          delegation: 'Microsoft.Network/dnsResolvers'
        }
      ],
      deploymentTarget == 'appservice'
        ? [
            {
              name: 'app-int-subnet'
              addressPrefix: '10.0.3.0/24'
              privateEndpointNetworkPolicies: 'Enabled'
              privateLinkServiceNetworkPolicies: 'Enabled'
              // TODO: Are we sure we don't need App Service Plan/ID? Test this.
              delegation: 'Microsoft.Web/serverFarms'
            }
          ]
        : [
            {
              name: 'app-int-subnet'
              addressPrefix: '10.0.0.0/21'
              networkSecurityGroupResourceId: containerAppsNSG.outputs.resourceId
              delegation: 'Microsoft.App/environments'
            }
          ]
    )
  }
}

module virtualNetworkGateway 'br/public:avm/res/network/virtual-network-gateway:0.8.0' = if (useVpnGateway) {
  name: 'virtual-network-gateway'
  params: {
    name: vpnGatewayName
    clusterSettings: {
      clusterMode: 'activePassiveNoBgp'
    }
    gatewayType: 'Vpn'
    virtualNetworkResourceId: vnet.outputs.resourceId
    vpnGatewayGeneration: 'Generation2'
    vpnClientAddressPoolPrefix: '172.16.201.0/24'
    skuName: 'VpnGw2'
    vpnClientAadConfiguration: {
      aadAudience: 'c632b3df-fb67-4d84-bdcf-b95ad541b5c8' // Azure VPN client
      aadIssuer: 'https://sts.windows.net/${tenant().tenantId}/'
      aadTenant: '${environment().authentication.loginEndpoint}${tenant().tenantId}'
      vpnAuthenticationTypes: [
        'AAD'
      ]
      vpnClientProtocols: [
        'OpenVPN'
      ]
    }
  }
}

// Based on https://luke.geek.nz/azure/azure-point-to-site-vpn-and-private-dns-resolver/
// Manual step required of updating azurevpnconfig.xml to use the correct DNS server IP address
module dnsResolver 'br/public:avm/res/network/dns-resolver:0.5.4' = if (useVpnGateway) {
  name: 'dns-resolver'
  params: {
    name: dnsResolverName
    location: location
    virtualNetworkResourceId: vnet.outputs.resourceId
    inboundEndpoints: [
      {
        name: 'inboundEndpoint'
        subnetResourceId: useVpnGateway ? vnet.outputs.subnetResourceIds[2] : ''
      }
    ]
  }
}

output backendSubnetId string = vnet.outputs.subnetResourceIds[0]
output privateDnsResolverSubnetId string = useVpnGateway ? vnet.outputs.subnetResourceIds[2] : ''
output appSubnetId string = vnet.outputs.subnetResourceIds[3]
output vnetName string = vnet.outputs.name
output vnetId string = vnet.outputs.resourceId
output virtualNetworkGatewayName string = useVpnGateway ? virtualNetworkGateway.outputs.name : ''
