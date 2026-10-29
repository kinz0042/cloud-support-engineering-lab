"""Inspect or explicitly replay one dead synthetic webhook delivery."""
import argparse
import json
from . import relay_store as store


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="read delivery and replay history")
    replay = commands.add_parser("replay", help="mutate one dead delivery after recipient review")
    for command in (inspect, replay):
        command.add_argument("delivery_id", type=positive)
        command.add_argument("--tenant", required=True)
    replay.add_argument("--expected-attempts", type=positive, required=True)
    replay.add_argument("--actor", required=True, help="operator-supplied label, not verified identity")
    replay.add_argument("--reason", required=True, help="synthetic incident reference and recovery rationale")
    replay.add_argument("--recipient-checked", action="store_true", required=True,
                        help="acknowledge recipient processing was reviewed")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = store.inspect_delivery(args.delivery_id, args.tenant)
            if result is None:
                print(json.dumps({"error": "delivery_not_found"}))
                return 2
        else:
            result = store.replay_delivery(args.delivery_id, args.tenant, args.expected_attempts,
                                           args.actor, args.reason, args.recipient_checked)
        print(json.dumps(result, indent=2))
        return 0
    except store.ReplayRejected:
        print(json.dumps({"error": "replay_rejected", "next_step": "inspect the delivery again"}))
        return 2
    except ValueError:
        print(json.dumps({"error": "invalid_input"}))
        return 2
    except Exception as exc:
        # Connection errors may include credentials. Never print the exception text.
        print(json.dumps({"error": "operation_failed", "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
