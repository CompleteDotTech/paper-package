"""Copy a complete, hash-verified CI evidence package and derive the results entry point.

No network calls, model calls, secret access, original-manuscript writes or changes
of research outcome definitions occur here. CI performs the authorized Git push.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

RELATIVE = Path('experiments/dspy-calibration-20260918/results')
PRIMARY_RUN = 35342763186
COMPLETION_RUN = 35345560822
BASE_COMMIT = 'f197f9f24076bf85b7739916669dae9fdb428adf'
ARMS = {'relation_support': ['baseline_choice','evidence_contract','conditional_nouls','fewshot_contract'],
        'entity_resolution': ['baseline_noul','identity_contract','identity_noul','fewshot_contract']}
WORKFLOWS = ['single','repeat_vote','blind_vote','targeted','structured','contrastive','selective']
SEEDS = [17,29,43,71,101]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def verify_package(root):
    manifest=read(root/'package-manifest.json')['sha256']
    if not manifest:raise ValueError('Empty evidence package')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'package-manifest.json'}
    if actual!=set(manifest):raise ValueError('Package inventory mismatch')
    for name,want in manifest.items():
        path=root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or sha(path)!=want:
            raise ValueError('Evidence hash/path mismatch: '+name)
        if path.suffix.lower() in ('.ttf','.otf','.woff','.woff2','.gguf','.safetensors','.pem','.key'):
            raise ValueError('Disallowed model/font/credential artifact: '+name)
    for part in ('primary','multicall','repeatability','quality'):
        if not (root/part/'REPORT.md').exists():raise ValueError('Missing report: '+part)
    expected={(task,arm) for task,arms in ARMS.items() for arm in arms}
    captures=sorted((root/'captures'/'primary').iterdir())
    if len(captures)!=8:raise ValueError('Require all eight formulations')
    found=set()
    for path in captures:
        protocol=read(path/'protocol.json');execution=read(path/'execution.json')
        if execution['status']!='completed' or execution['live'] is not True or protocol.get('revision')!=2:
            raise ValueError('Not a completed actual v2 capture')
        if protocol['seeds']!=SEEDS:raise ValueError('Missing seed grid')
        found.add((protocol['task'],protocol['arm']))
    if found!=expected:raise ValueError('Wrong formulation coverage')
    if {read(p/'protocol.json')['shard'] for p in (root/'captures'/'transfer').iterdir()}!=set(range(8)):
        raise ValueError('Missing transfer shards')
    if {read(p/'protocol.json')['task'] for p in (root/'captures'/'diagnostics').iterdir()}!=set(ARMS):
        raise ValueError('Missing service diagnostics')
    primary=read(root/'primary'/'all-results.json')
    if len(primary)!=792:raise ValueError('Expected 792 complete primary metric configurations')
    if len(read(root/'multicall'/'all-results.json'))!=378:raise ValueError('Missing workflow forecast comparisons')
    if len(read(root/'multicall'/'policy-results.json'))!=126:raise ValueError('Missing workflow policy comparisons')
    if len(read(root/'repeatability'/'repeat-metrics.json'))!=432:raise ValueError('Missing fresh service repetitions')
    if len(read(root/'primary'/'graph-replay.json'))!=528:raise ValueError('Missing graph-compiler replays')
    return manifest


def summarize(root):
    primary=read(root/'primary'/'seed-summary.json')
    workflow=read(root/'multicall'/'seed-summary.json')
    def pget(task,arm,selection,cal):
        return next(r for r in primary if r['task']==task and r['arm']==arm and r['panel']=='evaluation'
                    and r['selection']==selection and r['calibration']==cal)
    def wget(arm,selection,cal):
        return next(r for r in workflow if r['workflow']==arm and r['panel']=='full_transfer'
                    and r['selection']==selection and r['calibration']==cal)
    table=[];calibration=[];primary_rows=[]
    for task,arms in ARMS.items():
        for arm in arms:
            baseline=pget(task,arm,'baseline','raw');dspy=pget(task,arm,'accuracy','raw')
            t=pget(task,arm,'accuracy','temperature');b=pget(task,arm,'accuracy','temperature_bias')
            primary_rows.append({'task':task,'arm':arm,'baseline':baseline,'dspy':dspy,'dspy_temperature':t,'dspy_temperature_bias':b})
            table.append(f"| {task} / {arm} | {100*baseline['accuracy']['mean']:.2f}% | {100*dspy['accuracy']['mean']:.2f}% ± {100*dspy['accuracy']['std']:.2f} pp | {100*(dspy['accuracy']['mean']-baseline['accuracy']['mean']):+.2f} pp | {baseline['macro_f1']['mean']:.4f} | {dspy['macro_f1']['mean']:.4f} |")
            calibration.append(f"| {task} / {arm} | {dspy['log_loss']['mean']:.4f} → {t['log_loss']['mean']:.4f} → {b['log_loss']['mean']:.4f} | {dspy['brier']['mean']:.4f} → {t['brier']['mean']:.4f} → {b['brier']['mean']:.4f} | {100*b['accuracy']['mean']:.2f}% |")
    wtable=[];workflow_rows=[]
    for arm in WORKFLOWS:
        baseline=wget(arm,'baseline','raw');dspy=wget(arm,'dspy','raw');t=wget(arm,'dspy','temperature');b=wget(arm,'dspy','temperature_bias')
        workflow_rows.append({'workflow':arm,'baseline':baseline,'dspy':dspy,'dspy_temperature':t,'dspy_temperature_bias':b})
        wtable.append(f"| {arm} | {100*baseline['policy_accuracy']['mean']:.2f}% | {100*dspy['policy_accuracy']['mean']:.2f}% ± {100*dspy['policy_accuracy']['std']:.2f} pp | {100*dspy['policy_coverage']['mean']:.2f}% | {dspy['forecast_log_loss']['mean']:.4f} → {t['forecast_log_loss']['mean']:.4f} → {b['forecast_log_loss']['mean']:.4f} |")
    counters={}
    for method,name in [('dspy_temperature','temperature'),('dspy_temperature_bias','temperature_bias')]:
        counters[name]={metric:sum(row[method][metric]['mean'] < row['dspy'][metric]['mean'] for row in primary_rows)
                        for metric in ('log_loss','brier','ece')}
    executions={name:read(root/path/'execution.json') for name,path in [('primary','primary'),('transfer','multicall'),('diagnostics','repeatability')]}
    costs={key:{'http_attempts':sum(r['http_attempts'] for r in rows),
                'reported_input_tokens':sum(r['reported_input_tokens'] for r in rows)} for key,rows in executions.items()}
    pilots=read(root/'pilot-summary.json')
    costs['prior_pilots']={'http_attempts':sum(r['http_attempts'] for r in pilots),
                           'reported_input_tokens':sum(r['reported_input_tokens'] for r in pilots)}
    for row in costs.values():row['estimated_jev_usd']=row['reported_input_tokens']*.042/1_000_000
    statuses=Counter()
    for row in read(root/'primary'/'search-summary.json'):statuses.update(row['statuses'])
    summary={'scope':{'formulations':8,'independent_searches':40,'candidate_rounds_per_search':3,
        'primary_metric_configurations':792,'multicall_forecast_configurations':378,
        'multicall_policy_configurations':126,'graph_replays':528,'repeatability_metric_configurations':432},
        'primary':primary_rows,'workflows':workflow_rows,'calibration_improved_family_counts':counters,
        'search_status_counts':dict(statuses),'costs':costs,
        'warning':'Exploratory public-data comparisons with a small local proposer, not proof of global prompt optimum or broad superiority.'}
    costs_table=[f"| {name} | {r['http_attempts']:,} | {r['reported_input_tokens']:,} | ${r['estimated_jev_usd']:.4f} |" for name,r in costs.items()]
    text=['# Jev with and without DSPy: repeated searches and calibration','',
        '**Actual live Jev inference and actual DSPy-generated prompt proposals.** The named Jev credential stayed in GitHub Actions. The proposal model was a locally executed, checksum-verified Qwen2.5-1.5B-Instruct Q4_K_M through DSPy 3.3.1 and llama.cpp b10964.',
        '', '## Coverage','',
        'Eight original formulations × five independent searches × three candidate rounds. All original source splits and demonstrations were retained; 31 TRAIN and 29 VALIDATION examples per task controlled search. Calibration used separate 150-row relation and 390-row entity panels. All five searches froze before calibration or test inference.',
        '', 'The primary capture includes the full 339-row relation and 413-row entity evaluations, 50 relation fixtures, all 100 entity fixtures, the 336-row relation transfer corpus and 48-row challenge. Binary fixture metrics use 88 eligible entity fixtures; 12 original uncertain fixtures are reported separately, without inventing binary labels.',
        '', 'All seven original multi-call workflows were rerun with baseline and all five frozen few-shot accuracy-selected prompts. Fresh service repeatability and original cross-formulation batching/isolated comparisons cover both tasks. The existing graph compiler was replayed 528 times on the new captured probabilities at fixed thresholds 0 and 0.9.',
        '', '## Main held-out classification results','',
        'DSPy entries are mean ± sample standard deviation over **five searches**, not a cherry-picked seed. Percentage-point (pp) differences are absolute. The same test examples were reused across searches and are not counted as additional independent samples.',
        '', '| Task / original formulation | Baseline accuracy | DSPy accuracy mean ± SD | Difference | Baseline macro-F1 | DSPy macro-F1 |',
        '|---|---:|---:|---:|---:|---:|',*table,
        '', '## Does calibration improve it?','',
        'The sequences below are **raw → temperature → temperature plus class bias**, for the accuracy-selected DSPy prompts. Lower NLL and Brier are better. Improvements in NLL may coexist with worse Brier, ECE or accuracy; no single calibration metric establishes universal improvement. Baseline calibration results and NLL-selected-pool ablations are retained in the complete reports, not omitted.',
        '', '| Task / formulation | Mean NLL: raw → T → T+bias | Mean Brier: raw → T → T+bias | Accuracy after T+bias |',
        '|---|---:|---:|---:|',*calibration,
        '', f"Across these eight formulation comparisons, temperature lowered mean DSPy NLL in {counters['temperature']['log_loss']}/8, Brier in {counters['temperature']['brier']}/8, and ECE in {counters['temperature']['ece']}/8. Temperature plus bias lowered these metrics in {counters['temperature_bias']['log_loss']}/8, {counters['temperature_bias']['brier']}/8 and {counters['temperature_bias']['ece']}/8 respectively. These correlated comparisons are descriptive counts, not eight independent replications.",
        '', '**Scalar temperature preserves the winning label.** It cannot improve argmax classification accuracy here. Bias calibration can change labels and can harm accuracy. All calibrator fits use only the designated calibration split, with fixed bounds and regularization.',
        '', '## Seven multi-call workflows','',
        'This is transfer of the five already-frozen primary-verifier prompts, not independent DSPy optimization of every reviewer or workflow component. Original reviewer/adjudicator prompts, policies, threshold, demonstrations and abstention rules stay fixed.',
        '', '| Workflow | Baseline policy accuracy | DSPy policy accuracy mean ± SD | DSPy coverage | Forecast NLL: raw → T → T+bias |',
        '|---|---:|---:|---:|---:|',*wtable,
        '', 'These post-hoc workflow calibrations change **forecasts only**. They do not alter votes, abstentions, escalation, adjudication input or policy-label accuracy. Vote-mixture forecast argmax is a distinct metric. Unconditional policy accuracy counts abstentions as errors; coverage and conditional accuracy are reported separately.',
        '', '## Repeatability, packing and measurement quality','',
        '[Repeatability report](repeatability/REPORT.md) separates between-search dispersion from within-search service dispersion using three fresh passes on each original 20-row evaluation repeatability panel. Matched batching versus isolated requests use the original 20-row development batching panel solely for packing/cost diagnostics, not a new holdout accuracy claim.',
        '', '[Data-quality report](quality/REPORT.md) lists unchanged selected prompts, differences between identical prompts in the same request, and returned probability-mass defects. A difference for an unchanged prompt is not evidence of successful prompt optimization. A fixed, bounded rounding interpretation proportionally normalizes only eligible near-unit-mass vectors; raw values and all flags are retained. This input normalization is distinct from learned statistical calibration.',
        '', '## Actual execution and cost accounting','',
        '| Stage | HTTP attempts | Reported input tokens | Estimated Jev cost |',
        '|---|---:|---:|---:|',*costs_table,
        '', 'Estimates use $0.042 per million reported Jev input tokens, not an invoice. Missing usage on failed calls, local proposal CPU work, GitHub Actions runtime and other infrastructure costs are not included. Prior pilots are reported separately and are not pooled as successful v2 searches. Reporting completion reused existing raw calls and made zero new inference calls.',
        '', '## Complete results and reproduction','',
        '[Primary report](primary/REPORT.md) · [Every primary metric row, CSV](primary/all-results.csv) · [Primary JSON with confusion matrices](primary/all-results.json) · [Paired source-cluster intervals](primary/paired-intervals.json) · [Graph compiler outcomes](primary/graph-replay.json) · [Multi-call report](multicall/REPORT.md) · [Every workflow forecast row, CSV](multicall/all-results.csv) · [Workflow policy results](multicall/policy-results.json) · [Repeatability CSV](repeatability/repeat-metrics.csv).',
        '', 'The package contains raw compressed call journals, all proposal traces, rejected and duplicate candidates, frozen configurations, fitted calibrators, per-seed comparisons, prediction changes, calibration deltas, source/environment fingerprints, failed pilots and original workflow statuses. Manifests bind all published artifacts. The original frozen 161-file research inventory and original optimizer manifest are unchanged.',
        '', '## Interpretation limits','',
        'These public, previously evaluated datasets provide **retrospective exploratory evidence**, not a new untouched external benchmark. The local 1.5B proposal model, three-round budget and small validation panel limit conclusions about stronger models or longer searches. The NLL-selected arm is selected from the same accuracy-guided candidate pool, not a separate NLL-directed optimizer. No GEPA/MIPROv2 invocation or weight training is claimed.',
        '', 'Paired bootstrap intervals resample connected source/entity components and preserve baseline/candidate pairing. They are pointwise exploratory intervals conditional on frozen prompts and fitted calibrators; they do not incorporate calibration-fit uncertainty or multiple-testing correction. Shared reviewer controls and batched final predictions are not independent service replicates. Timing phases are not randomized across server load.',
        '', 'The 17 legacy graph research workflows were rerun as regression/replay checks. They are not 17 new independently DSPy-trained semantic systems. Archived specialist-model retraining, open-corpus retrieval evaluation and exhaustive search of every possible prompt are outside this comparison.',
        '', '## Source and execution provenance','',
        f'- Primary live capture: https://github.com/CompleteDotTech/paper-package/actions/runs/{PRIMARY_RUN}',
        f'- Completion, transfer, repeatability and independent audit: https://github.com/CompleteDotTech/paper-package/actions/runs/{COMPLETION_RUN}',
        f'- Audited analysis source commit: `{BASE_COMMIT}`.',
        '- TypeSafe API and model documentation: https://docs.typesafe.ai/api ; https://docs.typesafe.ai/models',
        '- Calibration reference: Guo et al. (2017), https://proceedings.mlr.press/v70/guo17a.html',
        '- Official proposal model: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF','']
    return summary,'\n'.join(text)


def publish(source,repo):
    manifest=verify_package(source)
    destination=repo/RELATIVE
    if destination.exists():raise ValueError('Do not overwrite a published experiment')
    destination.mkdir(parents=True)
    excluded={'repository-source.tar','package-manifest.json'}
    for path in source.rglob('*'):
        if path.is_file() and path.relative_to(source).as_posix() not in excluded:
            target=destination/path.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    write(destination/'original-ci-package-manifest.json',{'sha256':manifest})
    summary,text=summarize(destination)
    write(destination/'summary.json',summary)
    (destination/'SUMMARY.md').write_text(text,encoding='utf-8')
    write(destination/'publication.json',{'primary_run':PRIMARY_RUN,'completion_run':COMPLETION_RUN,
        'audited_source_commit':BASE_COMMIT,'publisher_source_sha256':sha(__file__),
        'original_ci_manifest_sha256':sha(source/'package-manifest.json'),
        'excluded_from_git':{'repository-source.tar':manifest.get('repository-source.tar')},
        'note':'The complete repository source tar is retained in CI evidence, not duplicated in Git. No model calls occur during publication.'})
    entry='# DSPy benchmark comparison results\n\n[Full comparison and conclusions]('+RELATIVE.as_posix()+'/SUMMARY.md)\n\n'
    entry+='Forty actual DSPy searches across eight Jev formulations, separate calibration ablations, all seven multi-call workflows, fresh repeatability and batching diagnostics, and independent raw-response audits.\n\n'
    entry+='Read the full report for positive, negative and null results, exact coverage, costs and limitations. This is exploratory evidence on public datasets, not a claim of universal accuracy improvement.\n'
    path=repo/'DSPY_BENCHMARK_RESULTS.md'
    if path.exists():raise ValueError('Do not overwrite an existing entry point')
    path.write_text(entry,encoding='utf-8')
    write(destination/'publication-manifest.json',{'sha256':{p.relative_to(destination).as_posix():sha(p) for p in sorted(destination.rglob('*')) if p.is_file() and p.name!='publication-manifest.json'}})
    print(json.dumps({'published_path':str(destination),'summary':summary['scope'],'costs':summary['costs']},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--repo',type=Path,default=Path('.'));args=parser.parse_args();publish(args.input,args.repo.resolve())

if __name__=='__main__':main()
