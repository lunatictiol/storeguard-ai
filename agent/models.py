from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime

class ProductOutlier(BaseModel):
    id: int
    title: str
    category: str
    price: float
    category_avg: float
    deviation_pct: float

class ProductRating(BaseModel):
    id: int
    title: str
    category: str
    price: float
    rating: float
    review_count: int

class ProductDemand(BaseModel):
    id: int
    title: str
    category: str
    price: float
    demand_count: int

class AnomalyEvent(BaseModel):
    anomaly_type: str
    severity: str
    triggered_at: datetime
    affected_count: int
    outliers: Optional[List[ProductOutlier]] = None
    products: Optional[List[Union[ProductRating, ProductDemand]]] = None
