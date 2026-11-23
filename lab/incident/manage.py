#!/usr/bin/env python3
"""Deploy and remove the disposable Azure NSG lab."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
REGION = "canadacentral"
GROUP = "rg-azure-nsg-incident-lab"
TAG = "nsg-incident-lab"
NETWORK_BLOB = "412b0154e6efb59d2b097d9d3d57422f0eb257df"
VNET = "vnet-enterprise-lab-dev"
HOSTS = (
    ("app", "snet-applications", "10.10.30.4"),
    ("client", "snet-servers", "10.10.10.4"),
)


def resource_id(kind, *names):
    arguments = ", ".join(f"'{value}'" for value in (kind, *names))
    return f"[resourceId({arguments})]"


def build_template():
    source = (ROOT / "network.json").read_bytes()
    blob_sha = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    if blob_sha != NETWORK_BLOB:
        raise ValueError("network.json differs from the reviewed Git blob")

    template = json.loads(source)
    template["parameters"] = {"sshKey": {"type": "string"}}
    custom_data = {}
    for role, subnet, address in HOSTS:
        vm = f"vm-nsg-{role}"
        nic = f"nic-nsg-{role}"
        nic_type = "Microsoft.Network/networkInterfaces"
        nic_id = resource_id(nic_type, nic)
        data_parameter = f"{role}Init"
        cloud_init = (ROOT / f"{role}.cloud-init.yml").read_bytes()
        if not cloud_init.startswith(b"#cloud-config\n"):
            raise ValueError(f"{role} custom data must start with #cloud-config")
        custom_data[data_parameter] = base64.b64encode(cloud_init).decode("ascii")
        template["parameters"][data_parameter] = {"type": "string"}
        template["resources"].extend([
            {
                "type": nic_type, "apiVersion": "2024-03-01", "name": nic,
                "location": REGION,
                "dependsOn": [resource_id("Microsoft.Network/virtualNetworks", VNET)],
                "properties": {"ipConfigurations": [{"name": "private", "properties": {
                    "privateIPAllocationMethod": "Static", "privateIPAddress": address,
                    "subnet": {"id": resource_id(
                        "Microsoft.Network/virtualNetworks/subnets", VNET, subnet
                    )},
                }}]},
            },
            {
                "type": "Microsoft.Compute/virtualMachines", "apiVersion": "2024-07-01",
                "name": vm, "location": REGION, "dependsOn": [nic_id],
                "properties": {
                    "hardwareProfile": {"vmSize": "Standard_D2als_v7"},
                    "storageProfile": {
                        "imageReference": {
                            "publisher": "Canonical", "offer": "0001-com-ubuntu-server-jammy",
                            "sku": "22_04-lts-gen2", "version": "latest",
                        },
                        "osDisk": {
                            "createOption": "FromImage", "diskSizeGB": 32,
                            "managedDisk": {"storageAccountType": "StandardSSD_LRS"},
                            "deleteOption": "Delete",
                        },
                    },
                    "osProfile": {
                        "computerName": vm, "adminUsername": "laboperator",
                        "customData": f"[parameters('{data_parameter}')]",
                        "linuxConfiguration": {
                            "disablePasswordAuthentication": True,
                            "ssh": {"publicKeys": [{
                                "path": "/home/laboperator/.ssh/authorized_keys",
                                "keyData": "[parameters('sshKey')]",
                            }]},
                        },
                    },
                    "networkProfile": {"networkInterfaces": [{
                        "id": nic_id, "properties": {"primary": True},
                    }]},
                    "diagnosticsProfile": {"bootDiagnostics": {"enabled": True}},
                },
            },
        ])
    return template, custom_data


def azure(subscription, *args, capture=False):
    result = subprocess.run(
        ["az", *args, "--subscription", subscription, "--only-show-errors"],
        check=True, text=True, stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else None


def exists(subscription):
    return json.loads(azure(subscription, "group", "exists", "-n", GROUP, "-o", "json", capture=True))


def cleanup(subscription):
    if not exists(subscription):
        print(f"{GROUP} is absent.")
        return
    tag = azure(subscription, "group", "show", "-n", GROUP, "--query", "tags.purpose",
                "-o", "tsv", capture=True)
    if tag != TAG:
        raise ValueError(f"Refusing to delete {GROUP}: expected purpose={TAG}")
    azure(subscription, "group", "delete", "-n", GROUP, "--yes")
    if exists(subscription):
        raise RuntimeError(f"Azure still reports {GROUP} present")
    print(f"Azure confirmed {GROUP} is absent.")


def deploy(subscription, key_path):
    template, values = build_template()
    key = key_path.read_text(encoding="utf-8").strip()
    if not key.startswith("ssh-rsa ") or "\n" in key:
        raise ValueError("Pass a single RSA public key, for example ~/.ssh/id_rsa.pub")
    values["sshKey"] = key
    with tempfile.TemporaryDirectory() as directory:
        template_path = Path(directory) / "lab.json"
        parameters_path = Path(directory) / "parameters.json"
        template_path.write_text(json.dumps(template), encoding="utf-8")
        parameters_path.write_text(json.dumps({
            "parameters": {name: {"value": value} for name, value in values.items()},
        }), encoding="utf-8")
        if exists(subscription):
            raise ValueError(f"{GROUP} already exists. Inspect it before retrying.")
        azure(subscription, "group", "create", "-n", GROUP, "-l", REGION,
              "--tags", f"purpose={TAG}", "-o", "none")
        arguments = ("-g", GROUP, "--mode", "Incremental", "-f", str(template_path),
                     "-p", f"@{parameters_path}")
        try:
            azure(subscription, "deployment", "group", "validate", *arguments,
                  "--validation-level", "Provider", "-o", "none")
            azure(subscription, "deployment", "group", "what-if", *arguments,
                  "--result-format", "ResourceIdOnly")
            if input("Type deploy to create the two billable VMs: ").strip() != "deploy":
                cleanup(subscription)
                return
            azure(subscription, "deployment", "group", "create", *arguments,
                  "-n", "nsg-incident-run", "--query", "properties.provisioningState", "-o", "tsv")
        except (Exception, KeyboardInterrupt):
            print(f"Deployment stopped. Check {GROUP} and run the cleanup subcommand.")
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Build and validate local inputs without Azure access")
    for command in ("deploy", "cleanup"):
        commands.add_parser(command).add_argument("--subscription", required=True)
    commands.choices["deploy"].add_argument("--ssh-public-key", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "check":
        template, _ = build_template()
        print(f"Validated the pinned network and built {len(template['resources'])} ARM resources.")
    elif args.command == "deploy":
        deploy(args.subscription, args.ssh_public_key.expanduser())
    else:
        cleanup(args.subscription)


if __name__ == "__main__":
    main()
