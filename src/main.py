from fastapi import FastAPI
from src.api import predict

app = FastAPI(title="ESP Failure Prediction System")

# Incluir las rutas de predicción
app.include_router(predict.router)

@app.get("/")
def home():
    return {"message": "ESP Failure Prediction API is running 🚀"}