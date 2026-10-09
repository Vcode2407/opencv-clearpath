import argparse
import json
from pathlib import Path

import cv2

from .evaluate import evaluate
from .fixtures import FIXTURES, fixture_by_id, generate
from .vision import Calibration, decode_image, inspect, runtime_info


def main():
    parser = argparse.ArgumentParser(description="ClearPath calibrated floor inspection")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Open the local browser UI/API")
    serve.add_argument("--port", type=int, default=4181)
    commands.add_parser("fixtures", help="Regenerate owned deterministic fixtures")
    commands.add_parser("runtime", help="Print actual cv2 runtime evidence")
    assessment = commands.add_parser("evaluate", help="Compare predictions against fixture labels")
    assessment.add_argument("--output", type=Path, default=Path("reports/evaluation.json"))
    analysis = commands.add_parser("inspect", help="Inspect a fixture or your own registered image pair")
    analysis.add_argument("--fixture")
    analysis.add_argument("--scene", type=Path)
    analysis.add_argument("--reference", type=Path)
    analysis.add_argument("--calibration", type=Path)
    analysis.add_argument("--output", type=Path, default=Path("reports/inspection.json"))
    args = parser.parse_args()
    if args.command == "serve":
        from .web import app
        if app.config["MODE"] != "local":
            parser.error("Use the production container entrypoint for AWS mode.")
        app.run(host="127.0.0.1", port=args.port, debug=False)
    elif args.command == "fixtures":
        print(json.dumps({"generated": len(generate()["fixtures"]), "directory": str(FIXTURES)}, indent=2))
    elif args.command == "runtime":
        print(json.dumps(runtime_info(), indent=2))
    elif args.command == "evaluate":
        print(json.dumps(evaluate(args.output)["summary"], indent=2))
    elif args.command == "inspect":
        if args.fixture:
            fixture = fixture_by_id(args.fixture)
            scene = cv2.imread(str(FIXTURES / fixture["image"]))
            reference = cv2.imread(str(FIXTURES / fixture["reference"]))
            calibration = Calibration.from_dict(fixture["calibration"])
        else:
            if not all((args.scene, args.reference, args.calibration)):
                parser.error("Supply --fixture or all of --scene, --reference and --calibration.")
            scene = decode_image(args.scene.read_bytes())
            reference = decode_image(args.reference.read_bytes())
            calibration = Calibration.from_dict(json.loads(args.calibration.read_text(encoding="utf-8")))
        report, _ = inspect(scene, reference, calibration)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"status": report["status"], "measurements": report["measurements"],
                          "capture_requests": report["capture_requests"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
