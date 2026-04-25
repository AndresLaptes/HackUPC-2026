# Pydantic models — mirror of the TypeScript domain types in front-app/src/domain/

from typing import List, Optional
from pydantic import BaseModel


class Warehouse(BaseModel):
    label: str
    polygon: List[List[float]]          # [[x, y], ...] in mm
    ceilingCtrlPoints: List[List[float]] # [[x, height], ...] in mm


class Bay(BaseModel):
    id: str
    x: float
    y: float
    width: float
    depth: float
    height: float
    gap: float
    nLoads: int
    price: float
    label: str
    rotation: float = 0.0


class Obstacle(BaseModel):
    id: str
    x: float
    y: float
    width: float
    depth: float
    height: Optional[float] = None
    label: str


class BayType(BaseModel):
    id: int
    width: float
    depth: float
    height: float
    gap: float
    nLoads: int
    price: float


class CaseData(BaseModel):
    warehouse: Warehouse
    bay_types: list[BayType]
    obstacles: list[Obstacle]
    bays: list[Bay] = []
