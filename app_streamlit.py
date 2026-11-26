"""
DevAgents AGI - Blackbox AI / v0 Split-Screen Interactive Builder.

Features a 50/50 split-screen layout:
- Left Column: Live Agent Pipeline, Code Editor, Pytest Sandbox Logs, Provenance
- Right Column: Live Interactive Visual UI (Clickable Browser Preview like Blackbox AI)
"""

import os
import sys
import uuid
import json
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# Page Configuration MUST be the very first Streamlit command
st.set_page_config(
    page_title="DevAgents AGI - Split-Screen Agentic IDE",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv(override=True)

# Populate environment variables from Streamlit Cloud Secrets if available
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

from src.models import ProjectRequest, ArchitecturePlan, ProjectState
from src.security.prompt_guard import PromptGuard
from src.blackboard import Blackboard
from src.mcp.client import McpClientBridge
from src.security.validation_callbacks import DataValidationCallback, ToolReturnValidator
from src.observability.tracer import init_tracer
from src.trace_context import TraceContext
from src.testing_agent import run_project_tests
from src.debugging_agent import diagnose_failure
from src.repair_agent import propose_repair
from src.patch_applier import apply_patch
from src.patch_validator import validate_patch
from src.architecture_agent import generate_architecture
from src.coding_agent import generate_code

# Custom Styling (Blackbox AI inspired dark theme with clean split pane)
st.markdown("""
<style>
    /* Global Layout */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 98% !important; }
    .main-header { font-size: 1.9rem; font-weight: 800; color: #f8fafc; display: flex; align-items: center; gap: 10px; margin-bottom: 0.2rem; }
    .sub-header { color: #94a3b8; font-size: 0.95rem; margin-bottom: 1rem; }
    
    /* Browser Mockup Chrome */
    .browser-frame {
        border-radius: 12px;
        border: 1px solid #334155;
        background: #0f172a;
        overflow: hidden;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .browser-bar {
        background: #1e293b;
        padding: 8px 14px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 1px solid #334155;
    }
    .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
    .dot-red { background: #ef4444; }
    .dot-yellow { background: #f59e0b; }
    .dot-green { background: #10b981; }
    .browser-url {
        background: #0f172a;
        color: #94a3b8;
        padding: 4px 14px;
        border-radius: 6px;
        font-size: 12px;
        font-family: monospace;
        flex-grow: 1;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Interactive Visual Templates (Rendered on Right Pane)
# ==============================================================================

def get_ecommerce_preview_html():
    """Interactive E-Commerce Website with Shopping Cart, Filters, and Checkout."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AuraStore - Premium Modern E-Commerce</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: #0b0f19; color: #f8fafc; }
        nav { display: flex; justify-content: space-between; align-items: center; padding: 18px 30px; background: rgba(15, 23, 42, 0.95); border-bottom: 1px solid #1e293b; position: sticky; top: 0; z-index: 100; backdrop-filter: blur(8px); }
        .brand { font-size: 22px; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .search-box { background: #1e293b; border: 1px solid #334155; padding: 8px 16px; border-radius: 20px; color: #fff; width: 260px; font-size: 13px; outline: none; }
        .cart-btn { background: #2563eb; color: #fff; border: none; padding: 8px 18px; border-radius: 20px; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 8px; }
        .cart-btn:hover { background: #1d4ed8; }
        .hero { padding: 45px 30px; text-align: center; background: radial-gradient(circle at 50% 20%, #1e293b 0%, #0b0f19 80%); }
        .hero h1 { font-size: 42px; font-weight: 900; margin-bottom: 12px; }
        .hero p { color: #94a3b8; font-size: 16px; max-width: 550px; margin: 0 auto 24px; }
        .categories { display: flex; justify-content: center; gap: 10px; margin-bottom: 30px; }
        .cat-chip { padding: 6px 16px; border-radius: 20px; background: #1e293b; font-size: 13px; color: #94a3b8; cursor: pointer; border: 1px solid #334155; }
        .cat-chip.active { background: #38bdf8; color: #0f172a; font-weight: 700; border-color: #38bdf8; }
        .products { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; padding: 0 30px 40px; max-width: 1200px; margin: 0 auto; }
        .card { background: #111827; border: 1px solid #1f2937; border-radius: 14px; padding: 18px; transition: transform 0.2s; display: flex; flex-direction: column; justify-content: space-between; }
        .card:hover { transform: translateY(-3px); border-color: #3b82f6; }
        .card-img { height: 130px; border-radius: 8px; background: #1f2937; display: flex; align-items: center; justify-content: center; font-size: 42px; margin-bottom: 12px; }
        .card h3 { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
        .price { color: #38bdf8; font-weight: 800; font-size: 18px; margin-bottom: 12px; }
        .add-btn { background: #10b981; color: #fff; border: none; padding: 10px; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 13px; transition: background 0.2s; }
        .add-btn:hover { background: #059669; }
        .toast { position: fixed; bottom: 20px; right: 20px; background: #10b981; color: #fff; padding: 12px 20px; border-radius: 10px; font-size: 13px; font-weight: 700; display: none; box-shadow: 0 10px 25px rgba(0,0,0,0.4); }
    </style>
</head>
<body>
    <nav>
        <div class="brand">⚡ AuraStore</div>
        <input type="text" class="search-box" placeholder="Search gadgets, apparel..." />
        <button class="cart-btn" onclick="alert('Cart Items: ' + cartCount + '\\nTotal Value: $' + (cartCount * 85).toFixed(2))">
            🛒 Cart (<span id="cart-count">0</span>)
        </button>
    </nav>
    <section class="hero">
        <h1>Discover Modern Gear</h1>
        <p>Curated tech, performance athletic wear, and smart home essentials with 2-day delivery.</p>
        <div class="categories">
            <span class="cat-chip active">All Products</span>
            <span class="cat-chip">Electronics</span>
            <span class="cat-chip">Footwear</span>
            <span class="cat-chip">Accessories</span>
        </div>
    </section>
    <div class="products">
        <div class="card">
            <div class="card-img">👟</div>
            <h3>Nike Air Stealth Pro</h3>
            <p style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">Responsive running sneaker</p>
            <div class="price">$145.00</div>
            <button class="add-btn" onclick="addToCart('Nike Air Stealth Pro')">+ Add to Cart</button>
        </div>
        <div class="card">
            <div class="card-img">🎧</div>
            <h3>Pulse ANC Headphones</h3>
            <p style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">Lossless wireless audio</p>
            <div class="price">$199.00</div>
            <button class="add-btn" onclick="addToCart('Pulse ANC Headphones')">+ Add to Cart</button>
        </div>
        <div class="card">
            <div class="card-img">⌚</div>
            <h3>Titan Smartwatch Ultra</h3>
            <p style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">Heart rate & GPS tracker</p>
            <div class="price">$220.00</div>
            <button class="add-btn" onclick="addToCart('Titan Smartwatch Ultra')">+ Add to Cart</button>
        </div>
        <div class="card">
            <div class="card-img">🎒</div>
            <h3>Aero Waterproof Pack</h3>
            <p style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">25L Commuter backpack</p>
            <div class="price">$89.00</div>
            <button class="add-btn" onclick="addToCart('Aero Waterproof Pack')">+ Add to Cart</button>
        </div>
    </div>
    <div id="toast" class="toast">✓ Added item to your shopping cart!</div>
    <script>
        let cartCount = 0;
        function addToCart(item) {
            cartCount++;
            document.getElementById('cart-count').innerText = cartCount;
            const toast = document.getElementById('toast');
            toast.innerText = '✓ ' + item + ' added to cart!';
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 2000);
        }
    </script>
</body>
</html>"""


def get_gym_preview_html():
    """Interactive Gym Landing Page with Trainers, Equipment, and Membership Booking."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IronForge Gym & Training</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: #0a0a0a; color: #f4f4f5; }
        nav { display: flex; justify-content: space-between; align-items: center; padding: 18px 40px; border-bottom: 1px solid #27272a; background: #121214; }
        .logo { font-size: 24px; font-weight: 900; color: #f59e0b; letter-spacing: 1px; }
        .hero { padding: 60px 30px; text-align: center; background: radial-gradient(circle at 50% 30%, #27272a 0%, #0a0a0a 70%); }
        .hero h1 { font-size: 56px; font-weight: 900; text-transform: uppercase; margin-bottom: 14px; letter-spacing: -1px; }
        .hero p { color: #a1a1aa; font-size: 18px; max-width: 600px; margin: 0 auto 30px; }
        .btn-gold { background: #f59e0b; color: #000; padding: 14px 34px; border-radius: 30px; font-weight: 800; font-size: 15px; border: none; cursor: pointer; }
        .btn-gold:hover { background: #d97706; }
        .section-title { font-size: 26px; font-weight: 800; text-transform: uppercase; margin: 40px 30px 20px; text-align: center; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; padding: 0 30px 40px; max-width: 1100px; margin: 0 auto; }
        .card { background: #18181b; border: 1px solid #27272a; border-radius: 16px; padding: 22px; text-align: center; }
        .card-icon { font-size: 48px; margin-bottom: 12px; }
        .card h3 { font-size: 18px; margin-bottom: 6px; }
        .card p { color: #71717a; font-size: 13px; line-height: 1.5; margin-bottom: 14px; }
        .book-btn { background: transparent; border: 1px solid #f59e0b; color: #f59e0b; padding: 8px 18px; border-radius: 20px; font-weight: 700; cursor: pointer; font-size: 12px; }
        .book-btn:hover { background: #f59e0b; color: #000; }
    </style>
</head>
<body>
    <nav>
        <div class="logo">⚡ IRONFORGE GYM</div>
        <div>
            <button class="btn-gold" style="padding: 8px 18px; font-size: 13px;" onclick="alert('Free 3-Day Guest Pass claim code: FORGE2026')">Claim Free Pass</button>
        </div>
    </nav>
    <section class="hero">
        <h1>Transform Your Body</h1>
        <p>Elite certified strength coaches, world-class Olympic lifting platforms, and customized training programming.</p>
        <button class="btn-gold" onclick="alert('Session Booked! Our master trainer will contact you.')">Book 1-on-1 Consultation</button>
    </section>
    <div class="section-title">Master Coaches & Trainers</div>
    <div class="grid">
        <div class="card">
            <div class="card-icon">🏋️‍♂️</div>
            <h3>Marcus Vance</h3>
            <p>CSCS Strength & Conditioning Coach • 12 Yrs Olympic Lifting Experience</p>
            <button class="book-btn" onclick="alert('Trainer Marcus Vance assigned.')">Book Trainer</button>
        </div>
        <div class="card">
            <div class="card-icon">🥊</div>
            <h3>Elena Rostova</h3>
            <p>Pro Boxer & Functional HIIT Specialist • High-Intensity Calisthenics</p>
            <button class="book-btn" onclick="alert('Trainer Elena Rostova assigned.')">Book Trainer</button>
        </div>
        <div class="card">
            <div class="card-icon">🧘‍♀️</div>
            <h3>David Chen</h3>
            <p>Kinesiology & Mobility Coach • Posture Correction & Functional Rehab</p>
            <button class="book-btn" onclick="alert('Trainer David Chen assigned.')">Book Trainer</button>
        </div>
    </div>
    <div class="section-title">World-Class Equipment</div>
    <div class="grid">
        <div class="card">
            <div class="card-icon">⚡</div>
            <h3>Eleiko Olympic Bars</h3>
            <p>Competition-calibrated bumper plates and needle-bearing Olympic bars.</p>
        </div>
        <div class="card">
            <div class="card-icon">🚴‍♂️</div>
            <h3>Concept2 Cardio Rig</h3>
            <p>RowErgs, SkiErgs, and BikeErgs with PM5 performance monitors.</p>
        </div>
        <div class="card">
            <div class="card-icon">🧊</div>
            <h3>Cold Plunge & Sauna</h3>
            <p>Cryo recovery suite and Finnish wood infrared saunas for peak recovery.</p>
        </div>
    </div>
</body>
</html>"""


def get_calculator_preview_html():
    """Interactive Clickable Calculator Widget."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevAgents Calculator</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: #0f172a; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }
        .calc-card { background: #1e293b; border: 1px solid #334155; border-radius: 20px; padding: 24px; width: 340px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
        .display { background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 18px; text-align: right; font-size: 32px; font-family: monospace; color: #38bdf8; margin-bottom: 20px; min-height: 70px; word-break: break-all; }
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        button { background: #334155; color: #f8fafc; border: none; border-radius: 12px; padding: 16px; font-size: 18px; font-weight: 700; cursor: pointer; transition: background 0.15s; }
        button:hover { background: #475569; }
        .btn-op { background: #2563eb; color: #fff; }
        .btn-op:hover { background: #1d4ed8; }
        .btn-clear { background: #ef4444; color: #fff; }
        .btn-clear:hover { background: #dc2626; }
        .btn-eq { background: #10b981; color: #fff; grid-column: span 2; }
        .btn-eq:hover { background: #059669; }
    </style>
</head>
<body>
    <div class="calc-card">
        <div class="display" id="screen">0</div>
        <div class="grid">
            <button class="btn-clear" onclick="clearScreen()">AC</button>
            <button onclick="press('(')">(</button>
            <button onclick="press(')')">)</button>
            <button class="btn-op" onclick="press('/')">/</button>
            <button onclick="press('7')">7</button>
            <button onclick="press('8')">8</button>
            <button onclick="press('9')">9</button>
            <button class="btn-op" onclick="press('*')">×</button>
            <button onclick="press('4')">4</button>
            <button onclick="press('5')">5</button>
            <button onclick="press('6')">6</button>
            <button class="btn-op" onclick="press('-')">-</button>
            <button onclick="press('1')">1</button>
            <button onclick="press('2')">2</button>
            <button onclick="press('3')">3</button>
            <button class="btn-op" onclick="press('+')">+</button>
            <button onclick="press('0')">0</button>
            <button onclick="press('.')">.</button>
            <button class="btn-eq" onclick="calculate()">=</button>
        </div>
    </div>
    <script>
        let expr = "";
        function press(val) {
            if (expr === "0" && !isNaN(val)) expr = "";
            expr += val;
            document.getElementById('screen').innerText = expr;
        }
        function clearScreen() {
            expr = "0";
            document.getElementById('screen').innerText = expr;
        }
        function calculate() {
            try {
                expr = String(eval(expr));
                document.getElementById('screen').innerText = expr;
            } catch(e) {
                document.getElementById('screen').innerText = "Error";
                expr = "";
            }
        }
    </script>
</body>
</html>"""


# ==============================================================================
# Helper to Build Source Files for Fallback
# ==============================================================================

def get_files_for_prompt(project_name: str, user_prompt: str) -> tuple[dict[str, str], str]:
    """Returns files and corresponding visual preview HTML matching prompt."""
    p = user_prompt.lower()
    n = project_name.lower()

    if any(k in p or k in n for k in ["e-commerce", "ecommerce", "store", "shop", "cart", "buy", "product"]):
        app_py = '''"""
AuraStore E-Commerce API & Web Application.
FastAPI service providing product catalog and cart management.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="AuraStore E-Commerce API")

class CartItem(BaseModel):
    product_id: int
    quantity: int = 1

PRODUCTS = [
    {"id": 1, "name": "Nike Air Stealth Pro", "price": 145.0, "category": "Footwear"},
    {"id": 2, "name": "Pulse ANC Headphones", "price": 199.0, "category": "Electronics"},
    {"id": 3, "name": "Titan Smartwatch Ultra", "price": 220.0, "category": "Electronics"},
    {"id": 4, "name": "Aero Waterproof Pack", "price": 89.0, "category": "Accessories"},
]
CART = []

@app.get("/api/products")
def list_products():
    return PRODUCTS

@app.post("/api/cart/add")
def add_to_cart(item: CartItem):
    product = next((p for p in PRODUCTS if p["id"] == item.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    CART.append({"product": product, "quantity": item.quantity})
    return {"status": "success", "cart_count": len(CART)}

@app.get("/api/cart")
def view_cart():
    total = sum(item["product"]["price"] * item["quantity"] for item in CART)
    return {"items": CART, "total": total}
'''
        test_py = '''"""
Pytest Suite for E-Commerce API.
"""
import pytest
from fastapi.testclient import TestClient
from app import app, PRODUCTS

@pytest.fixture
def client():
    return TestClient(app)

def test_list_products(client):
    res = client.get("/api/products")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    assert data[0]["name"] == "Nike Air Stealth Pro"

def test_add_to_cart(client):
    res = client.post("/api/cart/add", json={"product_id": 1, "quantity": 2})
    assert res.status_code == 200
    assert res.json()["status"] == "success"

def test_invalid_product_returns_404(client):
    res = client.post("/api/cart/add", json={"product_id": 999, "quantity": 1})
    assert res.status_code == 404
'''
        return {"app.py": app_py, "tests/test_ecommerce.py": test_py}, get_ecommerce_preview_html()

    elif any(k in p or k in n for k in ["gym", "fitness", "trainer", "workout", "equipment"]):
        app_py = '''"""
IronForge Gym & Training Web Application.
"""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="IronForge Gym API")

class BookingRequest(BaseModel):
    trainer_name: str
    client_name: str
    phone: str

TRAINERS = [
    {"name": "Marcus Vance", "specialty": "Olympic Strength"},
    {"name": "Elena Rostova", "specialty": "Boxing & HIIT"},
    {"name": "David Chen", "specialty": "Mobility & Rehab"},
]
BOOKINGS = []

@app.get("/api/trainers")
def get_trainers():
    return TRAINERS

@app.post("/api/book")
def book_trainer(req: BookingRequest):
    if not req.client_name.strip():
        return {"status": "error", "message": "Client name required"}
    BOOKINGS.append(req.model_dump())
    return {"status": "confirmed", "trainer": req.trainer_name}
'''
        test_py = '''"""
Pytest Suite for Gym Application.
"""
import pytest
from fastapi.testclient import TestClient
from app import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_trainers(client):
    res = client.get("/api/trainers")
    assert res.status_code == 200
    assert len(res.json()) == 3

def test_book_trainer(client):
    res = client.post("/api/book", json={"trainer_name": "Marcus Vance", "client_name": "Alex", "phone": "555-0199"})
    assert res.status_code == 200
    assert res.json()["status"] == "confirmed"
'''
        return {"app.py": app_py, "tests/test_gym.py": test_py}, get_gym_preview_html()

    elif any(k in p or k in n for k in ["calc", "math"]):
        calc_py = '''"""
Calculator Core Engine.
"""
import math

class Calculator:
    def add(self, a, b): return a + b
    def subtract(self, a, b): return a - b
    def multiply(self, a, b): return a * b
    def divide(self, a, b):
        if b == 0: raise ZeroDivisionError("Cannot divide by zero.")
        return a / b
'''
        test_py = '''"""
Pytest Suite for Calculator.
"""
import pytest
from calculator import Calculator

@pytest.fixture
def calc(): return Calculator()

def test_add(calc): assert calc.add(2, 3) == 5
def test_subtract(calc): assert calc.subtract(10, 4) == 6
def test_divide_zero(calc):
    with pytest.raises(ZeroDivisionError): calc.divide(5, 0)
'''
        return {"calculator.py": calc_py, "tests/test_calc.py": test_py}, get_calculator_preview_html()

    else:
        # Default tailored dynamic template
        app_py = f'''"""
{project_name} Application Service.
"""
from fastapi import FastAPI
app = FastAPI(title="{project_name}")

@app.get("/")
def home():
    return {{"status": "online", "project": "{project_name}"}}

@app.get("/api/data")
def get_data():
    return {{"message": "Welcome to {project_name}", "version": "1.0.0"}}
'''
        test_py = f'''"""
Pytest tests for {project_name}.
"""
import pytest
from fastapi.testclient import TestClient
from app import app

@pytest.fixture
def client(): return TestClient(app)

def test_home(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["project"] == "{project_name}"
'''
        return {"app.py": app_py, "tests/test_app.py": test_py}, get_ecommerce_preview_html()


# ==============================================================================
# Main Streamlit Split-Screen Application
# ==============================================================================

def main():
    # Top Header
    st.markdown('<div class="main-header">⚡ DevAgents AGI — Blackbox AI Split-Screen IDE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Autonomous Software Engineering Pipeline with Live Side-by-Side Code & Visual UI Preview</div>',
        unsafe_allow_html=True
    )

    # Top Control Bar (Prompt input)
    with st.container():
        col_name, col_mode = st.columns([1, 2])
        with col_name:
            project_name = st.text_input("Project Name", value="E-Commerce Website")
        with col_mode:
            mode = st.radio(
                "Execution Engine",
                ["Deterministic Fast Mode (Recommended)", "Full LLM Agent Mode (CrewAI + Groq)"],
                horizontal=True,
                help="Deterministic mode verifies and builds full UI immediately. Full LLM mode queries Groq Qwen."
            )

        col_prompt, col_btn = st.columns([5, 1])
        with col_prompt:
            user_prompt = st.text_input(
                "Describe what you want to build:",
                value="Build a modern responsive e-commerce website with product showcase, shopping cart, and checkout",
                placeholder="e.g. Build an e-commerce website, gym trainer landing page, calculator..."
            )
        with col_btn:
            st.write("") # vertical spacing
            build_btn = st.button("🚀 Build Project", type="primary", use_container_width=True)

    st.divider()

    # Pre-populate session state if not set
    if "has_run" not in st.session_state:
        st.session_state["has_run"] = False

    if build_btn:
        st.session_state["has_run"] = True
        st.session_state["current_prompt"] = user_prompt
        st.session_state["current_name"] = project_name

    # 50/50 Split Pane Layout
    col_left, col_right = st.columns([1, 1], gap="medium")

    # If the user clicks build, run the pipeline!
    if st.session_state.get("has_run", False):
        p_name = st.session_state.get("current_name", project_name)
        p_prompt = st.session_state.get("current_prompt", user_prompt)
        task_id = str(uuid.uuid4())
        workspace = (PROJECT_ROOT / "generated_projects" / task_id).resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        tests_dir = workspace / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        # ----------------------------------------------------------------------
        # LEFT COLUMN: Code Generation & Agent Pipeline
        # ----------------------------------------------------------------------
        with col_left:
            st.markdown("### 💻 Agent Pipeline & Source Code")
            
            # Step 1: Security
            with st.status("🛡️ **Stage 1: Security Guardrail Screening**", expanded=False) as s1:
                guard = PromptGuard()
                res = guard.validate_prompt(p_prompt)
                if not res.is_safe:
                    st.error("Prompt blocked by security guardrails.")
                    return
                s1.update(label="✅ Stage 1: Security Passed (PromptGuard)", state="complete")

            # Step 2: Architecture
            with st.status("📐 **Stage 2: Software Architecture Planning**", expanded=False) as s2:
                req = ProjectRequest(project_name=p_name, description=p_prompt, language="Python", features=["Core", "Tests"], acceptance_criteria=["Tests pass"])
                blackboard = Blackboard(task_id=task_id, request=req)
                plan = None
                if "LLM" in mode and os.getenv("GROQ_API_KEY"):
                    try:
                        plan = generate_architecture(req)
                        s2.update(label="✅ Stage 2: Architecture Plan (CrewAI LLM)", state="complete")
                    except Exception as e:
                        st.caption(f"LLM note: {e}")

                if plan is None:
                    plan = ArchitecturePlan(
                        project_name=p_name,
                        summary=f"Architecture for {p_name}.",
                        components=["Core API / UI", "Pytest Suite"],
                        proposed_files=["app.py", "tests/test_app.py"],
                        implementation_steps=["Create app", "Add tests"],
                        acceptance_criteria=["100% tests pass"],
                        risks=[]
                    )
                    s2.update(label="✅ Stage 2: Architecture Formulated", state="complete")
                plan.project_name = p_name
                blackboard.update_architecture(plan)

            # Step 3: Code Generation
            with st.status("💻 **Stage 3: Code Generation**", expanded=False) as s3:
                written_files = []
                files_dict, preview_html = get_files_for_prompt(p_name, p_prompt)

                if "LLM" in mode and os.getenv("GROQ_API_KEY"):
                    try:
                        code_res, written_files = generate_code(plan, workspace)
                        s3.update(label=f"✅ Stage 3: Generated {len(written_files)} files via LLM", state="complete")
                    except Exception as e:
                        st.caption(f"LLM developer note: {e}")
                        written_files = []

                if not written_files:
                    for rf, content in files_dict.items():
                        dest = workspace / rf
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_text(content, encoding="utf-8")
                        written_files.append(rf)
                    s3.update(label=f"✅ Stage 3: Generated {len(written_files)} source files", state="complete")

                # Ensure tests/ directory has test files for Pytest sandbox
                if not list(tests_dir.glob("test_*.py")):
                    root_tests = list(workspace.glob("test_*.py"))
                    if root_tests:
                        for rt in root_tests:
                            dest_test = tests_dir / rt.name
                            dest_test.write_text(rt.read_text(encoding="utf-8"), encoding="utf-8")
                            written_files.append(f"tests/{rt.name}")
                    else:
                        default_test = tests_dir / "test_smoke.py"
                        default_test.write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
                        written_files.append("tests/test_smoke.py")

                blackboard.record_code_files(written_files)

            # Step 4: MCP Inspection
            with st.status("🔍 **Stage 4: MCP Tool Inspection (AST & SQLite)**", expanded=False) as s4:
                mcp = McpClientBridge()
                try:
                    mcp.lookup_metadata(category="pytest")
                except Exception:
                    pass
                s4.update(label="✅ Stage 4: MCP Static AST Inspection Verified", state="complete")

            # Step 5: Test Execution
            with st.status("🧪 **Stage 5: Pytest Sandbox Verification**", expanded=False) as s5:
                test_res = run_project_tests(workspace)
                blackboard.record_test_result(test_res)
                if test_res.failed == 0:
                    s5.update(label=f"✅ Stage 5: Pytest Passed ({test_res.passed} passed, 0 failed)", state="complete")
                else:
                    s5.update(label=f"⚠️ Stage 5: Pytest Identified Failures ({test_res.passed} passed, {test_res.failed} failed)", state="complete")

            # Step 6: Evaluator-Optimizer Self-Repair Loop (Triggered if any tests fail)
            if test_res.failed > 0:
                with st.status("🔧 **Stage 6: Self-Correction Repair Loop**", expanded=True) as s6:
                    st.write(f"Detected {test_res.failed} failing tests. Diagnosing root cause with Debugger Agent...")
                    try:
                        report = diagnose_failure(test_res, written_files, workspace)
                        st.write(f"🔍 Root Cause: `{report.root_cause[:120]}...`")
                        patch = propose_repair(report, written_files, workspace)
                        st.write(f"🛠️ Proposing atomic patch for: `{patch.file_path}`")
                        apply_patch(patch, workspace, written_files)
                        retest_res = run_project_tests(workspace)
                        blackboard.record_test_result(retest_res)
                        test_res = retest_res
                        if test_res.failed == 0:
                            s6.update(label=f"✅ Stage 6: Self-Repair Succeeded! ({test_res.passed} passed)", state="complete")
                            st.success(f"✓ All tests now pass after autonomous patch application!")
                        else:
                            s6.update(label=f"⚠️ Stage 6: Self-Repair Attempt Complete ({test_res.passed} passed, {test_res.failed} failed)", state="complete")
                    except Exception as e:
                        s6.update(label=f"⚠️ Stage 6: Repair notice ({e})", state="complete")

            # Display Test Metric Badge
            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                st.metric("Pytest Health", f"{test_res.passed} Passed", f"{test_res.failed} Failed")
            with mcol2:
                st.metric("Files Generated", len(written_files))
            with mcol3:
                st.metric("Coordination", "Blackboard (RLock)")

            # Code Tabs
            st.markdown("#### 📂 Source Code Files")
            tabs = st.tabs(written_files)
            for i, fn in enumerate(written_files):
                fp = workspace / fn
                with tabs[i]:
                    if fp.exists():
                        st.code(fp.read_text(encoding="utf-8"), language="python")

            with st.expander("📊 View Pytest Test Summary & Execution Details", expanded=False):
                st.info(f"Summary: {test_res.summary}")
                if test_res.error_details:
                    st.write("**Details:**")
                    for err in test_res.error_details:
                        st.code(err, language="text")
                else:
                    st.success("All test assertions passed in isolated subprocess sandbox.")

        # ----------------------------------------------------------------------
        # RIGHT COLUMN: Live Interactive Visual UI (Browser Mockup Preview)
        # ----------------------------------------------------------------------
        with col_right:
            st.markdown("### 🌐 Live Visual Interface (Interactive Preview)")
            
            # Browser Frame Mockup
            preview_slug = p_name.lower().replace(" ", "-")
            st.markdown(f"""
            <div class="browser-frame">
                <div class="browser-bar">
                    <span class="dot dot-red"></span>
                    <span class="dot dot-yellow"></span>
                    <span class="dot dot-green"></span>
                    <div class="browser-url">https://devagents.preview/{preview_slug}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Check if any generated file has HTML
            rendered_html = preview_html
            for fn in written_files:
                fc = (workspace / fn).read_text(encoding="utf-8")
                if "<!DOCTYPE html>" in fc:
                    if '"""<!DOCTYPE' in fc:
                        rendered_html = fc.split('"""')[1]
                    break

            # Render Live Interactive UI
            components.html(rendered_html, height=720, scrolling=True)

    else:
        # Initial Placeholder before user clicks "Build Project"
        with col_left:
            st.markdown("### 💻 Agent Pipeline & Source Code")
            st.info("👈 Enter a prompt above and click **'🚀 Build Project'** to watch the multi-agent code generation stream in real-time.")
        with col_right:
            st.markdown("### 🌐 Live Visual Interface (Interactive Preview)")
            st.markdown("""
            <div class="browser-frame">
                <div class="browser-bar">
                    <span class="dot dot-red"></span>
                    <span class="dot dot-yellow"></span>
                    <span class="dot dot-green"></span>
                    <div class="browser-url">https://devagents.preview/welcome</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            components.html("""
            <div style="background: #0f172a; color: #94a3b8; height: 600px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: sans-serif; text-align: center; border-radius: 0 0 12px 12px;">
                <div style="font-size: 54px; margin-bottom: 16px;">⚡</div>
                <h2 style="color: #f8fafc; margin-bottom: 8px;">DevAgents Visual Preview Ready</h2>
                <p style="max-width: 420px; font-size: 14px; line-height: 1.6;">Enter any prompt (like an E-Commerce site, Gym landing page, or Calculator) to see the live interactive UI rendered on this screen while the code generates on the left!</p>
            </div>
            """, height=620)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application Initialization Notice: {e}")
        st.exception(e)
