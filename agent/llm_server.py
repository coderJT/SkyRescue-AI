import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage

app = FastAPI(title="Rescue Drone LLM Brain", description="Decision engine powered by LangChain and Mistral AI")

# Allow the HTML file to make fetch requests to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DroneState(BaseModel):
    drone_id: str
    battery: float
    position: list[float]
    other_drones: list[dict] # {id, pos, state, target_sector}
    unscanned_sectors: dict
    hazard_map: dict

class BatchDroneState(BaseModel):
    id: str
    battery: float
    pos: list[float]

class BatchRequest(BaseModel):
    idle_drones: list[BatchDroneState]
    active_drones: list[dict]  # {id, pos, state, target_sector}
    unscanned_sectors: dict
    hazard_map: dict

# Initialize LLM only if API key is present
api_key = os.environ.get("MISTRAL_API_KEY")
llm = None
if api_key:
    llm = ChatMistralAI(model="mistral-large-latest", mistral_api_key=api_key)

@app.get("/health")
async def health_check():
    return {"status": "ok", "llm_connected": llm is not None}

@app.post("/reset")
async def reset_brain():
    from simulation.simulation_engine import SimulationEngine
    SimulationEngine().reset_mission()
    return {"status": "reset"}

@app.post("/decide")
async def decide_next_sector(state: DroneState):
    if not llm:
        raise HTTPException(status_code=500, detail="MISTRAL_API_KEY not set on server")

    if not state.unscanned_sectors:
        return {"decision": "__RECALL__", "reasoning": "No scannable sectors available. All areas covered or timed out."}

    # Build prompt context with candidates provided by the browser (the source of truth)
    prompt = f"""
You are the high-level swarm commander for {state.drone_id} in a critical SAR mission.
Current Battery: {state.battery:.1f}%
Current Position [x, y, z]: {state.position}
Base Station: [5, 0, 5]

SWARM CONTEXT (Teammates):
"""
    for d in state.other_drones:
        ts = d.get('target_sector') or 'None'
        prompt += f"- {d['id']}: Position {d['pos']} | State: {d['state']} | Target: {ts}\n"

    prompt += """
TACTICAL RECOMMENDATIONS (Pre-selected by your Tactical Specialist):
DANGER: Survivors in FIRE die in 60s, SMOKE in 180s, others in 600s.
"""
    for sid, s in state.unscanned_sectors.items():
        prompt += f"- {sid}: {s['hazard']} | Time Remaining: {s['time_left']}s | Distance: {s['distance']} units\n"

    prompt += """
COMMANDERS GOAL:
1. Review the recommendations. 
2. Choose the BEST sector from the list.
3. DEADLINE PRIORITY: Prioritize sectors with the LOWEST 'Time Remaining'.
4. STRATEGIC SEPARATION: Do NOT pick a sector if another drone is already targeting it.

REQUIRED JSON FORMAT:
{
    "decision": "SectorID",
    "reasoning": "Explain your choice based on survival urgency (e.g., 'Choosing S3_2: critical fire area with only 15s remaining')."
}
"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a high-level rescue commander AI. You output ONLY valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        # Parse output
        import json
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        result = json.loads(content)
        # Final validation
        if result.get("decision") not in state.unscanned_sectors and result.get("decision") != "__RECALL__":
             # Fallback to the first recommended sector
             first_sid = list(state.unscanned_sectors.keys())[0]
             result["decision"] = first_sid
             result["reasoning"] = "(Validation Fallback) " + result.get("reasoning", "")
             
        return result
    except Exception as e:
        print(f"Error calling LLM: {e}")
        first_sid = list(state.unscanned_sectors.keys())[0] if state.unscanned_sectors else "__RECALL__"
        return {"decision": first_sid, "reasoning": f"Emergency fallback: {str(e)}"}

@app.post("/decide_batch")
async def decide_batch(req: BatchRequest):
    if not llm:
        raise HTTPException(status_code=500, detail="MISTRAL_API_KEY not set on server")

    if not req.unscanned_sectors:
        return {"assignments": {d.id: "__RECALL__" for d in req.idle_drones}, "reasoning": "No scannable sectors remain."}

    # Build multi-drone coordination prompt
    prompt = f"""
You are the GLOBAL SWARM COMMANDER for a critical Search & Rescue mission.
You must assign targets to {len(req.idle_drones)} IDLE drones simultaneously.

IDLE DRONES (Waiting for Orders):
"""
    for d in req.idle_drones:
        prompt += f"- {d.id}: Battery {d.battery:.1f}% | Position {d.pos}\n"

    prompt += "\nACTIVE TEAMMATES (Already busy):\n"
    for d in req.active_drones:
        ts = d.get('target_sector') or 'None'
        prompt += f"- {d['id']}: Position {d['pos']} | Target: {ts}\n"

    prompt += """
TACTICAL CANDIDATES:
DANGER: Survivors in FIRE die in 60s, SMOKE in 180s, others in 600s.
"""
    for sid, s in req.unscanned_sectors.items():
        prompt += f"- {sid}: {s['hazard']} | Time Remaining: {s['time_left']}s | Distance: {s['distance']} units\n"

    prompt += """
COMMANDERS COORDINATION GOAL:
1. Assign EXACTLY ONE unique sector to each IDLE drone.
2. GLOBAL OPTIMIZATION: Ensure the CLOSEST drone is assigned to the most critical (low time) fire areas.
3. CONFLICT AVOIDANCE: Do NOT assign a sector that is already being targeted by an ACTIVE teammate.
4. RECALL: If a drone has low battery or no good targets remain, assign "__RECALL__".

REQUIRED JSON FORMAT:
{
    "assignments": {
        "drone_1": "S2_3",
        "drone_3": "__RECALL__"
    },
    "reasoning": "Coordinated batch assignment: drone_1 sent to nearby fire front (S2_3), drone_3 recalled for charging."
}
"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a swarm coordination AI. You output ONLY valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        import json
        content = response.content.strip()
        if content.startswith("```json"): content = content[7:-3]
        elif content.startswith("```"): content = content[3:-3]
        
        result = json.loads(content)
        # Final safety check: ensure every idle drone has an entry
        for d in req.idle_drones:
            if d.id not in result.get("assignments", {}):
                result.setdefault("assignments", {})[d.id] = "__RECALL__"
                
        return result
    except Exception as e:
        print(f"Error calling LLM for batch: {e}")
        # Emergency fallback: Assign first available sector to first drone, others recall
        fallback = {"assignments": {}, "reasoning": f"Emergency batch fallback: {str(e)}"}
        sids = list(req.unscanned_sectors.keys())
        for i, d in enumerate(req.idle_drones):
            fallback["assignments"][d.id] = sids[i] if i < len(sids) else "__RECALL__"
        return fallback

if __name__ == "__main__":
    print("Starting LLM Server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
