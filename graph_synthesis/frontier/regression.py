"""Run every repository graph-synthesis unittest and record actual outcomes."""
import hashlib
import json
import platform
import unittest
from .report import HERE, ROOT, write


def main():
    files=sorted((ROOT/'graph_synthesis').rglob('test*.py'))
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName('.'.join(p.relative_to(ROOT).with_suffix('').parts)) for p in files)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
             'skipped':len(result.skipped),'successful':result.wasSuccessful(),'python':platform.python_version(),
             'test_files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    write(HERE/'all-regressions.json',json.dumps(summary,indent=2,sort_keys=True)+'\n')
    raise SystemExit(not result.wasSuccessful())


if __name__=='__main__':main()
