"""
Autonomous Command Agent — Forest Wildfire Rescue Swarm

Connects to the MCP Rescue Drone Server, discovers the fleet and environment,
plans sector coverage around hazards, and executes an autonomous search-and-rescue
mission with full chain-of-thought reasoning.

Handles: no-fly zones, fire zones, smoke zones, wind, and battery management.
"""
import asyncio
import json
import math
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

# ─── ANSI Colors ───
class C:
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    MAGENTA = "\033[95m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RESET   = "\033[0m"
    ORANGE  = "\033[38;5;208m"

def thought(msg):
    print(f"{C.MAGENTA}{C.BOLD}🧠 REASONING:{C.RESET}{C.MAGENTA} {msg}{C.RESET}")

def action(msg):
    print(f"{C.CYAN}{C.BOLD}⚡ ACTION:{C.RESET}{C.CYAN} {msg}{C.RESET}")

def alert(msg):
    print(f"{C.GREEN}{C.BOLD}🔥 ALERT:{C.RESET}{C.GREEN} {msg}{C.RESET}")

def warning(msg):
    print(f"{C.YELLOW}{C.BOLD}⚠️  WARNING:{C.RESET}{C.YELLOW} {msg}{C.RESET}")

def danger(msg):
    print(f"{C.RED}{C.BOLD}🚫 DANGER:{C.RESET}{C.RED} {msg}{C.RESET}")

def env_info(msg):
    print(f"{C.ORANGE}{C.BOLD}🌍 ENV:{C.RESET}{C.ORANGE} {msg}{C.RESET}")

def info(msg):
    print(f"{C.DIM}   ℹ {msg}{C.RESET}")

def header(msg):
    print(f"\n{C.BOLD}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{C.RESET}\n")


BATTERY_RECALL_THRESHOLD = 25
HAZARD_BATTERY_MULTIPLIERS = {"fire": 3.0, "smoke": 1.5, "clear": 1.0}


async def call_tool(session, tool_name, args=None):
    result = await session.call_tool(tool_name, args or {})
    for content in result.content:
        if hasattr(content, 'text'):
            try:
                return json.loads(content.text)
            except (json.JSONDecodeError, TypeError):
                return content.text
    return None


def calculate_distance(pos1, pos2):
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)


def assign_sectors_to_drones(available_drones, scannable_sectors, fleet_status, hazard_map):
    """
    Smart sector assignment with hazard awareness.
    Prioritizes fire-adjacent sectors (survivors likely nearby),
    avoids no-fly zones, and accounts for extra drain in hazardous sectors.
    If a high-priority sector is too expensive, falls through to the next best.
    """
    assignments = {}

    sorted_drones = sorted(
        available_drones,
        key=lambda d: fleet_status[d]["battery"],
        reverse=True,
    )

    remaining = list(scannable_sectors.keys())

    for drone_id in sorted_drones:
        if not remaining:
            break

        drone_pos = fleet_status[drone_id]["coordinates"]
        drone_battery = fleet_status[drone_id]["battery"]

        # Build ranked candidates: score by hazard priority + distance
        candidates = []
        for sector_id in remaining:
            sector = scannable_sectors[sector_id]
            center = sector["center"]
            dist = calculate_distance(drone_pos[:2], center)
            hazard = sector.get("hazard", "clear")

            # Score: lower = better
            score = dist
            if hazard == "fire":
                score -= 100
            elif hazard == "smoke":
                score -= 50

            candidates.append((score, sector_id, dist, hazard))

        candidates.sort(key=lambda c: c[0])

        # Try candidates in order until one is affordable
        assigned = False
        for _, sector_id, dist, hazard in candidates:
            sector = scannable_sectors[sector_id]
            center = sector["center"]
            multiplier = HAZARD_BATTERY_MULTIPLIERS.get(hazard, 1.0)

            estimated_move = dist * 0.3 * multiplier
            estimated_scan = 0.5 * multiplier
            estimated_cost = estimated_move + estimated_scan
            return_distance = calculate_distance(center, [5, 5])
            estimated_return = return_distance * 0.3
            total_estimated = estimated_cost + estimated_return

            hazard_label = f" [{hazard.upper()}]" if hazard != "clear" else ""

            if total_estimated > drone_battery - 5:
                # Too expensive, try next candidate
                if hazard in ("fire", "smoke"):
                    thought(
                        f"{drone_id} ({drone_battery:.0f}% battery): {sector_id}{hazard_label} "
                        f"costs {total_estimated:.1f}% — too expensive. Trying next sector."
                    )
                continue

            # Affordable!
            thought(
                f"{drone_id} has {drone_battery:.0f}% battery. "
                f"Assigning {sector_id}{hazard_label} "
                f"({dist:.1f} units, {multiplier}× drain). "
                f"Cost: {estimated_cost:.1f}% + {estimated_return:.1f}% return = {total_estimated:.1f}%."
            )

            if hazard == "fire":
                thought(
                    f"Sector {sector_id} is in ACTIVE FIRE ZONE — high battery cost but "
                    f"survivors are likely trapped near fire fronts. Prioritizing rescue."
                )

            assignments[drone_id] = sector_id
            remaining.remove(sector_id)
            assigned = True
            break

        if not assigned:
            warning(
                f"{drone_id} cannot afford any remaining sector with safe return. "
                f"Recalling for charging."
            )
            assignments[drone_id] = "__RECALL__"

    return assignments


