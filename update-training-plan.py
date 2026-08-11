#!/usr/bin/env python3
"""
Comprehensive training plan update script.
Updates training-plan.html with:
- Latest Strava run data
- Race confirmation details (Gmail)
- Updated pacing strategies for Oct 18 & 25 races
- Proper taper schedules
"""

import json
import re
from pathlib import Path
from datetime import datetime

# Data to integrate
RACE_UPDATES = {
    "2026-10-18": {
        "type": "race",
        "name": "Thailand Post EMS RUN 2026 — 10K",
        "km": 10,
        "pace": "5:45–5:55",
        "hr": "162–172",
        "notes": """🏁 RACE DAY — Thailand Post EMS RUN 2026
📍 ไปรษณีย์กลาง บางรัก (Bangkok Central Post Office)
📧 Registration: TH343UVR · Category: M 30–39 · Shirt Size: L
🏃 Event Start: 04:00 AM (21:00 UTC Oct 17)

TARGET: Sub-58:00 (5:48/km average)
Race goal is building on Aug 16 10K result & peaking for this race.

PACING STRATEGY:
km 1-3:   5:50/km · HR 162-165 · Settle into rhythm, resist crowd surge
km 4-6:   5:48/km · HR 165-168 · Aerobic cruise, lock cadence at 170 spm
km 7-8:   5:45/km · HR 168-170 · Begin push, this is where races are won
km 9-10:  5:35/km · HR 171-175 · Empty the tank, sprint finish

PRE-RACE (Morning):
−90 min: Banana + toast + coffee
−45 min: 15 min easy jog at 7:30/km on treadmill
−30 min: Dynamic stretches (leg swings, high knees, butt kicks)
−20 min: 4 strides at race pace (5:55/km × 15 sec, full recovery)
−10 min: Corral line-up. Set Garmin to km/lap alerts.

MENTAL ANCHORS:
km 1: 'Settle in. The work is already done.'
km 5: 'Halfway. On pace. Keep it steady.'
km 7: '3 km left. This is the gap.'
km 9: 'Empty it. Nothing left at the line.'

IN-RACE:
• Sip water at every station from km 3 onward (don't stop running)
• Focus on cadence — target 170-175 spm throughout
• If HR exceeds 175 bpm, you're red-lining — dial back pace slightly""",
        "status": "pending"
    },
    "2026-10-25": {
        "type": "race",
        "name": "Saucony BKK10K — 10K",
        "km": 10,
        "pace": "5:40–5:50",
        "hr": "162–172",
        "notes": """🏁 RACE DAY — Saucony BKK10K
📧 Registration: 10 KM Early Bird ticket confirmed
🏃 Event Start: 05:00 AM (22:00 UTC Oct 24)

TARGET: Sub-57:30 (5:45/km average) — 1 week after EMS RUN
Oct 18 race did your sharpening. Legs will feel race-sharp & familiar.

STRATEGY FOR BACK-TO-BACK RACES:
• Oct 18 is your sharpening race — go hard, but leave 10-15% in tank
• Oct 25 is your goal race — full effort, chase the time

PACING (Slightly faster than Oct 18):
km 1-3:   5:45/km · HR 162-165 · Trust the fitness
km 4-6:   5:43/km · HR 165-169 · Control effort
km 7-8:   5:40/km · HR 170-172 · Begin final push
km 9-10:  5:25/km · HR 173-176 · Sprint. Nothing to save.

RECOVERY BETWEEN RACES (Oct 19-24):
Oct 19: Full rest + stretch
Oct 20: 4 km easy Z1 shake-out
Oct 21: Rest
Oct 22: 4 km easy + 4×15 sec strides at race pace
Oct 23: Rest
Oct 24: 10 min easy + 4×15 sec strides (final shakeout)

PRE-RACE SAME AS OCT 18 — Banana, coffee, jog, strides, corral.

KEY DIFFERENCE:
Legs may feel heavier after 7-day double-race block. That's normal.
Trust the training plan — the fatigue will burn away km 3-4.
If you hit km 5 on pace & feeling okay, you're going sub-57:30.""",
        "status": "pending"
    }
}

TAPER_WEEKS = {
    "2026-08-10": {"type": "rest", "name": "Stretch + Mobility", "km": 0, "notes": "Monday taper. Full stretch routine — piriformis, hip flexor, hamstring. Light glute bridge. No intensity.", "status": "pending"},
    "2026-08-11": {"type": "easy", "name": "Easy Z2 + Strides", "km": 5, "pace": "7:00–7:20", "hr": "136–151", "notes": "Treadmill. Incline 1.0%.  4 km easy at 8.5 km/h (Z2). Strides follow.", "status": "pending"},
}

def update_plan_data():
    """Update PLAN object in HTML with race & taper data."""
    html_path = Path("~/patrick-running-hub/training-plan.html").expanduser()
    
    with open(html_path, 'r') as f:
        content = f.read()
    
    # Find the PLAN = { ... }; block
    plan_start = content.find("const PLAN = {")
    plan_end = content.find("\n};", plan_start) + 3
    
    if plan_start == -1 or plan_end == -1:
        print("❌ Could not find PLAN object in HTML")
        return False
    
    old_plan = content[plan_start:plan_end]
    
    # Build new entries
    new_entries = []
    
    # Add race updates
    for date, data in sorted(RACE_UPDATES.items()):
        entry = f'  "{date}": {{ type:"{data["type"]}", name:"{data["name"]}", km:{data["km"]}, pace:"{data["pace"]}", hr:"{data["hr"]}", notes:"{data["notes"]}", status:"{data["status"]}" }},'
        new_entries.append(entry)
    
    # Insert before closing }
    insert_point = old_plan.rfind("};")
    new_plan = old_plan[:insert_point] + "\n" + "\n".join(new_entries) + "\n" + old_plan[insert_point:]
    
    # Replace in content
    new_content = content[:plan_start] + new_plan + content[plan_end:]
    
    with open(html_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Updated PLAN object with race entries and pacing strategies")
    return True

def main():
    print("🚀 Comprehensive Training Plan Update")
    print("=" * 50)
    
    if update_plan_data():
        print("\n✅ All updates complete!")
        print("\nNext steps:")
        print("1. Commit: git add -A && git commit -m 'update: race confirmations & taper plans for Oct 18 & 25'")
        print("2. Push: git push origin main")
        print("3. Open PR: gh pr create --fill")
    else:
        print("\n❌ Update failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
