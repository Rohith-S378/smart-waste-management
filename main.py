"""
main.py — Menu-driven console application
Run with: python main.py
"""
import os
import sys
from models import Bin, Zone, Vehicle, Driver, SimulationState
from simulation.simulator import WasteSimulator
from simulation.events import generate_sample_bins
from utils.helpers import load_json, new_id
from config.settings import FILL_THRESHOLD, FUEL_PRICE


# ── Colours ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def clear():
    os.system('cls' if os.name=='nt' else 'clear')


def header(title: str):
    print(f"\n{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{CYAN}{'─'*60}{RESET}")


def pause():
    input(f"\n{YELLOW}[Press ENTER to continue]{RESET}")


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def bootstrap() -> WasteSimulator:
    state = SimulationState()
    raw = load_json("data/sample_data.json", {})
    for zd in raw.get("zones", []):   state.zones[zd["zone_name"]] = Zone.from_dict(zd)
    for vd in raw.get("vehicles", []): state.vehicles[vd["vehicle_id"]] = Vehicle.from_dict(vd)
    for dd in raw.get("drivers", []):  state.drivers[dd["driver_id"]] = Driver.from_dict(dd)
    sim = WasteSimulator(state)
    if not state.bins:
        for b in generate_sample_bins(list(state.zones.keys()), 4):
            sim.add_bin(b)
    return sim


# ── Menu Handlers ─────────────────────────────────────────────────────────────

def menu_critical_bins(sim):
    header("IDENTIFY CRITICAL BINS")
    bins = sim.identify_critical()
    if not bins:
        print(f"{GREEN}✓ No critical bins at this time.{RESET}")
    else:
        print(f"{'BIN ID':<14} {'ZONE':<22} {'WASTE':<12} {'FILL%':>6}  {'KG':>7}  PRIORITY")
        print("─"*72)
        for b in bins:
            col = RED if b.overflow else YELLOW
            print(f"{col}{b.bin_id:<14} {b.zone_name:<22} {b.waste_type:<12} {b.fill_level:>5.1f}%  {b.load_kg:>6.1f}  P{b.priority}{RESET}")
    pause()


def menu_generate_schedule(sim):
    header("GENERATE COLLECTION SCHEDULE")
    schedule = sim.generate_schedule()
    if not schedule:
        print(f"{YELLOW}No critical bins to schedule.{RESET}")
        pause(); return
    print(f"{'BIN':<14} {'VEHICLE':<10} {'DRIVER':<10} {'KG':>7} {'KM':>6}  STATUS")
    print("─"*68)
    for t in schedule:
        col = RED if t.get('emergency') else RESET
        print(f"{col}{t['bin_id']:<14} {str(t['vehicle_id']):<10} {str(t['driver_id']):<10} {t['kg']:>6.1f} {t['distance_km']:>5.1f}  {t['status']}{RESET}")
    pause()


def menu_route_plans(sim):
    header("OPTIMISED ROUTE PLANS")
    routes = sim.get_route_plans()
    if not routes:
        print(f"{YELLOW}No routes. Generate a schedule first.{RESET}")
        pause(); return
    for r in routes:
        print(f"\n{CYAN}Vehicle: {r['vehicle_id']}  Driver: {r['driver_id']}{RESET}")
        print(f"  Route : {' → '.join(r['path'])}")
        print(f"  Total : {r['total_km']} km  |  {r['total_kg']} kg  |  {r['fuel_needed']}L  |  ₹{r['fuel_cost']}")
    pause()


def menu_simulate(sim):
    header("RUN COLLECTION SIMULATION")
    if not sim.state.schedule:
        print(f"{YELLOW}Generating schedule first…{RESET}")
        sim.generate_schedule()
    results = sim.simulate_collection()
    if not results:
        print(f"{RED}No collections performed. Check vehicles and bin states.{RESET}")
        pause(); return
    print(f"\n{GREEN}✓ {len(results)} bins collected{RESET}\n")
    for l in results:
        print(f"  {l['bin_id']} → {l['vehicle_id']} | {l['kg_collected']:.1f}kg | {l['distance_km']}km | {l['fuel_used']:.2f}L")
    cost = sim.cost_report()
    print(f"\n{CYAN}{'─'*40}{RESET}")
    print(f"  Fuel: {cost['fuel_litres']}L  ₹{cost['fuel_cost']}")
    print(f"  Staff: ₹{cost['staff_cost']}")
    print(f"  {BOLD}TOTAL: ₹{cost['total_cost']}{RESET}")
    pause()


