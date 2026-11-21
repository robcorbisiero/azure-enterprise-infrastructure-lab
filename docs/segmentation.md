# Proposed subnet segmentation

The deployed baseline uses one shared NSG with Azure default rules. Those rules allow VNet traffic. This proposal defines which new connections a future segmented baseline should allow.

## Traffic policy

The application is assumed to expose HTTPS on TCP 443. Management must use a dedicated private admin host and an OS-specific port. Replace example host addresses with approved private addresses before implementation.

| Source | Destination | Protocol and port | Expected result |
| --- | --- | --- | --- |
| Approved management host in `10.10.20.0/24` | Approved server or application host | TCP 22 for SSH or TCP 3389 for RDP, selected per destination | Allow |
| Other sources in management subnet | Servers or applications | TCP 22 or 3389 | Deny |
| Approved server workload in `10.10.10.0/24` | Approved application listener in `10.10.30.0/24` | TCP 443 | Allow |
| Any other server source or destination port | Applications | Any | Deny |
| Applications | Servers or management | Any new connection | Deny |
| Servers | Management | Any new connection | Deny |
| Outside the lab | Any lab subnet | Unsolicited inbound traffic | Deny |

## Implementation and test plan

- Use destination subnet NSGs with narrow inbound allow rules at priorities 100–199. Add a VNet inbound deny at 300 so Azure's default VNet allow does not permit undeclared flows. This also blocks undeclared same-subnet traffic. Review any workload, peering, and platform dependencies before changing rules.
- Azure NSGs are stateful. Test new connections in both directions and verify that responses to allowed sessions work. Record the source, destination, protocol, port, effective rule and result.
- Test from an authorized admin host and a second private source that should be denied. Test HTTPS on the approved destination and at least one unapproved port. Verify private Internet egress separately.
- Keep the current template as the baseline for restoring subnet associations. Preview any future change with ARM what-if and review it before applying it.

## Verification status

The local template check passed. An Azure what-if run was attempted on November 21, 2026. The browser could open the Cloud Shell pane but could not start Bash, so Azure returned no deployment prediction. No template or NSG rule changes were applied. The traffic expectations above have not been tested against live workloads.

From an authenticated Azure CLI session, run this read-only preview from the repository root.

```sh
az deployment group what-if --resource-group rg-enterprise-lab-dev --template-file infra/network.json --result-format ResourceIdOnly
```

Record the operation date, change counts, and any relevant differences after replacing subscription identifiers. If the summary reports a modification, rerun with `--result-format FullResourcePayloads` and inspect the changed properties before recording a conclusion.
