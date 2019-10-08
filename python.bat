@echo off

if not exist ".env" (
    echo use `python.exe -m venv .env` to create new envrionment.
    goto:eof
)

if not exist ".env\Scripts\ipython.exe" (
    echo use `.env\Scripts\python.exe -m pip install -r .requirements.txt` to install envrionment.
    goto:eof
)

echo redirect "python" to "%CD%\.env\Scripts\ipython.exe"

.env\Scripts\ipython.exe %1 %2 %3 %4 %5 %6 %7 %8 %9
