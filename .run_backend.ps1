Set-Location "C:\Users\kosta\Documents\MARC\backend"
& "C:\Users\kosta\Documents\MARC\backend\.venv\Scripts\Activate.ps1"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
