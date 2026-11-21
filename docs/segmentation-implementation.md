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

The proposed template has not been deployed to Azure. The live [what-if evidence](segmentation.md#follow-up-preview) applies to the shared-NSG baseline only.
