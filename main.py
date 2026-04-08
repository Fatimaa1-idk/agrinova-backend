from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routes import router

# Créer toutes les tables automatiquement
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Agrinova API",
    description="API du marketplace agricole Agrinova 🌾",
    version="1.0.0"
)

# CORS — permet au frontend React d'appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrer toutes les routes avec le préfixe /api
app.include_router(router, prefix="/api")

@app.get("/")
def accueil():
    return {
        "message": "Bienvenue sur l'API Agrinova ! 🌾",
        "version": "1.0.0",
        "docs": "/docs"
    }