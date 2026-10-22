# Run SentiCare locally

SentiCare has a FastAPI backend (`backend/`) and a React + Vite frontend
(`frontend/`). Run every command below from the `SentiCare` directory unless
a step says otherwise.

## 1. Prerequisites

- Python 3.12
- Node.js and npm
- FFmpeg on your `PATH` (video/audio analysis). macOS: `brew install ffmpeg`
- Git

## 2. Get the code

```sh
git clone https://github.com/AMAN-JEET-SINGH/SKIT-CSE-2023-2024-12.git
cd SKIT-CSE-2023-2024-12/SentiCare
```

## 3. Get the `.env` file

The backend needs secrets (MongoDB, Groq, Deepgram, JWT) that are not stored
in the repository. **Ask Amanjeet for the `.env` file** and save it as:

```
SentiCare/backend/.env
```

`backend/.env.example` shows which variables it contains. Never commit `.env`.

## 4. Set up the backend (once)

```sh
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

`backend/requirements.txt` is the only requirements file; it also installs
the spaCy model `en_core_web_sm`. Keep the virtual environment at
`SentiCare/.venv`.

## 5. Set up the frontend (once)

```sh
npm --prefix frontend ci
```

## 6. Run the app

Use two terminals, both starting in `SentiCare`.

**Terminal 1 - backend**

```sh
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
cd backend
python -m uvicorn main:app --reload
```

The API runs on <http://localhost:8000> (docs at
<http://localhost:8000/docs>). The first start is slow while the ML models
load.

**Terminal 2 - frontend**

```sh
npm --prefix frontend run dev
```

Open the URL Vite prints (normally <http://localhost:5173>).

Stop either server with `Ctrl+C`; leave the virtual environment with
`deactivate`.

## Troubleshooting

- `command not found: uvicorn` - the virtual environment is not active. Run
  `source .venv/bin/activate`, or use `python -m uvicorn ...`.
- `ModuleNotFoundError` - re-run step 4 inside the active `.venv`.
- MongoDB does not connect - check `MONGODB_URI` in `backend/.env`, and ask
  Amanjeet to add your IP address to the MongoDB Atlas Network Access list.
