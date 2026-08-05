@echo off
REM ============================================================
REM DevFlow Fullstack - 一条命令接入你的项目 (Windows)
REM
REM 用法（在项目根目录执行）：
REM   方式 1（推荐，克隆后）：
REM     python setup.py install
REM
REM   方式 2（指定平台）：
REM     python setup.py install --platform claude,codex,opencode
REM
REM   方式 3（全局安装 claude 命令 / codex skill）：
REM     python setup.py install --global --platform codex,claude
REM
REM 支持的平台：claude / codex / opencode / cursor / windsurf / trae / copilot
REM ============================================================

echo.
echo [DevFlow] 一键安装器 (Windows)
echo ================================

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=python"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON=py -3"
    ) else (
        echo [错误] 未找到 Python，请先安装 Python 3.10+ (https://python.org)
        pause
        exit /b 1
    )
)

echo [DevFlow] 使用 %PYTHON%
%PYTHON% setup.py install %*

echo.
echo [DevFlow] 安装完成!
echo    运行自测: %PYTHON% scripts\selftest.py
pause
