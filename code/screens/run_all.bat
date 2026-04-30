@echo off
echo ============================================================
echo 周报图表批量生成脚本
echo ============================================================
echo.

cd /d %~dp0

echo [1/4] 生成S类回款率图表...
python screen_s_class.py
if errorlevel 1 (
    echo 错误: S类图表生成失败
    pause
    exit /b 1
)
echo.

echo [2/4] 生成M1分案回款图表...
python screen_m1.py
if errorlevel 1 (
    echo 错误: M1图表生成失败
    pause
    exit /b 1
)
echo.

echo [3/4] 生成M0逾期图表...
python screen_m0.py
if errorlevel 1 (
    echo 错误: M0图表生成失败
    pause
    exit /b 1
)
echo.

echo [4/4] 生成GRP催收员图表...
python screen_grp.py
if errorlevel 1 (
    echo 错误: GRP图表生成失败
    pause
    exit /b 1
)
echo.

echo ============================================================
echo 所有图表生成完成！
echo 图表保存位置: ../../screenshots/
echo ============================================================
pause
