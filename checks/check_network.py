"""Check that the ARM template preserves the documented lab baseline."""

import ipaddress
import json
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "infra" / "network.json"
EXPECTED_SUBNETS = {
    "snet-servers": "10.10.10.0/24",
    "snet-management": "10.10.20.0/24",
    "snet-applications": "10.10.30.0/24",
}
NSG_NAME = "nsg-enterprise-lab-dev"
NSG_ID = f"[resourceId('Microsoft.Network/networkSecurityGroups', '{NSG_NAME}')]"


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    require(set(template) == {"$schema", "contentVersion", "resources"}, "Unexpected template sections.")
    resources = template["resources"]
    for resource in resources:
        allowed = {"type", "apiVersion", "name", "location", "properties"}
        if resource["type"] == "Microsoft.Network/virtualNetworks":
            allowed.add("dependsOn")
        require(set(resource) == allowed, "Unexpected resource fields or nested resources.")
        require(resource["apiVersion"] == "2024-03-01", "Review API version changes explicitly.")
    by_name = {resource["name"]: resource for resource in resources}
    require(
        len(resources) == 2 and set(by_name) == {NSG_NAME, "vnet-enterprise-lab-dev"},
        "Expected exactly one lab NSG and one lab VNet.",
    )
    nsg = by_name[NSG_NAME]
    vnet = by_name["vnet-enterprise-lab-dev"]
    require(nsg["type"] == "Microsoft.Network/networkSecurityGroups", "Invalid NSG type.")
    require(vnet["type"] == "Microsoft.Network/virtualNetworks", "Invalid VNet type.")
    require(all(r["location"] == "canadacentral" for r in resources), "Unexpected region.")
    require(set(nsg["properties"]) == {"securityRules"}, "Unexpected NSG settings.")
    require(nsg["properties"]["securityRules"] == [], "Expected Azure default rules only.")
    require(vnet["dependsOn"] == [NSG_ID], "VNet must depend on the lab NSG.")

    properties = vnet["properties"]
    require(set(properties) == {"addressSpace", "subnets", "encryption", "privateEndpointVNetPolicies"},
            "Unexpected VNet settings; review security and cost implications.")
    require(properties["addressSpace"]["addressPrefixes"] == ["10.10.0.0/16"], "Unexpected VNet range.")
    require(properties["encryption"] == {"enabled": False, "enforcement": "AllowUnencrypted"}, "Unexpected VNet encryption configuration.")
    require(properties["privateEndpointVNetPolicies"] == "Disabled", "Unexpected VNet private endpoint policy.")
    vnet_range = ipaddress.ip_network("10.10.0.0/16")
    subnets = properties["subnets"]
    require(
        len(subnets) == len(EXPECTED_SUBNETS)
        and {subnet["name"] for subnet in subnets} == set(EXPECTED_SUBNETS),
        "Subnet names do not match the documented baseline.",
    )

    ranges = []
    for subnet in subnets:
        name = subnet["name"]
        require(set(subnet) == {"name", "properties"}, "Unexpected subnet fields.")
        settings = subnet["properties"]
        require(set(settings) == {"addressPrefixes", "defaultOutboundAccess", "networkSecurityGroup"},
                f"{name} has unapproved settings, endpoints, or gateways.")
        prefixes = settings["addressPrefixes"]
        require(len(prefixes) == 1, f"{name} must have one IPv4 range.")
        prefix = prefixes[0]
        require(prefix == EXPECTED_SUBNETS[name], f"{name} has an unexpected range.")
        subnet_range = ipaddress.ip_network(prefix)
        require(subnet_range.subnet_of(vnet_range), f"{name} must be inside the VNet range.")
        require(not any(subnet_range.overlaps(existing) for existing in ranges), f"{name} overlaps another subnet.")
        require(settings["defaultOutboundAccess"] is False, f"{name} must be private.")
        require(settings["networkSecurityGroup"]["id"] == NSG_ID, f"{name} must use the lab NSG.")
        require("natGateway" not in settings, f"{name} must not attach a NAT gateway.")
        ranges.append(subnet_range)

    print("Verified VNet and subnet ranges, private outbound settings, and NSG associations.")


if __name__ == "__main__":
    main()

