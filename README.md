# Azure Enterprise Infrastructure Lab

This lab establishes a private network foundation in Azure Canada Central.

## Deployed network

- Resource group `rg-enterprise-lab-dev`
- Virtual network `vnet-enterprise-lab-dev`
- IPv4 address space `10.10.0.0/16`

| Subnet | IPv4 range | Network security group |
| --- | --- | --- |
| `snet-servers` | `10.10.10.0/24` | `nsg-enterprise-lab-dev` |
| `snet-management` | `10.10.20.0/24` | `nsg-enterprise-lab-dev` |
| `snet-applications` | `10.10.30.0/24` | `nsg-enterprise-lab-dev` |

All three subnets are private, with Azure default outbound access disabled and no NAT gateway attached. The shared NSG uses Azure's default rules, which allow traffic within the virtual network and deny unmatched inbound traffic. The three subnets organize address space by role. Traffic between them is permitted by the default virtual network rules.

## Cost controls

This phase used the existing Azure trial subscription. It required only the existing VNet, three subnets and one NSG. No compute, public IP addresses, NAT gateway or paid networking appliances were deployed as part of this phase. The subscription was not upgraded.

The Azure Portal showed zero current and forecast cost at verification on November 21, 2026. Azure usage data can take time to appear. Microsoft's free trial spending limit is enabled by default, and Azure budgets provide alerts. See [Azure spending limits](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit) and [Azure budgets](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets).
