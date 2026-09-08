# BhuVistaar 3D — Backend

This directory houses the backend service for **BhuVistaar 3D** (SIH 26011: 3D ULPIN Generation and Vertical Property Mapping System).

## Python Environment

* **Required Python Version:** `Python 3.13.x`
* **Virtual Environment Path:** `backend/.venv`
* **Status:** Minimal FastAPI application initialized. No database models, PostgreSQL connections, authentication, or mock property data are active yet.

---

## PowerShell Activation & Deactivation Guide

### 1. Activating the Virtual Environment (Windows PowerShell)

#### Option A: From the repository root (`BhuVistar3D`)
```powershell
.\backend\.venv\Scripts\Activate.ps1
```

#### Option B: From within the `backend` directory
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

> **Note on Execution Policy:**  
> If PowerShell displays an execution policy restriction (`running scripts is disabled on this system`), enable script execution for the current process:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```
> Then run the activation command again.

---

### 2. Verifying the Active Environment

Once activated, your terminal prompt will display the `(.venv)` prefix. You can verify that Python 3.13 is active:

```powershell
# Check Python version
python --version
# Expected output: Python 3.13.x

# Check Python executable path
Get-Command python | Select-Object -ExpandProperty Source
# Expected path: ...\backend\.venv\Scripts\python.exe
```

---

### 3. Running the FastAPI Server

From the `backend` directory with the virtual environment activated:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Alternatively, from the repository root:

```powershell
.\backend\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

#### Available Endpoints:
* **Root status:** `GET http://127.0.0.1:8000/`
* **Health check:** `GET http://127.0.0.1:8000/health`
* **Interactive OpenAPI Docs:** `GET http://127.0.0.1:8000/docs`

---

### 4. Deactivating the Virtual Environment

To exit the virtual environment and return to your global Python environment, run:

```powershell
deactivate
```
