# TMS

Panel TMS dla firm, dokumentów, terminów oraz skrzynki e-mail.

## Uruchomienie

1. W `backend` utwórz `.env` na podstawie `.env.example` i ustaw `DATABASE_URL` oraz `APP_SECRET`.
2. Uruchom API: `python -m uvicorn app.main:app --reload --port 8000`.
3. W osobnym terminalu uruchom panel: `cd frontend; npm install; npm run dev`.

Panel działa na `http://127.0.0.1:5173`, a API na `http://127.0.0.1:8000`.