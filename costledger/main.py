from fastapi import FastAPI, HTTPException
app = FastAPI(title="CostLedger")

# Invented data. Cost per chip at each step, in rupees.
STEP_COSTS = {"die": 40, "bonding": 10, "moulding": 8, "final_test": 6}

@app.get("/step-costs")
def step_costs():
    """Cost per chip at each production step, and the total rupees already spent on a chip if it is scrapped after that step. Invented data."""
    carried = STEP_COSTS["die"]
    rows = []
    for step in ["bonding", "moulding", "final_test"]:
        carried += STEP_COSTS[step]
        rows.append({
            "step": step,
            "step_cost_inr": STEP_COSTS[step],
            "carried_cost_if_scrapped_after_inr": carried,
        })
    return {"currency": "INR", "die_cost_inr": STEP_COSTS["die"], "steps": rows}
@app.get("/price-losses/{bonding}/{moulding}/{final_test}")
def price_losses(bonding: int, moulding: int, final_test: int):
    """Turn counts of scrapped chips into rupees. Give the number of chips lost at bonding, moulding and final_test (use 0 for none). Each lost chip is priced at everything already spent on it by that step. The maths is done here, not by the caller. Invented data."""
    losses = {"bonding": bonding, "moulding": moulding, "final_test": final_test}
    if any(n < 0 for n in losses.values()):
        raise HTTPException(status_code=400, detail="Loss counts cannot be negative.")
    carried = STEP_COSTS["die"]
    rows = []
    total = 0
    for step in ["bonding", "moulding", "final_test"]:
        carried += STEP_COSTS[step]
        loss_inr = losses[step] * carried
        total += loss_inr
        rows.append({
            "step": step,
            "chips_lost": losses[step],
            "carried_cost_per_chip_inr": carried,
            "loss_inr": loss_inr,
        })
    return {"currency": "INR", "steps": rows, "total_loss_inr": total}