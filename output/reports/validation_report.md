# 数据验证报告 (Data Validation Report)

Data source: NASA TM-2011-216142 extraction results
- missions.csv: 136 rows (135 flights + cancelled STS 51-E)
- weights.csv: 135 rows (Appendix A; 7 DOD missions have no published weights in the source document)

## 1. Internal consistency

## 2. External cross-check

Reference: Wikipedia List of Space Shuttle missions, 135 rows, joined 135

## 3. Summary

| Check | Severity | Issues |
|---|---|---|
| flight sequence 1..135 complete | error | 0 |
| launch dates monotonic by sequence | error | 0 |
| GMT liftoff date within +-1 day of printed launch date | error | 0 |
| landing date within +-1 day of wheels-stop GMT date | warning | 0 |
| duration matches GMT delta (<3 min) | error | 0 |
| orbiter flight numbering continuous | warning | 0 |
| cross-source: Mach-3 EOM weight (page vs Appendix A) | warning | 0 |
| cross-source: landing weight (page vs Appendix A) | warning | 0 |
| liftoff weight = orbiter+payload+ET+2xSRB (<5000 lbs) | warning | 3 |
| orbit-insert weight <= orbiter+payload | warning | 1 |
| Mach-3 EOM Xcg within 1000-1200 in | warning | 1 |
| landing Xcg within 1000-1200 in | warning | 0 |
| inclination range 28-62.5 deg | error | 0 |
| duration range 0-440 h | error | 0 |
| external: launch dates match Wikipedia | error | 0 |
| external: durations match Wikipedia (<1.05 h) | warning | 1 |
| external: orbiters match Wikipedia | error | 0 |
| external: crew sizes match Wikipedia | warning | 1 |

**Result: 0 errors, 5 warnings**

Known gaps inherent to the source document (not extraction errors):
- 7 DOD missions (STS 51-C, 51-J, 27, 28, 33, 36, 38) have no published weight data
- STS 51-L and STS-107 have no landing data (accidents)
- STS 51-E is a cancelled mission (crew info only)
- STS-125: Appendix A prints the orbiter+payload and orbit-insert weights transposed (231548/254376 lbs); corrected in data/weights-revised.xlsx - payload becomes 22828 lbs (~10.36 t), consistent with the Hubble servicing mission
- STS-5: Appendix A prints the Mach-3 EOM Xcg as 2094.8 in (leading-digit misprint, physically impossible); should be 1094.8 in per neighbouring flights and the landing value - corrected in data/weights-revised.xlsx

Documented disagreements between TM-2011-216142 and the Wikipedia reference list:
- STS-60 duration: document 8d07h (GMT-consistent, matches NASA mission archive) vs list page 7d06h - document kept
- STS-85 crew: document header '(7)' vs list '6' - document kept
- liftoff weight sum differs on STS-1, STS-30, STS-32 by 9-30k lbs (independent bookkeeping columns in the source)