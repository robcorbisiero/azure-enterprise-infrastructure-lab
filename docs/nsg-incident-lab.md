# Azure NSG incident and recovery lab

**Status: prepared for a live run.** The evidence table below contains expected results. The existing lab documents a deployed network baseline and an ARM what-if preview of segmentation. This exercise uses a disposable copy of the proposed network to measure workload behaviour.

## Scenario

A private client at `10.10.10.4` must reach a private app at `10.10.30.4:443`. A separate listener on TCP 8443 gives us a negative control. Both services return a short test marker over TCP. Port 443 here tests the NSG rule; this exercise does not implement TLS. Use a fresh connection for each probe so existing stateful flows cannot mask a rule change.

## Scope and cost

Canada Central, two on-demand Linux `Standard_B2s` VMs, two 32 GiB Standard SSD LRS OS disks, and two private NICs. Use an Ubuntu LTS platform image with cloud-init and Python 3. VM boot diagnostics uses managed storage to read serial output from the probes. No public IP, NAT gateway or Bastion resource is part of the lab.

Azure Retail Prices API listed CA$0.0651 per VM-hour and CA$3.7059 per E4 disk-month, plus CA$0.0028 per 10,000 disk operations, on November 23, 2026. Two hours of compute and prorated disk capacity are roughly CA$0.28 before disk transactions and any diagnostics meters. Set a CA$5 credit budget for the session as a planning ceiling. This estimate is not a hard cap. Before provisioning, confirm the free trial spending limit is enabled, verify regional SKU availability and the deployment estimate, and get approval for the exact scope. Do not upgrade the subscription for this lab.

## Provision and observe

1. Create an isolated resource group named `rg-azure-nsg-incident-lab` in Canada Central. Ensure it is newly created for this exercise. Preview and then deploy the [segmented ARM template at the reviewed commit](https://github.com/robcorbisiero/azure-enterprise-infrastructure-lab/blob/03385c171e41ec9a8a5ede1a92a15393e15c5708/infra/segmented-network.json) in incremental mode. Keep this template unchanged for recovery.
2. Provision the client in `snet-servers` at private IP `10.10.10.4`, and the app in `snet-applications` at `10.10.30.4`. Use SSH-key authentication with the operator's public key, disable password authentication, and create neither a public IP nor a NIC-level NSG. Supply [client cloud-init](../lab/incident/client.cloud-init.yml) and [app cloud-init](../lab/incident/app.cloud-init.yml) to their respective VMs and enable managed boot diagnostics. The probes run as systemd services and print to the VM console so they do not require a remote shell or guest Internet access.
3. Check the app boot diagnostics serial log for the readiness line covering both listeners. Read the client serial log for connection results. In Network Watcher IP flow verify, select the app VM and NIC and test inbound TCP from `10.10.10.4:49152` to each app port. Save the rule and decision. Refresh logs until the observed timestamps match the phase.
4. Delete only `allow-server-https` from `nsg-applications-lab-dev` in the disposable group. Wait until a fresh probe and IP flow verify both show the outage. Record UTC timestamps. If the app readiness line is missing, diagnose guest startup before attributing a timeout to the NSG.
5. Preview restoration, reapply the same reviewed ARM template in incremental mode to the disposable group, and confirm a new connection succeeds and IP flow verify reports the allow rule. Run a final what-if and report any unexpected network changes.
6. Capture sanitized evidence, delete the disposable resource group, and confirm the group no longer exists. Verify billing after usage reporting catches up. Preserve the original lab resource group.

| Phase | Client result expected | Effective rule expected |
| --- | --- | --- |
| Baseline, TCP 443 | PASS | allow-server-https |
| Baseline, TCP 8443 | Timeout with app listener ready | deny-other-inbound |
| Incident, TCP 443 | Timeout with app listener ready | deny-other-inbound |
| Recovery, TCP 443 | PASS | allow-server-https |

## Evidence to publish after the live run

Record the UTC timeline, template commit, timestamped client output, app readiness, Network Watcher decisions, recovery preview, and cleanup verification. Remove subscription IDs, account information and unrelated serial output. Report what was actually observed for each phase and calculate the time between the first failed and first successful probe. This validates the server-to-app path only. A management-to-app SSH test would require its own client and evidence.

References: [IP flow verify](https://learn.microsoft.com/en-us/azure/network-watcher/diagnose-vm-network-traffic-filtering-problem), [cloud-init troubleshooting](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/cloud-init-troubleshooting), [Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices).
