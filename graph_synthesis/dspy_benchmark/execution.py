"""Execute the frozen study with a JSON-safe SDK audit boundary.

This serialization-only wrapper does not change prompts, metrics, candidate
selection, probability transforms, splits or inference requests. The original
study source remains byte-identical; wrapper and converter hashes are recorded.
"""
import argparse
from pathlib import Path
from . import study
from .audit import json_safe


def install_audit_boundary():
    if getattr(study, '_json_safe_audit_installed', False):
        return
    original_write, original_digest = study.write_json, study.digest
    study.write_json = lambda path, value: original_write(path, json_safe(value))
    study.digest = lambda value: original_digest(json_safe(value))
    study._json_safe_audit_installed = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=list(study.ARMS), required=True)
    parser.add_argument('--arm', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    install_audit_boundary()
    # Keep a sibling record so the study can enforce a new, empty output directory.
    study.write_json(args.output.parent / (args.output.name + '-execution-source.json'), {
        'study_sha256': study.sha(Path(study.__file__)),
        'wrapper_sha256': study.sha(Path(__file__)),
        'converter_sha256': study.sha(Path(__file__).with_name('audit.py')),
        'intervention': 'Lossless JSON conversion for DSPy trace metadata only',
    })
    study.run(args.task, args.arm, args.output)


if __name__ == '__main__':
    main()
