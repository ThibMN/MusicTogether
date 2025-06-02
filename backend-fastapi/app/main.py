from fastapi import FastAPI
from app.api.routes import router

app = FastAPI()

# Inclure les routes
app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API MusicTogether"}