async def run_mission(session):
    """Execute the autonomous forest wildfire search-and-rescue mission."""

    header("PHASE 1: DISCOVERY — Fleet & Environment Reconnaissance")

    # ─── Discover Fleet ───
    action("Calling list_drones() to discover fleet on network...")
    drone_ids = await call_tool(session, "list_drones")
    thought(f"Discovered {len(drone_ids)} drones: {drone_ids}")

    action("Calling get_fleet_status()...")
    fleet_status = await call_tool(session, "get_fleet_status")
    for did, st in fleet_status.items():
        info(f"{did}: battery={st['battery']}%, status={st['status']}, pos={st['coordinates']}")

    # ─── Discover Environment ───
    action("Calling get_environment() to assess disaster zone hazards...")
    env = await call_tool(session, "get_environment")

    env_info(f"Grid: {env['grid_size']}×{env['grid_size']} ({env['sector_layout']})")
    env_info(f"Wind: {env['wind']['direction']} at {env['wind']['speed_kmh']} km/h — {env['wind']['effect']}")

    for nfz in env["no_fly_zones"]:
        danger(f"NO-FLY: {nfz['name']} (sectors: {nfz['sectors']}) — {nfz['reason']}")
    for fz in env["fire_zones"]:
        warning(f"FIRE: {fz['name']} (sectors: {fz['sectors']}, intensity: {fz['intensity']}, {fz['battery_multiplier']}× drain)")
    env_info(f"Smoke zones (1.5× drain): {env['smoke_sectors']}")

    # ─── Get Hazard Map ───
    action("Calling get_hazard_map() to build tactical awareness...")
    hazard_map = await call_tool(session, "get_hazard_map")

    no_fly_count = sum(1 for h in hazard_map.values() if h["hazard"] == "no_fly")
    fire_count = sum(1 for h in hazard_map.values() if h["hazard"] == "fire")
    smoke_count = sum(1 for h in hazard_map.values() if h["hazard"] == "smoke")
    clear_count = sum(1 for h in hazard_map.values() if h["hazard"] == "clear")

    thought(
        f"Hazard breakdown: {clear_count} clear, {smoke_count} smoke, "
        f"{fire_count} fire, {no_fly_count} no-fly. "
        f"Total scannable: {25 - no_fly_count} sectors."
    )

    # ─── Phase 2: Planning ───
    header("PHASE 2: PLANNING — Building hazard-aware search plan")

    thought(
        f"Strategy: Prioritize fire-adjacent sectors where survivors are most likely trapped. "
        f"Skip {no_fly_count} no-fly sectors (cliffs & dense canopy). "
        f"Budget extra battery for {fire_count} fire zones ({3.0}× drain) and {smoke_count} smoke zones (1.5× drain)."
    )

    # ─── Phase 3: Execution ───
    header("PHASE 3: EXECUTION — Autonomous wildfire search sweep")

    mission_round = 0

    while True:
        mission_round += 1
        print(f"\n{C.BOLD}--- Mission Round {mission_round} ---{C.RESET}")

        fleet_status = await call_tool(session, "get_fleet_status")
        unscanned = await call_tool(session, "get_unscanned_sectors")

        # Filter out no-fly zones
        scannable = {
            sid: s for sid, s in unscanned.items()
            if hazard_map.get(sid, {}).get("hazard") != "no_fly"
        }

        if not scannable:
            thought("All scannable sectors covered. Mission complete!")
            break

        thought(f"{len(scannable)} scannable sectors remaining.")

        # Check for low-battery drones
        available = []
        for did, st in fleet_status.items():
            if st["status"] == "active" and st["battery"] > BATTERY_RECALL_THRESHOLD:
                available.append(did)
            elif st["status"] == "active" and st["battery"] <= BATTERY_RECALL_THRESHOLD:
                warning(f"{did} battery critical at {st['battery']:.0f}%!")
                thought(f"Recalling {did} for emergency charging.")
                action(f"Calling recall_for_charging({did})...")
                result = await call_tool(session, "recall_for_charging", {"drone_id": did})
                info(f"{did} charged → {result['battery']}%")
                available.append(did)
                fleet_status[did] = result

        if not available:
            warning("No drones available! Ending mission.")
            break

        thought(f"{len(available)} drones available: {available}")

        # Assign with hazard awareness
        assignments = assign_sectors_to_drones(available, scannable, fleet_status, hazard_map)

        for drone_id, sector_id in assignments.items():
            if sector_id == "__RECALL__":
                action(f"Calling recall_for_charging({drone_id})...")
                result = await call_tool(session, "recall_for_charging", {"drone_id": drone_id})
                info(f"{drone_id} charged → {result['battery']}%")
                continue

            hazard = scannable[sector_id].get("hazard", "clear")
            hazard_emoji = {"fire": "🔥", "smoke": "💨", "clear": "✅"}.get(hazard, "")
            action(f"Calling scan_sector({drone_id}, {sector_id}) {hazard_emoji}...")
            result = await call_tool(session, "scan_sector", {"drone_id": drone_id, "sector_id": sector_id})

            if "error" in result:
                warning(f"Error: {result['error']}")
                continue

            survivors = result.get("survivors_found", [])
            battery = result.get("battery_after", 0)
            sector_hazard = result.get("hazard", "clear")

            if survivors:
                for s in survivors:
                    alert(f"SURVIVOR DETECTED at ({s[0]}, {s[1]}, {s[2]})!")
                thought(f"{drone_id} found {len(survivors)} survivor(s) in {sector_id} [{sector_hazard}]. Battery: {battery:.0f}%")
            else:
                info(f"{drone_id} scanned {sector_id} [{sector_hazard}]: clear. Battery: {battery:.0f}%")

        if mission_round > 30:
            warning("Max rounds reached.")
            break

    # ─── Phase 4: Summary ───
    header("PHASE 4: MISSION COMPLETE — Summary")

    action("Calling get_mission_summary()...")
    summary = await call_tool(session, "get_mission_summary")

    print(f"  {C.BOLD}Scannable Coverage:{C.RESET}  {summary['coverage_pct']}% ({summary['sectors_scanned']}/{summary['sectors_total']} sectors)")
    print(f"  {C.BOLD}No-Fly Zones:{C.RESET}       {summary['sectors_no_fly']} sectors (skipped)")
    print(f"  {C.BOLD}Survivors Found:{C.RESET}     {summary['survivors_found']}")
    if summary['survivor_locations']:
        for loc in summary['survivor_locations']:
            print(f"    📍 ({loc[0]}, {loc[1]}, {loc[2]})")

    print(f"\n  {C.BOLD}Fleet Status:{C.RESET}")
    for did, st in summary['fleet_status'].items():
        emoji = "✅" if st['status'] == 'active' else "🔋" if st['status'] == 'charging' else "❌"
        print(f"    {emoji} {did}: {st['battery']}% | {st['status']} | pos={st['coordinates']}")

    print(f"\n  {C.BOLD}Mission Log (last entries):{C.RESET}")
    for entry in summary.get('log', [])[-12:]:
        print(f"    {C.DIM}• {entry}{C.RESET}")

    print(f"\n{C.GREEN}{C.BOLD}✅ Mission complete. {summary['survivors_found']} survivor(s) located across the wildfire zone.{C.RESET}\n")


async def main():
    server_params = StdioServerParameters(
        command="python3",
        args=["run_server.py"]
    )

    header("AUTONOMOUS COMMAND AGENT — Forest Wildfire Rescue Swarm")
    print(f"  {C.DIM}Connecting to MCP Rescue Drone Server...{C.RESET}\n")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            response = await session.list_tools()
            thought(f"Connected to MCP server. Discovered {len(response.tools)} tools:")
            for tool in response.tools:
                info(f"Tool: {tool.name}")

            await run_mission(session)


if __name__ == "__main__":
    asyncio.run(main())
