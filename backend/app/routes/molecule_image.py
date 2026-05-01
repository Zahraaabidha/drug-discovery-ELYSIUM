from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.chem.render import smiles_to_png
import io

router = APIRouter(
    prefix="/molecule",
    tags=["Molecules"]
)

@router.get("/image")
def get_molecule_image(
    smiles: str = Query(..., description="SMILES string")
):
    png_bytes = smiles_to_png(smiles)
    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png"
    )