def menu_emergency(sim):
    header("EMERGENCY OVERFLOW HANDLER")
    result = sim.trigger_emergency(None if True else "")
    if "error" in result:
        print(f"{RED}✗ {result['error']}{RESET}")
    else:
        print(f"{RED}🚨 {result['message']}{RESET}")
        t = result['task']
        print(f"   Bin: {t['bin_id']}  Vehicle: {t['vehicle_id']}  Dist: {t['distance_km']}km")
    pause()


def menu_cost_report(sim):
    header("FUEL & COST REPORT")
    r = sim.cost_report()
    print(f"  Fuel consumed  : {r['fuel_litres']} L")
    print(f"  Fuel cost      : ₹{r['fuel_cost']}")
    print(f"  Staff cost     : ₹{r['staff_cost']}")
    print(f"  {BOLD}Total cost      : ₹{r['total_cost']}{RESET}")
    print(f"  Collections    : {r['collections']}")
    print(f"  Kg collected   : {r['kg_collected']} kg")
    pause()


def menu_recycling_report(sim):
    header("RECYCLING & WASTE REPORT")
    r = sim.recycling_report()
    print(f"  Total waste    : {r['total_kg']} kg")
    print(f"  Recyclable     : {GREEN}{r['recyclable_kg']} kg{RESET}")
    print(f"  Landfill       : {RED}{r['landfill_kg']} kg{RESET}")
    print(f"  Efficiency     : {BOLD}{r['recycling_pct']}%{RESET}")
    print("\n  By type:")
    for wt, kg in r.get('by_type', {}).items():
        print(f"    {wt:<12}: {kg:.1f} kg")
    pause()


def menu_zone_report(sim):
    header("ZONE-WISE REPORT")
    for z in sim.zone_report():
        bar = '█' * int(z['avg_fill']/10) + '░' * (10 - int(z['avg_fill']/10))
        col = YELLOW if z['avg_fill'] >= 70 else GREEN
        print(f"  {col}{z['zone']:<24}{RESET} [{bar}] {z['avg_fill']}%  "
              f"bins:{z['total_bins']}  collected:{z['collected_today']}  critical:{z['critical_bins']}")
    pause()


def menu_advance_day(sim):
    header("ADVANCE TO NEXT DAY")
    sim.advance_day()
    print(f"{GREEN}✓ Advanced to Day {sim.state.day}. Bin fill levels updated.{RESET}")
    pause()


# ── Main Menu ─────────────────────────────────────────────────────────────────

MENU = [
    ("Identify Critical Bins",      menu_critical_bins),
    ("Generate Collection Schedule",menu_generate_schedule),
    ("Optimised Route Plans",       menu_route_plans),
    ("Run Collection Simulation",   menu_simulate),
    ("Trigger Emergency Override",  menu_emergency),
    ("Fuel & Cost Report",          menu_cost_report),
    ("Recycling Report",            menu_recycling_report),
    ("Zone-wise Report",            menu_zone_report),
    ("Advance Day",                 menu_advance_day),
]


def main():
    sim = bootstrap()
    while True:
        clear()
        print(f"\n{BOLD}{CYAN}  ╔══════════════════════════════════════════╗")
        print(f"  ║   SMART WASTE MANAGEMENT SYSTEM  v1.0   ║")
        print(f"  ║   Day {sim.state.day:>3}  |  {sum(1 for b in sim.state.bins.values() if b.is_critical()):>2} critical bins      ║")
        print(f"  ╚══════════════════════════════════════════╝{RESET}\n")
        for i,(label,_) in enumerate(MENU, 1):
            print(f"  {CYAN}{i:>2}.{RESET} {label}")
        print(f"\n   {RED}0.{RESET} Exit\n")
        choice = input(f"  {BOLD}Select >{RESET} ").strip()
        if choice == '0':
            print(f"\n{GREEN}Goodbye!{RESET}\n")
            sys.exit(0)
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(MENU):
                MENU[idx][1](sim)
        except (ValueError, IndexError):
            pass


if __name__ == "__main__":
    main()
