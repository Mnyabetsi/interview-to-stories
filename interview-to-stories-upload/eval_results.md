# Evaluation results (2026-10-16)

Model `claude-opus-5-5`, effort `medium`, output language English.

| Sample | Stories | Avg. quality | Quotes verified | Expected reqs found | Found incl. partial | Stories with ≥2 AC | Open questions | Time | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 01_building_permit_portal | 19 | 96 | 100% of 59 | 94% | 100% | 95% | 15 | 135s | $0.34 |
| 02_school_absence_reporting | 20 | 96 | 100% of 55 | 100% | 100% | 100% | 15 | 122s | $0.31 |
| 03_sozialdienst_terminbuchung | 12 | 99 | 100% of 35 | 100% | 100% | 100% | 12 | 131s | $0.24 |
| **Total / average** | 51 | 97 | 100% of 149 | 47/48 (98%) | 100% | 98% | 14.0 | 129s | $0.30 |

## Expected items not fully found

Review these by hand. The reviewer can be wrong in both directions.

**01_building_permit_portal**
- `G1` PARTIAL: Success: most applications arrive online, fewer completeness letters (target: half) and fewer status phone calls.  
  _Halving completeness letters and reducing status calls are captured, but the goal that most applications arrive online is only tracked, not stated as a target._

**02_school_absence_reporting**: all expected items found.

**03_sozialdienst_terminbuchung**: all expected items found.


Coverage review cost: $0.17. Full verdicts: `samples/outputs/*.coverage.json`.
