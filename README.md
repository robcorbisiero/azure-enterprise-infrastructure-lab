# Azure Enterprise Infrastructure Lab

I built and verified a private network foundation in Azure Canada Central as a hands-on infrastructure lab. The project demonstrates IPv4 subnet planning, Azure network security groups, cost-aware provisioning, and infrastructure as code.

**Azure-verified result.** The first ARM what-if flagged VNet differences. After aligning the template with the live settings, Azure predicted zero changes across the VNet and NSG. [See the before-and-after evidence](docs/segmentation.md#follow-up-preview).

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

## Azure Portal screenshots

Captured on November 21, 2026. The images are cropped to exclude account and subscription identifiers.

- [VNet address space](docs/screenshots/01-vnet-address-space.jpg)
- [Subnet inventory](docs/screenshots/02-vnet-subnets.jpg)
- [Servers private access](docs/screenshots/03-private-servers.jpg)
- [Management private access](docs/screenshots/03-private-management.jpg)
- [Applications private access](docs/screenshots/03-private-applications.jpg)
- [NSG subnet associations](docs/screenshots/06-nsg-associations.jpg)
- [Azure cost snapshot](docs/screenshots/07-cost-snapshot.jpg)

## Infrastructure as code and verification

[`infra/network.json`](infra/network.json) describes the verified network in an Azure Resource Manager template. It expects an existing resource group and declares the complete subnet list and default-only NSG. The template has not been applied to Azure. Review a what-if preview for unexpected changes before applying it to any existing network.

Run the local baseline checks with `python checks/check_network.py`. The checks require Python 3 and use only its standard library. For the design decisions, portal verification steps, and a connectivity test plan, see the [operations runbook](docs/runbook.md).

```sh
az deployment group what-if --resource-group rg-enterprise-lab-dev --template-file infra/network.json
```

## Proposed subnet segmentation

The [traffic policy and validation plan](docs/segmentation.md) records the current shared-NSG baseline, proposed least-privilege flows, and the before-and-after Azure what-if results.
