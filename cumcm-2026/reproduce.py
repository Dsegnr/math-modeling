"""Run historical offline scripts in a new, isolated output directory."""
from pathlib import Path
import argparse
import datetime
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TASKS = {
    'q3-offline': ('q3_offline_eval.py', '设计期 17 点布局的离线模型示例'),
    'q1-q2': ('q1_q2_analysis.py', '问题一、二数值实验与绘图'),
    'q3-certificate': ('q3_certset.py', '问题三建证集求解与网格复核'),
    'q4-detection': ('q4_detect_cover.py', '问题四检出覆盖证书求解'),
    'q4-localization': ('q4_l2l3_audit.py', '问题四 L2/L3 可定位性审计'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=TASKS, help='Offline task; see README for each task scope')
    parser.add_argument('--runs', type=int, default=3, help='Random cases for q3-offline only (default: 3)')
    parser.add_argument('--output', type=Path, help='New directory for staged scripts and outputs')
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('--runs must be positive')
    output = (args.output or ROOT / 'runs' / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + args.task)).resolve()
    # Only newly created directories receive executable copies and generated results.
    # Do not permit nesting an output inside the preserved submission or source tree.
    if ROOT in output.parents and not output.is_relative_to(ROOT / 'runs'):
        parser.error('An output inside this project must be under runs/')
    if output.exists():
        parser.error('Output already exists; choose a new directory')
    originals = list((ROOT / 'support/code').rglob('*.py'))
    names = [p.name for p in originals]
    if len(set(names)) != len(names):
        parser.error('Historical scripts have ambiguous filenames')
    script = next(p for p in originals if p.name == TASKS[args.task][0])
    output.mkdir(parents=True)
    work = output / 'work'
    work.mkdir()
    for original in originals:
        shutil.copy2(original, work / original.name)
    shutil.copy2(ROOT / 'support/code/01_冻结执行版/waypoints_p4.json', work / 'waypoints_p4.json')
    command = [sys.executable, str(work / script.name)]
    if args.task == 'q3-offline':
        command.append(str(args.runs))
    print(TASKS[args.task][1], flush=True)
    print('Output:', output, flush=True)
    # Formal simulator scripts are deliberately outside the public offline task menu.
    with (output / 'stdout.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT,
                                encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    print((output / 'stdout.log').read_text(encoding='utf-8'), end='')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
