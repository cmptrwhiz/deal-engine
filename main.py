from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

# -------- MODELS --------
class DealInput(BaseModel):
    price: float
    gross_rent: float
    expenses: float
    year_built: int
    rent_control: bool
    vacancy: float
    capex: float
    dom: int
    interest_rate: float
    ltv: float

class DealComparison(BaseModel):
    deals: List[DealInput]

# -------- CORE LOGIC --------
def calculate_metrics(data):
    noi = data.gross_rent - data.expenses

    tax_reset = data.price * 0.012
    insurance = 8000
    repairs = 10000

    noi_adj = noi - tax_reset - insurance - repairs

    loan = data.price * data.ltv
    debt = loan * data.interest_rate

    dscr = noi_adj / debt if debt else 0
    dscr_stress = (noi_adj * 0.8) / debt if debt else 0

    cap_rate = noi_adj / data.price

    market_cap = 0.06
    value = noi_adj / market_cap
    discount = value - data.price

    return {
        "noi": noi_adj,
        "dscr": dscr,
        "dscr_stress": dscr_stress,
        "cap_rate": cap_rate,
        "value": value,
        "discount": discount
    }

# -------- SCORING --------
def score_deal(data):
    m = calculate_metrics(data)

    score = 0

    # Downside
    if m["dscr_stress"] > 1.25:
        score += 30
    elif m["dscr_stress"] > 1.0:
        score += 15

    # Income
    if m["cap_rate"] > 0.06:
        score += 25

    # Discount
    if m["discount"] > 0:
        score += min(25, (m["discount"] / data.price) * 25)

    # Risk penalties
    if data.year_built < 1950:
        score -= 10
    if data.rent_control:
        score -= 5
    if data.vacancy > 0.1:
        score -= 5

    # DOM advantage
    if data.dom > 120:
        score += 10

    decision = "BUY" if score >= 75 else "WATCH" if score >= 60 else "PASS"

    return {
        "score": round(score, 2),
        "decision": decision,
        "metrics": m,
        "offer": {
            "anchor": round(m["value"] * 0.65),
            "target": round(m["value"] * 0.75),
            "max": round(m["value"] * 0.85)
        }
    }

# -------- ROUTES --------
@app.post("/score")
def score(data: DealInput):
    return score_deal(data)

@app.post("/compare")
def compare(data: DealComparison):
    results = [score_deal(d) for d in data.deals]
    return sorted(results, key=lambda x: x["score"], reverse=True)