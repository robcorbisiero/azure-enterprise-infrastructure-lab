# Segmented network proposal

[The segmented ARM template](../infra/segmented-network.json) is a review candidate for the lab. It adds destination-subnet NSGs for servers, management and applications. The example addresses assume Linux workloads and a single private HTTPS listener.

| Source | Destination | Allowed inbound traffic |
| --- | --- | --- |
| Management host `10.10.20.4` | Server `10.10.10.4` | TCP 22 |
| Management host `10.10.20.4` | Application `10.10.30.4` | TCP 22 |
| Server `10.10.10.4` | Application `10.10.30.4` | TCP 443 |

Priority 300 denies every other new inbound flow at each subnet boundary, including same-subnet inbound flows to workload interfaces. The policy includes no RDP or load-balancer probe exceptions. Confirm actual IP assignments, management access and required health probes before a future deployment.

## Review and validation

Run these commands from the repo root.

```sh
python checks/check_network.py
python checks/test_segmentation.py
```

The policy test reads the ARM rules directly and evaluates priority, protocol, source, destination and destination port for representative new connections. Azure effective-rule evaluation, stateful replies and host connectivity require live testing. The variant leaves default outbound access disabled on all three subnets.

The original [baseline template](../infra/network.json) is the rollback reference for the shared NSG associations. If this variant is approved, use incremental deployment and preview the exact target first. Expect three new NSGs and a subnet association change on the VNet. Review any additional predictions before proceeding. Restoring the baseline associations leaves the extra NSGs available for separately reviewed cleanup.

## Azure what-if evidence

On November 21, 2026, Azure ARM what-if succeeded in Incremental mode against `rg-enterprise-lab-dev` using the [exact proposed template](https://github.com/robcorbisiero/azure-enterprise-infrastructure-lab/blob/9dc0ae7d5d5d98bae97d6f4c70d1dd75926659c3/infra/segmented-network.json).

| Prediction | Resource | Detail |
| --- | --- | --- |
| Create | `nsg-applications-lab-dev` | Attach to `snet-applications` |
| Create | `nsg-management-lab-dev` | Attach to `snet-management` |
| Create | `nsg-servers-lab-dev` | Attach to `snet-servers` |
| Modify | `vnet-enterprise-lab-dev` | Azure flagged only the subnet array. Each subnet is predicted to use its dedicated NSG and retain `defaultOutboundAccess: false`. |
| Ignore | `nsg-enterprise-lab-dev` | Existing shared NSG is outside the proposed template. |

Azure predicted zero resource deletions. This was a read-only preview. The proposal has not been deployed or tested with live traffic. See the [separate baseline preview](segmentation.md#follow-up-preview) for the current shared-NSG deployment.
