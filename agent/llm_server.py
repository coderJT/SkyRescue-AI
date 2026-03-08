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
        response = llm.invoke([
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

if __name__ == "__main__":
    print("Starting LLM Server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
