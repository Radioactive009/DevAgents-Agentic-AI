@echo off
title DevAgents AGI - Streamlit Interactive Frontend Launcher
color 0B
cls
echo ======================================================================
echo           DEVAGENTS AGI - STREAMLIT LIVE BUILDER LAUNCHER
echo ======================================================================
echo.
echo Starting Streamlit app on http://localhost:8501...
echo Opening in your browser automatically...
echo Press Ctrl+C in this terminal when you want to stop the server.
echo.
.venv\Scripts\streamlit run app_streamlit.py
pause
