from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from ...database.models import ModelRegistry
from ...database.session import get_db
from ...models.registry import save_model



model_router = APIRouter(prefix="/models")


@model_router.post("/upload")
async def upload_model(name: str, framework: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, str]:

    result = save_model(file.file, file.filename or "model")

    model = ModelRegistry(
        id=result["id"],
        name=name,
        framework=framework,
        artifact_path=result["path"],
        checksum=result["checksum"],
        size=result["size"]
    )


    db.add(model)
    db.commit()
    db.refresh(model)


    return {
        "model_id": str(model.id),
        "status": "uploaded"
    }