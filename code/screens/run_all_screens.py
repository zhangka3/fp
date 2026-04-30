r"""
步骤 5：批量运行所有图表生成脚本（动态发现，支持新增 screen_*.py）

设计目标：
- glob `screens/screen_*.py`，自动发现所有图表脚本
- 每个脚本用 subprocess 独立进程跑，互不影响（一个挂了不影响其他）
- 支持过滤：`python run_all_screens.py screen_grp` 只跑指定脚本
- 输出统一到 `screenshots/` 目录（由各脚本自己控制）

新增图表流程：
1. 在项目根的 `code/screens/` 写 `screen_xxx.py`
2. 脚本里把 PNG 写到项目根的 `screenshots/`（推荐：`Path(__file__).resolve().parent.parent.parent / "screenshots"`）
3. 重新跑 `run_all_screens.py`，新脚本自动被发现
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import io
import time
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).parent
SCREENSHOTS_DIR = SCRIPT_DIR.parent.parent / 'screenshots'


def discover_screen_scripts(filter_stem: str | None = None) -> list[Path]:
    files = sorted(SCRIPT_DIR.glob('screen_*.py'))
    if filter_stem:
        files = [f for f in files if f.stem == filter_stem or f.stem.endswith(filter_stem)]
        if not files:
            raise SystemExit(f"未找到匹配的脚本: {filter_stem}")
    return files


def run_one(script: Path) -> dict:
    """跑一个 screen_*.py，返回 {name, ok, elapsed, png_count, err}"""
    info = {'name': script.stem, 'ok': False, 'elapsed': 0.0,
            'png_before': 0, 'png_after': 0, 'err': ''}

    pngs_before = {f.name for f in SCREENSHOTS_DIR.glob('*.png')}
    info['png_before'] = len(pngs_before)

    t0 = time.time()
    try:
        # cwd 设为脚本所在目录，避免相对路径出问题
        proc = subprocess.run(
            [sys.executable, script.name],
            cwd=str(SCRIPT_DIR),
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=300,
        )
        info['ok'] = (proc.returncode == 0)
        if not info['ok']:
            info['err'] = (proc.stderr or proc.stdout)[-500:]
    except subprocess.TimeoutExpired:
        info['err'] = 'TIMEOUT (>300s)'
    except Exception as e:
        info['err'] = repr(e)

    info['elapsed'] = round(time.time() - t0, 1)

    pngs_after = {f.name for f in SCREENSHOTS_DIR.glob('*.png')}
    info['png_after'] = len(pngs_after)
    info['new_pngs'] = sorted(pngs_after - pngs_before)
    return info


def main():
    parser = argparse.ArgumentParser(description='批量运行所有 screen_*.py')
    parser.add_argument('filter', nargs='?', default=None,
                        help='只跑指定脚本（如 screen_grp 或 grp）')
    parser.add_argument('--list', action='store_true', help='只列出待执行脚本')
    args = parser.parse_args()

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    scripts = discover_screen_scripts(args.filter)
    print('=' * 64)
    print(f'步骤 5：批量生成图表 ({len(scripts)} 个脚本)')
    print('=' * 64)
    for s in scripts:
        print(f'  - {s.name}')
    if args.list:
        return 0

    print('\n输出目录:', SCREENSHOTS_DIR)
    print('开始执行...\n')

    t_start = time.time()
    results = []
    for script in scripts:
        print(f'[RUN] {script.name} ...', end='', flush=True)
        info = run_one(script)
        results.append(info)
        if info['ok']:
            new_n = len(info['new_pngs'])
            print(f' [OK] {info["elapsed"]}s '
                  f'(新增 {new_n} 张, 总 {info["png_after"]} 张)')
        else:
            print(f' [FAIL] {info["elapsed"]}s')
            print(f'        错误: {info["err"]}')

    total = time.time() - t_start
    final_pngs = sorted(SCREENSHOTS_DIR.glob('*.png'))
    fails = [r for r in results if not r['ok']]

    print('\n' + '=' * 64)
    print(f'完成：{len(results) - len(fails)}/{len(results)} 个脚本成功，'
          f'总耗时 {total:.1f}s，最终 {len(final_pngs)} 张 PNG')
    print('=' * 64)
    if fails:
        print('失败脚本:')
        for r in fails:
            print(f'  ✗ {r["name"]}: {r["err"][:200]}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
