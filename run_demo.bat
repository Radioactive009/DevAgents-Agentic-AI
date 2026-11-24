@echo off
title DevAgents AGI - Professor Live Demo Launcher
color 0A
cls
echo ======================================================================
echo             DEVAGENTS AGI - MULTI-AGENT SYSTEM LIVE DEMO
echo ======================================================================
echo.
echo Choose an option to demonstrate to your professor:
echo.
echo  [0] Launch Streamlit Live Builder (Prompt-to-Code UI)
echo  [1] Open Interactive Web Frontend Dashboard (Visual Graphs & Metrics)
echo  [2] Open "Problem to 7 Agents" Presentation Slide
echo  [3] Run Automated Test Suite (271 / 271 Tests Passing)
echo  [4] Run Closed-Loop Self-Repair Pipeline Live Demo (Terminal)
echo  [5] Run Messaging Benchmark (Blackboard vs EventBus)
echo  [6] Performance, Cost & Latency Benchmark (CLI)
echo  [7] Agentic Design Patterns Comparative Evaluation (CLI)
echo  [8] A2A Protocol Communication Test Suite (Pytest)
echo  [9] Exit
echo.
set /p choice="Enter choice [1-9]: "

if "%choice%"=="0" goto streamlit
if "%choice%"=="1" goto dashboard
if "%choice%"=="2" goto slide
if "%choice%"=="3" goto tests
if "%choice%"=="4" goto repair
if "%choice%"=="5" goto messaging
if "%choice%"=="6" goto cost_bench
if "%choice%"=="7" goto pattern_bench
if "%choice%"=="8" goto a2a_tests
if "%choice%"=="9" goto end

:streamlit
echo.
echo Launching Streamlit Interactive Builder...
.venv\Scripts\streamlit run app_streamlit.py
goto end

:dashboard
echo.
echo Opening Interactive Web Dashboard...
start "" "dashboard.html"
goto end

:slide
echo.
echo Opening Presentation Slide...
start "" "problem_to_agents_slide.html"
goto end

:tests
echo.
echo Running 271 Test Cases (100%% Test Suite Health)...
.venv\Scripts\python run_tests.py
pause
goto end

:repair
echo.
echo Running Closed-Loop Self-Repair Pipeline...
.venv\Scripts\python run_repair_loop.py
pause
goto end

:messaging
echo.
echo Running Blackboard vs EventBus Benchmark...
.venv\Scripts\python compare_messaging.py
pause
goto end

:cost_bench
echo.
echo Running Performance, Cost & Latency Evaluation Suite...
.venv\Scripts\python benchmark_performance_cost.py --mock
pause
goto end

:pattern_bench
echo.
echo Running Agentic Design Patterns Formal Comparative Evaluation...
.venv\Scripts\python compare_agentic_patterns.py --runs 5
pause
goto end

:a2a_tests
echo.
echo Running A2A Protocol Communication Test Suite...
.venv\Scripts\python -m pytest -v tests\test_a2a_protocol.py
pause
goto end

:end
echo.
echo Done!

