import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_network


class NetworkPolicyTests(unittest.TestCase):
    def setUp(self):
        self.template = json.loads(check_network.TEMPLATE.read_text())

    def validate(self, template):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'network.json'
            path.write_text(json.dumps(template))
            with patch.object(check_network, 'TEMPLATE', path):
                check_network.main()

    def test_baseline(self):
        self.validate(self.template)

    def test_duplicate_property_is_rejected(self):
        body = json.dumps(self.template).replace('"resources":', '"resources": [], "resources":', 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "network.json"
            path.write_text(body)
            with patch.object(check_network, "TEMPLATE", path):
                with self.assertRaisesRegex(SystemExit, "Duplicate JSON property: resources"):
                    check_network.main()

    def test_reject_security_and_cost_regressions(self):
        mutations = {
            'extra resource': lambda t: t['resources'].append({'type': 'Microsoft.Compute/virtualMachines', 'name': 'vm'}),
            'nested deployment': lambda t: t['resources'][0].update(resources=[{'type': 'Microsoft.Resources/deployments'}]),
            'public outbound': lambda t: t['resources'][1]['properties']['subnets'][0]['properties'].update(defaultOutboundAccess=True),
            'NAT gateway': lambda t: t['resources'][1]['properties']['subnets'][0]['properties'].update(natGateway={'id': 'gateway'}),
            'private endpoint': lambda t: t['resources'][1]['properties']['subnets'][0]['properties'].update(privateEndpoints=[{'id': 'endpoint'}]),
            'NSG allow rule': lambda t: t['resources'][0]['properties']['securityRules'].append({'name': 'allow-all'}),
            'overlapping subnet': lambda t: t['resources'][1]['properties']['subnets'][1]['properties'].update(addressPrefixes=['10.10.10.0/24']),
            'missing NSG': lambda t: t['resources'][1]['properties']['subnets'][0]['properties'].update(networkSecurityGroup={'id': 'other'}),
            'address space drift': lambda t: t['resources'][1]['properties']['addressSpace'].update(extra=True),
            'template schema drift': lambda t: t.update({'$schema': 'unexpected'}),
            'API drift': lambda t: t['resources'][0].update(apiVersion='2099-01-01'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                template = copy.deepcopy(self.template)
                mutate(template)
                with self.assertRaises(SystemExit):
                    self.validate(template)


if __name__ == '__main__':
    unittest.main()
