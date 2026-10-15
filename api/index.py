# Ponto de entrada da Vercel (o app fica em app/main.py, caminho que ela não detecta).
from app.main import app

__all__ = ["app"]
