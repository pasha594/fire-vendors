# Vendor name merge

Written by `pipeline/sources/merge_vendor_maps.py` (rules in its docstring), except the block between the
`manual` markers. The states' proposed vendor names and categories
(`config/states/<st>/vendor_map_additions.csv`) were folded into the shared `config/vendor_map.csv`, so one
company has one canonical vendor name across Utah, Ohio, California, Idaho and Texas. The site's vendor id
is a slug of the canonical name, so the names decide which payees add up to one vendor.

## Result

| | Rows |
| --- | --- |
| config/vendor_map.csv before | 5,172 |
| Proposed by OH | 6,186 |
| Proposed by CA | 2,752 |
| Proposed by ID | 488 |
| Proposed by TX | 200 |
| Distinct proposed keys | 9,595 |
| Keys already in config/vendor_map.csv | 3 |
| Left out because a vendor rule already says the same | 99 |
| Rows added | 9,493 |
| config/vendor_map.csv after | 14,665 |
| Canonical names covering more than one proposed form, or renamed | 1,269 |

## Rules

1. **Key conflicts.** A key already in `config/vendor_map.csv` keeps that row (hand-reviewed for Utah); the
   only state fix taken is a category for a row that was `unclassified`, for the same company. A key
   proposed by several states gets one row: the proposal that uses a name `config/vendor_map.csv` or a
   vendor rule already uses, then higher confidence, then higher spend.
2. **Canonical names.** Names are grouped when equal apart from case, punctuation, '&'/'and', legal
   suffixes, a leading 'The', parenthetical notes, common abbreviations and a trailing branch region
   ('of Ohio'); for governments, associations, unions, funds and health plans the region counts unless
   every name comes from one state. Canonical name: a `to_vendor` of `config/vendor_name_merges.csv`, else
   the name `config/vendor_map.csv` uses, else a vendor rule's name, else the proposed form with the most
   spend, cleaned (no legal suffix or lower-case note, small words in lower case). Judgment calls are rows
   of `config/vendor_name_merges.csv`; pairs that only look alike stay apart and are listed below.
3. **Vendor rules.** A key that a `config/vendor_rules.csv` pattern names keeps the rule's vendor; a row
   that would say exactly what the rule says is left out.
4. **Categories.** One canonical vendor, one category: `config/vendor_map.csv`'s (unless `unclassified`),
   else the vendor rule's, else the category with the most proposed spend.
5. **Output** sorted by `name_key`, columns `name_key,vendor,category,confidence`.

## Key conflicts with config/vendor_map.csv

| Key | config/vendor_map.csv | State | Proposed (confidence, spend) | Decision |
| --- | --- | --- | --- | --- |
| ACROSS STREET PRODUCTIONS | Across the Street Productions / unclassified | OH | Across the Street Productions / training (medium, $313,238) | category filled: training (the row was unclassified) |
| KEVIN WARD | Individuals (names withheld) / individuals | OH | Kevin Ward / facilities (low, $5,441) | kept config/vendor_map.csv row |
| TODD SMITH | Individuals (names withheld) / individuals | OH | Todd Smith / facilities (low, $9,788) | kept config/vendor_map.csv row |

Rows of config/vendor_map.csv whose `unclassified` category was filled from the proposals:

- ACROSS STREET PRODUCTIONS: Across the Street Productions -> training

Proposals left out of the shared map by an empty `to_vendor` in `config/vendor_name_merges.csv`:

- CANOPY (CA): Canopy / government, $1,390,401

## Keys proposed by several states

| Key | Proposals (state: vendor / category, confidence, spend) | Row written |
| --- | --- | --- |
| CHARTER COMMUNICATIONS | CA: Charter Communications / telecom, medium, $833,371; OH: Spectrum / telecom, low, $604,848 | Charter Communications / telecom (from CA) |
| EXPEDITORS BY LINDALE | CA: Expeditors BY Lindale / wildland, low, $1,907,146; ID: Expeditors By Lindale / wildland, low, $525,107 | Expeditors by Lindale / wildland (from CA) |
| HARRIS AND HARRIS | TX: Harris & Harris / ems-billing, medium, $675,594; CA: Harris & Harris / finance, low, $974,503 | Harris & Harris / ems-billing (from TX) |
| INTERNATIONAL ASSOCIATION OF FIRE FIGHTERS | TX: International Association of Fire Fighters / training, medium, $115,525; OH: International Association Of Fire Fighters / training, low, $18,000 | International Association of Fire Fighters / training (from TX) |
| JPMORGAN CHASE BANK NA | CA: JPMorgan Chase Bank / finance, high, $13,784,818; OH: Jpmorgan Chase Bank Na / finance, low, $2,190 | JPMorgan Chase Bank / payroll (from CA) |
| MEDICAL PRIORITY CONSULTANTS | TX: Priority Dispatch (Medical Priority Consultants) / dispatch, high, $121,933; OH: Medical Priority Consultants Inc / professional, low, $245,894 | Priority Dispatch / dispatch (from TX) |
| PIERCE MANUFACTURING | CA: Pierce Manufacturing / apparatus, medium, $7,525,994; OH: Pierce Manufacturing Inc / apparatus, low, $8,235 | Pierce Manufacturing / apparatus (from CA) |
| PRIORITY DISPATCH | CA: Priority Dispatch / dispatch, medium, $1,378,783; OH: Priority Dispatch Corp / dispatch, medium, $35,220 | Priority Dispatch / dispatch (from CA) |
| PUBLIC CONSULTING GROUP | OH: Public Consulting Group / professional, high, $35,000; TX: Public Consulting Group / ems-billing, medium, $217,979 | Public Consulting Group / ems-billing (from OH) |
| PURVIS SYSTEMS | CA: Purvis Systems / dispatch, medium, $3,599,279; OH: Purvis Systems / fire-equipment, low, $138,011 | Purvis Systems / dispatch (from CA) |
| SNAP ON INDUSTRIAL | TX: Snap-on / fleet, medium, $815; CA: Snap-on Industrial / general, low, $5,151,732 | Snap-on / general (from TX) |
| TIMBERLINE HELICOPTERS | CA: Timberline Helicopters / apparatus, medium, $606,869; ID: Timberline Helicopters / wildland, low, $153,260 | Timberline Helicopters / apparatus (from CA) |
| US DEPT OF AGRICULTURE | ID: U.S. Department of Agriculture (Forest Service) / government, high, $46,704,949; CA: US Dept of Agriculture / government, medium, $5,945,629 | U.S. Department of Agriculture / government (from ID) |
| US TREASURY | OH: Internal Revenue Service / payroll, medium, $5,872,040; CA: US Treasury / government, low, $890,422 | Internal Revenue Service / payroll (from OH) |
| WS DARLEY AND | CA: W.S. Darley & Co. / fire-equipment, high, $622,061; OH: WS Darley & Co / fire-equipment, high, $48,750 | W.S. Darley & Co. / fire-equipment (from CA) |

## Canonical names

148 canonical names cover more than one proposed form (or a proposed form and a Utah name).
`How`: where the canonical name came from.

