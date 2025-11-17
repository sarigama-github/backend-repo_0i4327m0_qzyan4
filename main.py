import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

app = FastAPI(title="Shomee Spices API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


@app.get("/")
def read_root():
    return {"message": "Shomee Spices Backend Running"}


@app.get("/schema")
def get_schema():
    # Expose schemas for the database viewer
    from schemas import User, Product, Lead
    return {
        "user": User.model_json_schema(),
        "product": Product.model_json_schema(),
        "lead": Lead.model_json_schema(),
    }


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Business endpoints
class ProductIn(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
    image_url: Optional[str] = None
    buy_url: Optional[str] = None
    featured: bool = False
    tags: Optional[List[str]] = None


@app.get("/products", response_model=List[dict])
def list_products(category: Optional[str] = None, featured: Optional[bool] = None, limit: int = 50):
    from database import get_documents
    filter_dict = {}
    if category:
        filter_dict["category"] = category
    if featured is not None:
        filter_dict["featured"] = featured
    docs = get_documents("product", filter_dict=filter_dict, limit=limit)
    # Convert ObjectId to string
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return docs


@app.post("/products", status_code=201)
def create_product(payload: ProductIn):
    from database import create_document
    from schemas import Product as ProductSchema

    # Validate with schema
    _ = ProductSchema(**payload.model_dump())
    inserted_id = create_document("product", payload.model_dump())
    return {"id": inserted_id}


class LeadIn(BaseModel):
    name: str
    email: str
    message: Optional[str] = None
    source: Optional[str] = "website"


@app.post("/lead", status_code=201)
def create_lead(payload: LeadIn):
    from database import create_document
    from schemas import Lead as LeadSchema

    _ = LeadSchema(**payload.model_dump())
    inserted_id = create_document("lead", payload.model_dump())
    return {"id": inserted_id, "message": "Thanks for reaching out!"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
