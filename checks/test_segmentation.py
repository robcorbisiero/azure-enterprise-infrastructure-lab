"""Evaluate the proposed inbound rules for new connections using standard-library tests."""

import ipaddress
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def resources(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))["resources"]


def matches_address(prefix, address):
    return prefix == "*" or ipaddress.ip_address(address) in ipaddress.ip_network(prefix)


def inbound_action(rules, source, destination, port, protocol="Tcp"):
    for rule in sorted(rules, key=lambda item: item["properties"]["priority"]):
        properties = rule["properties"]
        if (
            properties["direction"] == "Inbound"
            and properties["protocol"] in {"*", protocol}
            and properties["sourcePortRange"] == "*"
            and properties["destinationPortRange"] in {"*", str(port)}
            and matches_address(properties["sourceAddressPrefix"], source)
            and matches_address(properties["destinationAddressPrefix"], destination)
        ):
            return properties["access"]
    raise AssertionError("No explicit rule matched this flow.")


class SegmentationTests(unittest.TestCase):
    def setUp(self):
        proposed = resources("infra/segmented-network.json")
        self.vnet = next(r for r in proposed if r["type"] == "Microsoft.Network/virtualNetworks")
        self.subnets = self.vnet["properties"]["subnets"]
        self.nsgs = {
            f"[resourceId('Microsoft.Network/networkSecurityGroups', '{r['name']}')]": r
            for r in proposed if r["type"] == "Microsoft.Network/networkSecurityGroups"
        }

    def test_baseline_is_preserved_apart_from_associations(self):
        baseline = next(
            resource for resource in resources("infra/network.json")
            if resource["type"] == "Microsoft.Network/virtualNetworks"
        )
        self.assertEqual(len(self.nsgs), 3)
        expected_ids = [subnet["properties"]["networkSecurityGroup"]["id"] for subnet in self.subnets]
        self.assertEqual(len(set(expected_ids)), 3)
        self.assertEqual(set(expected_ids), set(self.nsgs))
        expected = {subnet["name"]: subnet for subnet in baseline["properties"]["subnets"]}
        for subnet in self.subnets:
            subnet["properties"]["networkSecurityGroup"] = expected[subnet["name"]]["properties"]["networkSecurityGroup"]
        self.vnet["dependsOn"] = baseline["dependsOn"]
        self.assertEqual(self.vnet, baseline)

    def test_allow_rules_and_terminal_deny_are_explicit(self):
        for group in self.nsgs.values():
            rules = sorted(group["properties"]["securityRules"], key=lambda rule: rule["properties"]["priority"])
            priorities = [rule["properties"]["priority"] for rule in rules]
            with self.subTest(group=group["name"]):
                self.assertEqual(len(priorities), len(set(priorities)))
                self.assertEqual(priorities[-1], 300)
                self.assertTrue(all(rule["properties"]["access"] == "Allow" for rule in rules[:-1]))
                self.assertEqual(rules[-1]["properties"], {
                    "priority": 300, "access": "Deny", "direction": "Inbound",
                    "sourceAddressPrefix": "*", "destinationAddressPrefix": "*",
                    "sourcePortRange": "*", "destinationPortRange": "*", "protocol": "*",
                })

    def test_representative_new_connections(self):
        flows = [
            ("approved admin to server SSH", "10.10.20.4", "10.10.10.4", 22, "Tcp", "Allow"),
            ("approved admin to app SSH", "10.10.20.4", "10.10.30.4", 22, "Tcp", "Allow"),
            ("other management host to server SSH", "10.10.20.5", "10.10.10.4", 22, "Tcp", "Deny"),
            ("approved admin to wrong server", "10.10.20.4", "10.10.10.5", 22, "Tcp", "Deny"),
            ("approved server to app HTTPS", "10.10.10.4", "10.10.30.4", 443, "Tcp", "Allow"),
            ("approved server to app UDP 443", "10.10.10.4", "10.10.30.4", 443, "Udp", "Deny"),
            ("approved server to app HTTP", "10.10.10.4", "10.10.30.4", 80, "Tcp", "Deny"),
            ("other server to app HTTPS", "10.10.10.5", "10.10.30.4", 443, "Tcp", "Deny"),
            ("app initiates connection to server", "10.10.30.4", "10.10.10.4", 443, "Tcp", "Deny"),
            ("server initiates connection to management", "10.10.10.4", "10.10.20.4", 22, "Tcp", "Deny"),
            ("outside source to app HTTPS", "203.0.113.4", "10.10.30.4", 443, "Tcp", "Deny"),
            ("admin to server RDP", "10.10.20.4", "10.10.10.4", 3389, "Tcp", "Deny"),
        ]
        for name, source, destination, port, protocol, expected in flows:
            with self.subTest(name=name):
                subnet = next(
                    item for item in self.subnets
                    if matches_address(item["properties"]["addressPrefixes"][0], destination)
                )
                nsg = self.nsgs[subnet["properties"]["networkSecurityGroup"]["id"]]
                self.assertEqual(inbound_action(
                    nsg["properties"]["securityRules"], source, destination, port, protocol,
                ), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
