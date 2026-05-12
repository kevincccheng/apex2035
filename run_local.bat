@echo off
echo Starting Apex 2035 Portfolio Dashboard...
echo.
echo Open Refinitiv Workspace first if you want LSEG data.
echo The app will open in your browser automatically.
echo.
python -m streamlit run app.py --browser.gatherUsageStats false
pause
