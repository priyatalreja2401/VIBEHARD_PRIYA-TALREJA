from fastapi import FastAPI, HTTPException
app = FastAPI(title="LineOps")

STEPS = ["bonding", "moulding", "final_test"]

def batch(batch_id, machine, bonding, moulding, final_test, into_final_test):
    return {
        "batch_id": batch_id,
        "machine": machine,
        "units_started": 10000,
        "lost": {"bonding": bonding, "moulding": moulding, "final_test": final_test},
        "units_into_final_test": into_final_test,
    }

# Invented data: 20 batches of 10,000 chips.
BATCHES = []
# B1 = even batch numbers 446-464. Loses 800 chips per batch, all at bonding.
for n in range(446, 466, 2):
    BATCHES.append(batch(n, "B1", 800, 0, 0, 9200))
# B2 = odd batch numbers 447-465. Normally loses 600 chips at final test.
for n in range(447, 467, 2):
    if n == 447:
        BATCHES.append(batch(n, "B2", 0, 0, 120, 100))     # inconsistent record
    elif n in (455, 457):
        BATCHES.append(batch(n, "B2", 0, 0, 1050, 10000))  # just after a Tuesday restart
    else:
        BATCHES.append(batch(n, "B2", 0, 0, 600, 10000))

def problem(b):
    """Return a reason if the record is inconsistent, otherwise None."""
    lost = b["lost"]["final_test"]
    reached = b["units_into_final_test"]
    if lost > reached:
        return f"{lost} final-test scraps logged, but only {reached} units reached final test"
    return None

@app.get("/batches")
def batches():
    """List every production batch with chips lost at each step and whether its record is usable. Invented data."""
    out = []
    for b in BATCHES:
        reason = problem(b)
        out.append({**b, "status": "excluded" if reason else "usable", "note": reason})
    return {"batches": out}

@app.get("/data-quality")
def data_quality():
    """Report batches whose records are inconsistent and are left out of the averages. Invented data."""
    flagged = []
    for b in BATCHES:
        reason = problem(b)
        if reason:
            flagged.append({"batch_id": b["batch_id"], "machine": b["machine"], "reason": reason})
    return {"batches_checked": len(BATCHES), "batches_flagged": len(flagged), "flagged": flagged}

@app.get("/machines/loss-profile")
def loss_profile():
    """Average chips lost per batch at each step for machines B1 and B2, measured over usable batches only. Excluded batches are listed with the reason. The numbers can be passed straight into the cost pricing tool. Invented data."""
    machines = []
    for m in ["B1", "B2"]:
        mine = [b for b in BATCHES if b["machine"] == m]
        usable = [b for b in mine if problem(b) is None]
        excluded = [{"batch_id": b["batch_id"], "reason": problem(b)} for b in mine if problem(b)]
        avg = {s: round(sum(b["lost"][s] for b in usable) / len(usable)) for s in STEPS}
        machines.append({
            "machine": m,
            "usable_batches": len(usable),
            "excluded_batches": excluded,
            "avg_lost_per_batch": avg,
            "loss_rate_pct": round(100 * sum(avg.values()) / 10000, 1),
            "label": "measured, usable batches only",
        })
    return {"units_per_batch": 10000, "machines": machines}
# Invented stoppage record: B2 was stopped for 6 hours on a Tuesday, then restarted.
DOWNTIME = {"B2": {"day": "Tuesday", "stoppage_hours": 6, "restart_batches": [455, 457]}}

@app.get("/downtime-impact/{machine}")
def downtime_impact(machine: str):
    """Compare chips lost in the batches run right after a machine's stoppage with that machine's other usable batches. Returns stoppage hours, the batches compared, and the excess chips lost per step, which can be passed straight into the cost pricing tool. This is an association, not a proven cause. Invented data."""
    m = machine.upper()
    if m not in DOWNTIME:
        raise HTTPException(status_code=404, detail=f"No stoppage record for machine {machine}.")
    info = DOWNTIME[m]
    mine = [b for b in BATCHES if b["machine"] == m and problem(b) is None]
    after = [b for b in mine if b["batch_id"] in info["restart_batches"]]
    normal = [b for b in mine if b["batch_id"] not in info["restart_batches"]]
    excess = {}
    for s in STEPS:
        normal_avg = sum(b["lost"][s] for b in normal) / len(normal)
        excess[s] = round(sum(b["lost"][s] - normal_avg for b in after))
    return {
        "machine": m,
        "stoppage_day": info["day"],
        "stoppage_hours": info["stoppage_hours"],
        "batches_after_restart": [b["batch_id"] for b in after],
        "batches_compared_against": len(normal),
        "excess_chips_lost": excess,
        "label": "measured difference; association, not proven cause",
        "note": "Invented data. The comparison does not show the stoppage caused the extra losses.",
    }