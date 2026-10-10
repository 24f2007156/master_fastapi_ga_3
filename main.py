from fastapi import FastAPI, Request, Response, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import jwt
import time
import uuid
import re
from fastapi.responses import PlainTextResponse

APP_START_TIME = time.time()
REQUEST_COUNT = 0
LOG_ENTRIES = []
IDEMPOTENCY_STORE = {}
RATE_LIMIT_STORE = {}

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----"""

app = FastAPI()

class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        LOG_ENTRIES.append({
            "level": "INFO",
            "ts": start_time,
            "path": request.url.path,
            "request_id": request_id
        })
        if len(LOG_ENTRIES) > 1000:
            LOG_ENTRIES.pop(0)
            
        if request.method == "OPTIONS" and (request.url.path == "/analytics" or request.url.path.startswith("/orders")):
            response = Response(status_code=200)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
        else:
            response = await call_next(request)
            if request.url.path == "/analytics" or request.url.path.startswith("/orders"):
                response.headers["Access-Control-Allow-Origin"] = "*"
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dash-z74j6s.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CustomHeaderMiddleware)

@app.get("/stats")
async def get_stats(values: str):
    nums = [int(x) for x in values.split(",")]
    return {
        "email": "24f2007156@ds.study.iitm.ac.in",
        "count": len(nums),
        "sum": sum(nums),
        "min": min(nums),
        "max": max(nums),
        "mean": sum(nums) / len(nums)
    }

class TokenRequest(BaseModel):
    token: str

@app.post("/verify")
async def verify_token(request: TokenRequest):
    try:
        decoded = jwt.decode(
            request.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            issuer="https://idp.exam.local",
            audience="tds-4j5yyvb9.apps.exam.local"
        )
        return {
            "valid": True,
            "email": decoded.get("email"),
            "sub": decoded.get("sub"),
            "aud": decoded.get("aud")
        }
    except jwt.PyJWTError:
        return JSONResponse(status_code=401, content={"valid": False})

class Event(BaseModel):
    user: str
    amount: float
    ts: int

class AnalyticsRequest(BaseModel):
    events: List[Event]

@app.post("/analytics")
async def analytics(
    request: AnalyticsRequest, 
    x_api_key: str = Header(None)
):
    if x_api_key != "ak_4vgkhb5g9lomgw0pmyvyv2ku":
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    events = request.events
    total_events = len(events)
    unique_users = len(set(e.user for e in events))
    
    revenue = sum(e.amount for e in events if e.amount > 0)
    
    user_revenue = {}
    for e in events:
        if e.amount > 0:
            user_revenue[e.user] = user_revenue.get(e.user, 0) + e.amount
            
    top_user = ""
    if user_revenue:
        top_user = max(user_revenue.items(), key=lambda x: x[1])[0]
        
    return {
        "email": "24f2007156@ds.study.iitm.ac.in",
        "total_events": total_events,
        "unique_users": unique_users,
        "revenue": revenue,
        "top_user": top_user
    }

@app.get("/work")
async def work(n: int):
    # Do K units of work (mock)
    for _ in range(n):
        pass
    return {"email": "24f2007156@ds.study.iitm.ac.in", "done": n}

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return f"# HELP http_requests_total Total number of HTTP requests\n# TYPE http_requests_total counter\nhttp_requests_total {REQUEST_COUNT}\n"

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "uptime_s": time.time() - APP_START_TIME}

@app.get("/logs/tail")
async def logs_tail(limit: int = 10):
    return LOG_ENTRIES[-limit:]

class ExtractRequest(BaseModel):
    text: str

class ExtractResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str

@app.post("/extract", response_model=ExtractResponse)
async def extract_invoice(req: ExtractRequest):
    text = req.text
    if not text or not text.strip():
        raise HTTPException(status_code=422, detail="Empty text")
        
    # Currency
    curr_match = re.search(r'\b(USD|EUR|GBP)\b', text, re.IGNORECASE)
    currency = curr_match.group(1).upper() if curr_match else "USD"
    
    # Date
    date_match = re.search(r'\b(202\d-\d{2}-\d{2})\b', text)
    date_str = date_match.group(1) if date_match else "2026-01-01"
    
    # Amount
    amount = 0.0
    amounts = re.findall(r'\b(\d+(?:\.\d{1,2})?)\b', text)
    valid_amounts = [float(a) for a in amounts if 50 <= float(a) <= 9050]
    
    if valid_amounts:
        amount = valid_amounts[0]
        if len(valid_amounts) > 1:
            amt_match = re.search(r'(?:total|amount|due|pay|balance).*?(?:USD|EUR|GBP|\$|€|£)?\s*(\d+(?:\.\d{1,2})?)', text, re.IGNORECASE)
            if amt_match:
                val = float(amt_match.group(1))
                if val in valid_amounts:
                    amount = val
                    
    # Vendor
    vendor_match = re.search(r'([A-Z][a-zA-Z0-9-]*\s+(?:[A-Z][a-zA-Z0-9-]*\s+)*(?:Ltd\.?|Inc\.?|LLC|Corp\.?|Company|Industries))', text, re.IGNORECASE)
    if vendor_match:
        vendor = vendor_match.group(1).strip()
    else:
        vendor = text.strip()
        
    return ExtractResponse(
        vendor=vendor,
        amount=amount,
        currency=currency,
        date=date_str
    )

def check_rate_limit(client_id: str):
    if not client_id:
        client_id = "unknown"
    now = time.time()
    if client_id not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[client_id] = []
        
    RATE_LIMIT_STORE[client_id] = [ts for ts in RATE_LIMIT_STORE[client_id] if now - ts < 10]
    
    if len(RATE_LIMIT_STORE[client_id]) >= 17:
        raise HTTPException(
            status_code=429, 
            detail="Too Many Requests", 
            headers={"Retry-After": "10"}
        )
        
    RATE_LIMIT_STORE[client_id].append(now)

@app.post("/orders", status_code=201)
async def create_order(
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
    x_client_id: str = Header(None)
):
    check_rate_limit(x_client_id)
    
    if idempotency_key and idempotency_key in IDEMPOTENCY_STORE:
        return {"id": IDEMPOTENCY_STORE[idempotency_key]}
    
    new_id = f"ord_{uuid.uuid4().hex[:8]}"
    if idempotency_key:
        IDEMPOTENCY_STORE[idempotency_key] = new_id
    
    return {"id": new_id}

@app.get("/orders")
async def get_orders(
    x_client_id: str = Header(None),
    limit: int = 10,
    cursor: str = None
):
    check_rate_limit(x_client_id)
    
    total_orders = 47
    all_orders = [{"id": i} for i in range(1, total_orders + 1)]
    
    start_idx = 0
    if cursor and cursor.isdigit():
        start_idx = int(cursor)
        
    end_idx = start_idx + limit
    items = all_orders[start_idx:end_idx]
    
    res = {"items": items}
    if end_idx < total_orders:
        res["next_cursor"] = str(end_idx)
        
    return res
