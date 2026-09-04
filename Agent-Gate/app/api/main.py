from fastapi import FastAPI

from app.api.routes import evaluations, health, human_reviews

app = FastAPI(title="AgentGate", description="CI/CD security and evaluation gate for AI agents")

app.include_router(evaluations.router)
app.include_router(human_reviews.router)
app.include_router(health.router)
