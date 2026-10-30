import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.sg_inspect import inspect

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "cloud" / "aws-network" / "fixtures"
CLIENT = "sg-00000000000000001"
SERVICE = "sg-00000000000000002"
OTHER = "sg-00000000000000003"


def snapshot(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def analyze(data, source=None, destination=None, port=8081):
    return inspect(data, source or [CLIENT], destination or [SERVICE],
                   "10.24.1.20", "10.24.2.30", port)


class SecurityGroupInspectionTests(unittest.TestCase):
    def test_missing_ingress_and_scoped_recovery(self):
        broken = analyze(snapshot("broken.json"))
        self.assertEqual(broken["source_egress"]["state"], "match")
        self.assertEqual(broken["destination_ingress"]["state"], "no_match")
        self.assertEqual(broken["sg_rule_result"], "no_match")
        recovered = analyze(snapshot("recovered.json"))
        self.assertEqual(recovered["sg_rule_result"], "match")
        self.assertEqual(recovered["destination_ingress"]["matches"][0]["peer"], CLIENT)

    def test_other_client_and_wrong_port_remain_unmatched(self):
        data = snapshot("recovered.json")
        self.assertEqual(analyze(data, source=[OTHER])["destination_ingress"]["state"], "no_match")
        self.assertEqual(analyze(data, port=8082)["sg_rule_result"], "no_match")

    def test_rules_from_all_attached_groups_are_aggregated(self):
        data = snapshot("broken.json")
        extra = copy.deepcopy(snapshot("recovered.json")["SecurityGroups"][1])
        extra["GroupId"] = "sg-00000000000000004"
        data["SecurityGroups"].append(extra)
        report = analyze(data, destination=[SERVICE, extra["GroupId"]])
        self.assertEqual(report["sg_rule_result"], "match")
        self.assertEqual(report["destination_ingress"]["matches"][0]["group_id"], extra["GroupId"])

    def test_ipv4_cidrs_and_all_protocols(self):
        data = snapshot("broken.json")
        data["SecurityGroups"][0]["IpPermissionsEgress"] = [
            {"IpProtocol": "-1", "IpRanges": [{"CidrIp": "10.24.2.0/24"}],
             "UserIdGroupPairs": [], "PrefixListIds": []}
        ]
        data["SecurityGroups"][1]["IpPermissions"] = [
            {"IpProtocol": "6", "FromPort": 8080, "ToPort": 8090,
             "IpRanges": [{"CidrIp": "10.24.1.0/24"}], "UserIdGroupPairs": [], "PrefixListIds": []}
        ]
        report = analyze(data)
        self.assertEqual(report["sg_rule_result"], "match")
        self.assertEqual(report["destination_ingress"]["matches"][0]["type"], "ipv4_cidr")
        data["SecurityGroups"][1]["IpPermissions"][0]["IpRanges"][0]["CidrIp"] = "10.25.0.0/16"
        self.assertEqual(analyze(data)["destination_ingress"]["state"], "no_match")

    def test_prefix_list_or_unresolved_reference_is_not_claimed_denied(self):
        data = snapshot("broken.json")
        data["SecurityGroups"][1]["IpPermissions"] = [
            {"IpProtocol": "tcp", "FromPort": 8081, "ToPort": 8081,
             "PrefixListIds": [{"PrefixListId": "pl-0123456789abcdef0"}]}
        ]
        self.assertEqual(analyze(data)["sg_rule_result"], "indeterminate")
        data["SecurityGroups"][1]["IpPermissions"] = [
            {"IpProtocol": "tcp", "FromPort": 8081, "ToPort": 8081,
             "UserIdGroupPairs": [{"GroupName": "unknown"}]}
        ]
        self.assertEqual(analyze(data)["destination_ingress"]["state"], "indeterminate")

    def test_known_match_survives_other_unresolved_rules(self):
        data = snapshot("recovered.json")
        data["SecurityGroups"][1]["IpPermissions"].append(
            {"IpProtocol": "tcp", "FromPort": 8081, "ToPort": 8081,
             "PrefixListIds": [{"PrefixListId": "pl-0123456789abcdef0"}]})
        result = analyze(data)
        self.assertEqual(result["sg_rule_result"], "match")
        self.assertTrue(any(item["type"] == "unresolved_prefix_list"
                            for item in result["destination_ingress"]["unresolved"]))

    def test_missing_relevant_rule_fields_cannot_prove_denial(self):
        data = snapshot("recovered.json")
        del data["SecurityGroups"][1]["IpPermissions"][0]["PrefixListIds"]
        result = analyze(data, source=[OTHER])
        self.assertEqual(result["sg_rule_result"], "indeterminate")
        self.assertTrue(any(item["type"] == "incomplete_permission"
                            for item in result["destination_ingress"]["unresolved"]))

    def test_incomplete_snapshot_and_different_vpcs_are_rejected(self):
        data = snapshot("broken.json")
        del data["SecurityGroups"][0]["IpPermissionsEgress"]
        with self.assertRaisesRegex(ValueError, "complete snapshot"):
            analyze(data)
        data = snapshot("broken.json")
        data["SecurityGroups"][1]["VpcId"] = "vpc-00000000000000002"
        with self.assertRaisesRegex(ValueError, "same VPC"):
            analyze(data)
        with self.assertRaisesRegex(ValueError, "every supplied attached group"):
            analyze(snapshot("broken.json"), source=["sg-unknown"])

    def test_malformed_rules_fail_closed(self):
        data = snapshot("broken.json")
        data["SecurityGroups"][0]["IpPermissionsEgress"][0]["FromPort"] = "8081"
        with self.assertRaisesRegex(ValueError, "valid FromPort"):
            analyze(data)
        data = snapshot("broken.json")
        data["SecurityGroups"][0]["IpPermissionsEgress"][0]["IpRanges"] = [{"CidrIp": "not-a-cidr"}]
        with self.assertRaisesRegex(ValueError, "invalid IPv4 CIDR"):
            analyze(data)
        with self.assertRaises(ValueError):
            inspect(snapshot("broken.json"), [CLIENT], [SERVICE], "::1", "10.24.2.30", 8081)

    def test_cli_reports_real_result_and_rejects_missing_snapshot(self):
        command = [sys.executable, str(ROOT / "scripts" / "sg_inspect.py"),
                   "--snapshot", str(FIXTURES / "broken.json"),
                   "--source-sg", CLIENT, "--destination-sg", SERVICE,
                   "--source-ip", "10.24.1.20", "--destination-ip", "10.24.2.30", "--port", "8081"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["sg_rule_result"], "no_match")
        command[command.index("--snapshot") + 1] = str(FIXTURES / "missing.json")
        error = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(error.returncode, 2)
        self.assertIn("Cannot inspect snapshot", error.stderr)


if __name__ == "__main__":
    unittest.main()
