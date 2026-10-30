"""Inspect a saved AWS security-group snapshot for one direct IPv4 TCP flow.

This offline helper never calls AWS and does not determine end-to-end reachability.
It requires complete attached-group input and the direct same-VPC assumptions in
cloud/aws-network/README.md. Prefix-list membership is explicitly unresolved.
"""

import argparse
import ipaddress
import json
import sys
from pathlib import Path


def _items(value, name):
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")
    return value


def _direction(groups, own_ids, peer_ids, peer_ip, permission_key, port):
    matches = []
    unresolved = []
    for group_id in own_ids:
        group = groups[group_id]
        for rule in _items(group[permission_key], permission_key):
            if not isinstance(rule, dict):
                raise ValueError("security-group rules must be objects")
            protocol = rule.get("IpProtocol")
            if not isinstance(protocol, str):
                raise ValueError("every rule requires a string IpProtocol")
            if protocol != "-1":
                if protocol.lower() not in ("tcp", "6"):
                    continue
                low, high = rule.get("FromPort"), rule.get("ToPort")
                if (not isinstance(low, int) or isinstance(low, bool) or
                        not isinstance(high, int) or isinstance(high, bool) or
                        low < 0 or high > 65535 or low > high):
                    raise ValueError("TCP rules require a valid FromPort and ToPort")
                if not low <= port <= high:
                    continue
            for field in ("IpRanges", "UserIdGroupPairs", "PrefixListIds"):
                if field not in rule:
                    unresolved.append({"group_id": group_id, "type": "incomplete_permission", "field": field})
            for item in _items(rule.get("IpRanges", []), "IpRanges"):
                if not isinstance(item, dict) or not isinstance(item.get("CidrIp"), str):
                    raise ValueError("IPv4 ranges require CidrIp")
                try:
                    network = ipaddress.IPv4Network(item["CidrIp"], strict=False)
                except ValueError as exc:
                    raise ValueError("invalid IPv4 CIDR in snapshot") from exc
                if peer_ip in network:
                    matches.append({"group_id": group_id, "type": "ipv4_cidr", "peer": str(network)})
            for item in _items(rule.get("UserIdGroupPairs", []), "UserIdGroupPairs"):
                if not isinstance(item, dict) or not isinstance(item.get("GroupId"), str) or not item["GroupId"]:
                    unresolved.append({"group_id": group_id, "type": "unresolved_group_reference"})
                elif item["GroupId"] in peer_ids:
                    matches.append({"group_id": group_id, "type": "security_group", "peer": item["GroupId"]})
            if _items(rule.get("PrefixListIds", []), "PrefixListIds"):
                unresolved.append({"group_id": group_id, "type": "unresolved_prefix_list"})
    state = "match" if matches else "indeterminate" if unresolved else "no_match"
    return {"state": state, "matches": matches, "unresolved": unresolved}


def inspect(snapshot, source_groups, destination_groups, source_ip, destination_ip, port):
    """Evaluate relevant SG rules in an AWS CLI-shaped JSON snapshot, offline."""
    if not isinstance(snapshot, dict) or "SecurityGroups" not in snapshot:
        raise ValueError("snapshot must contain SecurityGroups")
    source_ip = ipaddress.IPv4Address(source_ip)
    destination_ip = ipaddress.IPv4Address(destination_ip)
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError("port must be a whole number from 1 to 65535")
    if not source_groups or not destination_groups:
        raise ValueError("provide at least one attached group for each endpoint")
    groups = {}
    for group in _items(snapshot["SecurityGroups"], "SecurityGroups"):
        if not isinstance(group, dict) or not isinstance(group.get("GroupId"), str):
            raise ValueError("each security group needs a GroupId")
        if group["GroupId"] in groups:
            raise ValueError("duplicate GroupId in snapshot")
        groups[group["GroupId"]] = group
    attached = set(source_groups) | set(destination_groups)
    if not attached <= groups.keys():
        raise ValueError("snapshot does not contain every supplied attached group")
    vpcs = set()
    for group_id in attached:
        group = groups[group_id]
        if not isinstance(group.get("VpcId"), str) or not group["VpcId"]:
            raise ValueError("every attached group needs a VpcId")
        vpcs.add(group["VpcId"])
        for key in ("IpPermissions", "IpPermissionsEgress"):
            if key not in group:
                raise ValueError(f"complete snapshot required: {key} is missing")
            _items(group[key], key)
    if len(vpcs) != 1:
        raise ValueError("only attached groups in the same VPC are supported")
    egress = _direction(groups, source_groups, set(destination_groups), destination_ip,
                        "IpPermissionsEgress", port)
    ingress = _direction(groups, destination_groups, set(source_groups), source_ip,
                         "IpPermissions", port)
    states = (egress["state"], ingress["state"])
    overall = "no_match" if "no_match" in states else "indeterminate" if "indeterminate" in states else "match"
    return {
        "scope": "offline SG-rule comparison for a new direct same-VPC IPv4 TCP flow",
        "port": port,
        "source_egress": egress,
        "destination_ingress": ingress,
        "sg_rule_result": overall,
        "limitations": "Not an AWS API call, packet test, route/NACL/host-firewall check, or proof of reachability.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, help="local describe-security-groups JSON")
    parser.add_argument("--source-sg", action="append", required=True, help="repeat for every source group")
    parser.add_argument("--destination-sg", action="append", required=True, help="repeat for every destination group")
    parser.add_argument("--source-ip", required=True, help="observed direct source IPv4 address")
    parser.add_argument("--destination-ip", required=True, help="destination private IPv4 address")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
        report = inspect(snapshot, args.source_sg, args.destination_sg,
                         args.source_ip, args.destination_ip, args.port)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(f"Cannot inspect snapshot: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
