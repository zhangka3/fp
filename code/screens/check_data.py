"""
数据文件检查脚本
运行前先检查所有必需的数据文件是否存在
"""
from pathlib import Path
import sys
import io

# 设置标准输出为UTF-8（Windows兼容）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 定义必需的数据文件
REQUIRED_DATA_FILES = {
    'S类图表': [
        's_class_all.json',
        's_class_new.json',
        's_class_mtd.json'
    ],
    'M1图表': [
        'm1_assignment_repayment.json'
    ],
    'M0图表': [
        'm0_billing.json',
        'm0_billing_grouped.json'
    ],
    'GRP图表': [
        'grp_collector.json'
    ]
}

def check_data_files():
    """检查数据文件是否存在"""
    data_dir = Path(__file__).parent.parent.parent / 'data'

    print("=" * 60)
    print("数据文件检查")
    print("=" * 60)
    print(f"\n数据目录: {data_dir}")
    print()

    all_ok = True
    missing_files = []

    for category, files in REQUIRED_DATA_FILES.items():
        print(f"[{category}]")
        for filename in files:
            filepath = data_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                size_mb = size / (1024 * 1024)
                print(f"  ✓ {filename} ({size_mb:.2f} MB)")
            else:
                print(f"  ✗ {filename} - 文件不存在")
                all_ok = False
                missing_files.append((category, filename))
        print()

    # 总结
    print("=" * 60)
    if all_ok:
        print("✓ 所有数据文件准备就绪！")
        print("\n可以运行图表生成脚本:")
        print("  python screen_s_class.py")
        print("  python screen_m1.py")
        print("  python screen_m0.py")
        print("  python screen_grp.py")
        print("\n或使用批处理脚本:")
        print("  run_all.bat  (Windows)")
        print("  ./run_all.sh (Linux/Mac)")
        return_code = 0
    else:
        print(f"✗ 缺少 {len(missing_files)} 个数据文件")
        print("\n缺少的文件:")
        for category, filename in missing_files:
            print(f"  - {filename} ({category})")
        print("\n请先运行数据提取脚本生成这些文件")
        return_code = 1

    print("=" * 60)
    return return_code

def check_output_dir():
    """检查输出目录"""
    output_dir = Path(__file__).parent.parent.parent / 'screenshots'

    if not output_dir.exists():
        print(f"\n输出目录不存在，正在创建: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
        print("✓ 输出目录创建成功")
    else:
        # 统计现有图表数量
        png_files = list(output_dir.glob('*.png'))
        print(f"\n输出目录: {output_dir}")
        print(f"现有图表: {len(png_files)} 张")

def check_dependencies():
    """检查Python依赖库"""
    print("\n检查Python依赖库:")

    required_packages = [
        ('matplotlib', 'matplotlib'),
        ('numpy', 'numpy'),
        ('pandas', 'pandas')
    ]

    all_ok = True

    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"  ✓ {package_name}")
        except ImportError:
            print(f"  ✗ {package_name} - 未安装")
            all_ok = False

    if not all_ok:
        print("\n请安装缺少的依赖:")
        print("  pip install matplotlib numpy pandas")

if __name__ == '__main__':
    # 检查依赖
    check_dependencies()

    # 检查输出目录
    check_output_dir()

    # 检查数据文件
    print()
    return_code = check_data_files()

    sys.exit(return_code)