| Canonical name | Other forms folded in | States | How | Proposed spend |
| --- | --- | --- | --- | --- |
| Payroll | Payroll (payee code 406) | UT, OH | config/vendor_name_merges.csv | $61,003,266 |
| JPMorgan Chase Bank | Jpmorgan Chase Bank Na | OH, CA, TX | config/vendor_name_merges.csv | $58,834,725 |
| Heartland Bank | Heartland Bank (payroll) | OH | config/vendor_name_merges.csv | $33,859,068 |
| Huntington Bank | Huntington Bank (payroll and benefits) | OH | config/vendor_name_merges.csv | $27,716,856 |
| Heli-1 | Heli 1 | CA, ID | most spend | $20,181,768 |
| Riverview International Trucks | Riverview Intl Trucks | CA | most spend | $14,932,411 |
| El Dorado Water & Shower Service | El Dorado Water & Shower SVC | CA | most spend | $10,443,262 |
| Ferrara Fire Apparatus | Ferrara Fire Apparatus Inc | OH, CA | most spend | $10,026,212 |
| Stark County Schools Council of Governments | Stark County Schools Council of Governments (health benefits); Stark County Schools Council of Governments (health plan) | OH | most spend | $9,207,932 |
| KeyBank | KeyBank (payroll taxes); Keybank | UT, OH | config/vendor_name_merges.csv | $9,118,116 |
| HeliQwest International | Heliqwest Intl | CA, ID | most spend | $8,581,127 |
| Sysco | Sysco of Central California | CA | config/vendor_name_merges.csv | $7,582,275 |
| U.S. Bank | US Bank (Credit Card Payments); Us Bank (Credit Card)*; Us Bank (Visa) | UT, OH, ID | config/vendor_name_merges.csv | $7,563,534 |
| Pierce Manufacturing | Pierce Manufacturing Inc | OH, CA | most spend | $7,534,229 |
| Fifth Third Bank | Fifth Third Bank Of Western Ohio | OH | config/vendor_name_merges.csv | $5,884,930 |
| 911 Fleet & Fire Equipment | 911 Fleet And Fire Equipment | OH | most spend | $5,784,056 |
| Municipal Emergency Services | Municipal Emergency SVCS; Municipal Emergency Service | UT, OH, CA | config/vendor_name_merges.csv | $4,295,800 |
| UC Physicians | Uc Physicians | OH | most spend | $3,744,589 |
| Cigna Health and Life Insurance | Cigna Health and Life Insurance Company | OH | config/vendor_name_merges.csv | $3,477,690 |
| Fire Safety Services | Fire Safety Service Inc | OH | most spend | $3,261,320 |
| Johnson's Fire Equipment | Johnson's Fire Equipment Company | OH | config/vendor_name_merges.csv | $3,205,116 |
| Treasurer of State of Ohio | Treasurer Of State; Treasurer Of State (Das); Treasurer Of State (Fund 5C2); Treasurer Of State Of Ohio | OH | config/vendor_name_merges.csv | $3,111,392 |
| CA Dept of Tax and Fee Admin | CA Dept of Tax & Fee Admin (boe) | CA | most spend | $3,108,053 |
| El Dorado Hills Fire Department | El Dorado Hills Fire Dept | CA | most spend | $2,819,281 |
| Aultcare | AultCare | OH | most spend | $2,736,246 |
| Delta Dental | Delta Dental of Ohio | OH | config/vendor_name_merges.csv | $2,547,781 |
| Expeditors by Lindale | Expeditors BY Lindale; Expeditors By Lindale | CA, ID | most spend | $2,432,253 |
| All American Fire Equipment | All American Fire Equip. Inc; All American Fire Equipment, Inc. | OH | config/vendor_name_merges.csv | $2,307,100 |
| Warren Fire Equipment | Warren Fire Equip Inc; Warren Fire Equipment,Inc. | OH | config/vendor_name_merges.csv | $2,200,304 |
| Thomas J Ferguson MD PHD | Thomas J. Ferguson, M.D., PH.D. | CA | most spend | $1,877,204 |
| Humana Health Plan Ohio | Humana Health Plan Of Ohio, Inc. | OH | config/vendor_name_merges.csv | $1,799,624 |
| Priority Dispatch | Priority Dispatch (Medical Priority Consultants); Priority Dispatch Corp | OH, CA, TX | most spend | $1,535,936 |
| Fire Apparatus Service & Repair | Fire Apparatus Service & Repair, Inc. | OH | config/vendor_name_merges.csv | $1,429,036 |
| Public Entities Pool of Ohio | Public Entities Pool Of Ohio (Pep) | OH | most spend | $1,331,914 |
| MECC Regional Council of Governments | MECC Regional Council of Governments (dispatch); Mecc Regional Council Of Governments | OH | most spend | $1,330,956 |
| First National Bank | First National Bank (payroll) | OH | most spend | $1,191,830 |
| Med-I-Bank | Med I Bank; Med-I-Bank (benefit accounts) | OH | most spend | $1,156,578 |
| Department of Human Resources | Dept of Human Resources | CA | most spend | $1,088,529 |
| Superfleet | Superfleet (fuel card) | OH | config/vendor_name_merges.csv | $941,021 |
| Ohio Child Support Payment Central | Ohio Child Support Payment Central (CSPC) | OH | config/vendor_name_merges.csv | $889,149 |
| Medicare | Medicare (employer tax) | OH | config/vendor_name_merges.csv | $850,255 |
| Ohio First Responder Grants | Ohio First Responder Grants (grant writing) | OH | config/vendor_name_merges.csv | $827,278 |
| W.W. Williams | W.W. Williams (Toledo) | OH | most spend | $697,213 |
| W.S. Darley & Co. | WS Darley & Co | UT, OH, CA | config/vendor_map.csv | $670,811 |
| Voya | Voya (retirement plan) | OH | most spend | $650,667 |
| Regional Income Tax Agency | Regional Income Tax Agency (Payroll) | OH | most spend | $633,990 |
| Beem's BP Distributing | Beem's BP Distributing Inc. | OH | config/vendor_name_merges.csv | $632,659 |
| Centerpoint Energy | Centerpoint Energy Ohio | OH | config/vendor_name_merges.csv | $597,942 |
| P & R Communications Service | P&R Communications Services | OH | config/vendor_name_merges.csv | $526,111 |
| Atwell's Police & Fire Equipment | Atwell's Police & Fire Equip. Co.; Atwell's Police & Fire Equipment Co | OH | config/vendor_name_merges.csv | $487,305 |
| Police & Firemen's Insurance Association | Police & Firemen's Insurance Assoc(Pfia); Police and Firemen's Insurance Association | OH | most spend | $466,303 |
| Optum Bank | Optum Bank (HSA) | OH | most spend | $453,725 |
| KEMBA Credit Union | KEMBA Credit Union (payroll deductions) | OH | config/vendor_name_merges.csv | $449,472 |
| Ohio Fire Chiefs' Association | Ohio Fire Chiefs Assn; Ohio Fire Chiefs Assoc | OH | most spend | $446,759 |
| Accumed Billing | Accumed Billing Inc. | OH | config/vendor_name_merges.csv | $445,606 |
| Redd Public Safety Equipment | Redd Public Safety Equip. LLC | OH | most spend | $434,723 |
| Teleflex | Teleflex LLC | UT, OH | config/vendor_map.csv | $376,047 |
| Montgomery County Sheriff | Montgomery County Sheriff (dispatch) | OH | most spend | $370,375 |
| Across the Street Productions | Across The Street Productions | UT, OH | config/vendor_name_merges.csv | $343,498 |
| Buckeye Power Sales | Buckeye Power Sales Co., Inc. | OH | most spend | $298,411 |
| Kings Ford | Kings Ford* | OH | most spend | $272,794 |
| Roy Tailors Uniform | Roy Tailors Uniform Co. | OH | config/vendor_name_merges.csv | $269,818 |
| Baycom | Baycom Inc | OH, TX | most spend | $258,553 |
| Security Benefit | Security Benefit (retirement plan) | OH | config/vendor_name_merges.csv | $248,814 |
| Bob Sumerel Tire | Bob Sumerel Tire Co Inc; Bob Sumerel Tire Company | OH | most spend | $241,654 |
| Kzf Design | Kzf Design Inc; Kzf Design, Inc | OH | most spend | $241,330 |
| Montgomery County | Montgomery County (health plan) | OH | most spend | $230,991 |
| Rumpke | Rumpke Of Ohio, Inc. | OH | config/vendor_name_merges.csv | $220,489 |
| Oregon Department of Forestry | Oregon Dept of Forestry | CA, ID | most spend | $213,194 |
| R.D. Holder Oil | R.D. Holder Oil Company | OH | most spend | $205,715 |
| HSA - Employer Match/Wellness | Hsa - Employer Match/Wellness | OH | config/vendor_name_merges.csv | $199,603 |
| Union Township | Union Township (flexible spending) | OH | most spend | $195,780 |
| Ohio Public Risk Insurance Agency | Ohio Public Risk Insurance Agency, Inc. | OH | config/vendor_name_merges.csv | $180,884 |
| Idaho Department of Fish & Game | Idaho Department of Fish and Game | ID | most spend | $172,004 |
| OhioHealth | Ohiohealth Corporation | OH | config/vendor_name_merges.csv | $163,970 |
| Shuttler's Uniform | Shuttler's Uniform Inc. | OH | config/vendor_name_merges.csv | $161,676 |
| Southwest Ohio Computer Association | Southwest Ohio Computer Assoc | OH | most spend | $159,173 |
| CDW Government | Cdw Government | UT, OH | config/vendor_name_merges.csv | $156,542 |
| International Association of Fire Fighters | International Association Of Fire Fighters; Intl Assoc Of Fire Fighters | OH, TX | config/vendor_name_merges.csv | $156,025 |
| Jg Luke | Jg Luke LLC | OH | config/vendor_name_merges.csv | $152,418 |
| Marathon Petroleum | Marathon Petroleum Company LLC | OH | config/vendor_name_merges.csv | $150,980 |
| Fire & Marine | Fire And Marine Inc. (Fmi) | OH | most spend | $149,539 |
| Duncan Oil | Duncan Oil Company | OH | config/vendor_name_merges.csv | $145,061 |
| Perfection Group | Perfection Group Inc | OH | most spend | $144,267 |
| Stigler Supply | Stigler Supply Company | OH | most spend | $139,578 |
| Ems Management & Consultants | Ems Management & Consultants Inc | OH | config/vendor_name_merges.csv | $136,226 |
| Cardmember Service | Cardmember Service (credit card); Cardmember Services (Security Bank) | UT, OH | config/vendor_map.csv | $133,544 |
| Mutual of Omaha | Mutual Of Omaha (Dental); Mutual Of Omaha (Life); Mutual Of Omaha (Vision) | OH | most spend | $130,540 |
| Department of Justice | Dept of Justice | CA | most spend | $114,106 |
| Communications Service | Communication Services | OH | most spend | $113,524 |
| University of Cincinnati | University Of Cincinnati; University Of Cincinnati Pc | OH | most spend | $110,613 |
| Cronin Ford | Cronin Ford Inc | OH | config/vendor_name_merges.csv | $104,943 |
| Waste Management | Waste Management Of Ohio, Inc. | UT, OH, ID | config/vendor_map.csv | $102,403 |
| J.K. Meurer | J. K. Meurer | OH | most spend | $101,310 |
| Smyth Automotive | Smyth Automotive Inc. | OH | most spend | $84,154 |
| Warren County Telecommunications Dept | Warren County Telecommunications Dept. | OH | most spend | $83,977 |
| First In-Last Out Fire Equipment & Training | First In-Last Out Fire Equip. & Training LLC; First In-Last Out Fire Equipment&Training LLC | OH | config/vendor_name_merges.csv | $82,888 |
| Warren County Career Center | Warren County Career Center (Fire Train | OH | most spend | $82,840 |
| American National Fleet Service | American Natl Fleet Svc, Inc | OH | most spend | $78,602 |
| Waterway | Waterway Southwest Pennsylvania; Waterway, Inc. | OH | config/vendor_name_merges.csv | $78,416 |
| First Arriving | First Arriving, LLC | UT, OH | config/vendor_map.csv | $75,544 |
| Life Extension Clinics | Life Extension Clinics, Inc. | OH | config/vendor_name_merges.csv | $70,478 |
| Super Laundry Equipment | Super Laundry Equipment Corp; Super Laundry Equipment Corporation | OH | most spend | $67,454 |
| US Postal Service | U.S. Postal Service | UT, CA | config/vendor_map.csv | $67,000 |
| Ohio Department of Job & Family Services | Ohio Dept. Of Job And Family Services | OH | most spend | $64,270 |
| K E Rose | K E Rose Company Ltd; K. E. Rose Company Ltd | OH | most spend | $59,936 |
| Squire Patton Boggs | Squire Patton Boggs (Us) LLP; Squire Patton Boggs LLP | OH | most spend | $57,211 |
| Ken Neyer Plumbing | Ken Neyer Plumbing, Inc. | OH | config/vendor_name_merges.csv | $53,299 |
| Emergency Services Consulting International | Emergency Service Consulting International | UT, OH | config/vendor_map.csv | $50,118 |
| Comdoc | Comdoc, Inc. | OH | config/vendor_name_merges.csv | $48,475 |
| Center for Resilience & Wellness | Center for Resilience & Wellness, LLC; The Center For Resilience & Wellness | OH | most spend | $47,200 |
| Republic Services | Republic Services, Inc. | UT, OH | config/vendor_name_merges.csv | $42,695 |
| D & T P M & Truck Repair | D & T P M & Truck Repair LLC; D& Tp.M & Truck Repair | OH | most spend | $41,719 |
| Lorain County Fire Chief's Assoc | Lorain County Fire Chiefs Assn | OH | most spend | $41,269 |
| Ohio Department of Commerce | Ohio Department Of Commerce; Ohio Dept Of Commerce | OH | most spend | $38,246 |
| Information Technology Department | Information Technology Dept. | OH | most spend | $35,694 |
| Shrader Tire & Oil | Shrader Tire & Oil Inc | OH | most spend | $34,154 |
| Birkley Consulting | Birkley Consulting LLC | OH | most spend | $31,611 |
| Lake County Fire Chiefs Association | Lake County Fire Chiefs' Assoc. | OH | config/vendor_name_merges.csv | $30,875 |
| Consolidated Fleet Services | Consolidated Fleet Service | UT, OH | config/vendor_name_merges.csv | $30,699 |
| Embroidery Wearhouse & Screenprinting | Embroidery Wearhouse & Screenprinting LLC | OH | config/vendor_name_merges.csv | $30,674 |
| R & T Yoder Electric | R & T Yoder Electric, Inc. | OH | config/vendor_name_merges.csv | $28,720 |
| NEOFPA | Neofpa | OH | config/vendor_name_merges.csv | $28,619 |
| Lexipol | Lexipol LLC | UT, OH | config/vendor_map.csv | $27,806 |
| Great Lakes Best One Tire & Service | Great Lakes Best One Tire & Service, LLC | OH | config/vendor_name_merges.csv | $27,408 |
| Coughlin Ford | Coughlin Ford, Inc. | OH | config/vendor_name_merges.csv | $26,871 |
| DreamSeat | Dreamseat | UT, OH | config/vendor_map.csv | $26,593 |
| City of Sharonville Fire Department | City Of Sharonville Fire Dept | OH | most spend | $26,465 |
| Price Consultation Services | Price Consultation Service LLC; Price Consultation Services, LLC | OH | most spend | $25,250 |
| Rmc-Resource Management Consultants | Rmc-Resource Management Consultants,LLC | OH | config/vendor_name_merges.csv | $24,489 |
| FleetPride | Fleetpride Inc | UT, OH | config/vendor_map.csv | $24,194 |
| Fire-Fly Fire Equipment | Fire-Fly Fire Equipment Inc. | OH | config/vendor_name_merges.csv | $23,920 |
| Ohio State Firefighter's Association | Ohio State Firefighters Assoc. | OH | most spend | $23,205 |
| Apple | Apple Inc | UT, OH | config/vendor_map.csv | $23,122 |
| Fastsigns | FastSigns | UT, CA | config/vendor_map.csv | $21,078 |
| University Hospitals Health System | University Hospitals Health System, Inc. | OH | config/vendor_name_merges.csv | $17,781 |
| First National Bank of Omaha | First National Bank Of Omaha | UT, OH | config/vendor_map.csv | $17,452 |
| Liberty Township Fire Department | Liberty Township Fire Dept. | OH | most spend | $17,242 |
| Construction Equipment and Supply | Construction Equip & Supply; Construction Equipment And Supply | OH | most spend | $16,060 |
| Truck Service | Truck Service Inc.; Truck Service, Inc. (E.A.B.) | OH | most spend | $14,201 |
| Truck Sales and Services | Truck Sales & Service; Truck Sales And Services | OH | most spend | $13,171 |
| RollNRack | Rollnrack LLC | UT, OH | config/vendor_map.csv | $9,970 |
| PAR Training and Props | Par Training And Props | UT, OH | config/vendor_map.csv | $8,350 |
| Firehouse Innovations | Firehouse Innovations Corp | UT, OH | config/vendor_map.csv | $7,600 |
| International Association of Fire Chiefs | International Assoc Of Fire Chiefs | UT, OH | config/vendor_map.csv | $6,740 |
| SiteOne Landscape Supply | Siteone Landscape Supply, LLC | OH | config/vendor_name_merges.csv | $5,852 |
| OpenGov | Opengov, Inc | OH | config/vendor_name_merges.csv | $5,000 |
| Uline | Uline, Inc | UT, OH | config/vendor_map.csv | $4,751 |

1121 proposed names were only cleaned (legal suffix or lower-case note dropped, small words in
lower case), or renamed by `config/vendor_name_merges.csv`:

<details><summary>List</summary>

- * Sedgwick Claims Mgt Services -> Sedgwick (OH)
- 10485 Olympic (lessor) -> 10485 Olympic (TX)
- 1St Nat'L Bank Of S.W. Ohio -> 1St Nat'L Bank of S.W. Ohio (OH)
- 2923 W Cessna LLC (lessor) -> 2923 W Cessna (ID)
- 3F Fitness, LLC -> 3F Fitness (OH)
- 66degrees, LLC -> 66degrees (OH)
- A And M Towing & Road Service -> A and M Towing & Road Service (OH)
- A J Door LLC -> A J Door (OH)
- A. E. David Company -> A. E. David (OH)
- A.D.A.M. Solutions LLC -> A.D.A.M. Solutions (OH)
- AHS Rescue LLC -> AHS Rescue (OH)
- Aaa Club Alliance, Inc -> Aaa Club Alliance (OH)
- Abbott Electric Inc -> Abbott Electric (OH)
- Abraham Miller Excavating, LLC -> Abraham Miller Excavating (OH)
- Accent Communication Services, Inc. -> Accent Communication Services (OH)
- Accurate Door Systems Inc -> Accurate Door Systems (OH)
- Accurate Mechanical Inc -> Accurate Mechanical (OH)
- Ach Debits To Federal Government -> Ach Debits to Federal Government (OH)
- Across The Street -> Across the Street Productions (OH)
- Adam-Eve Plumbing & Drain Service, Inc. -> Adam-Eve Plumbing & Drain Service (OH)
- Adrenline City Racing LLC -> Adrenline City Racing (OH)
- Advanced Mechanical Services, Inc -> Advanced Mechanical Services (OH)
- Advanced Services Of Gallipoli -> Advanced Services of Gallipoli (OH)
- Advantage Homes LLC -> Advantage Homes (OH)
- Advantech Services And Parts L -> Advantech Service & Parts (OH)
- Aero Aviation Company -> Aero Aviation (CA)
- Ag-Pro Ohio, LLC -> Ag-Pro Ohio (OH)
- Agile Network Builders, LLC -> Agile Network Builders (OH)
- Ah Sturgill Roofing Inc -> Ah Sturgill Roofing (OH)
- Air Comfort Inc -> Air Comfort (OH)
- Air Force One, Inc. -> Air Force One (OH)
- Akron Fire Credit Union Inc -> Akron Fire Credit Union (OH)
- Albert Motors, Inc -> Albert Motors (OH)
- Albert's Men's Shop* -> Albert's Men's Shop (OH)
- Alegeus (benefit accounts) -> Alegeus (OH)
- All Comfort Heating & Air Conditioning, LLC -> All Comfort Heating & Air Conditioning (OH)
- All Done Painting And Power Washing -> All Done Painting and Power Washing (OH)
- All Type Heating & Cooling LLC -> All Type Heating & Cooling (OH)
- All-American Fire Equipment In -> All American Fire Equipment (OH)
- Allen County Board Of Commissioners -> Allen County Board of Commissioners (OH)
- Alley Cat Design Inc -> Alley Cat Design (OH)
- Alliance Motors,Inc -> Alliance Motors (OH)
- Allied Benefit Systems, Inc. -> Allied Benefit Systems (OH)
- Allied Car Wash, Inc. -> Allied Car Wash (OH)
- Allied Corporation -> Allied (OH)
- Allied Roofing, Inc -> Allied Roofing (OH)
- Allstate Ford Of Youngstown -> Allstate Ford of Youngstown (OH)
- Alt & Witzig Engineering, Inc -> Alt & Witzig Engineering (OH)
- Alyn Corp -> Alyn (ID)
- Am Door & Supply Co, Inc -> Am Door & Supply (OH)
- Ambulance Maintenance Company Inc -> Ambulance Maintenance (OH)
- Amc Roofing LLC. -> Amc Roofing (OH)
- Amentum (formerly DynCorp International) -> Amentum (CA)
- America's Ink And Toner Supply -> America's Ink and Toner Supply (OH)
- American Diesel Service Inc -> American Diesel Service (OH)
- American Family Life Assurance Company -> American Family Life Assurance (OH)
- American Fidelity Assurance Company -> American Fidelity Assurance (OH)
- American Fire Company -> American Fire (ID)
- American Heritage Life Insurance Co -> American Heritage Life Insurance (OH)
- American On Site Services -> American on Site Services (ID)
- American Structurepoint, Inc -> American Structurepoint (OH)
- American United Life Insurance Company -> American United Life Insurance (OH)
- American Welding & Gas Inc. -> American Welding & Gas (OH)
- Americrane & Hoist Corp. -> Americrane & Hoist (OH)
- Ames Painting & More, Inc. -> Ames Painting & More (OH)
- Ankeney-Xenia Truck Service, Inc. -> Ankeney-Xenia Truck Service (OH)
- Apollo Propane, Inc. -> Apollo Propane (OH)
- App Architecture Inc -> App Architecture (OH)
- Applied Mechanical Systems Inc. -> Applied Mechanical Systems (OH)
- Aqua Ohio, Inc. -> Aqua Ohio (OH)
- Aramark Uniform & Career Apparel Group, Inc. -> Aramark Uniform & Career Apparel Group (OH)
- Armada Ltd -> Armada (OH)
- Ascendance Trucks, LLC -> Ascendance Trucks (OH)
- Ashtabula County Clerk Of Courts -> Ashtabula County Clerk of Courts (OH)
- At&T Mobility National Accounts, LLC -> At&T Mobility National Accounts (OH)
- Atlantic Sign Company -> Atlantic Sign (OH)
- Atlantic Signal, LLC -> Atlantic Signal (OH)
- Atlas Automotive, Inc. -> Atlas Automotive (OH)
- Auditor Of State -> Auditor of State (OH)
- Auditor Of State Keith Faber -> Auditor of State Keith Faber (OH)
- Auditor Of State, David Yost -> Auditor of State, David Yost (OH)
- Auto & Truck Of Williamsburg -> Auto & Truck of Williamsburg (OH)
- Auto & Truck Tire Center, Inc. -> Auto & Truck Tire Center (OH)
- Autonation, Inc. -> Autonation (OH)
- Autozone Stores Inc -> Autozone Stores (OH)
- Ayers Mechanical Group, LLC -> Ayers Mechanical Group (OH)
- BHM CPA Group, Inc. -> BHM CPA Group (OH)
- Babbitts Sports Center LLC -> Babbitts Sports Center (OH)
- Bad Day Training & Consulting, LLC -> Bad Day Training & Consulting (OH)
- Bank Capital Services LLC -> Bank Capital Services (OH)
- Bank Of Magnolia -> Bank of Magnolia (OH)
- Barbour Auto Parts Inc -> Barbour Auto Parts (OH)
- Bastin & Company LLC -> Bastin & Company (OH)
- Bay Bridge Administrators, LLC -> Bay Bridge Administrators (OH)
- Bazell Oil Co. -> Bazell Oil (OH)
- Be Solutions LLC -> Be Solutions (OH)
- Beau Townsend Ford Inc. -> Beau Townsend Ford (OH)
- Bell Medical Services Inc. -> Bell Medical Services (OH)
- Bells Custom Concrete LLC -> Bells Custom Concrete (OH)
- Belmont Petroleum Corp -> Belmont Petroleum (OH)
- Bender Communications Inc -> Bender Communications (OH)
- Berger Chevrolet Inc -> Berger Chevrolet (OH)
- Best One Tire & Service Of -> Best One Tire & Service (OH)
- Best One Tire & Service Of Mid America -> Best One Tire & Service (OH)
- Best One Tire Mid America, Inc. -> Best One Tire Mid America (OH)
- Best One Tire and Service of Mid Ameica, Inc. -> Best One Tire & Service (OH)
- Best Truck Equipment Inc. -> Best Truck Equipment (OH)
- Bfs Petroleum Products , Inc. -> Bfs Petroleum Products (OH)
- Bickett Mach & Gas Supply Inc -> Bickett Mach & Gas Supply (OH)
- Big E Landscaping and skid loader service llc -> Big E Landscaping and skid loader service (OH)
- Bihl Office Supply Inc -> Bihl Office Supply (OH)
- Bilbrey Construction Inc -> Bilbrey Construction (OH)
- Bill Spade Electric Inc -> Bill Spade Electric (OH)
- Black Ridge LLC -> Black Ridge (ID)
- Blazestack Inc. -> Blazestack (OH)
- Bling It On Apparel, LLC -> Bling It on Apparel (OH)
- Blue Mountain Electric Co -> Blue Mountain Electric (CA)
- Blust Motor Service Inc. -> Blust Motor Service (OH)
- Bme Mechanical Electrical Plumbing* -> Bme Mechanical Electrical Plumbing (OH)
- Board Of County Commissioners -> Board of County Commissioners (OH)
- Bob-Boyd Ford Inc. -> Bob-Boyd Ford (OH)
- Bobbys Truck And Bus Repair -> Bobbys Truck and Bus Repair (OH)
- Bockrath And Associates -> Bockrath and Associates (OH)
- Bon Secours Mercy Health Inc -> Bon Secours Mercy Health (OH)
- Boot Country, Inc -> Boot Country (OH)
- Botkins Electric And Plumbing Co., Inc. -> Botkins Electric and Plumbing (OH)
- Boyle Mechanical Solutions LLC -> Boyle Mechanical Solutions (OH)
- Bps Heating & Cooling, LLC* -> Bps Heating & Cooling (OH)
- Bradley D. Raetzke MD (medical direction) -> Bradley D. Raetzke MD (OH)
- Brakefire, Inc. -> Brakefire (OH)
- Bramhall Engineering & Surveying Co -> Bramhall Engineering & Surveying (OH)
- Brendza Electric Construction Company -> Brendza Electric Construction (OH)
- Bridges Excavating LLC -> Bridges Excavating (OH)
- Brighton Spring Service Co.,Inc. -> Brighton Spring Service (OH)
- Broadband Resources, LLC -> Broadband Resources (OH)
- Brondes Ford Maumee Ltd -> Brondes Ford (OH)
- Bronson Door Co -> Bronson Door (OH)
- Brown Bag Sandwich Co -> Brown Bag Sandwich (CA)
- Brown Pest Control Corp -> Brown Pest Control (OH)
- Brumbaugh Construction Inc -> Brumbaugh Construction (OH)
- Bsmh Employer Services, LLC -> Bsmh Employer Services (OH)
- Bubble Boy Cleaning LLC -> Bubble Boy Cleaning (OH)
- Buck Run Commercial Doors & Hardware Inc -> Buck Run Commercial Doors & Hardware (OH)
- Buckeye Apparatus Services, LLC -> Buckeye Apparatus Services (OH)
- Bulldog On Site Services -> Bulldog on Site Services (ID)
- Burgess Ambulance Sales, Inc. -> Burgess Ambulance Sales (OH)
- Byers Ford, LLC -> Byers Ford (OH)
- C & C Disposal LLC -> C & C Disposal (OH)
- C & Y Oil Co. -> C & Y Oil (OH)
- Cal Dreamscape Landscape Co -> Cal Dreamscape Landscape (CA)
- Cal Poly Corporation -> Cal Poly (CA)
- Cal-sierra Title Company -> Cal-sierra Title (CA)
- California Sandwich Company -> California Sandwich (CA)
- Campus Fire Safety Com LLC -> Campus Fire Safety Com (OH)
- Canton Township Board Of Trustees, Oh -> Canton Township Board of Trustees, Oh (OH)
- Capital Choice Office Furniture LLC -> Capital Choice Office Furniture (OH)
- Capital Electric Line Builders, Inc -> Capital Electric Line Builders (OH)
- Capitol Aluminum & Glass Corp -> Capitol Aluminum & Glass (OH)
- Capitol Varsity Sports, Inc. -> Capitol Varsity Sports (OH)
- Case Towing, LLC -> Case Towing (OH)
- Cbc Engineers & Associates Ltd -> Cbc Engineers & Associates (OH)
- Cdw Goverment, Inc. -> CDW Government (OH)
- Cee B Glass Inc -> Cee B Glass (OH)
- Central Fire Protection District In Santa Clara County -> Central Fire Protection District in Santa Clara County (CA)
- Central Ohio Cleaning Inc. -> Central Ohio Cleaning (OH)
- Central Square Technologies, LLC -> CentralSquare Technologies (OH)
- Certasite LLC -> Certasite (OH)
- Chad Abbott Signs LLC -> Chad Abbott Signs (OH)
- Chagrin /Se Council Of Governments -> Chagrin /Se Council of Governments (OH)
- Chagrin/Southeast Council Of Governments -> Chagrin/Southeast Council of Governments (OH)
- Change Healthcare Practice Mgmt Solutions Inc -> Change Healthcare (OH)
- Change Healthcare Practice Mgt Solutions Inc -> Change Healthcare (OH)
- Change Healthcare Tech. Enabled Serv., LLC -> Change Healthcare (OH)
- Chardon Oil Co Inc -> Chardon Oil (OH)
- Charles E Harris & Associates Inc -> Charles E Harris & Associates (OH)
- Chase Bank For Federal Withholding -> JPMorgan Chase Bank (OH)
- Cherry Lynne Poteet (attorney) -> Cherry Lynne Poteet (OH)
- Chicago Title Company -> Chicago Title (CA)
- Childers H.V.A.C. Systems Inc. -> Childers H.V.A.C. Systems (OH)
- Cincinnati Life Insurance Co. -> Cincinnati Life Insurance (OH)
- Cincinnati State Technical And Communit -> Cincinnati State Technical and Communit (OH)
- Cincinnati United Contractors LLC -> Cincinnati United Contractors (OH)
- Citizens National Bank (payroll) -> Citizens National Bank (OH)
- Citran Occupational Health, LLC -> Citran Occupational Health (OH)
- City Of Akron -> City of Akron (OH)
- City Of Ashtabula -> City of Ashtabula (OH)
- City Of Beavercreek -> City of Beavercreek (OH)
- City Of Brunswick -> City of Brunswick (OH)
- City Of Brunswick Department Of Taxation -> City of Brunswick Department of Taxation (OH)
- City Of Bryan Fire Department -> City of Bryan Fire Department (OH)
- City Of Canal Fulton -> City of Canal Fulton (OH)
- City Of Canal Winchester -> City of Canal Winchester (OH)
- City Of Carlisle -> City of Carlisle (OH)
- City Of Cleveland -> City of Cleveland (OH)
- City Of Cleveland Division Of Water -> City of Cleveland Division of Water (OH)
- City Of Columbiana (Utilities) -> City of Columbiana (Utilities) (OH)
- City Of Cortland -> City of Cortland (OH)
- City Of Cuyahoga Falls* -> City of Cuyahoga Falls (OH)
- City Of Dayton -> City of Dayton (OH)
- City Of Dover - Payroll -> City of Dover - Payroll (OH)
- City Of Dover Dental Ins -> City of Dover Dental Ins (OH)
- City Of East Liverpool -> City of East Liverpool (OH)
- City Of Eastlake Payroll -> City of Eastlake Payroll (OH)
- City Of Englewood -> City of Englewood (OH)
- City Of Euclid -> City of Euclid (OH)
- City Of Fairborn -> City of Fairborn (OH)
- City Of Fairlawn -> City of Fairlawn (OH)
- City Of Franklin -> City of Franklin (OH)
- City Of Franklin Div. Of Fire/Ems -> City of Franklin Div. of Fire/Ems (OH)
- City Of Franlin Division Of Fire & Ems -> City of Franlin Division of Fire & Ems (OH)
- City Of Girard -> City of Girard (OH)
- City Of Green -> City of Green (OH)
- City Of Grove City -> City of Grove City (OH)
- City Of Hamilton -> City of Hamilton (OH)
- City Of Highland Heights -> City of Highland Heights (OH)
- City Of Hilliard -> City of Hilliard (OH)
- City Of Huber Heights -> City of Huber Heights (OH)
- City Of Hudson -> City of Hudson (OH)
- City Of Huron -> City of Huron (OH)
- City Of Jackson/Utilities -> City of Jackson/Utilities (OH)
- City Of Lebanon, Dept. Of Service -> City of Lebanon, Dept. of Service (OH)
- City Of Lima -> City of Lima (OH)
- City Of Lima - Utilities -> City of Lima - Utilities (OH)
- City Of Marion, Ohio - Utilities Dept. -> City of Marion, Ohio - Utilities Dept. (OH)
- City Of Marysville, Oh -> City of Marysville, Oh (OH)
- City Of Mayfield Heights -> City of Mayfield Heights (OH)
- City Of Middletown -> City of Middletown (OH)
- City Of Monroe -> City of Monroe (OH)
- City Of Montgomery -> City of Montgomery (OH)
- City Of Montgomery - Payroll -> City of Montgomery - Payroll (OH)
- City Of N Canton Public -> City of N Canton Public (OH)
- City Of Newark -> City of Newark (OH)
- City Of Niles Dept. Of Public Service -> City of Niles Dept. of Public Service (OH)
- City Of North Canton-Internal -> City of North Canton-Internal (OH)
- City Of Orrville -> City of Orrville (OH)
- City Of Parma - Division Of Tax -> City of Parma - Division of Tax (OH)
- City Of Parma-Employee Health Care And -> City of Parma-Employee Health Care and (OH)
- City Of Parma-Eye Care Budget -> City of Parma-Eye Care Budget (OH)
- City Of Parma-Life Insurance -> City of Parma-Life Insurance (OH)
- City Of Perrysburg -> City of Perrysburg (OH)
- City Of Port Clinton -> City of Port Clinton (OH)
- City Of Ravenna -> City of Ravenna (OH)
- City Of Sandusky -> City of Sandusky (OH)
- City Of Sandusky-Insurance Prem -> City of Sandusky-Insurance Prem (OH)
- City Of South Euclid -> City of South Euclid (OH)
- City Of Springdale Payroll A/C -> City of Springdale Payroll A/C (OH)
- City Of Stow -> City of Stow (OH)
- City Of Toledo -> City of Toledo (OH)
- City Of Trenton -> City of Trenton (OH)
- City Of Troy -> City of Troy (OH)
- City Of Upper Arlington -> City of Upper Arlington (OH)
- City Of Vandalia -> City of Vandalia (OH)
- City Of Washington Court House -> City of Washington Court House (OH)
- City Of Wellston -> City of Wellston (OH)
- City Of Wickliffe -> City of Wickliffe (OH)
- City Of Worthington -> City of Worthington (OH)
- City Of Xenia -> City of Xenia (OH)
- City auditor-treasurer (payroll) -> City auditor-treasurer (OH)
- City of Bellefontaine (payroll) -> City of Bellefontaine (OH)
- City of Dover (health plan) -> City of Dover (OH)
- City of Niles (health self-insurance) -> City of Niles (OH)
- City of Parma (flexible spending) -> City of Parma (OH)
- City of Reading (payroll) -> City of Reading (OH)
- Clark Straight Line Roofing and Gutters Corp -> Clark Straight Line Roofing and Gutters (OH)
- Clarke Power Services, Inc. -> Clarke Power Services (OH)
- Clean Slate Landscapes LLC -> Clean Slate Landscapes (OH)
- Cleaning Supplies Company -> Cleaning Supplies (OH)
- Clearpoint Technology & Design LLC -> Clearpoint Technology & Design (OH)
- Clemans, Nelson & Associates, Inc. -> Clemans, Nelson & Associates (OH)
- Clermont Chamber Of Commerce -> Clermont Chamber of Commerce (OH)
- Cleveland City Div Of Water -> Cleveland City Div of Water (OH)
- Cleveland Division Of Water -> Cleveland Division of Water (OH)
- Cleveland Psychological Testing, LLC -> Cleveland Psychological Testing (OH)
- Clinton Township Board Of Trustees -> Clinton Township Board of Trustees (OH)
- Cloudbakers LLC -> Cloudbakers (OH)
- Cmh Solutions LLC -> Cmh Solutions (OH)
- Cmp Construction, LLC -> Cmp Construction (OH)
- Coblentz Roofing LLC -> Coblentz Roofing (OH)
- Coleman Oil Company -> Coleman Oil (ID)
- Coles Energy Inc -> Coles Energy (OH)
- Colliers Engineering & Design Inc -> Colliers Engineering & Design (OH)
- Collins Pine Company -> Collins Pine (CA)
- Colum80 (City Of Columbiana (Utilities)) -> Colum80 (City of Columbiana (Utilities)) (OH)
- Columbiana Dodge Inc -> Columbiana Dodge (OH)
- Columbus Door Sales, LLC -> Columbus Door Sales (OH)
- Columbus Pest Control Inc. -> Columbus Pest Control (OH)
- Columbus Scuba Inc. -> Columbus Scuba (OH)
- Commercial Maintenance Solutions Group, LLC -> Commercial Maintenance Solutions Group (OH)
- Companies By Design -> Companies by Design (OH)
- Competitive Contractors Inc -> Competitive Contractors (OH)
- Compton Cabinet Company -> Compton Cabinet (OH)
- Concentra Health Services, Inc. -> Concentra Health Services (OH)
- Concrete Flooring Solutions Of Ohio -> Concrete Flooring Solutions of Ohio (OH)
- Conners & Co.,Inc -> Conners & Co. (OH)
- Consumer Life Insurance company -> Consumer Life Insurance (OH)
- Continental Fire & Security, Inc. -> Continental Fire & Security (OH)
- Contractors Design Engineering, Ltd. -> Contractors Design Engineering (OH)
- Convoy Tire And Service, Inc. -> Convoy Tire and Service (OH)
- Coolants Plus, Inc. -> Coolants Plus (OH)
- Cose/Medical Mutual Of Ohio -> Cose/Medical Mutual of Ohio (OH)
- Coughlin Ford of CV, LLC -> Coughlin Ford (OH)
- County Of Summit* -> County of Summit (OH)
- Crackerjack Technology Services LLC -> Crackerjack Technology Services (OH)
- Crafty Electric Co -> Crafty Electric (OH)
- Cramer Oil, Inc. -> Cramer Oil (OH)
- Crash Rescue Village* -> Crash Rescue Village (OH)
- Criss Electric LLC -> Criss Electric (OH)
- Cromwell Mechanical LLC -> Cromwell Mechanical (OH)
- Cropper Plumbing LLC -> Cropper Plumbing (OH)
- Crown Castle International Corp -> Crown Castle International (OH)
- Crystal Springs Water Co LLC -> Crystal Springs Water (OH)
- Cs Enterprises, Inc. -> Cs Enterprises (OH)
- Cummins Bridgeway LLC -> Cummins (OH)
- Curry Electric, Inc -> Curry Electric (OH)
- Custom Clutch, Joint & Hydraulics, Inc. -> Custom Clutch, Joint & Hydraulics (OH)
- Custom Electric Service, Inc. -> Custom Electric Service (OH)
- D & R Garage Doors Plus, Inc. -> D & R Garage Doors Plus (OH)
- D & W Diesel, Inc. -> D & W Diesel (OH)
- D N D Uniforms, Inc. -> D N D Uniforms (OH)
- DMoulden Consulting LLC -> DMoulden Consulting (OH)
- DTB Distributiors Inc -> DTB Distributiors (OH)
- Damschroder Roofing Inc -> Damschroder Roofing (OH)
- Dan Hickman Construction LLC -> Dan Hickman Construction (OH)
- Darby Creek Excavating, Inc. -> Darby Creek Excavating (OH)
- Datacom, Inc. -> Datacom (OH)
- Daugherty Construction, Inc. -> Daugherty Construction (OH)
- Dave Wiltrout Roofing, Inc. -> Dave Wiltrout Roofing (OH)
- Dayton Door Sales, Inc -> Dayton Door Sales (OH)
- Dayton Fire Protection Inc -> Dayton Fire Protection (OH)
- Dc Door Company -> Dc Door (OH)
- Dearborn Life Insurance Company -> Dearborn Life Insurance (OH)
- Dearborn National Life Insurance Co. -> Dearborn National Life Insurance (OH)
- Deductions By County Auditor -> Deductions by County Auditor (OH)
- Degree Benefits LLC -> Degree Benefits (OH)
- Del-Co Water Co., Inc. -> Del-Co Water (OH)
- Delille Oxygen Co. -> Delille Oxygen (OH)
- Department Of Taxation -> Department of Taxation (OH)
- Department Of Treasury, Irs -> Department of Treasury, Irs (OH)
- Design 2 Wellness, LLC -> Design 2 Wellness (OH)
- Detroit Tire Inc. -> Detroit Tire (OH)
- Dial One Security Inc -> Dial One Security (OH)
- Diamond Door LLC -> Diamond Door (OH)
- Diehl Automotive Of Massillon -> Diehl Automotive of Massillon (OH)
- Dinsmore & Shohl LLP -> Dinsmore & Shohl (OH)
- Divens Custom Data, LLC -> Divens Custom Data (OH)
- Division Of Water -> Division of Water (OH)
- Dmc Technology, Inc. -> Dmc Technology (OH)
- Don Smith Auto Parts Inc -> Don Smith Auto Parts (OH)
- Donald Martens & Sons Ambulance Service, Inc -> Donald Martens & Sons Ambulance Service (OH)
- Dor-Mar Hvac LLC -> Dor-Mar Hvac (OH)
- Dover Brake Inc -> Dover Brake (OH)
- Dowsco Inc. -> Dowsco (OH)
- Dr. Sauber, EMS Physicians, LLC -> Dr. Sauber, EMS Physicians (OH)
- Dry Maxx Ohio Inc -> Dry Maxx Ohio (OH)
- E & H Hardware Group, LLC -> E&H Hardware (OH)
- E K Computer, Inc -> E K Computer (OH)
- E-Technologies Group LLC -> E-Technologies Group (OH)
- E.S. Consulting, Inc. -> E.S. Consulting (OH)
- EB Employee Solutions LLC -> EB Employee Solutions (OH)
- EMH Enterprises LLC -> EMH Enterprises (OH)
- EMS Technology Solutions LLC -> EMS Technology Solutions (OH)
- EQS Mechanical Inc. -> EQS Mechanical (OH)
- Eak Auto Parts Inc. -> Eak Auto Parts (OH)
- Easton Telecom Services,LLC -> Easton Telecom Services (OH)
- Easy E Construction LLC -> Easy E Construction (OH)
- Ed's Heating And Cooling -> Ed's Heating and Cooling (OH)
- Edward R Bacon Co -> Edward R Bacon (CA)
- Edwards Equipment Service LLC -> Edwards Equipment Service (OH)
- Eitel's Towing Inc -> Eitel's Towing (OH)
- Eitel's Towing Service Inc -> Eitel's Towing Service (OH)
- Element Electric Contracting LLC -> Element Electric Contracting (OH)
- Elevated Integrity Construction Services LLC -> Elevated Integrity Construction Services (OH)
- Elford Inc. -> Elford (OH)
- Elite Public Safety Consulting Inc -> Elite Public Safety Consulting (OH)
- Embroidery Express, LLC -> Embroidery Express (OH)
- Embroidery Wearhouse & Screen Printing LLC -> Embroidery Wearhouse & Screenprinting (OH)
- Emergency Medicine Physicians Of Franklin Co -> Emergency Medicine Physicians of Franklin Cty (OH)
- Emergency Parts Plus Co., LLC -> Emergency Parts Plus (OH)
- Emergency Reporting - Backdraft OpCo, LLC -> Emergency Reporting (OH)
- Employee Benefits Corporation -> Employee Benefits (OH)
- Employee Services, LLC -> Employee Services (OH)
- Engine Energy & Automation LLC -> Engine Energy & Automation (OH)
- Englefield Oil Company -> Englefield Oil (OH)
- Enterprise Uas, LLC -> Enterprise Uas (OH)
- Erie Bank (payroll) -> Erie Bank (OH)
- Ewers Technology LLC -> Ewers Technology (OH)
- Excalibur Auto Body, Inc. -> Excalibur Auto Body (OH)
- Executive Computer Management Solutions, Inc -> Executive Computer Management Solutions (OH)
- Expert It LLC -> Expert It (OH)
- Eyre Turf Services LLC -> Eyre Turf Services (OH)
- F.P. Allega Concrete Construction Corp. -> F.P. Allega Concrete Construction (OH)
- Fairfield Township Board Of Trustees -> Fairfield Township Board of Trustees (OH)
- Fairsite Technologies LLC -> Fairsite Technologies (OH)
- Falcon Plaza LLC -> Falcon Plaza (OH)
- Fastlane Truck Accessories, Inc -> Fastlane Truck Accessories (OH)
- Fcn Bank, N.A. -> Fcn Bank (OH)
- Feazel Roofing, LLC -> Feazel Roofing (OH)
- Federico Tire And Service -> Federico Tire and Service (OH)
- Fidelity Security Life In -> Fidelity Security Life in (OH)
- Fidelity Security Life Ins Co -> Fidelity Security Life Ins (OH)
- Fidelity Security Life Insurance Company -> Fidelity Security Life Insurance (OH)
- Findlay Fleet Repair & Welding LLC -> Findlay Fleet Repair & Welding (OH)
- Finke Logging Company -> Finke Logging (ID)
- Finley Fire Equipment Co, Inc -> Finley Fire Equipment (OH)
- Fire Foe Alarms, Inc -> Fire Foe Alarms (OH)
- Fire-Fly Fire Equipment Sales, Inc -> Fire-Fly Fire Equipment (OH)
- Firehouse Svc & Consulting LLC -> Firehouse Svc & Consulting (OH)
- Firehousedecals, Inc -> Firehousedecals (OH)
- Firelands Electric, Inc -> Firelands Electric (OH)
- First Capital Leasing Corp. -> First Capital Leasing (OH)
- First Choice Truck & Trailer Ltd -> First Choice Truck & Trailer (OH)
- First In Last Out Fire Equipment -> First In-Last Out Fire Equipment & Training (OH)
- First In Responder Technical Academy -> First in Responder Technical Academy (ID)
- First In-Last Out Fire & Safety Equipment LLC -> First In-Last Out Fire Equipment & Training (OH)
- First Safety Services, In -> First Safety Services, in (OH)
- First-Citizens Bank & Trust Co -> First-Citizens Bank & Trust (OH)
- Fisher Auto Parts Inc -> Fisher Auto Parts (OH)
- Fisher's Shop Inc. -> Fisher's Shop (OH)
- Five Star Roofing Systems Inc -> Five Star Roofing Systems (OH)
- Flatline Collision Ltd -> Flatline Collision (OH)
- Fleet And Fire Equipment -> Fleet and Fire Equipment (OH)
- Flyers Energy LLC -> Flyers Energy (OH)
- Focus 3, LLC -> Focus 3 (OH)
- Forest City Erectors Inc -> Forest City Erectors (OH)
- Frame & Spring Inc. -> Frame & Spring (OH)
- Franklin Co.Office Of Homeland Security Prog. -> Franklin Co.Office of Homeland Security Prog. (OH)
- Franklin Township Board Of Trustees -> Franklin Township Board of Trustees (OH)
- Fremont Auto Parts Inc -> Fremont Auto Parts (OH)
- Friends Service Company, Inc. -> Friends Service (OH)
- Frontier Signs & Displays Inc. -> Frontier Signs & Displays (OH)
- Frost Brown Todd LLC -> Frost Brown Todd (OH)
- Fuller Ford Inc -> Fuller Ford (OH)
- Fully Promoted Of Canton -> Fully Promoted of Canton (OH)
- Fulton Sign & Decal Inc. -> Fulton Sign & Decal (OH)
- Fusion LLC -> Fusion (OH)
- Ganley Automotive Of Aurora, LLC. -> Ganley Automotive of Aurora (OH)
- Ganley Chevrolet Of Aurora LLC -> Ganley Chevrolet of Aurora (OH)
- Ganley Village, LLC -> Ganley Village (OH)
- Garage Door Plus, Inc. -> Garage Door Plus (OH)
- Garvey Equipment Company -> Garvey Equipment (CA)
- Geer Gas Corporation -> Geer Gas (OH)
- Gene Ptacek & Son Fire Equipment, Inc. -> Gene Ptacek & Son Fire Equipment (OH)
- Generator One LLC -> Generator One (OH)
- Generator Specialist Inc -> Generator Specialist (OH)
- Generator Systems, LLC -> Generator Systems (OH)
- Geotechnical Consultants, Inc. -> Geotechnical Consultants (OH)
- Geotechnology Inc. -> Geotechnology (OH)
- Gingerich Trailer Sales Ltd -> Gingerich Trailer Sales (OH)
- Glenwood Electric Inc -> Glenwood Electric (OH)
- Global Emergency Vehicles, Inc -> Global Emergency Vehicles (OH)
- Global Equipment Company -> Global Equipment (OH)
- Global Training Academy, Inc -> Global Training Academy (OH)
- Gmelectric, Inc -> Gmelectric (OH)
- Goldstar Construction Group, LLC -> Goldstar Construction Group (OH)
- Goodyear Tire & Rubber Company -> Goodyear (OH)
- Goodyear Tire Co. -> Goodyear (OH)
- Gordon Flesch Company Inc -> Gordon Flesch (OH)
- Gouge Quality Roofing LLC -> Gouge Quality Roofing (OH)
- Graft Electric, Inc. -> Graft Electric (OH)
- Granlibakken Management Co -> Granlibakken Management (CA)
- Gravotech Inc -> Gravotech (OH)
- Graybar Electric Company -> Graybar Electric (CA)
- Great America Leasing Corp. -> Great America Leasing (OH)
- Great Lakes Ace Hardware Inc -> Great Lakes Ace Hardware (OH)
- Great Lakes Petroleum Co -> Great Lakes Petroleum (OH)
- Great Oak Construction Inc -> Great Oak Construction (OH)
- Great Oaks Institute Of -> Great Oaks Career Campuses (OH)
- Greene County Board Of Commissioners -> Greene County Board of Commissioners (OH)
- Greenwalt Lawn & Landscape LLC -> Greenwalt Lawn & Landscape (OH)
- Greve Chrysler Jeep Dodge Of -> Greve Chrysler Jeep Dodge of (OH)
- Grismer Tire Company -> Grismer Tire (OH)
- Groover Roofing & Siding, Inc. -> Groover Roofing & Siding (OH)
- Gross Plumbing Inc -> Gross Plumbing (OH)
- Grove City Garage Door, Inc. -> Grove City Garage Door (OH)
- Gta Fleet Solutions Inc -> Gta Fleet Solutions (OH)
- Guerra Maintenance And Construction -> Guerra Maintenance and Construction (OH)
- Guttman Energy, Inc. -> Guttman Energy (OH)
- H & W Door Company -> H & W Door (OH)
- H. Lull Construction Co -> H. Lull Construction (OH)
- H2O To Go -> H2O to Go (CA)
- HSI Investigations Inc. -> HSI Investigations (OH)
- Haddad Security, LLC -> Haddad Security (OH)
- Halcore Group, Inc -> Halcore Group (OH)
- Hallmark Incorporated -> Hallmark (OH)
- Hamilton Township Board Of Trustees -> Hamilton Township Board of Trustees (OH)
- Hangar 14 Solutions LLC -> Hangar 14 Solutions (OH)
- Hanna, Campbell & Powell, LLP -> Hanna, Campbell & Powell (OH)
- Happy Day Corporation -> Happy Day (ID)
- Harrison Fleet Tire Service, Inc. -> Harrison Fleet Tire Service (OH)
- Harry & Tim Roofing LLC -> Harry & Tim Roofing (OH)
- Hartville Hardware Inc -> Hartville Hardware (OH)
- Hatman Consulting LLC -> Hatman Consulting (OH)
- Haywood Electric Inc -> Haywood Electric (OH)
- HazMatOhio LLC -> HazMatOhio (OH)
- Health & Fitness Inc. -> Health & Fitness (OH)
- Health Care Logistics Inc. -> Health Care Logistics (OH)
- Heart of Ohio HVAC, Plumbing & Electric, LLC. -> Heart of Ohio HVAC, Plumbing & Electric (OH)
- Heinrich Law (client trust account) -> Heinrich Law (CA)
- Helmling Excavating, LLC -> Helmling Excavating (OH)
- Hendy Inc. -> Hendy (OH)
- Heritage Fire Equipment LLC -> Heritage Fire Equipment (OH)
- High Risk Training, LLC -> High Risk Training (OH)
- Highfield Door Sales LLC -> Highfield Door Sales (OH)
- Hightowers Petroleum Co. -> Hightowers Petroleum (OH)
- Hill International Trucks LLC -> Hill International Trucks (OH)
- Hinds Lawn Care & Landscaping LLC -> Hinds Lawn Care & Landscaping (OH)
- Hittle Roofing, Inc. -> Hittle Roofing (OH)
- Hoffman Electric Co, Inc -> Hoffman Electric (OH)
- Holland Computers Inc -> Holland Computers (OH)
- Holthaus Plumbing Company -> Holthaus Plumbing (OH)
- Home Appliance Co -> Home Appliance (OH)
- Homenik Door Co -> Homenik Door (OH)
- Horton Emergency Vehicle Co -> Horton Emergency Vehicles (OH)
- Hr Butler LLC -> Hr Butler (OH)
- Hsi Emergency Care Solutions, Inc. -> Hsi Emergency Care Solutions (OH)
- Hudson, City Of -> Hudson, City of (OH)
- Humana Insurance Co. -> Humana Insurance (OH)
- Humanadental Ins. Co. -> Humanadental Ins. (OH)
- Humboldt Redwood Company -> Humboldt Redwood (CA)
- Huntington Trust Company -> Huntington Bank (OH)
- I Supply Company -> I Supply (OH)
- Impact Fleet Service, Inc. -> Impact Fleet Service (OH)
- In Command Coaching & Consulting, LLC -> In Command Coaching & Consulting (OH)
- Indiana Dept. Of Revenue -> Indiana Dept. of Revenue (OH)
- Indoff Incorporated -> Indoff (OH)
- Insurance Specialists Group, Inc -> Insurance Specialists Group (OH)
- Insurance trust (group insurance) -> Insurance trust (OH)
- Intech Computer Solutions Inc -> Intech Computer Solutions (OH)
- International Association Of Firefighters -> International Association of Fire Fighters (OH)
- International Environmental Corporation -> International Environmental (CA)
- Interstate Oil Company -> Interstate Oil (CA)
- Invisio Communications, Inc. -> Invisio Communications (OH)
- It Made Real LLC -> It Made Real (OH)
- J & J Pumbing, Heating, & Cooling, LLC -> J & J Pumbing, Heating, & Cooling (OH)
- J & M Remodeling & Construction LLC -> J & M Remodeling & Construction (OH)
- J Meeker Co -> J Meeker (CA)
- J&K Truck And Trailer Repair -> J&K Truck and Trailer Repair (OH)
- J.R. Sbrocco Plumbing Inc. -> J.R. Sbrocco Plumbing (OH)
- Jack's Tire & Automotive Center, Inc. -> Jack's Tire & Automotive Center (OH)
- Jackson Petroleum, LLC -> Jackson Petroleum (OH)
- Jackson Township (internal charge) -> Jackson Township (OH)
- Jackson Township Central Maintenance (internal charge) -> Jackson Township Central Maintenance (OH)
- Jackson Twp. Trustees, Hardin Co. -> Jackson Twp. Trustees, Hardin (OH)
- Jam Best One Tire & Service Of Amherst -> Jam Best One Tire & Service of Amherst (OH)
- Janc Construction Company -> Janc Construction (CA)
- Jani Auto Parts* -> Jani Auto Parts (OH)
- Janitors Supply Inc -> Janitors Supply (OH)
- Jarrell Construction Co., L.L.C. -> Jarrell Construction (OH)
- Jay Petroleum, Inc. -> Jay Petroleum (OH)
- Jay-Car Construction Inc. -> Jay-Car Construction (OH)
- Jaymac Body & Frame, Inc. -> Jaymac Body & Frame (OH)
- Jdm Structures, Ltd. -> Jdm Structures (OH)
- Jefferson Smith LLC -> Jefferson Smith (TX)
- Jefferson Township Board Of Trustees -> Jefferson Township Board of Trustees (OH)
- Jennings Tent Company -> Jennings Tent (CA)
- Jmr Plumbing Services LLC -> Jmr Plumbing Services (OH)
- Jnj Cleaning Technologies, LLC -> Jnj Cleaning Technologies (OH)
- Joe Klosterman Plumbing, Inc -> Joe Klosterman Plumbing (OH)
- John D. Preuer & Associates, Inc -> John D. Preuer & Associates (OH)
- John Jones Automotive Dealerships, Inc. -> John Jones Automotive Dealerships (OH)
- John Madonna Const Co -> John Madonna Const (CA)
- John Preur And Associates -> John Preur and Associates (OH)
- John R. Jurgensen Co. -> John R. Jurgensen (OH)
- Johnson-Laux Construction, LLC -> Johnson-Laux Construction (OH)
- Joyce Buick GMC Inc -> Joyce Buick GMC (OH)
- Junction Buick, Pontiac, Gmc, Inc. -> Junction Buick, Pontiac, Gmc (OH)
- K Tire Inc. -> K Tire (OH)
- Kalida Truck Equipment, Inc. -> Kalida Truck Equipment (OH)
- Kastner Westman & Wilkins, LLC -> Kastner Westman & Wilkins (OH)
- Keith's Truck & Trailer, Inc. -> Keith's Truck & Trailer (OH)
- Keller Plumbing LLC -> Keller Plumbing (OH)
- Kerry Ford Inc -> Kerry Ford (OH)
- Key Chrysler Jeep, Dodge, Inc -> Key Chrysler (OH)
- Key Chysler Plymouth, Inc. -> Key Chysler Plymouth (OH)
- Kiddle's Auto LLC -> Kiddle's Auto (OH)
- Kinetic Business By Windstream -> Kinetic Business by Windstream (OH)
- Klaben Ford Lincoln Of Warren Inc. -> Klaben Ford Lincoln of Warren (OH)
- Klassen Corporation -> Klassen (CA)
- Kolsom Tire Co. -> Kolsom Tires (OH)
- Korrect Plumbing Co. -> Korrect Plumbing (OH)
- Kreiger Ford Inc. -> Kreiger Ford (OH)
- Krieger Ford Inc. -> Krieger Ford (OH)
- Kronos Saashr Inc -> Kronos Saashr (OH)
- Krugliak Wilkins Griffiths & Dougherty Co, Lp -> Krugliak Wilkins Griffiths & Dougherty (OH)
- Kuhls Hot Sportspot Inc -> Kuhls Hot Sportspot (OH)
- Kyle W. Jones, Attorney At Law -> Kyle W. Jones, Attorney at Law (OH)
- L.I. Proliner Inc -> L.I. Proliner (OH)
- LK Concrete Construction, LLC -> LK Concrete Construction (OH)
- LOGIC (regional dispatch) -> LOGIC (OH)
- Lac-mac Limited -> Lac-mac (CA)
- Lake Co. Board Of Commissioners -> Lake Co. Board of Commissioners (OH)
- Lake County Board Of Commissioners -> Lake County Board of Commissioners (OH)
- Lake County Department Of Utilities -> Lake County Department of Utilities (OH)
- Lakeland Glass Company -> Lakeland Glass (OH)
- Lance Roofing & Siding, Inc. -> Lance Roofing & Siding (OH)
- Lanigan Heating & Air Conditioning, LLC -> Lanigan Heating & Air Conditioning (OH)
- Larsen Architects, Inc. -> Larsen Architects (OH)
- Law Office of Eric Williams, LLC -> Law Office of Eric Williams (OH)
- Lbp Leasing Inc. -> Lbp Leasing (OH)
- Leach Painting Contractors, LLC -> Leach Painting Contractors (OH)
- Leadership Under Fire, Inc. -> Leadership Under Fire (OH)
- Leake Oil Co. -> Leake Oil (OH)
- Legacy Heating And Cooling -> Legacy Heating and Cooling (OH)
- Legend Investments Corporation -> Legend Investments (ID)
- Leiden Woodworking, LLC -> Leiden Woodworking (OH)
- Lepage Company -> Lepage (CA)
- Liberty Ford Canton, LLC -> Liberty Ford (OH)
- Liberty Ford Lincoln Mercury Inc -> Liberty Ford (OH)
- Life Extensions Clinic, Inc. -> Life Extension Clinics (OH)
- Life Insurance Company Of -> Life Insurance Company of (OH)
- Life Insurance Company Of Nort -> Life Insurance Company of Nort (OH)
- Life Insurance Company Of North America -> Life Insurance Company of North America (OH)
- Lifecare Ambulance, Inc. -> Lifecare Ambulance (OH)
- Lima Asphalt And Paving Corporation -> Lima Asphalt and Paving (OH)
- Lima Radio Hospital, Inc. -> Lima Radio Hospital (OH)
- Lincoln Investment (retirement plan) -> Lincoln Investment (OH)
- Lincoln Property Company -> Lincoln Property (TX)
- Linde Gas North America LLC -> Linde Gas & Equipment (OH)
- Lion Group, Inc -> LION (OH)
- Liquid Spring LLC. -> Liquid Spring (OH)
- Littler Mendelson, P.C. -> Littler Mendelson (OH)
- Logicalis, Inc. -> Logicalis (OH)
- Logocalis, Inc. -> Logocalis (OH)
- Longworth Property Services LLC -> Longworth Property Services (OH)
- Lorain County Data LLC -> Lorain County Data (OH)
- Loveland Community Firefighter's Assoc, -> Loveland Community Firefighter's Assoc (OH)
- Loyal American Life Insurance Co. -> Loyal American Life Insurance (OH)
- Lucas Truck Sales Inc -> Lucas Truck Sales (OH)
- Lunteys Mountain Water Company -> Lunteys Mountain Water (CA)
- Lyden Oil Company -> Lyden Oil (OH)
- Lykins Energy Solutions* -> Lykins Energy Solutions (OH)
- Lykins Oil Company -> Lykins Oil (OH)
- Lyons Lp Gas Co., Inc. -> Lyons Lp Gas (OH)
- M & M Aspahlt LLC -> M & M Aspahlt (OH)
- M&R Electric Motor Service, Inc. -> M&R Electric Motor Service (OH)
- MCKEE Paving Co. -> MCKEE Paving (OH)
- MS Consultants, Inc. -> MS Consultants (OH)
- Mac's Auto Parts Co. -> Mac's Auto Parts (OH)
- Magic Garage Door Inc -> Magic Garage Door (OH)
- Magnetic Springs Water Company -> Magnetic Springs Water (OH)
- Magulac's Tire Service, Inc. -> Magulac's Tire Service (OH)
- Maines Collision Repair & Body Shop Inc -> Maines Collision Repair & Body Shop (OH)
- Mainline Truck And Trailer Service -> Mainline Truck and Trailer Service (OH)
- Majestic Nursery Co -> Majestic Nursery (OH)
- Major Waste Disposal Services, Inc. -> Major Waste Disposal Services (OH)
- Mann Parsons Gray Architects, Inc -> Mann Parsons Gray Architects (OH)
- Mansfield Oil Company of Gainesville In -> Mansfield Oil Company of Gainesville in (CA)
- Marion Community Credit Union, Inc. -> Marion Community Credit Union (OH)
- Mark Spaulding Construction Co. -> Mark Spaulding Construction (OH)
- Marker Construction Co -> Marker Construction (OH)
- Masters Electrical Services Corp. -> Masters Electrical Services (OH)
- Matrix Trust (retirement plan) -> Matrix Trust (OH)
- Maxie Tire & Supply Co -> Maxie Tire & Supply (OH)
- Maxim Roofing Co. -> Maxim Roofing (OH)
- Mc Neil And Company Inc -> McNeil & Company (OH)
- McBurney Concrete, Inc. -> McBurney Concrete (OH)
- McCarty Associates, LLC -> McCarty Associates (OH)
- McKNIGHT & HOSTERMAN ARCHITECTS INC. -> McKNIGHT & HOSTERMAN ARCHITECTS (OH)
- McNaughton-McKay Electric Co. -> McNaughton-McKay Electric (OH)
- Mccluskey Chevrolet Inc* -> Mccluskey Chevrolet (OH)
- Mccormick Equipment Company, Inc. -> Mccormick Equipment (OH)
- Mcgowan Fire Company -> Mcgowan Fire (CA)
- Mcgranahan & Assoc. Inc. -> Mcgranahan & Assoc. (OH)
- Mcintosh Oil Co Inc -> Mcintosh Oil (OH)
- Mcintosh Painting Co. -> Mcintosh Painting (OH)
- Mechanical Systems Of Dayton -> Mechanical Systems of Dayton (OH)
- Medianet Av, LLC -> Medianet Av (OH)
- Medical Priority Consultants Inc -> Medical Priority Consultants (OH)
- Medline Industries, Lp -> Medline Industries (OH)
- Mellon Trust Of New England, N -> Mellon Trust of New England, N (OH)
- Melzer's Fuel Service Inc -> Melzer's Fuel Service (OH)
- Mendocino Forest Prod Co -> Mendocino Forest Prod (CA)
- Mendocino Redwood Co -> Mendocino Redwood (CA)
- Merchants National Bank (payroll) -> Merchants National Bank (OH)
- Michel Plumbing Inc -> Michel Plumbing (OH)
- Michigan Kenworth, LLC -> Michigan Kenworth (OH)
- Mid-City Electric Co -> Mid-City Electric (OH)
- Middlefield Banking Company -> Middlefield Banking (OH)
- Middletown Electric Supply Inc -> Middletown Electric Supply (OH)
- Midway Chevrolet Inc. -> Midway Chevrolet (OH)
- Midway Electronics Inc -> Midway Electronics (OH)
- Midwest Cylinder Company -> Midwest Cylinder (OH)
- Midwest Fire Equipment & Repair Company -> Midwest Fire Equipment & Repair (OH)
- Mike Castrucci Ford Inc -> Mike Castrucci Ford (OH)
- Millcraft Paper Co -> Millcraft Paper (OH)
- Millers Clothing And Shoes -> Millers Clothing and Shoes (OH)
- Minerva Bunker Gear Cleaners Of Ohio C -> Minerva Bunker Gear Cleaners of Ohio C (OH)
- Minor Insurance Agency, LLC -> Minor Insurance Agency (OH)
- Minton Door Service, Inc. -> Minton Door Service (OH)
- Mnj Technologies Direct Inc -> MNJ Technologies (OH)
- Mobile Radio Communications LLC -> Mobile Radio Communications (OH)
- Mobile Sleeper Company -> Mobile Sleeper (CA)
- Modern Office Products, Inc. -> Modern Office Products (OH)
- Monroeville Freightliner Inc -> Monroeville Freightliner (OH)
- Montgomery Cty Office Of Emerg -> Montgomery Cty Office of Emerg (OH)
- Montrose Ford, LLC -> Montrose Ford (OH)
- Morrow Painting LLC -> Morrow Painting (OH)
- Mount Carmel Healthproviders, Inc. -> Mount Carmel Healthproviders (OH)
- Mr Trailer Sales, Inc. -> Mr Trailer Sales (OH)
- Mt Business Technologies, Inc. -> Mt Business Technologies (OH)
- Muha Construction Inc -> Muha Construction (OH)
- Multi-Vendor For Wh Employees -> Multi-Vendor for Wh Employees (OH)
- Mun. Of Brookville -> Mun. of Brookville (OH)
- Municipal Signs & Sales Inc -> Municipal Signs & Sales (OH)
- Murphy Contracting Co. -> Murphy Contracting (OH)
- Myers Tire Supply Co -> Myers Tire Supply (OH)
- National Health Insurance Company -> National Health Insurance (OH)
- National Institute For Public Safety Tech. -> National Institute for Public Safety Tech. (OH)
- National Oil & Gas Inc -> National Oil & Gas (OH)
- Navigator Construction, LLC -> Navigator Construction (OH)
- Need A Door & More, LLC -> Need A Door & More (OH)
- Nelbud Services Group, Inc -> Nelbud Services (OH)
- Neo Electric Supply Co -> Neo Electric Supply (OH)
- New Start Construction LLC -> New Start Construction (OH)
- Nichols Paper & Supply Company -> Nichols Paper & Supply (OH)
- Nieman Plumbing, Inc -> Nieman Plumbing (OH)
- Nixco Plumbing, Inc -> Nixco Plumbing (OH)
- Noble Plumbing Inc -> Noble Plumbing (OH)
- Noble Reynolds Insurance Company -> Noble Reynolds Insurance (OH)
- North Canton Community Improvement Corporation -> North Canton Community Improvement (OH)
- North Canton Truck Ctr Inc -> North Canton Truck Ctr (OH)
- North Dixie Truck & Trailer Inc -> North Dixie Truck & Trailer (OH)
- Northeastern Electric Inc -> Northeastern Electric (OH)
- Northgate Tire Co., Inc. -> Northgate Tire (OH)
- Northwest Savings Bank (payroll) -> Northwest Savings Bank (OH)
- Norwalk Hardware, Ltd -> Norwalk Hardware (OH)
- Nu-Look Cleaning LLC -> Nu-Look Cleaning (OH)
- Nuwave Technology Inc. -> Nuwave Technology (OH)
- O'Reilly Automotive Stores, Inc. -> O'Reilly Automotive Stores (OH)
- O.R. Colan Associates, LLC -> O.R. Colan Associates (OH)
- OK Interiors Corp. -> OK Interiors (OH)
- Oak To Timberline Fire Safe -> Oak to Timberline Fire Safe (CA)
- Oakley Hospitality Group, Inc. -> Oakley Hospitality Group (OH)
- Occupational Health Centers Of -> Occupational Health Centers of (OH)
- Occupational Health Centers of Ohio, P.A., Co -> Occupational Health Centers of Ohio, P.A. (OH)
- Office Furniture,LLC -> Office Furniture (OH)
- Ohio Billing, Inc -> Ohio Billing (OH)
- Ohio Department Of Job & Famil -> Ohio Department of Job & Famil (OH)
- Ohio Dept Of Administrative Services -> Ohio Dept of Administrative Services (OH)
- Ohio Dept Of Job & Family Serv -> Ohio Dept of Job & Family Serv (OH)
- Ohio Dept Of Job/Family Serv -> Ohio Dept of Job/Family Serv (OH)
- Ohio Dept. Of Commerce C/O Ashley Campbell -> Ohio Dept. of Commerce C/O Ashley Campbell (OH)
- Ohio First Responders Grants, LLC -> Ohio First Responder Grants (OH)
- Ohio Gas Company -> Ohio Gas (OH)
- Ohio Paving & Construction Co., Inc. -> Ohio Paving & Construction (OH)
- Ohio Polygraph & Associates, LLC -> Ohio Polygraph & Associates (OH)
- Ohio Power Company -> Ohio Power (OH)
- Ohio Power Tool Inc -> Ohio Power Tool (OH)
- Ohio Public Risks Insurance Agency, Inc. -> Ohio Public Risk Insurance Agency (OH)
- Ohio Treasurer Of State -> Treasurer of State of Ohio (OH)
- Ohio Treasurer Of State-Dept Of Administrativ -> Ohio Treasurer of State-Dept of Administrativ (OH)
- Ohio Uav Services LLC -> Ohio Uav Services (OH)
- Ohio, Treasurer State Of -> Ohio, Treasurer State of (OH)
- Old Fort Banking Company -> Old Fort Banking (OH)
- Olinger Landscapes LLC -> Olinger Landscapes (OH)
- Olsavsky Jaminet Architects, Inc. -> Olsavsky Jaminet Architects (OH)
- Omega Door Company -> Omega Door (OH)
- One Click Away IT, LLC -> One Click Away IT (OH)
- One Stop Signs LLc -> One Stop Signs (OH)
- Onix Networking Corporation -> Onix Networking (OH)
- Oracle Elevator Co. -> Oracle Elevator (OH)
- Orlo Auto Parts, Inc -> Orlo Auto Parts (OH)
- Orrville Plbg & Heating Inc -> Orrville Plbg & Heating (OH)
- Orwell Oil Co. -> Orwell Oil (OH)
- Osburn Associates, Inc -> Osburn Associates (OH)
- Oster Sand & Gravel Inc -> Oster Sand & Gravel (OH)
- Overhead Door Co Of Cinci -> Overhead Door Co of Cinci (OH)
- Overhead Door Co Of Northern Ky -> Overhead Door Co of Northern Ky (OH)
- Overhead Door Of Greater Cincinnati -> Overhead Door of Greater Cincinnati (OH)
- Overhead Door Of Greater Cincinnati, In. -> Overhead Door of Greater Cincinnati, In. (OH)
- Overhead Door Of Greater Cinti -> Overhead Door of Greater Cinti (OH)
- Overhead Door Of Pike Co -> Overhead Door of Pike (OH)
- Overhead Door Of Pike County -> Overhead Door of Pike County (OH)
- Paper City Fire Protection LLC -> Paper City Fire Protection (OH)
- Paul's Car Care, LLC -> Paul's Car Care (OH)
- Paumier Medical Management Group, Inc -> Paumier Medical Management Group (OH)
- Pavement Technology Inc -> Pavement Technology (OH)
- Paylocity Corporation -> Paylocity (OH)
- Payroll - City Of Wapakoneta -> Payroll (OH)
- Payroll Select Service LLC -> Payroll Select Service (OH)
- Penserv Plan Services Inc -> PenServ (OH)
- Performance Redefined Corporation -> Performance Redefined (OH)
- Pest Off Exterminators LLC -> Pest Off Exterminators (OH)
- Peterman Plumbing And Heating -> Peterman Plumbing and Heating (OH)
- Pettibone Construction Inc. -> Pettibone Construction (OH)
- Pfann Enterprises LLC -> Pfann Enterprises (OH)
- Phillips Heating And Air Conditioning LLC -> Phillips Heating and Air Conditioning (OH)
- Phillips Supply Co. -> Phillips Supply (OH)
- Pickaway-Ross Career And Technology Center -> Pickaway-Ross Career and Technology Center (OH)
- Pierce Township Professional Firefighters (union) -> Pierce Township Professional Firefighters (OH)
- Pillar Insurance Agency, Inc -> Pillar Insurance Agency (OH)
- Pilot Travel Centers LLC -> Pilot Travel Centers (OH)
- Pinnacle Construction & Dev. Group, Inc -> Pinnacle Construction & Dev. Group (OH)
- Pinnacle Public Finance, Inc. -> Pinnacle Public Finance (OH)
- Pitney Bowes Bank, Inc -> Pitney Bowes Bank (OH)
- Pitsch Plumbing & Heating Company, Inc. -> Pitsch Plumbing & Heating (OH)
- Pitts Fire Extinguisher Inc -> Pitts Fire Extinguisher (OH)
- Pk Designs, Inc. -> Pk Designs (OH)
- Pl Vulcan Fire Training Concepts, LLC -> Pl Vulcan Fire Training Concepts (OH)
- Placer Title Company -> Placer Title (CA)
- Plain Township (payroll and benefits) -> Plain Township (OH)
- Platinum Restoration Cleaning Inc -> Platinum Restoration Cleaning (OH)
- Plattenburg & Associates Inc -> Plattenburg & Associates (OH)
- Plumas Corporation -> Plumas (CA)
- Pneu-Matic Engineering, Inc -> Pneu-Matic Engineering (OH)
- Police/Fire Disability And Pension Fund -> Police/Fire Disability and Pension Fund (OH)
- Poly-Tech & Associates, Inc. -> Poly-Tech Associates (OH)
- Pony Powersports Group, LLC -> Pony Powersports Group (OH)
- Poulos + Schmid Design Group, Inc. -> Poulos + Schmid Design Group (OH)
- Premier Truck Parts, Inc. -> Premier Truck Parts (OH)
- Premiere Builders Supply Inc -> Premiere Builders Supply (OH)
- Preston Ford, Inc. -> Preston Ford (OH)
- Primary Pharmaceuticals Inc. -> Primary Pharmaceuticals (OH)
- Princeton Tire Co -> Princeton Tire (OH)
- Pro Air Inc. -> Pro Air (OH)
- Pro Coat Ltd. -> Pro Coat (OH)
- Pro-Art Signs LLC -> Pro-Art Signs (OH)
- Prodigy EMS, Inc -> Prodigy EMS (OH)
- Progressive Intelligence Technologies, LLC -> Progressive Intelligence Technologies (OH)
- Protech Security Inc -> Protech Security (OH)
- Psychological & Family Consultants, Inc. -> Psychological & Family Consultants (OH)
- Ptacek & Son Fire Equipment Inc -> Ptacek & Son Fire Equipment (OH)
- Public Safety Services Of The Oaks -> Public Safety Services of the Oaks (OH)
- Quadmed, Inc. -> Quadmed (OH)
- Quality Overhead Door, Inc. -> Quality Overhead Door (OH)
- Quanta LLC -> Quanta (OH)
- Quinn Company -> Quinn (CA)
- R & S Truck Caps Of Akron Inc -> R & S Truck Caps of Akron (OH)
- R T Hampton Plumb & Heat Inc -> R T Hampton Plumb & Heat (OH)
- R&S Truck Caps And Accessories, LLC -> R&S Truck Caps and Accessories (OH)
- RB Equipment Co -> RB Equipment (CA)
- RITE Academy LLC -> RITE Academy (OH)
- RMH Concrete & Foundation, Inc. -> RMH Concrete & Foundation (OH)
- RS Logistics Inc -> RS Logistics (OH)
- Rack & Ballauer Excavating Co. -> Rack & Ballauer Excavating (OH)
- Ramsdell's Garage Inc. -> Ramsdell's Garage (OH)
- Randy Gravitt Leadership, LLC -> Randy Gravitt Leadership (OH)
- Randy Moore Petroleum Dist. LLC -> Randy Moore Petroleum Dist. (OH)
- Randy Moore Petroleum Distribution LLC -> Randy Moore Petroleum Distribution (OH)
- RapidScale Inc. -> RapidScale (OH)
- Raylecom Commun LLC -> Raylecom Commun (OH)
- Raylecom Communications LLC -> Raylecom Communications (OH)
- Rb's Truck & Trailer Service,Ltd -> Rb's Truck & Trailer Service (OH)
- Recker And Boerger -> Recker and Boerger (OH)
- Recology Sunset Scavenger Company -> Recology (CA)
- Red Diamond Uniform & Police Supply Inc. -> Red Diamond Uniform & Police Supply (OH)
- Red Hot Fire Equipment Co -> Red Hot Fire Equipment (OH)
- Redstone Architects, Inc -> Redstone Architects (OH)
- Redwood Empire Title Company -> Redwood Empire Title (CA)
- Reed Oil Company -> Reed Oil (OH)
- Reineke Ford Of Finley -> Reineke Ford of Finley (OH)
- Reliable Metal Building LLC -> Reliable Metal Building (OH)
- Residential Heating & Cooling LLC -> Residential Heating & Cooling (OH)
- Revac Usa, LLC -> Revac Usa (OH)
- Rich Holthaus Plumbing Co -> Rich Holthaus Plumbing (OH)
- Rich's Towing And Service, Inc. -> Rich's Towing and Service (OH)
- Richard L Bowen & Associates Inc -> Richard L Bowen & Associates (OH)
- Richard L. Bowen & Assoc, Inc -> Richard L. Bowen & Assoc (OH)
- Riedy Roofing Inc -> Riedy Roofing (OH)
- Right Stuff Software Corporation -> Right Stuff Software (OH)
- Riley Petroleum Products LLC -> Riley Petroleum Products (OH)
- River City Floor Care Co. -> River City Floor Care (OH)
- River City Supply, LLC -> River City Supply (OH)
- Rmc-Resource Manaement Consultants,LLC -> Rmc-Resource Management Consultants (OH)
- Robinson Ent Investment Co -> Robinson Ent Investment (CA)
- Rockmill Financial Consulting LLC -> Rockmill Financial Consulting (OH)
- Rocky Mountain Fire Company -> Rocky Mountain Fire (ID)
- Rocky's Hardware Co Inc -> Rocky's Hardware (OH)
- Rolland Specialty pVehicles & Products, Inc. -> Rolland Specialty pVehicles & Products (OH)
- Rolling & Sliding Doors Of Dayton Ltd -> Rolling & Sliding Doors of Dayton (OH)
- Rolta Advizex Technologies LLC -> Rolta Advizex Technologies (OH)
- Ron Marhofer Chevrolet Inc -> Ron Marhofer Chevrolet (OH)
- Rose Plumbing LLC -> Rose Plumbing (OH)
- Ross County Water Co. Inc. -> Ross County Water (OH)
- Roy Tailors Uniform Co. of Columbus, Inc -> Roy Tailors Uniform (OH)
- Rt Hampton Plbg & Htg Inc -> Rt Hampton Plbg & Htg (OH)
- Rtc Heating And Cooling, LLC -> Rtc Heating and Cooling (OH)
- Rugged Solutions America LLC -> Rugged Solutions America (OH)
- Rusty Nuts Fix It Shop, LLC -> Rusty Nuts Fix It Shop (OH)
- Rusty's Towing Srevices, INC. -> Rusty's Towing Service (OH)
- S S Tire & Repair Inc -> S S Tire & Repair (OH)
- S&G Painting Contractors, Inc. -> S&G Painting Contractors (OH)
- S&K Building Services, Inc. -> S&K Building Services (OH)
- S3D Public Safety Consultants LLC -> S3D Public Safety Consultants (OH)
- San Diego Police Equip Co -> San Diego Police Equip (CA)
- Sand Technologics LLC -> Sand Technologics (OH)
- Sandusky, City Of -> Sandusky, City of (OH)
- Sandy's Landscaping Inc -> Sandy's Landscaping (OH)
- Santander Bank Na -> Santander Bank (OH)
- Sarchione Chevrolet, Inc. -> Sarchione Chevrolet (OH)
- Savings Bank, The -> Savings Bank, the (OH)
- Schwarz Uniform Corporation -> Schwarz Uniform (OH)
- Scioto Valley Hot Tubs & Spas, Inc. -> Scioto Valley Hot Tubs & Spas (OH)
- Seagrave Fire Apparatus, LLC -> Seagrave Fire Apparatus (OH)
- Security & Polygraph Consultants, Inc -> Security & Polygraph Consultants (OH)
- Sedensky Truck and Tractor, LLC -> Sedensky Truck and Tractor (OH)
- Sedgwick Claims Management Services, Inc -> Sedgwick (OH)
- Sedgwick Claims Manangment Services, Inc -> Sedgwick (OH)
- Select Comfort Retail Corporation -> Select Comfort Retail (OH)
- Selectus Consulting, LLC -> Selectus Consulting (OH)
- Self-insurance fund (health) -> Self-insurance fund (OH)
- Servall Electric Company, Inc. -> Servall Electric (OH)
- Seven Seventeen Credit Union, Inc. -> Seven Seventeen Credit Union (OH)
- Shagovac Heating & Cooling Inc -> Shagovac Heating & Cooling (OH)
- Shamrock Foods Company -> Shamrock Foods (CA)
- Shane Fisk Roofing Inc -> Shane Fisk Roofing (OH)
- Shanklin Heating & Air Conditioning LLC -> Shanklin Heating & Air Conditioning (OH)
- Sheraton Redding Hotel AT the -> Sheraton Redding Hotel at the (CA)
- Shirley's Powder Coating LLC -> Shirley's Powder Coating (OH)
- Shuster Oil Co. -> Shuster Oil (CA)
- Shuttler's Apparel Inc. -> Shuttler's Uniform (OH)
- Shuttlers Uniforms Inc -> Shuttler's Uniform (OH)
- Siemens Industry Inc -> Siemens Industry (OH)
- Sign Pro Wraps, LLC -> Sign Pro Wraps (OH)
- Site Engineering Solutions, Inc. -> Site Engineering Solutions (OH)
- Small's Ashpalt Paving, Inc. -> Small's Ashpalt Paving (OH)
- Smedley's Chevrolet Sales Inc -> Smedley's Chevrolet Sales (OH)
- Snyder Collision Inc -> Snyder Collision (OH)
- Software Solutions, Inc. -> Software Solutions (OH)
- South Summit Council Of Government -> South Summit Council of Government (OH)
- Southern Computer Warehouse, Inc -> Southern Computer Warehouse (OH)
- Southway Fence Co -> Southway Fence (OH)
- Spear Corporation -> Spear (OH)
- Specialty Truck Repair, Inc. -> Specialty Truck Repair (OH)
- Specialty Truck Sales And Service -> Specialty Truck Sales and Service (OH)
- Speckman Automotive, Inc -> Speckman Automotive (OH)
- Spencer Manufacturing, Inc -> Spencer Manufacturing (OH)
- Springfield Truck Center, Inc -> Springfield Truck Center (OH)
- Springsteel Door Co. -> Springsteel Door (OH)
- Sprint Solutions Inc -> Sprint Solutions (OH)
- St Vincent Health Wellness And -> St Vincent Health Wellness and (OH)
- Stack Heating & Cooling, LLC -> Stack Heating & Cooling (OH)
- Standard Plumbing & Heating Co -> Standard Plumbing & Heating (OH)
- Star 2 Star Communications, LLC -> Star2Star Communications (OH)
- Star Consultants Inc. -> Star Consultants (OH)
- Stark Materials, Inc -> Stark Materials (OH)
- State Electric Supply Co -> State Electric Supply (OH)
- State Of Ohio -> State of Ohio (OH)
- State Of Ohio Treasurer -> State of Ohio Treasurer (OH)
- Steel Supply Co, Inc. -> Steel Supply (OH)
- Sterling May Equipment Co -> Sterling May Equipment (CA)
- Stock Enterprises, LLC -> Stock Enterprises (OH)
- Strand Associates, Inc. -> Strand Associates (OH)
- Stykemain Trucks Inc -> Stykemain Trucks (OH)
- Summit County Fiscal Officer* -> Summit County Fiscal Office (OH)
- Sunny Co munications LLC -> Sunny Communications (OH)
- Sunrise Cooperative, Inc -> Sunrise Cooperative (OH)
- Sunrise Springs Water Company -> Sunrise Springs Water (OH)
- Superior Petroleum Equipment, LLC -> Superior Petroleum Equipment (OH)
- Superior Spring Inc -> Superior Spring (OH)
- Sutphen Corporation -> Sutphen (OH)
- Swickard Gas Co -> Swickard Gas (OH)
- Symetra Life Insurance Company -> Symetra Life Insurance (OH)
- T R Snyder Construction Inc -> T R Snyder Construction (OH)
- T. Rowe Price Retirement Plan Services, Inc. -> T. Rowe Price Retirement Plan Services (OH)
- TASC (benefit accounts) -> TASC (OH)
- Tartan Benefit Services, Ltd -> Tartan Benefit Services (OH)
- Tax-Exempt Leasing Corp. -> Tax-Exempt Leasing (OH)
- Taylor Tire Company -> Taylor Tire (OH)
- Technicon Design Group, Inc. -> Technicon Design Group (OH)
- Technique Roofing Systems, LLC -> Technique Roofing Systems (OH)
- Tectronic Office Products, Inc. -> Tectronic Office Products (OH)
- Teledoc Inc. -> Teledoc (OH)
- Tfs Leasing Program Of De Lage -> Tfs Leasing Program of De Lage (OH)
- The Amazing Cloud, LLC -> The Amazing Cloud (OH)
- The Cabinet Co. -> The Cabinet (OH)
- The City Of Shaker Heights -> The City of Shaker Heights (OH)
- The Danielsen Co -> The Danielsen (CA)
- The Dover Tank & Plate Co. -> The Dover Tank & Plate (OH)
- The East Ohio Gas Company -> The East Ohio Gas (OH)
- The Farmers And Merchants Bank -> The Farmers and Merchants Bank (OH)
- The Garland Company -> The Garland (OH)
- The Illuminating Company -> The Illuminating (OH)
- The Lincoln National Life Insurance Company -> The Lincoln National Life Insurance (OH)
- The M. Conley Company -> The M. Conley (OH)
- The McGlaughlin Oil Company -> The McGlaughlin Oil (OH)
- The Mobile Laundry Company -> The Mobile Laundry (CA)
- The Shelly Company -> The Shelly (OH)
- The Smith & Oby Service Company -> The Smith & Oby Service (OH)
- The Will-Burt Company -> The Will-Burt (OH)
- The Ziegler Tire & Supply Co Inc -> Ziegler Tire (OH)
- Thomas Gas Service, Inc. -> Thomas Gas Service (OH)
- Thompson Heating & Cooling Inc. -> Thompson Heating & Cooling (OH)
- Tim Lally Chevrolet Inc -> Tim Lally Chevrolet (OH)
- Tire And Wheel Auto Service Center -> Tire and Wheel Auto Service Center (OH)
- Titan Asphalt & Paving Inc. -> Titan Asphalt & Paving (OH)
- Tj Farm Service LLC -> Tj Farm Service (OH)
- Tom Dew Excavating Inc. -> Tom Dew Excavating (OH)
- Training Marbles Inc -> Training Marbles (OH)
- Trane U.S. Inc. -> Trane U.S. (OH)
- Trans Aero Limited -> Trans Aero (CA)
- Treas St Of Ohio -> Treasurer of State of Ohio (OH)
- Treas St Of Ohio, Fund 615 -> Treasurer of State of Ohio (OH)
- Treasure Of State Of Ohio -> Treasurer of State of Ohio (OH)
- Treasurer Of State - Uan -> Treasurer of State - Uan (OH)
- Treasurer Of State Of Ohio-Tax -> Treasurer of State of Ohio-Tax (OH)
- Treasurer Of State- Das Finance -> Treasurer of State- Das Finance (OH)
- Treasurer Of State- Odadas -> Treasurer of State- Odadas (OH)
- Treasurer Of State-Ohio Das -> Treasurer of State-Ohio Das (OH)
- Tri-Med Tactical, LLC -> Tri-Med Tactical (OH)
- Triad Technologies LLC -> Triad Technologies (OH)
- Trinity County Title Company -> Trinity County Title (CA)
- Trion Group (benefits) -> Trion Group (OH)
- Trippensee Construction Co. -> Trippensee Construction (OH)
- Tristate Preventive Health Consultants LLC -> Tristate Preventive Health Consultants (OH)
- Truck & Van Land Inc. -> Truck & Van Land (OH)
- Truckside Advertising Inc -> Truckside Advertising (OH)
- Trucraft Roofing LLC -> Trucraft Roofing (OH)
- Trustees Of Ashtabula Township -> Trustees of Ashtabula Township (OH)
- Tuned Care Inc -> Tuned Care (OH)
- Turk Construction, LLC -> Turk Construction (OH)
- Turnout Maintenance Co -> Turnout Maintenance (CA)
- Turnouts LLC -> Turnouts (OH)
- TyTek Medical, Inc. -> TyTek Medical (OH)
- U.S. Bank Trust Company -> U.S. Bank (OH)
- UAG Cerritos (auto dealer) -> UAG Cerritos (CA)
- UC HEALTH dba WEST CHESTER HOSPITAL LLC -> UC HEALTH dba WEST CHESTER HOSPITAL (OH)
- US Bank Equipment Financing, Inc -> U.S. Bank (OH)
- USDA Rural Development (loan) -> USDA Rural Development (OH)
- Ucpc Univer Of Cinti Emerg Med -> Ucpc Univer of Cinti Emerg Med (OH)
- Ullman Oil, Inc. -> Ullman Oil (OH)
- Underground Connections, LLC -> Underground Connections (OH)
- United Fire Apparatus Corporation -> United Fire Apparatus (OH)
- United Firefighters of Los Angeles City-local 112-iaff- Afl- -> United Firefighters of Los Angeles City-local 112-iaff- Afl (CA)
- Univ Of Cinti Physicians -> Univ of Cinti Physicians (OH)
- Universal Oil Inc -> Universal Oil (OH)
- University Corp AT Monterey -> University Corp at Monterey (CA)
- University Hospital Health Systems Inc -> University Hospitals Health System (OH)
- University Of Akron -> University of Akron (OH)
- University Of Cincinnati Physicians Com -> University of Cincinnati Physicians Com (OH)
- Us Bancorp Equip. Finance, Inc -> U.S. Bancorp Government Leasing & Finance (OH)
- V.I.P. Plumbing, Inc. -> V.I.P. Plumbing (OH)
- V.L. Chapman Electric, Inc. -> V.L. Chapman Electric (OH)
- Valley Firefighters Inc. -> Valley Firefighters (OH)
- Valley Ford Of Huron Inc -> Valley Ford of Huron (OH)
- Van Wert Fire Equipment Co. -> Van Wert Fire Equipment (OH)
- Vance Outdoors, Inc. -> Vance Outdoors (OH)
- Vandenbos Consulting LLC -> Vandenbos Consulting (OH)
- Vasco Asphalt Co -> Vasco Asphalt (OH)
- Vasu Communitcations, Inc. -> Vasu Communications (OH)
- Vectren Energy Services Corp -> Vectren Energy Services (OH)
- Vickers Consulting Services, Inc. -> Vickers Consulting Services (OH)
- Victory Air Mechanical LLC -> Victory Air Mechanical (OH)
- Village Hardware Inc. -> Village Hardware (OH)
- Village Of Amanda -> Village of Amanda (OH)
- Village Of Belmont Volunteer Fire & Emergency -> Village of Belmont Volunteer Fire & Emergency (OH)
- Village Of Bluffton -> Village of Bluffton (OH)
- Village Of Clinton -> Village of Clinton (OH)
- Village Of Dennison Income Tax Dept. -> Village of Dennison Income Tax Dept. (OH)
- Village Of Donnelsville -> Village of Donnelsville (OH)
- Village Of Elida -> Village of Elida (OH)
- Village Of Jackson Center -> Village of Jackson Center (OH)
- Village Of Jackson Center Utility Clerk -> Village of Jackson Center Utility Clerk (OH)
- Village Of Kingston -> Village of Kingston (OH)
- Village Of Lockland -> Village of Lockland (OH)
- Village Of Millersport -> Village of Millersport (OH)
- Village Of Mt Orab -> Village of Mt Orab (OH)
- Village Of Mt. Gilead -> Village of Mt. Gilead (OH)
- Village Of Payne -> Village of Payne (OH)
- Village Of South Lebanon -> Village of South Lebanon (OH)
- Village Of South Solon -> Village of South Solon (OH)
- Village Of South Zanesville -> Village of South Zanesville (OH)
- Village Of Spencerville -> Village of Spencerville (OH)
- Village Of Thurston -> Village of Thurston (OH)
- Village Of Valley View -> Village of Valley View (OH)
- Village Of Walbridge -> Village of Walbridge (OH)
- Village Of Waynesville -> Village of Waynesville (OH)
- Village Of West Lafayette -> Village of West Lafayette (OH)
- Vision Benefits Of America Inc -> Vision Benefits of America (OH)
- Vision Communications Company -> Vision Communications (CA)
- Visual Edge It, Inc -> Visual Edge It (OH)
- W.S. Eletronics LLC -> W.S. Electronics (OH)
- Walco Inc -> Walco (ID)
- Warren County Clerk Of Courts -> Warren County Clerk of Courts (OH)
- Warren Door Co. -> Warren Door (OH)
- Washington Marine, LLC -> Washington Marine (OH)
- Washington National Ins. Co. -> Washington National Ins. (OH)
- Washington National Insurance Co -> Washington National Insurance (OH)
- Water-Watts Inc. -> Water-Watts (OH)
- Waterway Of Southwest Pa, LLC -> Waterway (OH)
- Waterways of Southwest PA, LLC -> Waterway (OH)
- Wayne Electric Company -> Wayne Electric (CA)
- Wayne Garage Door Sales and Service Inc. -> Wayne Garage Door Sales and Service (OH)
- Wayne Township Board Of Trustees -> Wayne Township Board of Trustees (OH)
- Wayne Truck & Trailer Ltd -> Wayne Truck & Trailer (OH)
- Wellers Plumbing & Heating Inc. -> Wellers Plumbing & Heating (OH)
- Wesbanco Bank Inc -> Wesbanco (OH)
- West Roofing Systems, Inc. -> West Roofing Systems (OH)
- West Virginia Signal & Light Inc -> West Virginia Signal & Light (OH)
- Westerheide Construction Co -> Westerheide Construction (OH)
- Western Blue, an NWN Company -> Western Blue, an NWN (CA)
- Western Branch Diesel Inc -> Western Branch Diesel (OH)
- Western Ohio Rescue Supply Company -> Western Ohio Rescue Supply (OH)
- Western Ohio Truck And Fire LLC -> Western Ohio Truck and Fire (OH)
- Western Water Company -> Western Water (OH)
- Westgate Petroleum Co -> Westgate Petroleum (CA)
- Wharton Electric company -> Wharton Electric (OH)
- Whisler Plumbing & Heating Inc -> Whisler Plumbing & Heating (OH)
- Whispering Pines Sandwich Co. -> Whispering Pines Sandwich (CA)
- Wilhelm Construction Co -> Wilhelm Construction (OH)
- Willits Redwood Co -> Willits Redwood (CA)
- Wilson Electric Displays, LLC -> Wilson Electric Displays (OH)
- Windstream Western Reserve, Inc -> Windstream (OH)
- Wise Heating & Cooling LLC -> Wise Heating & Cooling (OH)
- Wood Electric, Inc. -> Wood Electric (OH)
- Woodstone Woodworks, LLC -> Woodstone Woodworks (OH)
- Worksmart Consultants, LLC -> Worksmart Consultants (OH)
- World Fuel Services, Inc. -> World Fuel Services (OH)
- Worly Plumbing Supply, Inc. -> Worly Plumbing Supply (OH)
- Xtek Partners, Inc. -> Xtek Partners (OH)
- Yipes Stripes Of Dayton -> Yipes Stripes of Dayton (OH)
- Ymca Of Central Stark County -> Ymca of Central Stark County (OH)
- Yoder Builders LTD -> Yoder Builders (OH)
- Youngstown Oxygen And Welding Supply -> Youngstown Oxygen and Welding Supply (OH)
- Your Lawn, Inc -> Your Lawn (OH)
- Zetron A Codan Company -> Zetron (CA)
- Zin's Plumbing LLC -> Zin's Plumbing (OH)
- Zuber Safety & Security, LLC -> Zuber Safety & Security (OH)
- iPAD MOBILE SOLUTIONS, LLC -> iPAD MOBILE SOLUTIONS (OH)
- iTech Managed Solutions, LLC -> iTech Managed Solutions (OH)
- policyBUILDERS, LLC -> policyBUILDERS (OH)

</details>

Names equal apart from a region that were kept apart (bodies that exist separately per state):

- State of Alaska / State of Colorado / State of New Mexico / State Of Ohio / State of South Dakota / State of Utah / State of Washington / State of Wyoming
- University of Utah / University of Washington

Names of local bodies (cities, counties, townships, fire departments, districts) that are equal in
several states were not grouped across states; equal names still share a vendor id:

- Milford Volunteer Fire Dept / Milford Volunteer Fire Department

Utah names in config/vendor_map.csv that fall into one group (left as they are):

- Bank of Utah / Bank (unspecified)

## Names set by a vendor rule

Keys a `config/vendor_rules.csv` pattern names: the row uses the rule's vendor.

| Key | State | Proposed canonical name | Rule's vendor |
| --- | --- | --- | --- |
| AT AND T MOBILITY CC | OH | At & T Mobility - Cc | AT&T |
| AT AND T MOBILITY NATIONAL ACCOUNTS | OH | At&T Mobility National Accounts | AT&T |
| AUTO ZONE | OH | Auto Zone | AutoZone |
| AUTOZONE COMMERCIAL | OH | Autozone Commercial | AutoZone |
| AUTOZONE STORES | OH | Autozone Stores | AutoZone |
| CDW G | OH | Cdw-G | CDW Government |
| DELL | OH | Dell | Dell Technologies |
| INTERNATIONAL ASSOC ARSON INV | OH | International Assoc Arson Inv | International Association of Arson Investigators |
| NARCBOX | OH | NarcBox | EMS LogiK |
| O REILLY AUTO PARTS | OH | O Reilly Auto Parts | O'Reilly Auto Parts |
| OREILLY AUTOMOTIVE STORES | OH | O'Reilly Automotive Stores | O'Reilly Auto Parts |
| OVERHEAD DOOR OF CINCI | OH | Overhead Door Co of Cinci | Overhead Door |
| OVERHEAD DOOR OF GREATER CINCINNATI | OH | Overhead Door of Greater Cincinnati | Overhead Door |
| OVERHEAD DOOR OF GREATER CINCINNATI IN | OH | Overhead Door of Greater Cincinnati, In. | Overhead Door |
| OVERHEAD DOOR OF GREATER CINTI | OH | Overhead Door of Greater Cinti | Overhead Door |
| OVERHEAD DOOR OF NORTHERN KY | OH | Overhead Door Co of Northern Ky | Overhead Door |
| OVERHEAD DOOR OF PIKE | OH | Overhead Door of Pike | Overhead Door |
| OVERHEAD DOOR OF PIKE COUNTY | OH | Overhead Door of Pike County | Overhead Door |
| PEDIATRIC EMERGENCY STANDARDS | OH | Pediatric Emergency Standards | Handtevy |
| REPUBLIC SERVICES 224 | OH | Republic Services #224 | Republic Services |
| REPUBLIC SERVICES 870 | OH | Republic Services #870 | Republic Services |
| RUSH TRUCK CENTER AKRON INTL | OH | Rush Truck Center Akron Intl | Rush Truck Centers |
| RUSH TRUCK CENTER CLEVELAND | OH | Rush Truck Center, Cleveland | Rush Truck Centers |
| SAMS CLUB BUSINESS SYNCHRONY BANK | OH | Sams Club Business/Synchrony Bank | Sam's Club |
| SAMS CLUB DIRECT | OH | Sam's Club Direct | Sam's Club |
| SAMS CLUB SYNCHRONY BANK | OH | Sam's Club / Synchrony Bank | Sam's Club |
| TRACTOR SUPPLY CREDIT PLAN | OH | Tractor Supply Credit Plan | Tractor Supply |
| WAL MART BUSINESS | OH | Wal-Mart Business | Walmart |
| WAL MART BUSINESS GEMB | OH | Wal-Mart Business/Gemb | Walmart |
| WAL MART STORE 1330 | OH | Wal Mart Inc. Store #1330 | Walmart |
| WALMART CAPITAL ONE | OH | Walmart - Capital One | Walmart |
| ZOLL DATA SYSTEMS | OH | Zoll Medical | Zoll Data Systems |

Keys where a rule's pattern catches another company; the reviewed name in
`config/vendor_name_merges.csv` is kept (the config/vendor_map.csv row decides before the rule):

- DELUXE DOOR SYSTEMS (OH): Deluxe Door Systems, not Deluxe
- JE DUNN CONSTRUCTION (TX): JE Dunn Construction, not No vendor named

Left out because the vendor rule already gives the same vendor and category (99):

- AIRGAS GAS USA -> Airgas / ems-supplies (OH, $21,720)
- AIRGAS GREAT LAKES -> Airgas / ems-supplies (OH, $89,579)
- AMAZON ACCOUNT -> Amazon / general (OH, $46,888)
- AMAZON BOOKS -> Amazon / general (ID, $69,010)
- AMAZON CAPITAL SERVICES NC -> Amazon / general (OH, $18,584)
- AMAZON CREDIT PLAN -> Amazon / general (OH, $20,576)
- AMAZON PAYMENTS -> Amazon / general (OH, $6,209)
- APPLE -> Apple / it (OH, $23,122)
- AT AND T MOBILITY ACCOUNTS -> AT&T / telecom (CA, $434,372)
- AT AND T MOBILITY CC -> AT&T / telecom (OH, $19,281)
- AT AND T MOBILITY II -> AT&T / telecom (OH/ID, $322,813)
- AT AND T MOBILITY NATIONAL ACCOUNTS -> AT&T / telecom (OH, $9,616)
- AUTO ZONE -> AutoZone / fleet (OH, $22,924)
- AUTOZONE COMMERCIAL -> AutoZone / fleet (OH, $17,401)
- AUTOZONE STORES -> AutoZone / fleet (OH, $5,067)
- BOUND TREE PARR -> Bound Tree Medical / ems-supplies (OH, $226,190)
- BOUNDTREE -> Bound Tree Medical / ems-supplies (OH, $12,294)
- CDW G -> CDW Government / it (OH, $35,630)
- DELL -> Dell Technologies / it (OH, $23,104)
- DOMINION ENERGY OHIO -> Enbridge Gas / utilities (OH, $184,670)
- ENBRIDGE GAS OHIO -> Enbridge Gas / utilities (OH, $157,987)
- ENTERPRISE CAR RENTAL -> Enterprise Rent-A-Car / fleet (ID, $64,256)
- FERNO -> Ferno / ems-equipment (OH, $13,692)
- FIRST ARRIVING -> First Arriving / software (OH, $75,544)
- HOLIDAY INN EXPRESS LEWI -> Holiday Inn Express / training (ID, $28,695)
- HOME DEPOT CRC -> Home Depot / facilities (OH, $20,288)
- HOME DEPOT CREDIT CARD SERVICE -> Home Depot / facilities (OH, $5,432)
- HOME DEPOT FIRE -> Home Depot / facilities (OH, $40,157)
- HOME DEPOT GECF -> Home Depot / facilities (OH, $18,063)
- HOME DEPOT PRO -> Home Depot / facilities (OH, $30,520)
- HOME DEPOT USA -> Home Depot / facilities (TX/OH, $308,514)
- INTERNATIONAL ASSOC ARSON INV -> International Association of Arson Investigators / training (OH, $15,754)
- INTERNATIONAL ASSOC OF FIRE CHIEFS -> International Association of Fire Chiefs / training (OH, $6,740)
- JONES AND BARTLETT PUBLISHERS -> Jones & Bartlett Learning / training (TX, $136,606)
- KEYBANK -> KeyBank / finance (OH, $105,180)
- LES SCHWAB WAREHOUSE CENTER -> Les Schwab / fleet (ID, $62,715)
- LOWES HOME CENTERS -> Lowe's / facilities (OH, $11,471)
- MUNICIPAL EMERGENCY SERVICE -> Municipal Emergency Services / fire-equipment (OH, $17,688)
- MUNICIPAL EMERGENCY SERVICES DEPOSIT ACCT -> Municipal Emergency Services / fire-equipment (OH, $15,177)
- MUNICIPAL EMERGENCY SERVICES DEPOSITORY -> Municipal Emergency Services / fire-equipment (OH, $9,780)
- MUNICIPAL EMERGENCY SERVICES DEPOSITORY ACCOU -> Municipal Emergency Services / fire-equipment (OH, $71,381)
- MUNICIPAL EMERGENCY SERVICES DEPOSITORY ACCT -> Municipal Emergency Services / fire-equipment (OH, $369,784)
- MUNICIPAL EMERGENCY SERVICES MES -> Municipal Emergency Services / fire-equipment (OH, $58,893)
- MUNICIPAL EMERGENCY SVCS -> Municipal Emergency Services / fire-equipment (OH, $395,636)
- NAPA -> NAPA Auto Parts / fleet (OH, $19,682)
- NAPA AUTO PARTS BROOKLYN -> NAPA Auto Parts / fleet (OH, $30,524)
- NARCBOX -> EMS LogiK / software (OH, $28,850)
- NATIONAL FIRE PROTECTION ASSOC -> NFPA / training (OH, $22,229)
- O REILLY AUTO PARTS -> O'Reilly Auto Parts / fleet (OH, $14,455)
- OREILLY AUTOMOTIVE STORES -> O'Reilly Auto Parts / fleet (OH, $42,832)
- OVERHEAD DOOR OF CINCI -> Overhead Door / facilities (OH, $6,831)
- OVERHEAD DOOR OF COVINGTON -> Overhead Door / facilities (OH, $76,487)
- OVERHEAD DOOR OF GREATER CINCINNATI -> Overhead Door / facilities (OH, $8,348)
- OVERHEAD DOOR OF GREATER CINCINNATI IN -> Overhead Door / facilities (OH, $11,600)
- OVERHEAD DOOR OF GREATER CINTI -> Overhead Door / facilities (OH, $15,847)
- OVERHEAD DOOR OF NORTHERN KY -> Overhead Door / facilities (OH, $53,770)
- OVERHEAD DOOR OF PIKE -> Overhead Door / facilities (OH, $10,714)
- OVERHEAD DOOR OF PIKE COUNTY -> Overhead Door / facilities (OH, $68,446)
- PEDIATRIC EMERGENCY STANDARDS -> Handtevy / software (OH, $71,053)
- REPUBLIC SERVICES 224 -> Republic Services / utilities (OH, $6,996)
- REPUBLIC SERVICES 870 -> Republic Services / utilities (OH, $8,307)
- ROSENBAUER OF SOUTH DAKOTA -> Rosenbauer / apparatus (OH, $388,060)
- RUSH TRUCK CENTER AKRON INTL -> Rush Truck Centers / fleet (OH, $29,018)
- RUSH TRUCK CENTER CLEVELAND -> Rush Truck Centers / fleet (OH, $31,794)
- RUSH TRUCK CENTER OF CA -> Rush Truck Centers / fleet (CA, $1,877,320)
- RUSH TRUCK CENTERS -> Rush Truck Centers / fleet (OH, $32,161)
- RUSH TRUCK CENTERS OF OHIO -> Rush Truck Centers / fleet (OH, $189,796)
- RUSH TRUCK CENTERS OF TEXAS LP -> Rush Truck Centers / fleet (TX, $163,184)
- SAMS CLUB BUSINESS SYNCHRONY BANK -> Sam's Club / general (OH, $4,289)
- SAMS CLUB DIRECT -> Sam's Club / general (OH, $69,540)
- SAMS CLUB SYNCHRONY BANK -> Sam's Club / general (OH, $25,608)
- SPRINGHILL SUITES BOIS -> SpringHill Suites / training (ID, $71,456)
- STAPLES ADVANTAGE -> Staples / general (OH, $127,658)
- STAPLES BUSINESS ADVANTAGE -> Staples / general (CA/OH, $2,325,247)
- STRYKER EMS -> Stryker / ems-equipment (OH, $80,115)
- STRYKER EMS EQUIPMENT -> Stryker / ems-equipment (OH, $643,007)
- STRYKER EMS EQUIPMENT SALES -> Stryker / ems-equipment (OH, $80,894)
- STRYKER FLEET FINANCIAL -> Stryker / ems-equipment (OH, $545,763)
- STRYKER FLEX FINANCIAL -> Stryker / ems-equipment (OH, $197,016)
- STRYKER MED -> Stryker / ems-equipment (OH, $124,879)
- STRYKER SALES CORPORATON -> Stryker / ems-equipment (OH, $754,306)
- STRYKER SALES STRYKER MEDICAL -> Stryker / ems-equipment (OH, $74,959)
- SUPER 8 MOTELS -> Super 8 / training (ID, $36,096)
- TRACTOR SUPPLY CREDIT PLAN -> Tractor Supply / general (OH, $6,464)
- US DEPARTMENT OF TREASURY -> U.S. Department of the Treasury / payroll (OH, $76,676)
- VERIZON WIRELESS FIRE -> Verizon / telecom (OH, $16,252)
- VERIZON WIRELESS GREAT LAKES -> Verizon / telecom (OH, $61,778)
- VERIZON WIRELESS MESSAGING SERVICES -> Verizon / telecom (OH, $6,152)
- VERIZON WIRELESS SERVICES -> Verizon / telecom (ID, $308,167)
- VERIZON WIRELESS SVCS -> Verizon / telecom (CA, $553,855)
- VISA -> Visa / finance (OH, $89,227)
- WAL MART BUSINESS -> Walmart / general (OH, $6,210)
- WAL MART BUSINESS GEMB -> Walmart / general (OH, $5,277)
- WAL MART STORE 1330 -> Walmart / general (OH, $5,714)
- WALMART CAPITAL ONE -> Walmart / general (OH, $3,463)
- WS DARLEY AND -> W.S. Darley & Co. / fire-equipment (CA/OH, $670,811)
- WW GRAINGER -> Grainger / general (TX/OH/ID/CA, $13,380,011)
- ZOLL DATA SYSTEMS -> Zoll Data Systems / rms (OH, $9,151)
- ZOLL MEDICAL GPO -> Zoll Medical / ems-equipment (OH, $69,230)

## Category decisions

Canonical vendors whose proposals named different categories, or whose category came from
config/vendor_map.csv or a vendor rule instead of the proposal.

| Vendor | States | Proposed (category: spend) | Category | Why |
| --- | --- | --- | --- | --- |
| CAL FIRE | CA | government: $1,335,465,382; professional: $396,958 | government | most proposed spend |
| JPMorgan Chase Bank | OH, CA, TX | payroll: $42,507,472; finance: $16,678,480 | payroll | most proposed spend |
| Radiomobile | CA | it: $46,658,619; radios: $474,153 | it | most proposed spend |
| Heartland Bank | OH | payroll: $33,839,512; finance: $19,555 | payroll | most proposed spend |
| Huntington Bank | OH | payroll: $21,935,400; finance: $5,902,408 | payroll | most proposed spend |
| LION | OH, TX | ppe: $20,145,738; fire-equipment: $42,083 | ppe | most proposed spend |
| Heli-1 | CA, ID | apparatus: $15,017,331; wildland: $5,164,437 | apparatus | most proposed spend |
| U.S. Bank | OH, ID | finance: $17,685,656; payroll: $2,049,008 | finance | config/vendor_map.csv |
| Ohio Bureau of Workers' Compensation | OH | insurance: $12,207,508; payroll: $50,826; apparatus: $5,923 | insurance | most proposed spend |
| KeyBank | OH | payroll: $9,063,650; finance: $54,467 | finance | config/vendor_map.csv |
| Sierra Pacific Industries | CA | professional: $9,049,347 | facilities | config/vendor_name_merges.csv |
| HeliQwest International | CA, ID | apparatus: $5,649,643; wildland: $2,931,484 | apparatus | most proposed spend |
| Ohio Township Association Risk Management Authority | OH | insurance: $8,547,944; government: $10,000 | insurance | most proposed spend |
| Fidelity National Title | CA | finance: $7,000,000; construction: $400,467 | finance | most proposed spend |
| Snap-on | CA, TX | general: $5,173,903; fleet: $815 | general | most proposed spend |
| Act Fast Nationwide Fire Support | CA | wildland: $4,411,242; software: $410,317 | wildland | config/vendor_name_merges.csv |
| Line Gear | CA | uniforms: $3,185,511; wildland: $1,372,497 | uniforms | most proposed spend |
| PennCare | OH | ambulance: $3,863,344; ems-supplies: $464,503 | ambulance | most proposed spend |
| Howell Rescue Systems | OH | fire-equipment: $3,416,814; payroll: $594,447 | fire-equipment | most proposed spend |
| Purvis Systems | OH, CA | dispatch: $3,599,279; fire-equipment: $138,011 | dispatch | most proposed spend |
| Treasurer of State of Ohio | OH | government: $1,981,182; payroll: $1,747,908 | government | most proposed spend |
| Algerine West | CA | wildland: $2,451,414; construction: $391,018 | wildland | most proposed spend |
| Recology | CA | facilities: $2,570,865; utilities: $236,257 | utilities | config/vendor_name_merges.csv |
| FTS Forest Technology Systems | CA | it: $2,670,248 | wildland | config/vendor_map.csv |
| Fire Dept Extractor Supply | CA | government: $2,230,167 | fire-equipment | config/vendor_name_merges.csv |
| Harris & Harris | CA, TX | finance: $974,503; ems-billing: $675,594 | ems-billing | config/vendor_name_merges.csv |
| Ohio Department of Taxation | OH | payroll: $1,574,165; government: $31,363 | payroll | most proposed spend |
| Farella Braun & Martel | CA | ambulance: $1,590,830 | professional | config/vendor_name_merges.csv |
| Emergency Medical Service Auth | CA | ems-supplies: $1,488,245 | government | config/vendor_name_merges.csv |
| Honeywell | TX | facilities: $1,483,108 | fire-equipment | config/vendor_map.csv |
| MECC Regional Council of Governments | OH | dispatch: $1,305,706; government: $25,250 | dispatch | most proposed spend |
| Med-I-Bank | OH | payroll: $1,152,477; finance: $4,102 | payroll | most proposed spend |
| Forge Fire & Company | OH | fire-equipment: $1,096,231 | training | config/vendor_map.csv |
| U.S. Department of the Treasury | OH, CA | government: $890,422; payroll: $86,676 | payroll | config/vendor_map.csv |
| Hylant | OH | insurance: $749,928; payroll: $45,865 | insurance | most proposed spend |
| Mountain Gate Fire Protection District | CA | wildland: $729,636; government: $66,010 | wildland | most proposed spend |
| Napa County Resc Conserv Dist | CA | fleet: $763,427 | government | config/vendor_name_merges.csv |
| Timberline Helicopters | CA, ID | apparatus: $606,869; wildland: $153,260 | apparatus | most proposed spend |
| Burton's Fire | CA | fleet: $759,738 | apparatus | config/vendor_name_merges.csv |
| United Rentals | CA | general: $738,110 | facilities | config/vendor_map.csv |
| Burnham & Flower Insurance Group | OH | payroll: $474,422; insurance: $236,737 | payroll | most proposed spend |
| W.W. Williams | OH | fleet: $680,590; facilities: $16,623 | fleet | most proposed spend |
| Unity National Bank | OH | payroll: $619,056; finance: $12,781 | payroll | most proposed spend |
| Hastings Air Energy Control | OH | facilities: $580,378; utilities: $2,985 | facilities | most proposed spend |
| Cummins | OH | facilities: $550,578; utilities: $30,646 | facilities | config/vendor_map.csv |
| Atwell's Police & Fire Equipment | OH | fire-equipment: $329,159; uniforms: $158,145 | fire-equipment | most proposed spend |
| Police & Firemen's Insurance Association | OH | payroll: $436,088; training: $30,215 | payroll | most proposed spend |
| Optum Bank | OH | payroll: $441,125; finance: $12,600 | payroll | most proposed spend |
| Home Depot | OH, TX | facilities: $436,341; finance: $5,432 | facilities | config/vendor_map.csv |
| Sedgwick | OH | insurance: $285,511; payroll: $149,808 | insurance | most proposed spend |
| Hall Public Safety Upfitters | OH | fleet: $387,706; fire-equipment: $18,295 | fleet | most proposed spend |
| Montgomery County Sheriff | OH | dispatch: $235,345; government: $135,030 | dispatch | most proposed spend |
| Premier Bank | OH | payroll: $346,894; finance: $10,258 | payroll | most proposed spend |
| PNC Bank | OH | finance: $250,170; payroll: $104,142 | finance | most proposed spend |
| Cintas | OH | uniforms: $182,712; facilities: $150,411 | uniforms | config/vendor_map.csv |
| Jason M. Pauline | OH | general: $298,883 | payroll | config/vendor_name_merges.csv |
| Buckeye Power Sales | OH | facilities: $270,239; utilities: $28,172 | facilities | most proposed spend |
| Baycom | OH, TX | it: $232,130; payroll: $26,423 | it | most proposed spend |
| Lowe's | OH | facilities: $253,173; finance: $4,277 | facilities | config/vendor_map.csv |
| Public Consulting Group | OH, TX | ems-billing: $217,979; professional: $35,000 | ems-billing | most proposed spend |
| Kzf Design | OH | construction: $196,254; professional: $45,076 | construction | most proposed spend |
| Montgomery County | OH | government: $186,246; payroll: $44,745 | government | most proposed spend |
| Austin D Hurst | OH | fire-equipment: $220,576 | payroll | config/vendor_name_merges.csv |
| Axcess Fire and Safety Supply | ID, TX | fire-equipment: $108,767; wildland: $86,000 | fire-equipment | most proposed spend |
| Matheson Tri-Gas | OH | ems-supplies: $133,197; utilities: $32,538 | ems-supplies | most proposed spend |
| OhioHealth | OH | payroll: $89,263; medical-exams: $74,707 | medical-exams | config/vendor_name_merges.csv |
| Jg Luke | OH | uniforms: $103,327; payroll: $49,090 | uniforms | most proposed spend |
| Butler Tech | OH | it: $105,651; training: $31,868 | training | config/vendor_name_merges.csv |
| First In-Last Out Fire Equipment & Training | OH | fire-equipment: $96,419; training: $36,433 | fire-equipment | most proposed spend |
| Greene County | OH | government: $74,152; payroll: $38,473 | government | most proposed spend |
| Crash Course Village | OH | government: $94,060; payroll: $14,900 | training | config/vendor_name_merges.csv |
| J.K. Meurer | OH | construction: $77,910; facilities: $23,400 | construction | most proposed spend |
| Sam's Club | OH | general: $69,540; finance: $29,897 | general | config/vendor_map.csv |
| MSA Safety | OH | fire-equipment: $83,939 | scba | config/vendor_map.csv |
| John D. Suban Spring Service | OH | fleet: $76,804; payroll: $5,476 | fleet | most proposed spend |
| Lucas Parmelee | OH | ems-equipment: $78,278 | payroll | config/vendor_name_merges.csv |
| Handtevy | OH | ems-supplies: $71,053 | software | config/vendor_map.csv |
| Super Laundry Equipment | OH | fire-equipment: $51,033; payroll: $16,421 | fire-equipment | most proposed spend |
| FireStationFurniture.com | CA | general: $60,772 | facilities | config/vendor_name_merges.csv |
| Lucas Roberts | OH | ems-equipment: $52,417 | payroll | config/vendor_name_merges.csv |
| Comdoc | OH | it: $35,600; finance: $12,876 | it | most proposed spend |
| Mega City Fire Protection | OH | facilities: $43,066; government: $2,060 | facilities | most proposed spend |
| Lion Creative Studios | OH | fire-equipment: $35,500 | professional | config/vendor_name_merges.csv |
| Brian Cummins | OH | facilities: $33,685 | payroll | config/vendor_name_merges.csv |
| DellaPenna Construction | OH | it: $33,125 | facilities | config/vendor_name_merges.csv |
| Nelbud Services | OH | facilities: $24,443; professional: $5,172 | facilities | most proposed spend |
| Jasmine M Pierce | OH | apparatus: $29,545 | payroll | config/vendor_name_merges.csv |
| EMS LogiK | OH | ems-supplies: $28,850 | software | config/vendor_map.csv |
| R & T Yoder Electric | OH | utilities: $26,386; construction: $2,334 | utilities | most proposed spend |
| NEOFPA | OH | training: $27,341; government: $1,278 | training | most proposed spend |
| Spartan IT | OH | apparatus: $27,858 | it | config/vendor_name_merges.csv |
| Howard W. Goodyear | OH | fleet: $26,898 | payroll | config/vendor_name_merges.csv |
| DreamSeat | OH | general: $26,593 | facilities | config/vendor_map.csv |
| Individuals (names withheld) | OH | payroll: $23,211 | individuals | config/vendor_name_merges.csv |
| Fastsigns | CA | general: $21,078 | professional | config/vendor_map.csv |
| Walmart | OH | general: $17,202; finance: $3,463 | general | config/vendor_map.csv |
| Ryan M Lucas | OH | ems-equipment: $19,775 | payroll | config/vendor_name_merges.csv |
| Spartan Armor Systems | OH | apparatus: $18,688 | ppe | config/vendor_name_merges.csv |
| Matt Hurst | OH | fire-equipment: $17,712 | payroll | config/vendor_name_merges.csv |
| Lucas S Welsh | OH | ems-equipment: $17,387 | payroll | config/vendor_name_merges.csv |
| Lucas Jagger | OH | ems-equipment: $16,871 | payroll | config/vendor_name_merges.csv |
| PowerDMS | OH | utilities: $16,515 | training-software | config/vendor_map.csv |
| Craig P Stires | OH | fleet: $13,236 | payroll | config/vendor_name_merges.csv |
| Wendell A Slagell | OH | it: $12,936 | payroll | config/vendor_name_merges.csv |
| Bethel Fire Association | OH | training: $12,264 | payroll | config/vendor_name_merges.csv |
| Spartan Tool Supply | OH | apparatus: $12,245 | general | config/vendor_name_merges.csv |
| All-Star Inflatables | OH | payroll: $10,870 | general | config/vendor_map.csv |
| Berlin Twp Firefighter's Association Fire | OH | training: $10,122 | payroll | config/vendor_name_merges.csv |
| RollNRack | OH | payroll: $9,970 | fire-equipment | config/vendor_map.csv |
| Tanner S Glass | OH | facilities: $9,374 | payroll | config/vendor_name_merges.csv |
| Zoll Data Systems | OH | ems-equipment: $9,151 | rms | vendor rule |
| Health Care Logistics | OH | rms: $7,845 | ems-supplies | config/vendor_name_merges.csv |
| 8x8 | OH | fleet: $7,757 | telecom | config/vendor_name_merges.csv |
| Firehouse Innovations | OH | fire-equipment: $7,600 | training | config/vendor_map.csv |
| Travelers | OH | training: $7,392 | insurance | config/vendor_map.csv |
| Interstate Billing Service | OH | ems-billing: $5,974 | fleet | config/vendor_map.csv |

## Judgment calls

Merged or kept apart by `config/vendor_name_merges.csv` (a row whose `to_vendor` equals its `from_vendor`
keeps that name out of the automatic grouping):

| From | To | Note |
| --- | --- | --- |
| 2 Hot Uniforms | 2 Hot Activewear & Uniforms | same uniform company |
| 8x8, Inc | 8x8 | 8x8 is a telephone (VoIP) company: telecom, not fleet |
| AccuMed | Accumed Billing | same ambulance billing company |
| Across the Street | Across the Street Productions | the name config/vendor_map.csv uses |
| Act Fast Fire Support | Act Fast Nationwide Fire Support | water tenders hired for going fires (SCPRS lines), as Act Fast Nationwide Fire Support: wildland, not software |
| Act Fast Nationwide Fire Supp | Act Fast Nationwide Fire Support | same company; the source cuts the name off |
| ADP Payroll | ADP | same company |
| ADP Payroll Services | ADP | same company |
| Advanced Gas & Welding Solutions | Advanced Gas & Welding | same company |
| Advantech Services and Parts L | Advantech Service & Parts | same company |
| AE Door | Ae Door Sales | same company |
| Aes | AES Ohio | AES Ohio (formerly Dayton Power & Light) |
| Algerine West Construction | Algerine West | same company |
| All-American Fire Equipment in | All American Fire Equipment | same company |
| Allstate Insurance | Allstate | same insurer |
| American Safety & | American Safety & Health Institute | name cut off in the source |
| Amerivet | Amerivet Contracting | same company |
| FIRSTNET AT&T Mobility II LLC | AT&T | FirstNet is AT&T's public safety network |
| Atlanic Emergency Solutions | Atlantic Emergency Solutions | spelling |
| Atwell's | Atwell's Police & Fire Equipment | same company |
| Atwell's Police & Fire Equipments | Atwell's Police & Fire Equipment | same company |
| Atwell's Police & Fire Equipmt | Atwell's Police & Fire Equipment | same company |
| Axcess Fire | Axcess Fire and Safety Supply | same company |
| B&W Automotive Dba Bravo Chrysler Dodge Jeep of Alhambra | B&W Automotive Dba Bravo Chrysler | same dealer |
| Bachman's HVAC Solutions | Bachman's | same company |
| Beem's BP Distr. Inc. | Beem's BP Distributing | same fuel distributor; the source cuts the name off |
| Benistar/Hartford-6795 | Benistar/Hartford | same plan |
| Best One Tire & Service of | Best One Tire & Service | same company |
| Best One Tire & Service of Mid America | Best One Tire & Service | same company |
| Best One Tire & SVC of Columbus | Best One Tire & Service | same company |
| Best One Tire and Service of Mid Ameica | Best One Tire & Service | same company |
| Best One Tire Service | Best One Tire & Service | same company |
| Boeing Distribution SVCS | Boeing Distribution | same company |
| Breating Air Systems | Breathing Air Systems | spelling |
| Brondes Ford Maumee | Brondes Ford | same dealer |
| Burgess Hearse & Ambulance Sales | Burgess Hearse & Ambulance | same company |
| Burnham & Flower Agency Of Ohio, Inc. | Burnham & Flower Insurance Group | same insurance and benefits broker |
| Burnham & Flower Group | Burnham & Flower Insurance Group | same insurance and benefits broker |
| Burnham & Flower Of Ohio | Burnham & Flower Insurance Group | same insurance and benefits broker |
| Burnham & Flowers Insurance Group | Burnham & Flower Insurance Group | spelling |
| Burtons Fire | Burton's Fire | fire pump and apparatus repair (CAL FIRE lines): apparatus |
| Butler Tech Ad Ed | Butler Tech | Butler Technology & Career Development Schools; paid for fire training services: training, not it |
| Butler Technology & Career | Butler Tech | Butler Technology & Career Development Schools |
| Butler Technology & Career Dev. School | Butler Tech | Butler Technology & Career Development Schools |
| Butler Technology & Career Development School | Butler Tech | Butler Technology & Career Development Schools |
| Cal Fire | CAL FIRE | California Department of Forestry and Fire Protection, as it names itself |
| CAL FIRE (State of California) | CAL FIRE | California Department of Forestry and Fire Protection, as it names itself |
| Calif Dept of Forestry & Fire Protection | CAL FIRE | California Department of Forestry and Fire Protection, as it names itself |
| Calif. Dept of Health Care Srvcs | California Department of Health Care Services | same state department |
| Capital One Trade Credit | Capital One | the name config/vendor_map.csv uses |
| Cdw Goverment | CDW Government | spelling; the name config/vendor_rules.csv uses |
| Cdw Government LLC, Cdw Government | CDW Government | the name config/vendor_map.csv uses |
| Cdw Government, Ind. | CDW Government | the name config/vendor_map.csv uses |
| CDW-G CDW Government | CDW Government | the name config/vendor_map.csv uses |
| Center Point Energy | Centerpoint Energy | same utility |
| Vectren Energy Delivery | Centerpoint Energy | Vectren Energy Delivery of Ohio, renamed CenterPoint Energy Ohio after CenterPoint bought Vectren in 2019 |
| Vectren Energy Delivery Of Ohio, Inc. | Centerpoint Energy | Vectren Energy Delivery of Ohio, renamed CenterPoint Energy Ohio after CenterPoint bought Vectren in 2019 |
| Central Square Technologies | CentralSquare Technologies | same software company |
| CentralSquare Technoligies | CentralSquare Technologies | same software company |
| CERNI MOTORS - Painesville | Cerni Motors | same dealer |
| Change Healthcare Practice | Change Healthcare | same ambulance billing company |
| Change Healthcare Practice Mgmt Solutions | Change Healthcare | same ambulance billing company |
| Change Healthcare Practice Mgt Solutions | Change Healthcare | same ambulance billing company |
| Change Healthcare Tech Enabled | Change Healthcare | same ambulance billing company |
| Change Healthcare Tech Enabled Service | Change Healthcare | same ambulance billing company |
| Change Healthcare Tech. Enabled Serv. | Change Healthcare | same ambulance billing company |
| Change Healthcare Technology | Change Healthcare | same ambulance billing company |
| Change Healthcare Technology Enabled Services | Change Healthcare | same ambulance billing company |
| Spectrum | Charter Communications | Spectrum is Charter's brand (Time Warner Cable joined it in 2016); not Utah's 'The Spectrum', a St. George newspaper that shares the key SPECTRUM |
| Time Warner - Spectrum | Charter Communications | Spectrum is Charter's brand (Time Warner Cable joined it in 2016); not Utah's 'The Spectrum', a St. George newspaper that shares the key SPECTRUM |
| Time Warner - Spectrum Business | Charter Communications | Spectrum is Charter's brand (Time Warner Cable joined it in 2016); not Utah's 'The Spectrum', a St. George newspaper that shares the key SPECTRUM |
| Time Warner Cable (Spectrum Enterprise) | Charter Communications | Spectrum is Charter's brand (Time Warner Cable joined it in 2016); not Utah's 'The Spectrum', a St. George newspaper that shares the key SPECTRUM |
| Time Warner Cable-Northeast | Charter Communications | Spectrum is Charter's brand (Time Warner Cable joined it in 2016); not Utah's 'The Spectrum', a St. George newspaper that shares the key SPECTRUM |
| Cigna Health And Life Ins Co. | Cigna Health and Life Insurance | same insurer |
| Altafiber | Cincinnati Bell | Cincinnati Bell, renamed altafiber in 2022 |
| altafiber | Cincinnati Bell | Cincinnati Bell, renamed altafiber in 2022 |
| Cincinnati Bell Any Distance | Cincinnati Bell | Cincinnati Bell, renamed altafiber in 2022 |
| Cincinnati Bell Telephone | Cincinnati Bell | Cincinnati Bell, renamed altafiber in 2022 |
| Cincinnati Bell Telephone Co. Dba Altaf | Cincinnati Bell | Cincinnati Bell, renamed altafiber in 2022 |
| Colonial Life & Accident | Colonial Life | the name config/vendor_map.csv uses |
| Comdoc Leasing | Comdoc | same company |
| Comuunity First National Bank | Community First National Bank | spelling |
| Companion Life | Companion Life Insurance | same insurer |
| Computerland Silicon Valley | ComputerLand of Silicon Valley | same company |
| Consolidated Fleet Services In | Consolidated Fleet Services | the name config/vendor_map.csv uses |
| Coughlin Ford of CV | Coughlin Ford | same dealer |
| Riverside County Fire Department, Office of Emergency Services | County of Riverside Fire Dept | same county fire department |
| Riverside County Fire Dept | County of Riverside Fire Dept | same county fire department |
| Riverside County Fire Dept - Revenue Section | County of Riverside Fire Dept | same county fire department |
| Craig Mountain | Craig Mountain Excavation | same Idaho contractor |
| Crash Course Village Inc | Crash Course Village | same training site; a fire and rescue training site paid for training services and registrations: training, not government |
| Crashcourse Village Inc. | Crash Course Village | same training site |
| Crewboss | CrewBoss | the company's spelling |
| Cronin Ford Kia | Cronin Ford | same dealer |
| Cummins Bridgeway | Cummins | the name config/vendor_map.csv uses |
| Cummins Inc Dba Cummins Sales & Service | Cummins | the name config/vendor_map.csv uses |
| Cummins Sales & Service | Cummins | the name config/vendor_map.csv uses |
| Darol Stanton Logging | Darold Stanton Logging | spelling |
| Dell Computers | Dell Technologies | the name config/vendor_map.csv uses |
| Delta Dental Plan of Ohio Inc. | Delta Dental | Delta Dental of Ohio (Delta Dental Plan of Ohio), as the other Ohio forms |
| Deltadental | Delta Dental | spelling |
| Dental Care Plus Group | Dental Care Plus | same dental plan |
| Digitech | Digitech Computer | the name config/vendor_map.csv uses |
| M O Dion & Sons | Dion & Sons | same company |
| Direct Line | Direct Line Dozer | same CAL FIRE dozer contractor |
| Duncan Oil - Propane | Duncan Oil | same company |
| Dvbe-sbe Enterprises, Inc. / dba Lenahan's Water Truck Service | Dvbe-sbe Enterprises | same company |
| E & H Hardware Group | E&H Hardware | same company |
| Elk Grove Auto | Elk Grove Auto Group | same dealer group |
| Embroidery Wearhouse & Screen Printing | Embroidery Wearhouse & Screenprinting | same company |
| Emergency Medicine Physicians of Franklin | Emergency Medicine Physicians of Franklin Cty | same practice |
| Emergency Reporting - Backdraft OpCo | Emergency Reporting | same software company |
| Empower Financial Services | Empower | same retirement plan company |
| Ems Management & | Ems Management & Consultants | same company |
| EMSAR Central | EMSAR | same company |
| Equitable Financial Life Insurance | Equitable | same company |
| Eso Soultions Inc | ESO Solutions | spelling; the name config/vendor_map.csv uses |
| Exxon Fleet Services | ExxonMobil | the name config/vendor_map.csv uses |
| Fallsway | Fallsway Equipment | same company |
| Farmers National | Farmers National Bank | same bank |
| Fastspring | FastSpring | the company's spelling |
| Federal Express | FedEx | FedEx (Federal Express Corporation); the name config/vendor_map.csv uses |
| Fidelity Natl Title Co of CA | Fidelity National Title | same company |
| Fifth Third Bank-Cc | Fifth Third Bank | same bank |
| Fifth Third Bank-Mastercard | Fifth Third Bank | same bank |
| Fifth Third Bank/Card Center | Fifth Third Bank | same bank |
| Fire Apparatus Serv & Repair | Fire Apparatus Service & Repair | same Ohio apparatus repair company; the source cuts the name off |
| Fire Apparatus Service | Fire Apparatus Service & Repair | same Ohio apparatus repair company (Montgomery County agencies use both forms) |
| Fire Etc | Fire-Etc | the company's spelling |
| Fire-Fly Fire Equipment Sales | Fire-Fly Fire Equipment | same company |
| Firestorm Trucking CA | Firestorm Trucking | same company |
| First in Last Out Fire Equipment | First In-Last Out Fire Equipment & Training | same Ohio company |
| First In-Last Out Fire & Safety Equipment | First In-Last Out Fire Equipment & Training | same Ohio company |
| First In-Last Out Fire & Safty Equipmen | First In-Last Out Fire Equipment & Training | same Ohio company |
| First In-Last Out Fire Ezuipment & Training | First In-Last Out Fire Equipment & Training | same Ohio company |
| First Merit | First Merit Bank | same bank |
| Forge and Fire | Forge Fire & Company | Forge & Fire Company LLC (published as 'FORGE & FIRE COMPANY LLC' and 'Forge Fire & Company'); the name config/vendor_map.csv uses |
| Gerber Collision & Glass- Wilmington | Gerber Collision & Glass | same company |
| Goodyear Comm Tire & Serv Cent | Goodyear | the name config/vendor_map.csv uses |
| Goodyear Commercial Truck | Goodyear | the name config/vendor_map.csv uses |
| Goodyear Commerical Tire & Svc Ctrs | Goodyear | the name config/vendor_map.csv uses |
| Goodyear Tire | Goodyear | the name config/vendor_map.csv uses |
| Goodyear Tire & Rubber | Goodyear | the name config/vendor_map.csv uses |
| Great Lakes Best One Tire | Great Lakes Best One Tire & Service | same company |
| Great Oaks | Great Oaks Career Campuses | same career school |
| Great Oaks Institute of | Great Oaks Career Campuses | same career school |
| Hall Public Safety Outfitters | Hall Public Safety Upfitters | same company |
| Hastings Air Energy | Hastings Air Energy Control | same company |
| Heartland Bank Mastercard | Heartland Bank | same bank |
| Holt of CA | Holt of California | same Caterpillar dealer |
| HD SUPPLY Formerly Home Depot Pro | Home Depot | Home Depot Pro (HD Supply), as vendor rule '^HOME DEPOT' names it |
| Horton Emergency Vehicle | Horton Emergency Vehicles | same company |
| HSA - Employer | HSA - Employer Match/Wellness | same account |
| Humana Hlth Plan Ohio | Humana Health Plan Ohio | same plan |
| Hunti50 (Huntington Bank) | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington Bank Mastercard | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington Bank Taxes Withheld | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington Bank-Credit Card | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington Credit Card | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington Nat'L Bank - Fire | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington Nat'L Bank-Fin Dir | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington National Bank | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington National Bank Card | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington Public Capital | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Huntington Trust | Huntington Bank | The Huntington National Bank: payroll accounts, cards, trust and leasing |
| Hylant - Cincinnati | Hylant | same insurance broker |
| Hylant Adminstrative Services | Hylant | same insurance broker |
| Jason Brown | Individuals (names withheld) | a private person; a Utah payee has the same key and pipeline/build.py withholds Utah persons' names (a vendor_map row would show it) |
| Matthew Evans | Individuals (names withheld) | a private person; a Utah payee has the same key and pipeline/build.py withholds Utah persons' names (a vendor_map row would show it) |
| Tyler Anderson | Individuals (names withheld) | a private person; a Utah payee has the same key and pipeline/build.py withholds Utah persons' names (a vendor_map row would show it) |
| International Association of Firefighters | International Association of Fire Fighters | IAFF |
| Interstate Billing Servic | Interstate Billing Service | the name config/vendor_map.csv uses |
| Jake Sweeney Chrysler Jeep Dodge | Jake Sweeney | same dealer group |
| Jg Luke LLC Dba Moccasin Creek Tactical | Jg Luke | same company |
| John Dsuban Spring Service | John D. Suban Spring Service | spelling |
| Johnsons Emergency Vehicle | Johnson's Emergency Vehicle Solutions | same company |
| Johnson Fire Equipment | Johnson's Fire Equipment | same Ohio dealer |
| Chase Bank | JPMorgan Chase Bank | one bank: payroll accounts, cards and debt service |
| Chase Bank for Federal Withholding | JPMorgan Chase Bank | one bank: payroll accounts, cards and debt service |
| Chase Ink (credit card) | JPMorgan Chase Bank | one bank: payroll accounts, cards and debt service |
| Jp Morgan Chase Bank | JPMorgan Chase Bank | one bank: payroll accounts, cards and debt service |
| JPMorgan Chase | JPMorgan Chase Bank | one bank: payroll accounts, cards and debt service |
| JPMorgan Chase (credit card) | JPMorgan Chase Bank | one bank: payroll accounts, cards and debt service |
| JPMorgan Chase (debt service) | JPMorgan Chase Bank | one bank: payroll accounts, cards and debt service |
| JPMorgan Chase Bank (payroll) | JPMorgan Chase Bank | one bank: payroll accounts, cards and debt service |
| Kembra Credit Union | KEMBA Credit Union | spelling |
| Ken Neyer Plumbling | Ken Neyer Plumbing | spelling |
| Key Chrysler Jeep, Dodge | Key Chrysler | same dealer |
| Hsa Key Bank | KeyBank | the name config/vendor_map.csv uses |
| Key Bank - Hsa | KeyBank | the name config/vendor_map.csv uses |
| Key Bank Credit Card | KeyBank | the name config/vendor_map.csv uses |
| Key Bank- Key2Purchase | KeyBank | the name config/vendor_map.csv uses |
| Kilroy Realty 303 | Kilroy Realty | same landlord |
| Kovatch Mobile Equipment dba KME Fire Apparatus | KME Fire Apparatus | same apparatus maker |
| Knapheide Truck Equipment | Knapheide Truck Equipment Center | same company |
| Kolsom Tire | Kolsom Tires | same company |
| Kolsom Tires Sales & Services | Kolsom Tires | same company |
| Lake Cnty. Fire Chiefs Assoc. | Lake County Fire Chiefs Association | same association |
| Levinson's Uniforms & Accessories | Levinson's Uniforms | same company |
| Liberty Ford Canton | Liberty Ford | same dealer group |
| Liberty Ford Lincoln Mercury | Liberty Ford | same dealer group |
| Life Extensions Clinic | Life Extension Clinics | same clinic |
| Life-Force | Life Force Management | same Ohio billing company |
| Life Scan Wellness | Life Scan Wellness Center | same clinic |
| Linde Gas North America | Linde Gas & Equipment | the name config/vendor_map.csv uses |
| Linegear | Line Gear | same company |
| Linegear Fire & Rescue | Line Gear | same company |
| Lion Group | LION | LION Group, the turnout gear maker |
| * Lion Creative Studios LLC | Lion Creative Studios | a creative studio paid for special projects; the LION keyword caught it |
| Lube Depot & Tire | Lube Depot | same company |
| Marathon | Marathon Petroleum | Marathon fuel and its fleet card |
| Marathon Ashland Fleet Service | Marathon Petroleum | Marathon fuel and its fleet card |
| Marathon Fleet Services | Marathon Petroleum | Marathon fuel and its fleet card |
| Massh North | MASSH | same company |
| Matheson Tri Gas Dba Valley | Matheson Tri-Gas | same company |
| McKesson | McKesson Medical-Surgical | the name config/vendor_map.csv uses |
| McKESSON MEDICAL SURGICAL GOV'T SOLUTION | McKesson Medical-Surgical | the name config/vendor_map.csv uses |
| Mc Neil and | McNeil & Company | McNeil & Company (emergency services insurance), as config/vendor_map.csv names it |
| Medicare Matching | Medicare | employer Medicare tax |
| Megacity Fire Protection | Mega City Fire Protection | same company |
| Menard's | Menards | same retailer |
| Menards - Evendale | Menards | same retailer |
| Mnj Technologies | MNJ Technologies | same company |
| Mnj Technologies Direct | MNJ Technologies | same company |
| Mnj Technologies Public Sector | MNJ Technologies | same company |
| Mobilcom | MobilComm | same Ohio radio company |
| Mobile Modular Management | Mobile Modular | same company |
| Mountain Gate Fire | Mountain Gate Fire Protection District | same district |
| Msa | MSA Safety | the name config/vendor_map.csv uses |
| Munic51 (Mes I Acquisition Inc) | Municipal Emergency Services | MES (MES I Acquisition): the name config/vendor_map.csv uses |
| Municipal Emergency Scvs | Municipal Emergency Services | MES (MES I Acquisition): the name config/vendor_map.csv uses |
| Municipal Emergency Serv. depository acct | Municipal Emergency Services | MES (MES I Acquisition): the name config/vendor_map.csv uses |
| Municipal Emergency Srvcs | Municipal Emergency Services | MES (MES I Acquisition): the name config/vendor_map.csv uses |
| Municipal Emergengy Services | Municipal Emergency Services | spelling |
| Cleves Auto Parts/NAPA | NAPA Auto Parts | NAPA stores, as vendor rule '^NAPA' names them |
| Cleves Napa | NAPA Auto Parts | NAPA stores, as vendor rule '^NAPA' names them |
| D&S Auto Parts dba NAPA Auto Parts | NAPA Auto Parts | NAPA stores, as vendor rule '^NAPA' names them |
| Napa | NAPA Auto Parts | NAPA stores, as vendor rule '^NAPA' names them |
| Napa - Canal Winchester | NAPA Auto Parts | NAPA stores, as vendor rule '^NAPA' names them |
| Napa Auto Parts Brooklyn | NAPA Auto Parts | NAPA stores, as vendor rule '^NAPA' names them |
| Napa Ohio | NAPA Auto Parts | NAPA stores, as vendor rule '^NAPA' names them |
| Napa Vandalia | NAPA Auto Parts | NAPA stores, as vendor rule '^NAPA' names them |
| NAPA, Inc.-Columbus, OH | NAPA Auto Parts | NAPA stores, as vendor rule '^NAPA' names them |
| National Hose Testing Specialties | National Hose Testing | same company |
| Nelbud Services Group | Nelbud Services | same company |
| NEOFPA Treasurer | NEOFPA | Northeast Ohio Fire Prevention Association |
| National Fire Protection Assn | NFPA | National Fire Protection Association |
| National Fire Protection Assoc | NFPA | National Fire Protection Association |
| Nfpa International | NFPA | National Fire Protection Association |
| No Vendor | No vendor named | placeholder payee |
| Burea51 (Bwc State Insurance Fund) | Ohio Bureau of Workers' Compensation | same state agency (BWC) |
| Bureau Of Workmans Compensation | Ohio Bureau of Workers' Compensation | same state agency (BWC) |
| Bureau of Workmen's Compensation | Ohio Bureau of Workers' Compensation | same state agency (BWC) |
| Oh Child Support Payment Central | Ohio Child Support Payment Central | same office |
| Ohio Child Support | Ohio Child Support Payment Central | same office |
| Ohio Fire & Emergency | Ohio Fire & Emergency Services Foundation | same foundation |
| Ohio Fire & Emergency Serv. Foundation | Ohio Fire & Emergency Services Foundation | same foundation |
| Ohio Fire & Emergency Services | Ohio Fire & Emergency Services Foundation | same foundation |
| Ohio Fire & Emergency Services Fnd | Ohio Fire & Emergency Services Foundation | same foundation |
| Ohio First Responders Grants | Ohio First Responder Grants | spelling |
| Oh Police/Fire Pension Fund | Ohio Police & Fire Pension Fund | OP&F (formerly the Police & Firemen's Disability and Pension Fund) |
| Police & Firemen Pension & | Ohio Police & Fire Pension Fund | OP&F (formerly the Police & Firemen's Disability and Pension Fund); name cut off in the source |
| Police & Firemen's | Ohio Police & Fire Pension Fund | OP&F (formerly the Police & Firemen's Disability and Pension Fund); paid from 'Ohio Police and Fire Pension Fund' accounts |
| Police & Firemens Pension Fund | Ohio Police & Fire Pension Fund | OP&F (formerly the Police & Firemen's Disability and Pension Fund) |
| Opedc | Ohio Public Employees Deferred Compensation | OPEDC is the Ohio Public Employees Deferred Compensation program |
| Opedc Roth | Ohio Public Employees Deferred Compensation | OPEDC Roth accounts |
| Ohio Public Employee Retirement System | Ohio Public Employees Retirement System | spelling |
| Ohio Public Employees Retirment System | Ohio Public Employees Retirement System | spelling |
| Ohio Public Risk Ins. Agency dba VFIS of Ohio | Ohio Public Risk Insurance Agency | same agency (dba VFIS of Ohio) |
| Ohio Public Risk Insurance Agency DBA VFIS | Ohio Public Risk Insurance Agency | same agency (dba VFIS of Ohio) |
| Ohio Public Risks Insurance Agency | Ohio Public Risk Insurance Agency | spelling |
| VFIS of Ohio | Ohio Public Risk Insurance Agency | the agency publishes itself as Ohio Public Risk Insurance Agency dba VFIS of Ohio |
| Ohio Township Ass. Risk Management Auth. | Ohio Township Association Risk Management Authority | OTARMA, the township insurance pool |
| Ohio Township Ass. Risk Mngt Authority | Ohio Township Association Risk Management Authority | OTARMA, the township insurance pool |
| Ohio Township Assn Risk Mgmt Authority | Ohio Township Association Risk Management Authority | OTARMA, the township insurance pool |
| Ohio Township Assoc. Risk Mgmt. Authoriy | Ohio Township Association Risk Management Authority | OTARMA, the township insurance pool |
| Ohio Twp Assoc Risk Management Authority | Ohio Township Association Risk Management Authority | OTARMA, the township insurance pool |
| Ohio Twp. Assn Risk Management Authority | Ohio Township Association Risk Management Authority | OTARMA, the township insurance pool |
| OTARMA | Ohio Township Association Risk Management Authority | OTARMA, the township insurance pool |
| Ohio Health/Workhealth | OhioHealth | OhioHealth (WorkHealth is its occupational health service); WorkHealth is occupational medicine (physicals): medical-exams, not payroll |
| OhioHealth/WorkHealth | OhioHealth | OhioHealth (WorkHealth is its occupational health service) |
| Ok Fine Productions | OK Fine Productions | the company's spelling |
| Old Fort Bank Visa | Old Fort Bank | same bank |
| Opengov | OpenGov | the company's spelling |
| P&R Communications | P & R Communications Service | same Ohio radio company (P&R Communications Service) |
| Payroll - City of Wapakoneta | Payroll | a payroll entry, not a company: the name config/vendor_map.csv uses |
| Payroll - Net | Payroll | a payroll entry, not a company: the name config/vendor_map.csv uses |
| Payroll Deduction From Checking | Payroll | a payroll entry, not a company: the name config/vendor_map.csv uses |
| Payroll Gross Vendor | Payroll | a payroll entry, not a company: the name config/vendor_map.csv uses |
| Payroll Gross Voucher | Payroll | a payroll entry, not a company: the name config/vendor_map.csv uses |
| Payroll Medicare & Fica | Payroll | a payroll entry, not a company: the name config/vendor_map.csv uses |
| Payroll Only | Payroll | a payroll entry, not a company: the name config/vendor_map.csv uses |
| Payroll Vendor | Payroll | a payroll entry, not a company: the name config/vendor_map.csv uses |
| Penserv Plan Services | PenServ | same company |
| Pitney Bowes Reserve Account | Pitney Bowes | postage account |
| Pk Safety Supply | PK Safety Supply | the company's spelling |
| Pnc | PNC Bank | same bank (cards, HSA accounts) |
| Pnc Bank | PNC Bank | same bank (cards, HSA accounts) |
| Pnc Bank - Purchase Card | PNC Bank | same bank (cards, HSA accounts) |
| Pnc Bank Business Card | PNC Bank | same bank (cards, HSA accounts) |
| Pnc Bank C.C. | PNC Bank | same bank |
| PNC Bank Health Savings Account Services | PNC Bank | same bank (cards, HSA accounts) |
| PNC Benefit Plus | PNC Bank | same bank (cards, HSA accounts) |
| Pnc National Bank Assoc. (Pnc Credit Card) | PNC Bank | same bank (cards, HSA accounts) |
| Poly-Tech & Associates | Poly-Tech Associates | same company |
| Power Dms | PowerDMS | the name config/vendor_map.csv uses |
| Ppe Software | PPE Software | the company's spelling |
| Premier Bank Cardmember Service | Premier Bank | same bank |
| Prodump and Excavating | Pro-Dump and Excavating | spelling |
| Prudential Retirement | Prudential | same company |
| The Prudential Insurance Company of America | Prudential | same company |
| R & T Yoder | R & T Yoder Electric | same company |
| Radio Mobile | Radiomobile | same radio company |
| Rasix Computer | Rasix Computer Center | same company |
| Recology San Francisco | Recology | same company; waste haulers are utilities, as Waste Management and Republic Services in config/vendor_map.csv |
| Recology Sunset Scavenger | Recology | Recology's San Francisco company |
| Regents of the Univ of CA | Regents of the University of California | one legal body for every UC campus |
| Regents of the Univ of CA SD | Regents of the University of California | one legal body for every UC campus |
| Regents of the University of | Regents of the University of California | one legal body for every UC campus |
| Regents of the University of California at Los Angeles | Regents of the University of California | one legal body for every UC campus |
| Regents of the University of California, UC Davis | Regents of the University of California | one legal body for every UC campus |
| Regents of Univ of CA Davis | Regents of the University of California | one legal body for every UC campus |
| Reliance Standard Life Ins.Co | Reliance Standard Life | same insurer |
| Republic Services #798 | Republic Services | the name config/vendor_map.csv uses |
| Rmc-Resource Manaement Consultants | Rmc-Resource Management Consultants | spelling |
| Roy Tailor Uniform | Roy Tailors Uniform | same company |
| Roy Tailors Uniform Co. of Columbus | Roy Tailors Uniform | same company |
| Rumpke Consolidated Companies | Rumpke | same company |
| Rumpke Waste Removal Systems | Rumpke | same company |
| Rusty's Towing Srevices | Rusty's Towing Service | spelling |
| Sacramento Metro Fire Dist | Sacramento Metropolitan Fire District | same fire district |
| Sacramento Metro Fire District | Sacramento Metropolitan Fire District | same fire district |
| Sand Hollow Fire Deistrict | Sand Hollow Fire District | spelling |
| Security Benefits | Security Benefit | spelling |
| Sedgwick Claims Management | Sedgwick | same claims administrator |
| Sedgwick Claims Management Services | Sedgwick | same claims administrator |
| Sedgwick Claims Managment | Sedgwick | same claims administrator |
| Sedgwick Claims Manangment Services | Sedgwick | same claims administrator |
| Sedgwick Claims Mgt Services | Sedgwick | same claims administrator |
| Shuttler's (Parma) | Shuttler's Uniform | same Ohio uniform store |
| Shuttler's Apparel | Shuttler's Uniform | same Ohio uniform store |
| Shuttlers Uniforms | Shuttler's Uniform | same Ohio uniform store |
| Siteone Landscape Supply | SiteOne Landscape Supply | the company's spelling |
| Snap-on Industrial | Snap-on | Snap-on and its industrial division |
| Snap-on Tools | Snap-on | Snap-on and its industrial division |
| Spartan It LLC | Spartan IT | an IT company; the apparatus keyword rule (SPARTAN) caught it |
| Speedway Super America LLC | Speedway | the name config/vendor_map.csv uses |
| Speedway Superamerica | Speedway | the name config/vendor_map.csv uses |
| Star 2 Star Communications | Star2Star Communications | same company |
| Statewide Ford Lincoln Mercury | Statewide Ford Lincoln | same dealer |
| Stoops Freightliner - Dayton | Stoops Freightliner | same dealer |
| Suburban Propane - A/R Ctr | Suburban Propane | same company |
| Summit County Fiscal Officer | Summit County Fiscal Office | same office |
| Summitt Fire Apparatus | Summit Fire Apparatus | spelling |
| Sun Life Financial / Dental | Sun Life | same insurer |
| Sun Life Financial Policy 214802 | Sun Life | same insurer |
| Sunny Co munications | Sunny Communications | spelling |
| Superfleet Master Card | Superfleet | same fuel card |
| Superfleet Mastercard | Superfleet | same fuel card |
| Superfleet Mastercard Pro | Superfleet | same fuel card |
| Sysco Food Services | Sysco | same company |
| Sysco Foods | Sysco | same company |
| Sysco of Central CA | Sysco | same company |
| Sysco Sacramento | Sysco | same company |
| Travelers Insurance | Travelers | the name config/vendor_map.csv uses: insurance, not training |
| Ohio Treasurer of State | Treasurer of State of Ohio | same office |
| Treas St of Ohio | Treasurer of State of Ohio | same office |
| Treas St of Ohio, Fund 615 | Treasurer of State of Ohio | same office |
| Treasure of State of Ohio | Treasurer of State of Ohio | spelling |
| Treasureer of State of Ohio | Treasurer of State of Ohio | spelling |
| Trivan and Truck Body | Trivan Truck Body | same company |
| TruckPro-Columbus | TruckPro | the name config/vendor_map.csv uses |
| U.S. Bancorp Government | U.S. Bancorp Government Leasing & Finance | U.S. Bancorp leasing payments: the name config/vendor_map.csv uses |
| Us Bancorp | U.S. Bancorp Government Leasing & Finance | U.S. Bancorp leasing payments: the name config/vendor_map.csv uses |
| Us Bancorp Equip. Finance | U.S. Bancorp Government Leasing & Finance | U.S. Bancorp leasing payments: the name config/vendor_map.csv uses |
| Us Bancorp Government Leasing | U.S. Bancorp Government Leasing & Finance | U.S. Bancorp leasing payments: the name config/vendor_map.csv uses |
| Usbancorp | U.S. Bancorp Government Leasing & Finance | U.S. Bancorp leasing payments: the name config/vendor_map.csv uses |
| U S Bank National Assn | U.S. Bank | the name config/vendor_map.csv uses |
| U.S. Bank Trust | U.S. Bank | the name config/vendor_map.csv uses |
| Us Bank Cardmember Service | U.S. Bank | the name config/vendor_map.csv uses |
| US Bank Equipment Financing | U.S. Bank | the name config/vendor_map.csv uses |
| Us Bank Institutional Custody | U.S. Bank | the name config/vendor_map.csv uses |
| Us Bank Voyager | U.S. Bank Voyager Fleet Systems | U.S. Bank's fleet fuel card, kept apart from the bank: its lines are fuel purchases |
| Voyager | U.S. Bank Voyager Fleet Systems | U.S. Bank's fleet fuel card, kept apart from the bank: its lines are fuel purchases |
| Voyager Fleet Systems | U.S. Bank Voyager Fleet Systems | U.S. Bank's fleet fuel card, kept apart from the bank: its lines are fuel purchases |
| U.S. Department of Agriculture (Forest Service) | U.S. Department of Agriculture | one department |
| US Dept of Agriculture | U.S. Department of Agriculture | one department |
| Us Treasurey | U.S. Department of the Treasury | spelling |
| US Treasury | U.S. Department of the Treasury | the name config/vendor_map.csv uses for UNITED STATES TREASURY |
| United Rentals N America | United Rentals | the name config/vendor_map.csv uses |
| Unity National Bank/Card Member Services | Unity National Bank | same bank |
| University Hospital Health Systems | University Hospitals Health System | same hospital system |
| University Hospital Occupational Health | University Hospitals Occupational Health | same clinic |
| UNUM Insurance Co of Am | Unum | same insurer |
| US Food Service | US Foods | US Foodservice is US Foods' former name; the name config/vendor_map.csv uses |
| US Foodservice | US Foods | US Foodservice is US Foods' former name; the name config/vendor_map.csv uses |
| US Foodservice/los Angeles | US Foods | US Foodservice is US Foods' former name; the name config/vendor_map.csv uses |
| Valley Ford Truck | Valley Ford Truck Sales | same dealer |
| Vasu Communitcations | Vasu Communications | spelling |
| TargetSolutions Learning LLC Dba Vector Solut | Vector Solutions | TargetSolutions is Vector Solutions' former name; the name config/vendor_map.csv uses |
| Vision Service Plan - (Ct) | Vision Service Plan | VSP, one national company |
| Vision Service Plan Of Ohio | Vision Service Plan | VSP, one national company |
| Vision Service Plan-(OH) | Vision Service Plan | VSP, one national company |
| Vision Services Plan | Vision Service Plan | VSP, one national company |
| Vision Services Plan - (OH) | Vision Service Plan | VSP, one national company |
| Vsp Vision Service Plan | Vision Service Plan | VSP, one national company |
| W.S. Eletronics | W.S. Electronics | spelling |
| Warren Fire Equiptment | Warren Fire Equipment | spelling |
| Waterway of Southwest Pa | Waterway | Waterway (fleet wash), its Southwest Pennsylvania branch |
| Waterway Southwest Pa | Waterway | Waterway (fleet wash), its Southwest Pennsylvania branch |
| Waterway Sw Pa | Waterway | Waterway (fleet wash), its Southwest Pennsylvania branch |
| Waterways of Southwest PA | Waterway | Waterway (fleet wash), its Southwest Pennsylvania branch |
| Wells Fargo Financial Leasing | Wells Fargo | same bank |
| Wesbanco Bank | Wesbanco | same bank |
| West Mark Service Center | West Mark | same company |
| Western Extrication Spec | Western Extrication Specialists | same company; the source cuts the name off |
| Windstream Western Reserve | Windstream | same telephone company |
| Windstream/Alltel | Windstream | same telephone company |
| Witmer | Witmer Public Safety Group | the name config/vendor_map.csv uses |
| Yoche Dehe Fire Department | Yocha Dehe Fire Department | spelling |
| Zetron A Codan | Zetron | Zetron, a Codan company |
| The Ziegler Tire & Supply | Ziegler Tire | same company |
| Zimcom Internet Solutions | Zimcom | same company |
| Austin D Hurst | Austin D Hurst | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Berlin Twp Firefighter's Association Fire | Berlin Twp Firefighter's Association Fire | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Bethel Fire Association | Bethel Fire Association | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Brian Cummins | Brian Cummins | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Craig P Stires | Craig P Stires | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| DellaPenna Construction | DellaPenna Construction | paid for building repairs: facilities, not it |
| Deluxe Door Systems | Deluxe Door Systems | a door company; vendor rule '^DELUXE' (Deluxe checks and forms) catches it by mistake |
| Emergency Medical Service Auth | Emergency Medical Service Auth | the California Emergency Medical Services Authority, a state agency (dues and consulting): government |
| Farella Braun & Martel | Farella Braun & Martel | a San Francisco law firm; the ambulance keyword rule (BRAUN) caught it |
| Fire Dept Extractor Supply | Fire Dept Extractor Supply | sells turnout gear extractors (laundry machines), as Super Laundry Equipment: a company, not a government |
| FireStationFurniture.com | FireStationFurniture.com | station furniture: facilities, as Utah's keyword rule files it |
| Harris & Harris | Harris & Harris | collection agency for ambulance bills (TX, CA): ems-billing, not finance |
| Health Care Logistics | Health Care Logistics | EMS and pharmacy supplies: ems-supplies, not rms |
| Howard W. Goodyear | Howard W. Goodyear | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Jasmine M Pierce | Jasmine M Pierce | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Jason M. Pauline | Jason M. Pauline | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| JE Dunn Construction | JE Dunn Construction | a construction company; the journal-entry keyword rule '^JE\b' catches it by mistake |
| Lucas Jagger | Lucas Jagger | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Lucas Parmelee | Lucas Parmelee | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Lucas Roberts | Lucas Roberts | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Lucas S Welsh | Lucas S Welsh | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Matt Hurst | Matt Hurst | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Napa County Resc Conserv Dist | Napa County Resc Conserv Dist | a resource conservation district, as the other RCDs: government, not fleet (the NAPA keyword caught it) |
| Ryan M Lucas | Ryan M Lucas | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Sierra Pacific Industries | Sierra Pacific Industries | paid for rents and leases: facilities |
| Spartan Armor Systems | Spartan Armor Systems | body armor; the apparatus keyword rule (SPARTAN) caught it |
| Spartan Tool Supply | Spartan Tool Supply | tools; the apparatus keyword rule (SPARTAN) caught it |
| Tanner S Glass | Tanner S Glass | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Wendell A Slagell | Wendell A Slagell | paid from 'Other - Salaries' accounts: payroll (a keyword in the name set a purchasing category) |
| Canopy |  | CAL FIRE greenhouse payee; the key CANOPY also names an unrelated Utah payee, so no shared row |

Pairs that look alike but stay apart, for review (229 found; the 184 with $25,000
or more of proposed and Utah spend together are listed). Merge one by adding a row to
`config/vendor_name_merges.csv` and running the script again.

| Name | Name | Spend | Spend |
| --- | --- | --- | --- |
| A & P Helicopters | PJ Helicopters | $2,925,364 | $88,766,216 |
| Payroll | Payroll Select Service | $67,796,290 | $2,323,477 |
| U.S. Bank | U.S. Bank Voyager Fleet Systems | $23,605,468 | $18,568,486 |
| American Forest Foundation | National Forest Foundation | $16,202,352 | $22,858,443 |
| Erickson | Erickson Air-Crane | $1,096,194 | $25,849,873 |
| Atlantic | Atlantic Emergency Solutions | $39,864 | $21,438,404 |
| Cal Poly | Cal Poly Humboldt Sponsored | $12,164,898 | $2,230,568 |
| Butler Tech | Hr Butler | $137,519 | $11,994,542 |
| City of Reading | City of Redding | $4,095,686 | $6,928,767 |
| SCI Consulting Group | SRT Consulting Group | $9,900,000 | $16,000 |
| Environmental Solutions | International Environmental | $1,205 | $7,392,926 |
| Maintenance Supplies | SW Maintenance | $4,716,098 | $1,976,820 |
| System Solutions | System Solutions DVBE | $942,882 | $5,153,911 |
| Phoenix | Phoenix Safety Outfitters | $74,924 | $4,547,373 |
| Horizon | Horizon International Group | $52,028 | $4,252,344 |
| Sierra Fire Services | Sierra Site Services | $1,138,270 | $2,944,635 |
| UC Davis | UC Davis FD | $2,034,484 | $1,923,326 |
| Allied | Allied Network Solutions | $12,762 | $3,631,612 |
| Fire Safety Services | Fire Safety USA | $3,261,320 | $22,767 |
| City of Nampa | City of Napa | $452,648 | $2,749,262 |
| Hopland Fire Protection Dist | Orland Fire Protection Dist | $1,603,545 | $1,255,585 |
| D-g Backhoe Service | J R Backhoe | $1,587,043 | $1,017,498 |
| JW Enterprises | RJW Enterprises | $562,208 | $1,818,114 |
| Central FPD | North Central FPD | $1,312,645 | $1,017,342 |
| Guardian | Guardian Helicopters | $509,303 | $1,711,172 |
| Parkland Health (Dallas County Hospital District) | Parkland USA | $2,172,839 | $6,569 |
| Stellar | Stellar Restaurants | $83,976 | $2,035,320 |
| Commercial Truck | Commercial Truck & Trailer | $2,090,942 | $18,223 |
| Burst Communications | First Communications | $1,974,303 | $95,136 |
| F.N.B. Equipment Finance | PNC Equipment Finance | $347,657 | $1,602,720 |
| Federal | Federal 941 Deposit | $1,658,972 | $186,668 |
| Federal | Federal Resources | $1,658,972 | $54,917 |
| Harris | Harris & Harris | $13,525 | $1,650,097 |
| Federal | Federal Processing Registry | $1,658,972 | $1,798 |
| PC Specialists | TV Specialists | $1,641,101 | $17,127 |
| Idaho Fire Technologies | North Idaho Fire | $1,200 | $1,629,443 |
| Erickson | Erickson Construction | $1,096,194 | $461,309 |
| Corona Fire Department | Coronado Fire Dept | $1,264,059 | $244,129 |
| Pala Fire Department | Pauma Fire Department | $815,292 | $660,142 |
| Fountain Valley Fire Dept | Mountain Valley Fire Dept | $1,341,200 | $70,584 |
| American Water Truck SVCS | K & B Water Truck Service | $967,398 | $418,729 |
| Colton Fire Department | Colton Incorporated | $1,367,375 | $11,536 |
| First National Bank | First National Bank of Omaha | $1,191,830 | $115,153 |
| Corona Fire Department | Moroni Fire Department | $1,264,059 | $32,388 |
| Harris | Harris Emergency Services | $13,525 | $1,275,647 |
| Prodigy | Prodigy Consulting | $18,387 | $1,255,437 |
| First National Bank | First National Bank-Loan | $1,191,830 | $72,407 |
| Premier Companies | Premier Vehicle Installation | $14,488 | $1,211,174 |
| First National Bank | First National Bank - Visa | $1,191,830 | $2,197 |
| Emergency Vehicle Equipment | Hi-tech Emergency Vehicle Service | $528,013 | $618,588 |
| Emergency Vehicle Systems | Hi-tech Emergency Vehicle Service | $477,009 | $618,588 |
| Mission Communications | Vision Communications | $92,210 | $986,227 |
| Summit Land Management | The Summit | $1,020,290 | $1,161 |
| Emergency Vehicle Equipment | Emergency Vehicle Systems | $528,013 | $477,009 |
| Clark County Treasurer | Stark County Treasurer | $232,237 | $721,238 |
| Western Water | Western Waters | $6,013 | $914,237 |
| Premier Companies | Premier Portables | $14,488 | $891,170 |
| Rc Construction | VC Construction | $7,050 | $851,515 |
| Ec Construction | VC Construction | $4,617 | $851,515 |
| Salary | Salary Readychex | $837,261 | $9,588 |
| Salina Fire Department | Salinas Fire Department | $83,270 | $757,166 |
| Phoenix | Phoenix Farms | $74,924 | $693,200 |
| B&C Communications | J&K Communications | $664,269 | $101,743 |
| Summit Fire Apparatus | The Summit | $735,944 | $1,161 |
| CO Building Systems | S&K Building Services | $706,778 | $5,728 |
| Wyatt | Wyatt Letki | $670,298 | $16,110 |
| Wyatt | Wyatt Lm Letki | $670,298 | $2,329 |
| Emergency Vehicle Products | Hi-tech Emergency Vehicle Service | $28,904 | $618,588 |
| Eastern Municipal Water Dist | Western Municipal Water Dist | $218,794 | $405,520 |
| True North | True North Behavioral Health | $579,955 | $32,030 |
| A & A Construction | L & S Construction | $430,842 | $165,445 |
| Citizens Bank | Citizens National Bank | $63,728 | $508,326 |
| Emergency Vehicle Equipment | Emergency Vehicle Products | $528,013 | $28,904 |
| Allied | Allied Universal | $12,762 | $537,060 |
| Allied | Allied Storage Containers | $12,762 | $532,510 |
| G and J Truck Sales | Truck Sales and Services | $507,938 | $13,171 |
| Guardian | Guardian Alarm | $509,303 | $10,391 |
| Western Fire Equipment | Western Fire Supply | $438,000 | $76,451 |
| Petroleum Equipment Company | R B Petroleum Services | $31,739 | $476,989 |
| Emergency Vehicle Products | Emergency Vehicle Systems | $28,904 | $477,009 |
| DAT Management | Day Management | $720 | $500,959 |
| Apple | Apple One | $89,240 | $404,809 |
| Felton Fire Protection Dist | Wilton Fire Protection Dist | $149,739 | $267,880 |
| Allied | Allied Benefit Systems | $12,762 | $397,623 |
| Pitney Bowes | Pitney Bowes Purchase Power | $386,883 | $13,450 |
| Pitney Bowes | Pitney Bowes Bank | $386,883 | $6,100 |
| Premier Bank | Premier Companies | $357,152 | $14,488 |
| City of Oroville | City of Orrville | $355,488 | $3,800 |
| Elite | Elite Fire Support | $17,035 | $298,706 |
| Larson & Company | The Larson Group | $290,363 | $5,129 |
| Basic | Basic American Supply | $289,018 | $986 |
| CC Auto Parts | D & S Auto Parts | $267,344 | $13,835 |
| CT Electric | Cr Electric | $269,479 | $11,301 |
| Spectrum Imaging Technologies | The Spectrum | $276,751 | $1,436 |
| CC Auto Parts | G & W Auto Parts | $267,344 | $5,179 |
| JC Auto | JC Auto Enterprise Cal | $3,275 | $261,683 |
| Garland/DBS | The Garland | $225,826 | $38,541 |
| City of Emmet | City of Emmett | $41,818 | $221,097 |
| B&K Concrete Construction & | LK Concrete Construction | $191,550 | $68,050 |
| Valley Ford | Valley Ford Truck Sales | $150,303 | $105,349 |
| Premier Companies | Premier Truck Group | $14,488 | $239,869 |
| Shelly L Lacey | The Shelly | $212,131 | $38,166 |
| 3F Fitness | G&G Fitness Equipment | $77,540 | $115,414 |
| GT Logging | RT Logging | $152,995 | $39,204 |
| Plain Twp | Plain Twp FF Assoc Acct 4594 | $86,894 | $98,176 |
| Phoenix | Phoenix Rebellion Therapy | $74,924 | $109,871 |
| Cleaning Supplies | ML Cleaning | $18,382 | $162,737 |
| CMT Technical Services | Jet Technical Services | $171,335 | $5,203 |
| Premier Companies | Premier Safety | $14,488 | $152,429 |
| Brite | Brite Computers | $99,152 | $63,095 |
| Skyline Roofing | Skyline Roofing & Exteriors | $77,200 | $80,421 |
| Valley Ford | Valley Ford of Huron | $150,303 | $6,596 |
| Douglas Allan Theobald | Douglas Allen Theobald | $112,416 | $42,829 |
| EB Employee Solutions | Employee | $84,840 | $68,481 |
| Phoenix | Phoenix Fire Service | $74,924 | $75,637 |
| Pro Air | Pro Air Midwest | $28,324 | $121,438 |
| Elite | Elite Housing | $17,035 | $124,801 |
| Be Solutions | CE Solutions | $122,549 | $10,374 |
| Clean Sport | The Clean Spot | $81,893 | $44,280 |
| Tomas Bilson | Tomas Bilson-Jimenez | $66,686 | $56,685 |
| Neal R Arsenio | Neil R Arsenio | $20,731 | $101,743 |
| Holiday Inn | Holiday Inn Express | $17,414 | $102,267 |
| Devin M Brown | Kevin M Brown | $2,063 | $116,232 |
| C. G. Construction | CM Construction | $53,560 | $51,623 |
| Foresthill Fire Protection District | Forestville Fire Protection District | $29,389 | $75,166 |
| Phoenix Fire | Phoenix Fire Service | $28,623 | $75,637 |
| Phoenix | Phoenix Fire | $74,924 | $28,623 |
| Christopher J Scott | Christopher M Scott | $5,023 | $97,600 |
| Colton A Akers | Colton Incorporated | $90,355 | $11,536 |
| Sign Pro | Sign Pro Wraps | $8,007 | $93,652 |
| CM Construction | Cmp Construction | $51,623 | $45,947 |
| Standard Plumbing Supply | The Standard | $38,878 | $57,539 |
| Phoenix | Phoenix Outfitters | $74,924 | $19,675 |
| EB Employee Solutions | Employee Services | $84,840 | $3,846 |
| TruckPro | TruckPro Collision | $36,793 | $50,751 |
| Michael C Smith | Michael L Smith | $23,348 | $61,898 |
| Standard-Examiner | The Standard | $26,280 | $57,539 |
| Summit Contracting | The Summit | $80,389 | $1,161 |
| Black Ridge | Blackridge | $36,750 | $40,317 |
| Allied | Allied Roofing | $12,762 | $63,838 |
| Employee | Employee Benefits | $68,481 | $6,121 |
| Sinclair | Sinclair Community College | $1,217 | $71,545 |
| Brendan D Wagner | Brendon D Wagner | $63,768 | $8,571 |
| Employee | Employee Services | $68,481 | $3,846 |
| Pepsi Cola | Pepsi-Cola of Ogden | $67,825 | $4,132 |
| Employee | Employee Dedcution Reimbursement | $68,481 | $3,291 |
| Employee | Employee Assistance Group | $68,481 | $2,500 |
| Elite | Elite Computers | $17,035 | $51,864 |
| Ohio Power | Ohio Power Tool | $20,849 | $47,825 |
| National Wildland Fire | Wildland Fire | $63,000 | $5,093 |
| Premier Companies | Premier Fire Rescue | $14,488 | $53,099 |
| Garland Fire Department | The Garland | $25,895 | $38,541 |
| Standard Restaurant Equipment | The Standard | $6,574 | $57,539 |
| Garage Door Service | Garage Door Service & Repair | $52,854 | $4,300 |
| D & S Auto Parts | M&D Auto Parts | $13,835 | $41,660 |
| American Diesel Service | D & W Diesel | $30,425 | $24,241 |
| Tylar M Palm | Tyler M Palm | $44,239 | $8,888 |
| Building Solutions | S&K Building Services | $46,838 | $5,728 |
| HSI Investigations | Hs Investigations | $7,747 | $44,348 |
| Colton B Foor | Colton Incorporated | $39,188 | $11,536 |
| G & W Auto Parts | M&D Auto Parts | $5,179 | $41,660 |
| Matthew D Benigni | Matthew P Benigni | $17,746 | $28,512 |
| Atlantic | Atlantic Signal | $39,864 | $5,400 |
| Atlantic | Atlantic Sign | $39,864 | $4,726 |
| Kimco Fire Protection | Silco Fire Protection | $3,701 | $40,115 |
| Premier Athletics | Premier Companies | $28,301 | $14,488 |
| Garland City | The Garland | $2,254 | $38,541 |
| Kyle P Stechschulte | Kyle W. Stechschulte | $11,152 | $29,014 |
| Allied | Allied Administrators | $12,762 | $26,309 |
| B&H | B&H Photo & Electronics | $2,064 | $36,985 |
| Colton Incorporated | Colton Taylor Lewis | $11,536 | $26,399 |
| Larsen | Larsen Architects | $11,377 | $24,944 |
| Allied | Allied Mechanical | $12,762 | $22,332 |
| Prodigy | Prodigy EMS | $18,387 | $15,940 |
| Premier Companies | Premier Occupational Health | $14,488 | $19,661 |
| On-Target | Target | $29,990 | $1,808 |
| Multi Vendor | Multi-Vendor for Wh Employees | $28,224 | $3,034 |
| Brian P Huston | Brian S. Huston | $2,858 | $27,995 |
| Synchrony Bank | Synchrony Bank - Amazon Prox | $22,498 | $7,715 |
| Allied | Allied Car Wash | $12,762 | $14,937 |
| Synchrony Bank | Synchrony Bank-Sams Club | $22,498 | $5,007 |
| TRUCK SERVICE INC C/O Interstate Billing Serv | Truck Service | $11,421 | $14,201 |
| 3-D Roofing | Jb Roofing | $20,000 | $5,382 |
| Premier Community Health | Premier Companies | $10,711 | $14,488 |

## Cross-state vendors

<!-- cross-state:start -->

Top 50 canonical vendors by purchasing spend over the five states: Utah from `data/data.json` (rows in
purchasing categories), the states from `data/states/<st>/transactions.csv.gz` (payee key through
config/vendor_map.csv, then the vendor rules; payees in a purchasing category). Each cell: net dollars
(agencies). Recomputed by every run of the script.

| # | Vendor | Category | Total | UT | OH | CA | ID | TX | States |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Amentum | apparatus | $652,315,090 |  |  | $652,315,090 (1) |  |  | 1 |
| 2 | Logistic Specialties | apparatus | $269,469,982 |  |  | $269,469,982 (1) |  |  | 1 |
| 3 | Air Methods (United Rotorcraft) | apparatus | $226,652,619 |  |  | $226,652,619 (1) |  |  | 1 |
| 4 | Perimeter Solutions | wildland | $194,715,834 |  |  | $193,966,134 (1) | $749,700 (1) |  | 2 |
| 5 | WEX | fleet | $101,607,418 | $518,280 (25) | $2,207,438 (41) | $96,998,386 (2) | $1,883,314 (1) |  | 4 |
| 6 | L.N. Curtis & Sons | fire-equipment | $91,078,196 | $33,093,028 (165) | $5,932 (3) | $57,074,127 (5) | $905,109 (1) |  | 4 |
| 7 | Allstar Fire Equipment | fire-equipment | $90,411,881 | $75,442 (2) |  | $90,336,439 (6) |  |  | 2 |
| 8 | PJ Helicopters | apparatus | $88,766,216 |  |  | $88,766,216 (1) |  |  | 1 |
| 9 | Helicopter Transport Services | apparatus | $82,540,029 |  |  | $82,540,029 (1) |  |  | 1 |
| 10 | Siddons-Martin Emergency Group | apparatus | $79,704,448 | $43,256,660 (106) | $2,036 (2) |  |  | $36,445,753 (3) | 3 |
| 11 | Metro Fire Apparatus Specialists | apparatus | $66,922,636 |  |  |  |  | $66,922,636 (3) | 1 |
| 12 | Motorola Solutions | radios | $59,308,838 | $8,739,484 (82) | $6,628,475 (99) | $38,478,971 (5) | $97,254 (1) | $5,364,654 (53) | 5 |
| 13 | Billings Flying Service | apparatus | $58,227,301 |  |  | $58,227,301 (1) |  |  | 1 |
| 14 | JE Dunn Construction | construction | $57,557,606 |  |  |  |  | $57,557,606 (1) | 1 |
| 15 | US Foods | general | $55,446,000 | $1,417 (2) |  | $55,444,584 (1) |  |  | 2 |
| 16 | Pacific Gas & Electric | utilities | $47,553,275 |  |  | $47,553,275 (1) |  |  | 1 |
| 17 | Radiomobile | it | $47,132,772 |  |  | $47,132,772 (2) |  |  | 1 |
| 18 | Coulson Aviation | apparatus | $46,805,449 |  |  | $46,805,449 (1) |  |  | 1 |
| 19 | Advanced Data Processing (Intermedix) | ems-billing | $44,399,610 |  |  | $44,399,610 (2) |  |  | 1 |
| 20 | Municipal Emergency Services | fire-equipment | $43,847,628 | $1,858,969 (65) | $3,634,138 (117) | $27,004,918 (6) |  | $11,349,602 (2) | 4 |
| 21 | Rosenbauer | apparatus | $41,836,891 | $35,711,665 (18) | $4,685,524 (11) | $1,439,701 (2) |  |  | 3 |
| 22 | Siller Helicopters | apparatus | $41,744,146 |  |  | $41,744,146 (1) |  |  | 1 |
| 23 | Columbia Helicopters | apparatus | $38,067,505 |  |  | $38,067,505 (1) |  |  | 1 |
| 24 | Rezek Equipment | general | $37,597,022 |  |  | $37,597,022 (1) |  |  | 1 |
| 25 | Stryker | ems-equipment | $37,148,385 | $7,297,986 (55) | $12,444,346 (121) | $10,024,506 (6) |  | $7,381,547 (2) | 4 |
| 26 | Bauer Compressors | scba | $36,725,596 |  |  | $36,725,596 (5) |  |  | 1 |
| 27 | AT&T | telecom | $36,517,157 | $1,517,753 (47) | $1,815,831 (92) | $29,048,908 (5) | $345,679 (1) | $3,788,985 (170) | 5 |
| 28 | Verizon | telecom | $35,113,506 | $1,557,617 (70) | $1,968,038 (125) | $29,895,423 (5) | $308,167 (1) | $1,384,261 (76) | 5 |
| 29 | Peraton | it | $35,070,574 |  |  | $35,049,238 (2) |  | $21,336 (1) | 2 |
| 30 | Digitech Computer | ems-billing | $34,719,706 | $174,009 (1) | $841,940 (3) |  |  | $33,703,757 (2) | 3 |
| 31 | Life-Assist | ems-supplies | $34,087,982 | $2,342,095 (33) | $36,302 (7) | $19,307,689 (5) |  | $12,401,896 (3) | 4 |
| 32 | ICL Performance Products | wildland | $33,677,540 |  |  | $33,677,540 (1) |  |  | 1 |
| 33 | Bound Tree Medical | ems-supplies | $30,747,351 | $4,281,744 (55) | $7,557,598 (118) | $9,094,260 (5) |  | $9,813,749 (3) | 4 |
| 34 | Tom's Equipment Rental | general | $30,516,271 |  |  | $30,516,271 (1) |  |  | 1 |
| 35 | Hogan & Associates Construction | construction | $29,790,267 | $29,790,267 (6) |  |  |  |  | 1 |
| 36 | Trust One Components | apparatus | $28,803,794 |  |  | $28,803,794 (1) |  |  | 1 |
| 37 | Grainger | general | $28,802,984 | $1,159,248 (47) | $1,137,038 (71) | $23,664,713 (5) | $172,163 (1) | $2,669,821 (1) | 5 |
| 38 | Courtney Aviation | apparatus | $27,864,231 |  |  | $27,864,231 (1) |  |  | 1 |
| 39 | Flintco | construction | $27,352,466 |  |  |  |  | $27,352,466 (1) | 1 |
| 40 | Neptune Aviation Services | apparatus | $27,329,166 |  |  | $27,329,166 (1) |  |  | 1 |
| 41 | Erickson Air-Crane | apparatus | $25,849,873 |  |  | $25,849,873 (2) |  |  | 1 |
| 42 | SIRQ | construction | $24,688,318 | $24,688,318 (5) |  |  |  |  | 1 |
| 43 | Technosylva | software | $24,519,464 |  |  | $24,519,464 (1) |  |  | 1 |
| 44 | All American Emergency Services | general | $24,407,402 |  |  | $24,407,402 (1) |  |  | 1 |
| 45 | South Coast Fire Equipment | fire-equipment | $24,140,413 |  |  | $24,140,413 (1) |  |  | 1 |
| 46 | Aero Air | apparatus | $22,854,462 |  |  | $22,854,462 (1) |  |  | 1 |
| 47 | Big-D Construction | construction | $22,846,215 | $22,846,215 (2) |  |  |  |  | 1 |
| 48 | Northrop Grumman | rms | $22,657,723 |  |  | $22,657,723 (2) |  |  | 1 |
| 49 | Helimax Aviation | apparatus | $22,210,882 |  |  | $22,210,882 (1) |  |  | 1 |
| 50 | Elk Grove Auto Group | fleet | $22,154,376 |  |  | $22,154,376 (2) |  |  | 1 |

Vendors with purchasing spend in at least three of the five states: 322. The 50
with the most spend (the national vendors, each under one name):

| # | Vendor | Category | Total | UT | OH | CA | ID | TX | States |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | WEX | fleet | $101,607,418 | $518,280 (25) | $2,207,438 (41) | $96,998,386 (2) | $1,883,314 (1) |  | 4 |
| 2 | L.N. Curtis & Sons | fire-equipment | $91,078,196 | $33,093,028 (165) | $5,932 (3) | $57,074,127 (5) | $905,109 (1) |  | 4 |
| 3 | Siddons-Martin Emergency Group | apparatus | $79,704,448 | $43,256,660 (106) | $2,036 (2) |  |  | $36,445,753 (3) | 3 |
| 4 | Motorola Solutions | radios | $59,308,838 | $8,739,484 (82) | $6,628,475 (99) | $38,478,971 (5) | $97,254 (1) | $5,364,654 (53) | 5 |
| 5 | Municipal Emergency Services | fire-equipment | $43,847,628 | $1,858,969 (65) | $3,634,138 (117) | $27,004,918 (6) |  | $11,349,602 (2) | 4 |
| 6 | Rosenbauer | apparatus | $41,836,891 | $35,711,665 (18) | $4,685,524 (11) | $1,439,701 (2) |  |  | 3 |
| 7 | Stryker | ems-equipment | $37,148,385 | $7,297,986 (55) | $12,444,346 (121) | $10,024,506 (6) |  | $7,381,547 (2) | 4 |
| 8 | AT&T | telecom | $36,517,157 | $1,517,753 (47) | $1,815,831 (92) | $29,048,908 (5) | $345,679 (1) | $3,788,985 (170) | 5 |
| 9 | Verizon | telecom | $35,113,506 | $1,557,617 (70) | $1,968,038 (125) | $29,895,423 (5) | $308,167 (1) | $1,384,261 (76) | 5 |
| 10 | Digitech Computer | ems-billing | $34,719,706 | $174,009 (1) | $841,940 (3) |  |  | $33,703,757 (2) | 3 |
| 11 | Life-Assist | ems-supplies | $34,087,982 | $2,342,095 (33) | $36,302 (7) | $19,307,689 (5) |  | $12,401,896 (3) | 4 |
| 12 | Bound Tree Medical | ems-supplies | $30,747,351 | $4,281,744 (55) | $7,557,598 (118) | $9,094,260 (5) |  | $9,813,749 (3) | 4 |
| 13 | Grainger | general | $28,802,984 | $1,159,248 (47) | $1,137,038 (71) | $23,664,713 (5) | $172,163 (1) | $2,669,821 (1) | 5 |
| 14 | Zoll Medical | ems-equipment | $21,661,287 | $8,430,452 (47) | $1,801,404 (24) | $10,793,602 (6) |  | $635,830 (1) | 4 |
| 15 | LION | ppe | $20,553,658 |  | $42,083 (1) | $365,838 (3) |  | $20,145,738 (2) | 3 |
| 16 | Boise Mobile Equipment | apparatus | $17,929,883 | $241 (1) |  | $17,388,800 (2) | $540,842 (1) |  | 3 |
| 17 | ImageTrend | rms | $12,970,087 | $2,540,445 (49) | $561,779 (12) | $9,705,622 (3) |  | $162,241 (2) | 4 |
| 18 | McKesson Medical-Surgical | ems-supplies | $12,907,248 | $26,945 (6) | $42,979 (4) | $12,649,069 (3) |  | $188,255 (1) | 4 |
| 19 | Insight Public Sector | it | $12,507,948 | $98,789 (7) | $5,508 (1) | $12,273,261 (4) |  | $130,392 (3) | 4 |
| 20 | Ferrara Fire Apparatus | apparatus | $10,027,626 |  | $1,545,052 (1) | $8,481,160 (1) |  | $1,415 (1) | 3 |
| 21 | Galls | uniforms | $9,744,636 | $16,516 (15) | $3,109,455 (57) | $6,520,130 (3) |  | $98,535 (2) | 4 |
| 22 | Henry Schein | ems-supplies | $8,901,838 | $6,347,677 (53) | $2,329,274 (16) | $78,185 (3) |  | $146,701 (2) | 4 |
| 23 | 49er Communications | radios | $8,144,947 | $210,259 (12) |  | $7,182,543 (3) | $752,145 (1) |  | 3 |
| 24 | Western Fire Supply | fire-equipment | $7,661,253 | $76,451 (5) | $15,237 (4) | $7,569,565 (2) |  |  | 3 |
| 25 | Pierce Manufacturing | apparatus | $7,536,638 | $2,410 (2) | $8,235 (3) | $7,525,994 (1) |  |  | 3 |
| 26 | Vector Solutions | training-software | $7,163,847 | $1,233,062 (35) | $654,916 (23) | $5,275,869 (1) |  |  | 3 |
| 27 | Tablet Command | rms | $6,859,918 | $57,822 (1) | $78,648 (5) | $6,723,447 (3) |  |  | 3 |
| 28 | Rocky Mountain Power | utilities | $6,504,282 | $5,861,988 (88) |  | $635,378 (1) | $6,916 (1) |  | 3 |
| 29 | CDW Government | it | $6,481,855 | $788,847 (22) | $487,859 (34) | $3,462,366 (4) | $21,819 (1) | $1,720,964 (27) | 5 |
| 30 | Frazer | ambulance | $6,239,339 | $986,679 (1) | $192,621 (1) | $187,990 (1) |  | $4,872,049 (1) | 4 |
| 31 | Comcast | telecom | $6,120,628 | $1,450,244 (24) | $43,205 (6) | $4,627,178 (1) |  |  | 3 |
| 32 | National Auto Fleet Group | fleet | $5,455,481 | $459,468 (1) | $91,960 (1) | $4,904,053 (2) |  |  | 3 |
| 33 | Teleflex | ems-supplies | $5,441,931 | $1,210,809 (39) | $856,300 (62) | $2,139,161 (4) |  | $1,235,662 (2) | 4 |
| 34 | ESO Solutions | rms | $5,303,931 | $1,121,845 (33) | $3,075,745 (116) | $1,687 (1) |  | $1,104,654 (1) | 4 |
| 35 | Snap-on | general | $5,186,262 | $9,210 (1) | $2,334 (2) | $5,173,903 (3) |  | $815 (1) | 4 |
| 36 | Dell Technologies | it | $4,739,997 | $271,898 (26) | $357,456 (22) | $1,494,528 (3) | $23,630 (1) | $2,592,485 (49) | 5 |
| 37 | Carahsoft | software | $4,681,321 | $2,437 (2) |  | $4,392,227 (1) |  | $286,657 (4) | 3 |
| 38 | Line Gear | uniforms | $4,558,932 | $409 (1) |  | $4,558,008 (3) | $515 (1) |  | 3 |
| 39 | Amazon | general | $4,270,333 | $1,801,211 (75) | $1,169,793 (69) | $940,670 (4) | $303,761 (1) | $54,898 (1) | 5 |
| 40 | Staples | general | $3,909,038 | $61,817 (27) | $300,883 (78) | $2,460,927 (4) | $4,995 (1) | $1,080,416 (1) | 5 |
| 41 | T-Mobile | telecom | $3,804,698 | $269,974 (21) | $91,172 (19) | $3,443,551 (4) |  |  | 3 |
| 42 | NAPA Auto Parts | fleet | $3,532,178 | $898,794 (56) | $427,833 (82) | $2,129,267 (4) | $76,284 (1) |  | 4 |
| 43 | Ferno | ems-equipment | $3,396,633 | $217,576 (8) | $51,746 (6) | $3,127,311 (2) |  |  | 3 |
| 44 | Cummins | facilities | $3,265,464 | $268,713 (20) | $933,397 (57) | $2,063,354 (3) |  |  | 3 |
| 45 | Lexipol | training-software | $3,056,256 | $1,085,926 (51) | $1,100,282 (59) | $594,758 (1) |  | $275,290 (3) | 4 |
| 46 | Axon | it | $3,023,366 | $2,505 (1) | $15,151 (2) | $2,825,927 (3) |  | $179,782 (1) | 4 |
| 47 | HP | it | $3,021,606 | $87,537 (3) |  | $2,814,157 (2) | $1,146 (1) | $118,766 (5) | 4 |
| 48 | Rush Truck Centers | fleet | $2,999,079 | $646,435 (25) | $299,357 (17) | $1,890,076 (2) | $28 (1) | $163,184 (1) | 5 |
| 49 | Mud Lake Oil | fleet | $2,918,746 | $119 (1) |  | $2,868,138 (1) | $50,489 (1) |  | 3 |
| 50 | FTS Forest Technology Systems | wildland | $2,841,105 | $55,592 (1) |  | $2,670,248 (1) |  | $115,264 (1) | 3 |

Large fire and EMS vendors: every vendor name with purchasing spend whose name matches the brand, so a
second spelling would show here (Zoll Data Systems is Zoll's ePCR software company, kept apart as in
config/vendor_rules.csv).

| Brand | Vendor names (states) | Total |
| --- | --- | --- |
| Zoll | Zoll Medical (UT, OH, CA, TX); Zoll Data Systems (UT, OH) | $21,674,732 |
| Stryker / Physio-Control | Stryker (UT, OH, CA, TX) | $37,148,385 |
| L.N. Curtis | L.N. Curtis & Sons (UT, OH, CA, ID) | $91,078,196 |
| MSA | MSA Safety (UT, OH, CA) | $127,390 |
| Pierce | Pierce Manufacturing (UT, OH, CA) | $7,536,638 |
| Motorola | Motorola Solutions (UT, OH, CA, ID, TX) | $59,308,838 |
| Verizon | Verizon (UT, OH, CA, ID, TX) | $35,113,506 |
| AT&T | AT&T (UT, OH, CA, ID, TX) | $36,517,157 |
| Municipal Emergency Services | Municipal Emergency Services (UT, OH, CA, TX) | $43,847,628 |
| Bound Tree | Bound Tree Medical (UT, OH, CA, TX) | $30,747,351 |
| Henry Schein | Henry Schein (UT, OH, CA, TX) | $8,901,838 |
| Life-Assist | Life-Assist (UT, OH, CA, TX) | $34,087,982 |
| Fire-Dex | Fire-Dex (UT, OH, CA) | $375,387 |
| LION | LION (OH, CA, TX); Lion Creative Studios (OH); LION ENERGY LLC (UT) | $20,591,685 |
| Rosenbauer | Rosenbauer (UT, OH, CA) | $41,836,891 |
| Ferrara | Ferrara Fire Apparatus (OH, CA, TX) | $10,027,626 |
| Sutphen | Sutphen (OH) | $14,823,166 |
| KME | KME Fire Apparatus (CA) | $7,834,352 |
| Spartan | Spartan Fire (UT, CA) | $447,244 |
| Grainger | Grainger (UT, OH, CA, ID, TX) | $28,802,984 |
| Galls | Galls (UT, OH, CA, TX) | $9,744,636 |
| Teleflex | Teleflex (UT, OH, CA, TX) | $5,441,931 |
| Ferno | Ferno (UT, OH, CA) | $3,396,633 |
| ImageTrend | ImageTrend (UT, OH, CA, TX) | $12,970,087 |
| ESO | ESO Solutions (UT, OH, CA, TX) | $5,303,931 |
| Lexipol | Lexipol (UT, OH, CA, TX) | $3,056,256 |
| Vector Solutions | Vector Solutions (UT, OH, CA) | $7,163,847 |

<!-- cross-state:end -->

## Review notes and Utah impact

<!-- manual:start -->
Written by hand for the merge of 2026-10-07 (the script keeps this block as it is).

### Inputs and what was done before the merge

The four proposal files were read as committed at 56f6710 (OH 6,186 rows, CA 2,753, ID 488, TX 200) and then
deleted: `config/vendor_map.csv` is the source of truth. After main's Utah work was merged into this branch,
108 proposal keys repeated a key of `config/vendor_map.csv`, 72 of them with another vendor or category
(the 'about 72' of the task). The state agents had already removed all but three in favour of the Utah row
(OH 65, CA 24, ID 6, TX 10 rows); the three left are under 'Key conflicts' above. The 69 removed rows that
differed were reviewed again here: the Utah row is right or as good in each, so none was restored. One is a real
collision rather than an error: the key SPECTRUM is Utah's St. George newspaper (The Spectrum, professional) and
Ohio's Charter Spectrum ($165,246 in Ohio). A key carries one row, so Ohio payees published exactly as 'SPECTRUM'
show under The Spectrum; Ohio's other Spectrum spellings are under Charter Communications.

<details><summary>The removed rows that differed from config/vendor_map.csv</summary>

| State | Key | config/vendor_map.csv (kept) | Proposed | Proposed spend |
| --- | --- | --- | --- | --- |
| CA | BME FIRE TRUCKS | BME Fire Trucks / apparatus | Bme Fire Trucks / apparatus | $6,295,503 |
| CA | CARAHSOFT TECHNOLOGY | Carahsoft / software | Carahsoft Technology / it | $4,392,227 |
| CA | ENTENMANN ROVIN | Entenmann-Rovin / uniforms | Entenmann Rovin / unclassified | $634,498 |
| CA | FRONTIER | Frontier Communications / telecom | Frontier / telecom | $2,295,337 |
| CA | HIGHWAY PRODUCTS | Highway Products / apparatus | Highway Products / general | $491,788 |
| CA | LAWSON PRODUCTS | Lawson Products / fleet | Lawson Products / general | $390,307 |
| CA | OHD LLLP | OHD / scba | Ohd Lllp / it | $459,781 |
| CA | RICOH USA | Ricoh / it | Ricoh USA / general | $387,190 |
| CA | RS HUGHES | R.S. Hughes / fire-equipment | R S Hughes Company / fire-equipment | $517,602 |
| CA | SAFETY KLEEN SYSTEMS | Safety-Kleen / fleet | Safety Kleen Systems / fleet | $406,727 |
| CA | SIGTRONICS | Sigtronics / radios | Sigtronics / general | $441,972 |
| CA | SUN BADGE | Sun Badge Company / uniforms | Sun Badge / unclassified | $380,257 |
| CA | TAYLORS TINS | Taylor's Tins / unclassified | Taylors Tins / unclassified | $33,699 |
| CA | VORTEX INDUSTRIES | Vortex Industries / facilities | Vortex Industries / unclassified | $430,858 |
| CA | WM CORPORATE SERVICES | Waste Management / utilities | WM Corporate Services / utilities | $376,240 |
| ID | BUREAU OF LAND MANAGEMENT | Bureau of Land Management / government | U.S. Bureau of Land Management / government | $9,949,786 |
| ID | H AND E EQUIPMENT SERVICES | H&E Equipment Services / facilities | H & E Equipment Services / general | $80,409 |
| ID | MOTION AND FLOW CONTROL PRODUCTS | Motion & Flow Control Products / fleet | Motion and Flow Control Products / general | $55,409 |
| ID | SAFETY KLEEN SYSTEMS | Safety-Kleen / fleet | Safety-Kleen Systems / fleet | $50,909 |
| OH | AMERICAN EXPRESS | American Express / finance | American Express / payroll | $14,123 |
| OH | CARDMEMBER SERVICE | Cardmember Service / finance | Cardmember Service (credit card) / finance | $242,009 |
| OH | CET FIRE PUMPS MFG | CET Fire Pumps / fire-equipment | Cet Fire Pumps Mfg / apparatus | $58,442 |
| OH | CORE AND MAIN | Core & Main / facilities | Core & Main* / facilities | $6,271 |
| OH | CORE AND MAIN LP | Core & Main / facilities | Core & Main / fire-equipment | $170,025 |
| OH | COULTER VENTURES | Rogue Fitness / medical-exams | Coulter Ventures LLC / general | $40,851 |
| OH | DALMATIAN FIRE EQUIPMENT | Dalmatian Fire Equipment / fire-equipment | Dalmatian Fire Equipment, Inc. / fire-equipment | $12,912 |
| OH | DALMATION FIRE EQUIPMENT | Dalmatian Fire Equipment / fire-equipment | Dalmation Fire Equipment / fire-equipment | $5,113 |
| OH | DIGITECH COMPUTER | Digitech Computer / ems-billing | Digitech / ems-billing | $807,557 |
| OH | DREAMSEATS | DreamSeat / facilities | DreamSeats / facilities | $95,594 |
| OH | ELAN FINANCIAL SERVICES | Elan Financial Services / finance | Elan Financial Services (credit card) / finance | $121,543 |
| OH | EMERGENCY MEDICAL PRODUCTS | Emergency Medical Products / ems-supplies | Emergency Medical Products, Inc / ems-supplies | $191,148 |
| OH | EMERGENCY SERVICES MARKETING | IamResponding / software | Emergency Services Marketing Corp. Inc. / software | $34,625 |
| OH | FASTSIGNS | Fastsigns / professional | Fastsigns / general | $35,985 |
| OH | FIRST NATIONAL BANK OMAHA | First National Bank of Omaha / finance | First National Bank Omaha / finance | $47,654 |
| OH | FORGE FIRE AND | Forge Fire & Company / training | Forge and Fire / fire-equipment | $152,390 |
| OH | FRAZER | Frazer / ambulance | Frazer Ltd / ambulance | $193,003 |
| OH | FRONTIER | Frontier Communications / telecom | Frontier / telecom | $97,066 |
| OH | GEAR WASH | Fire-Dex / ppe | Gear Wash / fire-equipment | $34,901 |
| OH | GEARGRID | GearGrid / facilities | GearGrid LLC / fire-equipment | $33,268 |
| OH | GLOBAL INDUSTRIAL | Global Industrial / general | Global Industrial / facilities | $6,777 |
| OH | GRAINGER WW | Grainger / general | Grainger, W.W., Inc. / general | $19,636 |
| OH | HONEYWELL ANALYTICS | Honeywell / fire-equipment | Honeywell Analytics, Inc. / fire-equipment | $39,390 |
| OH | INTERSTATE BILLING SERVICE | Interstate Billing Service / fleet | Interstate Billing Service (truck parts) / fleet | $41,739 |
| OH | JOHN DEERE FINANCIAL | John Deere Financial / finance | John Deere Financial / fleet | $108,312 |
| OH | KNOX ASSOCIATES | Knox Company / fire-equipment | Knox Associates Inc / training | $9,062 |
| OH | MATTRESS FIRM | Mattress Firm / facilities | Mattress Firm / general | $31,635 |
| OH | MED TECH RESOURCE | Med-Tech Resource / fire-equipment | Med-Tech Resource Inc. / ems-supplies | $28,457 |
| OH | NATIONAL BUSINESS FURNITURE | National Business Furniture / facilities | National Business Furniture / general | $66,362 |
| OH | NATIONAL TESTING NETWORK | National Testing Network / professional | National Testing Network / it | $25,951 |
| OH | OTIS ELEVATOR | Otis Elevator / facilities | Otis Elevator Company / facilities | $37,083 |
| OH | PRAXAIR DISTRIBUTION | Linde Gas & Equipment / ems-supplies | Praxair Distribution Inc / ems-supplies | $15,447 |
| OH | QUADIENT FINANCE USA | Quadient / general | Quadient Finance USA Inc / general | $6,027 |
| OH | SALSBURY INDUSTRIES | Salsbury Industries / facilities | Salsbury Industries / utilities | $8,808 |
| OH | SENSIT TECHNOLOGIES | Sensit Technologies / fire-equipment | Sensit Technologies LLC / it | $13,819 |
| OH | SPECTRUM | The Spectrum / professional | Spectrum / telecom | $165,246 |
| OH | TABLET COMMAND | Tablet Command / rms | Tablet Command / software | $80,065 |
| OH | TIMECLOCK PLUS | TimeClock Plus / staffing-software | Timeclock Plus LLC / staffing-software | $42,900 |
| OH | TRUCKPRO | TruckPro / fleet | Truckpro / fleet | $33,783 |
| OH | TRUCKPRO HOLDING | TruckPro / fleet | TruckPro Holding Corp. / fleet | $36,241 |
| OH | TSI | TSI / scba | Tsi, Inc. / scba | $39,655 |
| OH | US BANCORP GOVERNMENT LEASING AND FINANCE | U.S. Bancorp Government Leasing & Finance / finance | U.S. Bancorp Government Leasing and Finance / finance | $441,408 |
| OH | US BANK | U.S. Bank / finance | Us Bank / finance | $2,321,025 |
| OH | US BANK EQUIPMENT FINANCE | U.S. Bank / finance | US Bank Equipment Finance / finance | $100,306 |
| OH | VFIS | VFIS / insurance | Vfis / payroll | $29,323 |
| OH | WITMER ASSOCIATES | Witmer Public Safety Group / fire-equipment | Witmer Associates Inc. / training | $67,711 |
| OH | WL CONSTRUCTION SUPPLY | WL Construction Supply / general | WL Construction Supply / construction | $5,240 |
| TX | CARAHSOFT TECHNOLOGY | Carahsoft / software | Carahsoft Technology / software | $286,657 |
| TX | GEAR GRID | GearGrid / facilities | Gear-Grid / facilities | $12,657 |
| TX | RS HUGHES | R.S. Hughes / fire-equipment | RS Hughes / general | $21,547 |

</details>

### Decisions worth a second look

- **Private persons.** `pipeline/build.py` lets a `config/vendor_map.csv` row decide before its person-name tests, so a
  state row for a person's name would show a Utah payee with the same key under that name. Three Ohio payroll rows
  collided with Utah payees that the Utah build withholds (Jason Brown, Matthew Evans, Tyler Anderson); they are
  mapped to `Individuals (names withheld)` / `individuals` by `config/vendor_name_merges.csv`, like Utah's own person
  rows. Ohio proposed 2,381 payroll rows, most of them persons, and they are in the shared map as proposed (owner
  decision 1); a new Utah payee with one of those keys would be shown by name, so re-run the Utah diff after every
  merge or Utah refetch.
- **Rule false hits.** Keyword rule `^JE\b` (journal entries) would turn JE Dunn Construction ($57.6M, Houston) into
  'No vendor named', and vendor rule `^DELUXE` (Deluxe checks) would take Deluxe Door Systems; both keep their own
  rows. Every other key a vendor rule names uses the rule's vendor (listed above).
- **Left out:** Canopy (a CAL FIRE greenhouse payee; the key CANOPY also names an unrelated Utah payee).
- **Category calls** (fourth column of `config/vendor_name_merges.csv`, which otherwise has the three columns the task
  names): Harris & Harris ems-billing (collects ambulance bills; by spend it would be finance), Recology utilities (waste
  haulers, as Waste Management and Republic Services), 8x8 telecom, Health Care Logistics ems-supplies, Burton's Fire
  apparatus, FireStationFurniture.com facilities, JE Dunn construction, Deluxe Door Systems facilities.
- **One category per vendor flattens some uses:** JPMorgan Chase Bank is payroll by spend (Ohio payroll accounts)
  although California's lines are card and bank payments; Honeywell keeps Utah's fire-equipment for Texas's building
  controls; Line Gear is uniforms. None of the three moves dollars between purchasing and non-purchasing; the
  category decisions table lists every such case.
- **Equal local names across states** (cities, townships, fire departments, dealers) are not grouped by the rules,
  but two payees with exactly the same name still share a vendor id on the site.
- **Utah rows added by hand (11):** payee spellings that the vendor rules miss, so AT&T, Verizon, Grainger and Vector
  Solutions have one name in Utah as well: AT AND T 4IRX 135346, AT AND T FIRSTNET, AT AND T STREETS AND TRAFFIC,
  GRAINGER DEPT 853392421, WW GRAINGER GRAINGER, TARGETSOLUTIONS, TARGETSOLUTIONS LEARNING 22 032, VERIZON BUSINESS,
  VERIZON COMMUNICATIONS CELLCO PARTNERSHIP, VERIZON COMMUNICATIONS WIRELESS, VERIZON COMMUNICATIONS WIRELESS CELLCO
  PARTNERSHIP. The map now has 14,676 rows.

### Utah impact

`python3 pipeline/build.py` before the merge (baseline: identical to the committed `data/data.json` apart from the
build date) and after it, from the final `config/vendor_map.csv`:

| | Before | After |
| --- | --- | --- |
| Vendors | 9,990 | 9,966 |
| Payee names shown | 18,696 | 18,704 |
| Rows | 63,963 | 63,962 |
| Single payments | 58,725 | 58,726 |
| Purchasing dollars | $677,363,961 | $677,373,536 |
| Unclassified purchasing dollars | $18,913,478 | $18,765,698 |
| Classified share of purchasing | 97.21% | 97.23% |
| Payees grouped as Individuals without a vendor_map row | 3,799 names, $3,733,357 | 3,788 names, $3,720,724 |
| Agencies matching the raw file | 185 of 185 | 185 of 185 |

Dollars that moved between categories (net, all years):

| Category | Before | After | Change |
| --- | --- | --- | --- |
| unclassified | $18,913,478 | $18,765,698 | -$147,779 |
| training | $14,386,870 | $14,439,734 | +$52,864 |
| fire-equipment | $48,811,452 | $48,837,660 | +$26,207 |
| facilities | $21,005,218 | $21,023,693 | +$18,475 |
| general | $6,909,395 | $6,925,819 | +$16,424 |
| wildland | $4,772,956 | $4,786,934 | +$13,978 |
| individuals | $14,544,281 | $14,532,439 | -$11,842 |
| software | $4,932,862 | $4,941,636 | +$8,774 |
| fleet | $56,073,052 | $56,081,591 | +$8,539 |
| uniforms | $11,592,718 | $11,585,981 | -$6,737 |
| apparatus | $100,880,890 | $100,886,861 | +$5,971 |
| telecom | $8,993,051 | $8,998,469 | +$5,418 |
| utilities | $17,931,960 | $17,927,914 | -$4,046 |
| ems-equipment | $18,370,897 | $18,374,497 | +$3,600 |
| ems-supplies | $18,853,957 | $18,856,855 | +$2,898 |
| professional | $9,644,974 | $9,647,548 | +$2,574 |
| payroll | $388,469,199 | $388,471,466 | +$2,267 |
| it | $11,130,473 | $11,131,606 | +$1,133 |
| ambulance | $16,552,581 | $16,553,309 | +$728 |
| ppe | $10,092,368 | $10,092,668 | +$300 |
| radios | $19,473,217 | $19,473,472 | +$255 |

103 Utah payee keys changed vendor name or category ($314,418 net spend). Each was reviewed:
unclassified payees given a category (Across the Street Productions training, Avenza it, Schindler Elevator
facilities, Botach and Forcible Entry fire-equipment, ...); spellings folded into an existing vendor (AT&T, Verizon,
Grainger, Vector Solutions, Lowe's, Stryker for Howmedica, NFPA, Fleetcor, Capital One); life and health insurers
moved to payroll as `config/vendor_map.csv` files MetLife, PEHP and SelectHealth; Esri to software as the ESRI row;
drones (Unmanned Vehicle Technologies) to fire-equipment; names cleaned (legal suffixes, capitals). Eight company
payee names that the build had grouped as Individuals are now shown under their vendor (Firehouse Innovations,
Firehouse Vigilance, Kimball Midwest, Prodigy EMS, UnitedHealthcare, Xerox, Genuine Parts as NAPA Auto Parts). No
person's name became visible. Reverted during review: Skyline Roofing (Utah's roofer is not Ohio's Skyline Roofing &
Exteriors), Canopy (unrelated payees), the three persons above, and the capitalisation of SiteOne, OK Fine
Productions, FastSpring, PK Safety Supply, PPE Software and Fire-Etc.

<details><summary>Every Utah payee key that changed (key | before | after | Utah net spend)</summary>

- ACROSS STREET PRODUCTIONS \| Across the Street Productions / unclassified / map -> Across the Street Productions / training / map \| 48,525
- AVENZA SYSTEMS \| AVENZA SYSTEMS INC / unclassified / none -> Avenza Systems / it / map \| 10,456
- SCHINDLER ELEVATOR \| SCHINDLER ELEVATOR CORP / unclassified / none -> Schindler Elevator / facilities / map \| 9,874
- HANGAR 14 SOLUTIONS \| HANGAR 14 SOLUTIONS, LLC / unclassified / none -> Hangar 14 Solutions / it / map \| 9,864
- TARGETSOLUTIONS \| TARGETSOLUTIONS INC / training-software / rule -> Vector Solutions / training-software / map \| 9,679
- CREWBOSS \| CrewBoss / unclassified / none -> CrewBoss / wildland / map \| 9,654
- GLOBAL EQUIPMENT \| GLOBAL EQUIPMENT COMPANY INC. / unclassified / none -> Global Equipment / facilities / map \| 9,399
- SNAP ON INDUSTRIAL \| Snap on Industrial / unclassified / none -> Snap-on / general / map \| 9,210
- REDD PUBLIC SAFETY EQUIPMENT \| REDD PUBLIC SAFETY EQUIPMENT LLC / unclassified / none -> Redd Public Safety Equipment / fire-equipment / map \| 8,978
- FIREHOUSE INNOVATIONS \| FIREHOUSE INNOVATIONS / unclassified / none -> Firehouse Innovations / training / map \| 8,840
- FITNESS SUPERSTORE \| Fitness Superstore, Inc. / medical-exams / rule -> Fitness Superstore / medical-exams / map \| 8,611
- FORCIBLE ENTRY \| Forcible Entry Inc. / unclassified / none -> Forcible Entry / fire-equipment / map \| 8,264
- BOTACH \| BOTACH / unclassified / none -> Botach / fire-equipment / map \| 7,677
- AMERICAN SAFETY AND HEALTH INSTITUTE \| AMERICAN SAFETY & HEALTH INSTITUTE / training / rule -> American Safety & Health Institute / training / map \| 7,316
- PITNEY BOWES \| Pitney Bowes / unclassified / none -> Pitney Bowes / general / map \| 7,106
- ENVIRONMENTAL SYSTEMS RESEARCH INSTITUTE ESRI \| ENVIRONMENTAL SYSTEMS RESEARCH INSTITUTE, INC. DBA ESRI / training / rule -> Esri / software / map \| 7,069
- UNMANNED VEHICLE TECHNOLOGIES \| Unmanned Vehicle Technologies,LLC / it / rule -> Unmanned Vehicle Technologies / fire-equipment / map \| 6,969
- CHASE CARD SERVICES \| CHASE CARD SERVICES / finance / rule -> Chase Card Services / finance / map \| 6,188
- DREAMSEAT \| Dreamseat LLC / unclassified / none -> DreamSeat / facilities / map \| 6,005
- BURTONS FIRE \| BURTON'S FIRE, INC. / unclassified / none -> Burton's Fire / apparatus / map \| 5,971
- CONEXWEST \| CONEXWEST / unclassified / none -> ConexWest / general / map \| 5,525
- FIRE APPARATUS SOLUTIONS \| FIRE APPARATUS SOLUTIONS / apparatus / rule -> Fire Apparatus Solutions / apparatus / map \| 5,134
- AT AND T STREETS AND TRAFFIC \| AT&T - Streets & Traffic / unclassified / none -> AT&T / telecom / map \| 5,017
- LINCOLN NATIONAL LIFE INSURANCE \| THE LINCOLN NATIONAL LIFE INSURANCE CO / insurance / rule -> The Lincoln National Life Insurance / payroll / map \| 4,994
- LOWES BUSINESS ACCOUNT \| LOWE'S BUSINESS ACCOUNT / facilities / rule -> Lowe's / facilities / map \| 4,878
- AT AND T FIRST NET \| AT&T FIRST NET / unclassified / none -> AT&T / telecom / map \| 4,765
- ETHOS FIRE \| ETHOS FIRE / unclassified / none -> Ethos Fire / wildland / map \| 4,324
- FLEETCOR TECHNOLOGIES \| FLEETCOR TECHNOLOGIES / it / rule -> Fleetcor / fleet / map \| 4,094
- HOWMEDICA OSTEONICS \| HOWMEDICA OSTEONICS CORP / unclassified / none -> Stryker / ems-equipment / map \| 3,600
- PPE SOFTWARE \| P P E SOFTWARE LLC / software / rule -> PPE Software / software / map \| 3,600
- GRANITE DATA SOLUTIONS \| GRANITE DATA SOLUTIONS / unclassified / none -> Granite Data Solutions / it / map \| 3,264
- OK FINE PRODUCTIONS \| OK Fine Productions / unclassified / none -> OK Fine Productions / training / map \| 3,166
- WESTERN STATE DESIGN \| Western State Design / unclassified / none -> Western State Design / facilities / map \| 3,071
- 8X8 \| 8X8 Inc / unclassified / none -> 8x8 / telecom / map \| 3,015
- AMBU \| Ambu / unclassified / none -> Ambu / ems-supplies / map \| 2,898
- DEERE AND \| Deere & Company / unclassified / none -> Deere & Company / fleet / map \| 2,861
- WESTERN SHELTER SYSTEMS \| WESTERN SHELTER SYSTEMS / unclassified / none -> Western Shelter Systems / fire-equipment / map \| 2,562
- PIERCE MANUFACTURING \| PIERCE MANUFACTURING / apparatus / rule -> Pierce Manufacturing / apparatus / map \| 2,410
- CAPITAL ONE TRADE CREDIT \| Capital One Trade Credit / unclassified / none -> Capital One / finance / map \| 2,370
- KALMIKOV ENTERPRISES \| KALMIKOV ENTERPRISES INC / unclassified / none -> Kalmikov Enterprises / fleet / map \| 1,896
- OES GLOBAL \| OES GLOBAL INC. / unclassified / none -> OES Global / general / map \| 1,777
- WW GRAINGER GRAINGER \| W.W. GRAINGER, INC dba GRAINGER / general / rule -> Grainger / general / map \| 1,728
- TIMMONS GROUP \| TIMMONS GROUP INC / unclassified / none -> Timmons Group / software / map \| 1,705
- FAST SIGNS \| Fast Signs / unclassified / none -> Fastsigns / professional / map \| 1,634
- NATIONAL FIRE PROTECTION ASSN \| NATIONAL FIRE PROTECTION ASSN. / unclassified / none -> NFPA / training / map \| 1,575
- SITEONE LANDSCAPE SUPPLY \| SiteOne Landscape Supply, LLC / facilities / rule -> SiteOne Landscape Supply / facilities / map \| 1,529
- FIREQUICK PRODUCTS \| Firequick Products Inc / unclassified / none -> FireQuick Products / fire-equipment / map \| 1,520
- BLAZESTACK \| Blazestack Inc / unclassified / none -> Blazestack / fire-equipment / map \| 1,500
- VERIZON COMMUNICATIONS CELLCO PARTNERSHIP \| VERIZON COMMUNICATIONS INC (CELLCO PARTNERSHIP) / telecom / rule -> Verizon / telecom / map \| 1,440
- RUGGED SOLUTIONS AMERICA \| RUGGED SOLUTIONS AMERICA / unclassified / none -> Rugged Solutions America / fleet / map \| 1,307
- BATTALION 3 TECHNOLOGIES \| Battalion 3 Technologies, LLC / it / rule -> Battalion 3 Technologies / it / map \| 1,300
- VERIZON BUSINESS \| VERIZON BUSINESS / telecom / rule -> Verizon / telecom / map \| 1,251
- FIRE ETC \| FIRE-ETC / unclassified / none -> Fire-Etc / fire-equipment / map \| 1,047
- VERIZON COMMUNICATIONS WIRELESS \| VERIZON COMMUNICATIONS INC - WIRELESS / telecom / rule -> Verizon / telecom / map \| 960
- OPENGOV \| OPENGOV, INC. / unclassified / none -> OpenGov / professional / map \| 940
- VERIZON COMMUNICATIONS WIRELESS CELLCO PARTNERSHIP \| VERIZON COMMUNICATIONS INC - WIRELESS (CELLCO PARTNERSHIP) / telecom / rule -> Verizon / telecom / map \| 899
- FASTSPRING \| FastSpring / unclassified / none -> FastSpring / training / map \| 844
- UNITED HEALTHCARE \| United Healthcare / unclassified / none -> UnitedHealthcare / payroll / map \| 833
- UNITEDHEALTHCARE INSURANCE \| UnitedHealthcare Insurance Company / insurance / rule -> UnitedHealthcare / payroll / map \| 810
- EMS TECHNOLOGY SOLUTIONS \| EMS Technology Solutions LLC / it / rule -> EMS Technology Solutions / it / map \| 765
- PENN CARE \| PENN CARE, INC. / unclassified / none -> PennCare / ambulance / map \| 728
- PRODIGY EMS \| Prodigy EMS / unclassified / none -> Prodigy EMS / training / map \| 700
- TARGETSOLUTIONS LEARNING 22 032 \| TARGETSOLUTIONS LEARNING LLC #22-032 / training-software / rule -> Vector Solutions / training-software / map \| -672
- PK SAFETY SUPPLY \| PK SAFETY SUPPLY / general / rule -> PK Safety Supply / fire-equipment / map \| 590
- FIDELITY SECURITY LIFE INSURANCE \| FIDELITY SECURITY LIFE INSURANCE CO / insurance / rule -> Fidelity Security Life Insurance / payroll / map \| 580
- LIBERTY MUTUAL INSURANCE \| Liberty Mutual Insurance / insurance / rule -> Liberty Mutual / insurance / map \| 562
- PENSERV PLAN SERVICES \| PenServ Plan Services, Inc. / unclassified / none -> PenServ / payroll / map \| 500
- ENDEAVOR BUSINESS MEDIA \| ENDEAVOR BUSINESS MEDIA / unclassified / none -> Endeavor Business Media / training / map \| 464
- LINEGEAR \| Linegear / unclassified / none -> Line Gear / uniforms / map \| 409
- AT AND T LONG DISTANCE \| AT&T - LONG DISTANCE / unclassified / none -> AT&T / telecom / map \| 400
- JASON BROWN \| Jason Brown / unclassified / none -> Individuals (names withheld) / individuals / map \| 394
- WITMER \| Witmer / unclassified / none -> Witmer Public Safety Group / fire-equipment / map \| 394
- KIMBALL MIDWEST \| KIMBALL MIDWEST / unclassified / none -> Kimball Midwest / fleet / map \| 381
- HONEYWELL INTERNATIONAL \| HONEYWELL INTERNATIONAL INC. / unclassified / none -> Honeywell / fire-equipment / map \| 327
- CALIFORNIA PPE RECON \| California-PPE Recon, Inc. / unclassified / none -> California PPE Recon / ppe / map \| 300
- RIVERVIEW INTERNATIONAL TRUCKS \| Riverview International Trucks, LLC / fleet / rule -> Riverview International Trucks / fleet / map \| 293
- MATTHEW EVANS \| MATTHEW EVANS / unclassified / none -> Individuals (names withheld) / individuals / map \| 287
- UNKNOWN \| UNKNOWN / placeholder / rule -> Unknown / placeholder / map \| 277
- LEAVITT COMMUNICATIONS \| LEAVITT COMMUNICATIONS LLC / unclassified / none -> Leavitt Communications / radios / map \| 255
- BOISE MOBILE EQUIPMENT \| BOISE MOBILE EQUIPMENT / apparatus / rule -> Boise Mobile Equipment / apparatus / map \| 241
- NFPA INTERNATIONAL \| NFPA INTERNATIONAL / training / rule -> NFPA / training / map \| 229
- AMERICAN SAFETY AND \| AMERICAN SAFETY AND / unclassified / none -> American Safety & Health Institute / training / map \| 224
- GRAYBAR ELECTRIC \| Graybar Electric Company, Inc. / facilities / rule -> Graybar Electric / facilities / map \| 192
- XEROX \| XEROX CORPORATION / unclassified / none -> Xerox / it / map \| 180
- SPRINT SOLUTIONS \| SPRINT SOLUTIONS INC / unclassified / none -> Sprint Solutions / telecom / map \| 171
- AT AND T FIRSTNET \| AT&T FIRSTNET / unclassified / none -> AT&T / telecom / map \| 160
- MOUNTAIN VILLAGE RESORT \| Mountain Village resort / unclassified / none -> Mountain Village Resort / training / map \| 137
- SOCIAL SECURITY ADMINISTRATION \| SOCIAL SECURITY ADMINISTRATION / unclassified / none -> Social Security Administration / payroll / map \| 124
- CASEYS GENERAL STORE \| Casey's General Store / unclassified / none -> Casey's General Store / fleet / map \| 122
- HEALTH CARE LOGISTICS \| HEALTH CARE LOGISTICS / unclassified / none -> Health Care Logistics / ems-supplies / map \| 120
- MUD LAKE OIL \| Mud Lake Oil Company / fleet / rule -> Mud Lake Oil / fleet / map \| 119
- GRAINGER DEPT 853392421 \| GRAINGER/DEPT 853392421 / general / rule -> Grainger / general / map \| 116
- TYLER ANDERSON \| Tyler Anderson / unclassified / none -> Individuals (names withheld) / individuals / map \| 110
- FIRE HOUSE \| Fire House / unclassified / none -> The Fire House / fire-equipment / map \| 105
- MEAN GENES GAS \| Mean Genes Gas / unclassified / none -> Mean Genes Gas / fleet / map \| 98
- MYERS TIRE SUPPLY \| MYERS TIRE SUPPLY INC / fleet / rule -> Myers Tire Supply / fleet / map \| 87
- FIREHOUSE VIGILANCE \| FIREHOUSE VIGILANCE / unclassified / none -> Firehouse Vigilance / fire-equipment / map \| 51
- AT AND T 4IRX 135346 \| AT&T 4IRX 135346 / unclassified / none -> AT&T / telecom / map \| 49
- AHS RESCUE \| AHS RESCUE / unclassified / none -> AHS Rescue / fire-equipment / map \| 49
- GENUINE PARTS \| Genuine parts / unclassified / none -> NAPA Auto Parts / fleet / map \| 47
- MISCELLANEOUS \| Miscellaneous / placeholder / rule -> No vendor named / placeholder / map \| 30
- MCMASTER CARR SUPPLY \| MCMASTER-CARR SUPPLY COMPANY / general / rule -> McMaster-Carr / general / map \| 28
- FEDERAL EXPRESS \| Federal Express Corporation / unclassified / none -> Federal Express / general / map \| 0

</details>


### Review of names and categories (2026-10-07)

A second review of the canonical names and categories, made through `config/vendor_name_merges.csv` (70 rows
added, 3 rows given a category) and a re-run of the merge on the inputs of 56f6710 plus the 11 hand rows above.
It changed 81 rows of `config/vendor_map.csv`. In Utah only one payee moved: Spartan Armor Systems, from
apparatus to ppe. Utah's purchasing total is unchanged.

- **One company under two names, now one:** FedEx (Federal Express in CA, ID, OH and TX, $1.13M, had its
  own name beside Utah's FedEx); Forge Fire & Company (Ohio's $1.1M 'FORGE & FIRE COMPANY LLC', which was
  filed as fire-equipment under 'Forge and Fire'); P & R Communications Service; Holt of California; Western
  Extrication Specialists; 2 Hot Activewear & Uniforms; Act Fast Nationwide Fire Support (and no longer software);
  Dental Care Plus; Cigna Health and Life Insurance; Delta Dental; four more spellings of the Ohio Police & Fire
  Pension Fund ($6.0M); California Department of Health Care Services ($109.8M under a second spelling);
  CAL FIRE; Regents of the University of California (UC Davis, $23.3M); County of Riverside Fire Dept;
  Sacramento Metropolitan Fire District; Ohio Public Risk Insurance Agency (dba VFIS of Ohio);
  Centerpoint Energy (Vectren Energy Delivery of Ohio, renamed CenterPoint Energy Ohio); Burnham & Flower
  Insurance Group; Beem's BP Distributing; NAPA Auto Parts (Columbus); Colonial Life; Unum; Vision Service Plan;
  Travelers; KeyBank; Fire Apparatus Service & Repair.
- **Categories set by a keyword in a person's or company's name:** 16 Ohio payees paid only from
  'Other - Salaries' accounts (firefighters such as Austin D Hurst, Jasmine M Pierce, Lucas Parmelee, Ryan M
  Lucas, Howard W. Goodyear, and two firefighter associations, $0.9M) were in fire-equipment, apparatus,
  ems-equipment, fleet, it, facilities or general; they are payroll now. Farella Braun & Martel (a law firm,
  $1.59M) was ambulance; Spartan IT, Spartan Armor Systems and Spartan Tool Supply were apparatus; Lion Creative
  Studios was fire-equipment; Travelers Insurance was training.
- **Other categories:** Crash Course Village (training site) was government; Butler Tech (training services) was
  it; OhioHealth WorkHealth (occupational medicine, $164K) was payroll and is medical-exams; Fire Dept Extractor
  Supply ($2.2M, gear extractors) was government; the California EMS Authority was ems-supplies and is
  government; the Napa County RCD was fleet and is government; Sierra Pacific Industries (rent) is facilities.
- The Utah impact list above predates this review: the key FEDERAL EXPRESS now maps to FedEx.

Left for the owner (not changed):

- **SPECTRUM** stays Utah's newspaper The Spectrum, so $165K of Ohio cable and internet payments show under a
  St. George newspaper. A name-only map cannot give one key two vendors.
- **COMMUNITY FIRST NATIONAL BANK** is one key for an Ohio bank ($1.7M of Ohio debt payments) and a Utah payee
  ($73K); they share the Utah row and one vendor id.
- **Aircraft contractors** are apparatus in California (Heli-1, HeliQwest, Timberline Helicopters by spend) and
  wildland in Idaho (Aero Spray, Eagle Helicopters, Aeronautical Technologies). Both are purchasing categories.
- **California grant recipients** (fire safe councils, foundations, timber companies such as Mendocino Redwood
  and Collins Timber) are filed as government, which is not purchasing.
- **Many California fire districts and departments** still have two spellings (for example Idyllwild Fire
  Protection Dist and District, San Ramon VLLY Fire Prot Dist and San Ramon Valley Fire Protection District).
  All are government and outside purchasing.
- Look-alike pairs that may be one company but were not merged without more evidence: NWN and NWN Solutions,
  System Solutions and System Solutions DVBE, Cross Connections and Cross Connections Emergency, Black Knight
  Enterprises and Black Knight Fire Support, Phoenix / Phoenix Fire / Phoenix Fire Service (Ohio), Valley Ford
  and Valley Ford Truck Sales, Atlantic and Atlantic Emergency Solutions.
- JPMorgan Chase Bank is payroll by spend; Chase Card Services and 'Jp Morgan Chase Commericial Credit Card'
  stay apart as finance. Both categories are outside purchasing.

<!-- manual:end -->
