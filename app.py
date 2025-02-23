from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tech0-gen8-step4-pos-app-88.azurewebsites.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

# Database connection setup
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="your_username",
        password="your_password",
        database="pos_db"
    )

# Pydantic models
class Product(BaseModel):
    code: str
    name: str
    price: float

class PurchaseItem(BaseModel):
    product_code: str
    quantity: int

class PurchaseRequest(BaseModel):
    cashier_id: str
    items: List[PurchaseItem]

# API endpoints
@app.get("/api/product/{code}")
def get_product(code: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM product_master WHERE code = %s", (code,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/api/purchase/")
def create_purchase(request: PurchaseRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Insert transaction
        cursor.execute(
            "INSERT INTO transactions (cashier_id, total_amount) VALUES (%s, %s)",
            (request.cashier_id, 0)
        )
        transaction_id = cursor.lastrowid

        # Insert transaction details
        total_amount = 0
        for item in request.items:
            cursor.execute(
                "SELECT * FROM product_master WHERE code = %s", (item.product_code,)
            )
            product = cursor.fetchone()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_code} not found")

            amount = product["price"] * item.quantity
            total_amount += amount

            cursor.execute(
                "INSERT INTO transaction_details (transaction_id, product_code, quantity, amount) "
                "VALUES (%s, %s, %s, %s)",
                (transaction_id, item.product_code, item.quantity, amount)
            )

        # Update total amount in transaction
        cursor.execute(
            "UPDATE transactions SET total_amount = %s WHERE id = %s",
            (total_amount, transaction_id)
        )

        conn.commit()
        return {"transaction_id": transaction_id, "total_amount": total_amount}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()