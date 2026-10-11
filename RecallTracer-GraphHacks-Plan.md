# Recall Tracer
### Graph Hacks: Context for AI Agents (WeMakeDevs × FalkorDB), Oct 15–18, 2026
**Tracks:** 01 (Agents That Act on Connected Data) and 02 (Agent Memory and Coordination)

---

## 1. The idea

**BazaarMart** is a fictional value hypermarket chain in India, similar in format to DMart. It sells staples, packaged foods, beverages and apparel. Several suppliers also sell to a second fictional chain, **CityMart**.

Products get recalled for many reasons: contamination, a faulty part, a labelling error, or a quality defect. A recall can start in two ways:

- **Path A, cause unknown:** complaints arrive from several stores (illness, injury, defects). The agents must **find the shared supplier lot** first.
- **Path B, cause known:** a supplier or regulator notice names a lot or batch (e.g. "zipper lot ZP-0412 is faulty"). The agents skip the search and go straight to the spread.

From there, Recall Tracer's AI agents use FalkorDB to:

1. **Find the cause (Path A only):** the single supplier lot (ingredient, beverage input, fabric, dye or component part) shared by the complaints, while ruling out common lots that are in almost everything.
2. **Find the spread:** every batch, product, brand, store, shelf and customer touched by that lot.
3. **Classify severity:** Class I (dangerous), Class II (moderate) or Class III (minor). Severity decides how fast stock is pulled and who gets told.
4. **Act in the store:** send a "Pull this batch" task to the associate currently logged into that section, with escalation and shift handoff.
5. **Inform people:** draft customer, supplier and in-store notices for a human to approve.

**Scope:**
- Text is English only.
- All data is synthetic, and every brand, store and supplier name is fictional.
- Hardware (handhelds) is mocked in the web UI.

---

## 2. Why the graph is essential (Rule 3)

| Agent question | Graph work |
|---|---|
| Complaints about *different products* in 3 stores: what single lot do they share? | Complaint → Batch → Lot, intersected across stores |
| Why not blame salt or sugar? | Those lots reached almost every store, so they don't single out the complaint stores (low specificity) |
| A supplier says zipper lot ZP-0412 is faulty: which of our products use it? | Lot → Batch → Product, often across several styles and brands |
| Where did the bad lot go? | Lot → Batch → Store → Location |
| Who should pull it right now? | Location → Section ← associate with an active login |
| Who bought it? | Batch ← Customer |
| How did a store outside the delivery plan get it? | Store-to-store transfer edges |

Without the graph, none of these can be answered. The LLM only reads complaints, plans steps, explains results and writes notices.

---

## 3. Two-graph setup

| Graph | Owner | Contains |
|---|---|---|
| `network` | Shared supplier side | Suppliers, lots, batches, products, recall notices from suppliers |
| `bazaarmart` | Chain A (main demo) | Stores, sections, locations, stock, customers, purchases, associates, complaints, investigations, tasks, notices |
| `citymart` | Chain B | Same structure as BazaarMart, with its own data |

**Why two graphs:**
- **Data separation per chain (Track 02).** Each chain's customers, staff and investigation memory stay private. CityMart can never see BazaarMart's customers.
- **Shared knowledge.** When the cause is confirmed, a `RecallNotice` is written to the shared network graph. CityMart's agents pick it up and act on their own stores.
- **The link between graphs is the batch ID.** Chain graphs hold a lightweight `BatchRef` with the same ID as the network `Batch`.

**What it costs:** root-cause search runs as three short queries (chain → network → chain) instead of one. The tool layer hides this from the agents.

---

## 4. Product categories and recall reasons

| Category | What a "Lot" is | Contamination / quality example | Faulty part / labelling example | Common decoy lots |
|---|---|---|---|---|
| Staples | Bulk commodity lot repacked into private-label packs | Contaminated besan lot | Pack label lot with an undeclared allergen | Salt |
| Packaged foods | Ingredient lot used by a co-packer | **Groundnut lot used in masala peanuts and bhujia** (main demo) | Wrong expiry date printed on a batch | Salt, palm oil |
| Beverages | Concentrate lot, bottle lot or cap lot | Contaminated mango concentrate in two juices | **Cap lot that leaks** across juices from 2 brands | Sugar, PET bottles |
| Apparel | Fabric, dye or component lot (zippers, buttons, drawstrings) | Dye lot causing skin rash in 3 kidswear styles | **Zipper lot whose pull detaches (choking risk)** in kidswear from 2 vendors | Thread, poly bags |

The same model, queries and agents handle every category and reason. A faulty part is just another `Lot` with `USED_IN` edges.

### Recall reasons and severity

| Reason | Usually starts from |
|---|---|
| `contamination` | Path A (complaints) or Path B (lab result) |
| `faulty_part` | Path B (supplier notice) or Path A (injury or defect complaints) |
| `labelling` | Path B |
| `quality` | Path A |

| Severity | Meaning | What the agents do |
|---|---|---|
| **Class I** | Can cause serious harm (pathogen, choking hazard, undeclared allergen) | Urgent pull task, due in 2 hours; manager copied; customer notices drafted; recall shared with other chains |
| **Class II** | Could cause temporary or minor harm (leaking cap, skin irritation) | Pull task due the same day; customer notices drafted |
| **Class III** | Unlikely to cause harm (wrong label detail, quality issue) | Pull task due in 48 hours; in-store notice only |

The Investigator suggests a class with a one-line reason, and a human confirms it in the UI.

**Expiry is not in scope.** Removing expired stock is routine housekeeping that a date filter handles, not a recall.

**Simplification:** every bill records the batch number. For apparel, the "batch" is the production lot printed on the care label.

---

## 5. Graph model

### 5.1 `network` graph (shared)

| Node | Properties |
|---|---|
| `Supplier` | id, name, type (`aggregator`, `co_packer`, `bottler`, `garment_vendor`, `packaging`) |
| `Lot` | id, material (groundnut, salt, palm_oil, mango_concentrate, sugar, pet_bottle, bottle_cap, dye_red_14, fabric_cotton, zipper, label_roll…), kind (`ingredient`, `component`, `packaging`), category, received_on |
| `Batch` | id, batch_no, mfd, expiry (null for apparel) |
| `Product` | id, name, brand, category (`staples`, `packaged_food`, `beverage`, `apparel`) |
| `RecallNotice` | id, reason (`contamination`, `faulty_part`, `labelling`, `quality`), severity (`I`, `II`, `III`), text, source (`supplier`, `regulator`, `chain`), issued_on |

```
(Supplier)-[:SUPPLIED]->(Lot)
(Supplier)-[:MADE]->(Batch)
(Lot)-[:USED_IN]->(Batch)
(Batch)-[:OF_PRODUCT]->(Product)
(RecallNotice)-[:FOR_LOT]->(Lot)
(RecallNotice)-[:FOR_BATCH]->(Batch)       // when only specific batches are named
(RecallNotice)-[:ISSUED_BY]->(Supplier)    // supplier-issued notices
```

### 5.2 Chain graphs (`bazaarmart`, `citymart`)

| Node | Properties |
|---|---|
| `Store` | code (TH-07), city |
| `Section` | id, name (Staples, Packaged Foods, Beverages, Apparel, Godown, Returns Desk) |
| `Location` | id, code ("Aisle 9-C", "Endcap E-3", "Chiller C-2", "Rack A-5", "Godown G-12"), type |
| `BatchRef` | id (same as network Batch), batch_no, product_name, category |
| `Customer` | id, phone_masked |
| `Associate` | id, name, role (`associate`, `manager`) |
| `Complaint` | id, text, issue_type (`illness`, `injury`, `defect`, `quality`), details, onset_on, reported_on |
| `Investigation` | id, category, trigger (`complaints`, `notice`), notice_id (Path B; the notice lives in the network graph), lot_id (once known), reason, severity, status (`open`, `confirmed`, `closed`), opened_at |
| `Hypothesis` | id, lot_id, material, score, status (`open`, `ruled_out`, `confirmed`), reason |
| `Task` | id, type (`PULL_BATCH`), priority (`urgent`, `today`, `routine`), due_by, status (`sent`, `accepted`, `done`), created_at |
| `Notice` | id, audience (`customer`, `supplier`, `in_store`), body, status (`draft`, `approved`) |

```
(Store)-[:HAS_SECTION]->(Section)-[:HAS_LOCATION]->(Location)
(Section)-[:NEXT_TO]->(Section)
(BatchRef)-[:DELIVERED_TO {on, qty}]->(Store)
(BatchRef)-[:TRANSFERRED_TO {on, qty, from_store}]->(Store)
(BatchRef)-[:STOCKED_AT {qty, status}]->(Location)        // status: available / pulled
(Customer)-[:BOUGHT {on, qty, store}]->(BatchRef)
(Associate)-[:WORKS_AT]->(Store)
(Associate)-[:LOGGED_INTO {since, active}]->(Section)
(Complaint)-[:FILED_BY]->(Customer)
(Complaint)-[:ABOUT]->(BatchRef)
(Complaint)-[:AT]->(Store)
(Investigation)-[:TRIGGERED_BY]->(Complaint)
(Investigation)-[:HAS]->(Hypothesis)
(Hypothesis)-[:EXPLAINS]->(Complaint)
(Investigation)-[:CREATED]->(Task)
(Investigation)-[:CREATED]->(Notice)
(Task)-[:FOR_LOCATION]->(Location)
(Task)-[:FOR_BATCH]->(BatchRef)
(Task)-[:ASSIGNED_TO]->(Associate)
(Task)-[:HANDED_TO {reason, at}]->(Associate)
```

---

## 6. Agents (four)

**The agents never call each other directly.** Each agent watches for graph nodes in a certain state and writes new nodes for the next agent:

```
Path A: Sentinel ──complaint cluster──▶ Investigation (open, trigger=complaints)
Path B: Sentinel ──supplier/regulator notice──▶ Investigation (open, trigger=notice, lot already known)

Investigator ──Path A: ranks lots──▶ Hypothesis (confirmed)
             ──both paths: forward trace + severity──▶ Investigation (confirmed) + RecallNotice (network)
Store-Ops ──reads confirmed Investigation / RecallNotice──▶ Task (priority from severity)
Comms ──reads confirmed Investigation──▶ Notice (draft; audiences depend on severity)
```

This shared-graph coordination is the core of the Track 02 entry. Every step is a node or edge with a timestamp, so any investigation can be replayed. Each chain runs its own set of agents against its own graph.

### 6.1 Sentinel Agent: watches complaints
| Tool | Does |
|---|---|
| `add_complaint(text, customer_id, batch_id, store_code)` | The LLM reads the complaint and extracts the issue type (illness, injury, defect, quality), details and onset date. Saves a `Complaint` |
| `check_for_cluster(category, issue_type)` | If complaints with the same category and issue type come from 3+ stores within 72 hours, opens a Path A `Investigation`. If one is already open, attaches the new complaints to it |
| `ingest_notice(text)` | Reads a supplier or regulator notice in English. The LLM extracts the lot or batch numbers, reason and suggested severity, saves a `RecallNotice` to the network graph and opens a Path B `Investigation` |
| `watch_recall_notices()` | Picks up new `RecallNotice` nodes in the network graph, so each chain responds to notices from suppliers, regulators or the other chain |

### 6.2 Investigator Agent: finds the cause (UC-2)
| Tool | Does |
|---|---|
| `rank_lots(investigation_id)` | Path A only: runs Q1a → Q1b → Q1c and returns lots with coverage, specificity and score |
| `resolve_notice(notice_id)` | Path B only: Q7 turns the named lot or batches into the full batch list |
| `suggest_severity(investigation_id)` | The LLM proposes Class I/II/III with a one-line reason, based on the reason, issue type and product (e.g. "children's product + choking hazard → Class I"). A human confirms |
| `save_hypotheses(results)` | Writes a `Hypothesis` per candidate with status and a plain-English reason (e.g. "salt reached 11 of 12 stores, not specific") |
| `explain(lot_id)` | Returns one evidence path per complaint store for graph highlighting |
| `forward_trace(lot_id)` | Q2: all affected batches, products, stores and customer counts |
| `publish_recall(lot_id)` | Writes a `RecallNotice` to the network graph |

### 6.3 Store-Ops Agent: acts in stores (UC-1)
| Tool | Does |
|---|---|
| `pull_list(batch_ids)` | Q3: per store and section, the locations, quantities and logged-in associates |
| `dispatch(store, section, items, associate, severity)` | Creates a `PULL_BATCH` Task with priority and deadline from the severity (Class I: urgent, 2 h, manager copied; Class II: today; Class III: 48 h) and shows it on the handheld mock |
| `escalate(task_id)` | Q4: if nobody is logged in or there's no reply in time, the associate in the next section, then the manager |
| `handoff_on_logout(associate_id)` | Moves open tasks to the next associate who logs into that section, with a `HANDED_TO` edge |
| `confirm_pulled(task_id, location_id, qty)` | Marks the stock `pulled`, closes the task and updates store progress |

### 6.4 Comms Agent: drafts notices
| Tool | Does |
|---|---|
| `affected_customers(batch_ids)` | Customers who bought an affected batch, from this chain's graph only |
| `draft(audience)` | Drafts a customer SMS, a supplier notice and an in-store notice board message. The audience depends on severity: Class I and II include customers, Class III is in-store only. The wording depends on the reason (e.g. "stop using" for a choking hazard, "return for a refund" for a quality issue) |
| `approve(notice_id)` | A human approves in the UI. Nothing is actually sent |

---

## 7. Queries

> These are drafts written from memory, not run. Check them against the FalkorDB docs before Day 1. Pass lists as query parameters.

### Q1: root cause (UC-2), three steps

**Q1a (chain graph): which batches are the complaints about, and in how many stores?**
```cypher
MATCH (inv:Investigation {id: $iid})-[:TRIGGERED_BY]->(c:Complaint)-[:AT]->(s:Store)
MATCH (c)-[:ABOUT]->(b:BatchRef)
RETURN s.code AS store, collect(DISTINCT b.id) AS batch_ids;
```

**Q1b (network graph): which lots made those batches, and which batches did each lot make?**
```cypher
UNWIND $store_batches AS row                       // [{store, batch_ids}, …] from Q1a
MATCH (l:Lot)-[:USED_IN]->(b:Batch)
WHERE b.id IN row.batch_ids
WITH l, count(DISTINCT row.store) AS complaint_stores
MATCH (l)-[:USED_IN]->(all_b:Batch)
RETURN l.id AS lot_id, l.material AS material, complaint_stores,
       collect(DISTINCT all_b.id) AS lot_batch_ids;
```

**Q1c (chain graph): how many stores did each lot reach in total?**
```cypher
UNWIND $lots AS lot                                // [{lot_id, lot_batch_ids}, …] from Q1b
MATCH (b:BatchRef)-[:DELIVERED_TO|TRANSFERRED_TO]->(s:Store)
WHERE b.id IN lot.lot_batch_ids
RETURN lot.lot_id AS lot_id, count(DISTINCT s) AS all_stores;
```

**Score (Python):**
```
coverage    = complaint_stores / number_of_complaint_stores
specificity = complaint_stores / all_stores
score       = coverage × specificity
```

**Expected demo result (food outbreak):**

| Lot | Material | Coverage | Specificity | Score | Verdict |
|---|---|---|---|---|---|
| GN-2214 | groundnut | 1.0 | 0.60 | **0.60** | confirmed |
| PO-0611 | palm oil | 1.0 | 0.25 | 0.25 | ruled out: used in most snacks |
| SL-0042 | salt | 1.0 | 0.25 | 0.25 | ruled out: in almost everything |

**Expected demo result (apparel outbreak):**

| Lot | Material | Coverage | Specificity | Score | Verdict |
|---|---|---|---|---|---|
| DY-0314 | red dye 14 | 1.0 | 0.75 | **0.75** | confirmed |
| TH-0099 | polyester thread | 1.0 | 0.30 | 0.30 | ruled out |

### Q2: forward trace

**Network graph: which batches and products?**
```cypher
MATCH (l:Lot {id: $lot})-[:USED_IN]->(b:Batch)-[:OF_PRODUCT]->(p:Product)
RETURN collect(DISTINCT b.id) AS batch_ids, collect(DISTINCT p.name) AS products;
```

**Chain graph: which stores, and how many customers?**
```cypher
MATCH (b:BatchRef) WHERE b.id IN $batch_ids
OPTIONAL MATCH (b)-[:DELIVERED_TO|TRANSFERRED_TO]->(s:Store)
OPTIONAL MATCH (cu:Customer)-[:BOUGHT]->(b)
RETURN count(DISTINCT s) AS stores, count(DISTINCT cu) AS customers;
```

### Q3: pull list and who is on duty (UC-1)
```cypher
MATCH (b:BatchRef)-[st:STOCKED_AT]->(loc:Location)
WHERE b.id IN $batch_ids AND st.status = 'available' AND st.qty > 0
MATCH (loc)<-[:HAS_LOCATION]-(sec:Section)<-[:HAS_SECTION]-(s:Store)
OPTIONAL MATCH (a:Associate)-[li:LOGGED_INTO]->(sec)
WHERE li.active = true
RETURN s.code AS store, sec.id AS section_id, sec.name AS section,
       collect(DISTINCT {location: loc.code, batch: b.batch_no,
                         product: b.product_name, qty: st.qty}) AS pull_list,
       collect(DISTINCT {id: a.id, name: a.name}) AS on_duty
ORDER BY store, section;
```

### Q4: escalation
```cypher
// first try: someone active in a neighbouring section
MATCH (sec:Section {id: $section_id})-[:NEXT_TO]-(other:Section)<-[li:LOGGED_INTO]-(a:Associate)
WHERE li.active = true
RETURN a.id AS assignee, other.name AS via
LIMIT 1;
```
```cypher
// fallback: the store manager
MATCH (sec:Section {id: $section_id})<-[:HAS_SECTION]-(s:Store)<-[:WORKS_AT]-(m:Associate {role: 'manager'})
RETURN m.id AS assignee, 'manager' AS via
LIMIT 1;
```

### Q5: hidden route (day-2 scene)
```cypher
MATCH (b:BatchRef)-[t:TRANSFERRED_TO]->(dest:Store {code: $store})
WHERE b.id IN $batch_ids
MATCH (b)-[:DELIVERED_TO]->(origin:Store {code: t.from_store})
RETURN b.batch_no, origin.code AS from_store, dest.code AS to_store, t.on, t.qty;
```

### Q7: resolve a supplier or regulator notice (Path B, network graph)
```cypher
MATCH (n:RecallNotice {id: $notice_id})
OPTIONAL MATCH (n)-[:FOR_LOT]->(:Lot)-[:USED_IN]->(lb:Batch)
OPTIONAL MATCH (n)-[:FOR_BATCH]->(nb:Batch)
WITH n, collect(DISTINCT lb) + collect(DISTINCT nb) AS batches
UNWIND batches AS b
MATCH (b)-[:OF_PRODUCT]->(p:Product)
RETURN n.reason AS reason, n.severity AS severity,
       collect(DISTINCT b.id) AS batch_ids,
       collect(DISTINCT p.name + ' (' + p.brand + ')') AS products;
```
For a faulty zipper lot, this returns kidswear styles from **both garment vendors** that used it. Without the graph, nobody would know which styles to pull.

### Q6: investigation replay (memory and audit)
```cypher
MATCH (inv:Investigation {id: $iid})
OPTIONAL MATCH (inv)-[:HAS]->(h:Hypothesis)
OPTIONAL MATCH (inv)-[:CREATED]->(t:Task)-[r:ASSIGNED_TO|HANDED_TO]->(a:Associate)
OPTIONAL MATCH (inv)-[:CREATED]->(n:Notice)
RETURN inv,
       collect(DISTINCT {lot: h.material, status: h.status, reason: h.reason}) AS hypotheses,
       collect(DISTINCT {task: t.id, how: type(r), who: a.name, status: t.status}) AS tasks,
       collect(DISTINCT {notice: n.audience, status: n.status}) AS notices;
```

---

## 8. Demo script (about 3 minutes)

**Scene 1: "Different products, three cities, one cause" (UC-2, Track 01), about 50 s**
- Complaints arrive at BazaarMart: Thane (masala peanuts), Pune (bhujia) and Hyderabad (masala peanuts).
- The Sentinel opens an investigation. The Investigator ranks the lots.
- **Salt and palm oil are ruled out** with plain-English reasons. **Groundnut lot GN-2214** is confirmed, and its paths to all three stores light up.

**Scene 2: "Pull it" (UC-1, Track 01), about 45 s**
- Forward trace: 2 products, 5 batches, 9 stores, 140 customers.
- The handheld mock shows Rahul's task (Packaged Foods, TH-07): **"Pull BATCH MP-2409-17 only. Aisle 9-C: 22 packs. Endcap E-3: 40 packs. Godown G-12: 3 cartons. Replace from a safe batch."**
- Rahul taps Done on each location, and the store progress bar reaches 100%.

**Scene 3: "Nobody there, then a shift change" (Track 02), about 30 s**
- Pune: nobody is logged into Packaged Foods, so the task escalates to the Staples associate next door.
- Hyderabad: Sana logs out mid-task, and the task is handed to Kiran with full context. The `HANDED_TO` edge appears in the graph.

**Scene 4: "Next day" (Track 02 memory), about 25 s**
- A new complaint comes from Navi Mumbai, a store that never received GN-2214 directly.
- The Sentinel attaches it to the open investigation. The Investigator **doesn't re-check salt or palm oil** because they're already ruled out in memory, and finds a transfer from Thane to Navi Mumbai.

**Scene 5: "Another chain, its own data" (Track 02), about 15 s**
- The confirmed cause was published as a `RecallNotice` in the network graph.
- Switching to CityMart: its agents pick up the notice and dispatch pull tasks in CityMart stores. Its customer list shows only CityMart customers.

**Scene 6: "A faulty part, not an illness" (Path B), about 20 s**
- A zipper supplier sends an English notice: **"Zipper lot ZP-0412: the pull can detach. Choking risk for small children."**
- The Sentinel opens a Path B investigation; there's no root-cause search because the lot is known.
- The Investigator traces it to **4 kidswear styles from 2 garment vendors** and suggests **Class I** ("children's product + choking hazard"). A human confirms.
- Store-Ops sends **urgent** pull tasks (due in 2 hours, manager copied) to the Apparel section associates, covering racks, the trial-room return rail and the godown. Comms drafts a "stop using" customer notice.

**Closing:** the Comms Agent's drafts are approved on screen, followed by the accuracy table (§10).

---

## 9. Synthetic data

**Network graph**
- 20 suppliers: aggregators, co-packers, bottlers, garment vendors, packaging
- 90 lots: ingredients, components (bottle caps, zippers, buttons, drawstrings) and packaging (label rolls), including common decoys: salt, palm oil, sugar, PET bottles, thread, poly bags
- 2 zipper suppliers whose lots go to 2 garment vendors, so one faulty zipper lot spans several styles and brands
- 60 products: 15 staples, 20 packaged foods, 10 beverages, 15 apparel. Each product uses 2–4 lots.
- About 300 batches

**BazaarMart graph**
- 12 stores (Mumbai, Thane, Navi Mumbai, Pune, Hyderabad)
- 6 sections per store, about 8 locations per section (shelves, endcaps, chillers, racks, godown)
- About 70 associates with shift logins
- 1,500 customers and about 12,000 purchases
- 3 store-to-store transfers

**CityMart graph**
- 5 stores with the same structure, buying the bhujia and two beverages from the shared suppliers

**Scenario generator**
- **Path A:** picks a bad lot and an issue type, creates complaints from customers who bought its batches (onset 1–3 days after purchase), and adds random noise complaints.
- **Path B:** writes an English supplier or regulator notice naming a lot or batch, with a reason and severity.
- Used for the demo scenes and the accuracy check.

---

## 10. Accuracy check
- Generate **20 complaint-driven (Path A) scenarios** covering different reasons and categories:
  - 6 illness (packaged food, staples)
  - 4 quality complaints (staples, beverages)
  - 4 defect complaints (leaking beverage caps)
  - 3 skin-rash cases (apparel dye)
  - 3 injury cases (apparel zipper)
- Path B (notices) needs no accuracy test because the lot is given. Instead, a unit test checks that Q7 returns exactly the right batches.
- Compare **coverage only** (naive shared lot) with **coverage × specificity**.
- Report how often the correct lot is ranked first, and how many complaints were needed before it was.
- Show the result as one table in the README and for about 10 seconds in the video.

---

## 11. Architecture

```
┌──────────────────────────── Web UI (one page) ─────────────────────────────┐
│  Graph view (Cytoscape.js)  │  Handheld mock  │  Agent feed  │  Approvals  │
│  chain switcher: BazaarMart / CityMart                                      │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │ REST + WebSocket
┌──────────────────────────────────▼─────────────────────────────────────────┐
│  FastAPI + agent runner (Python, Claude tool use)                          │
│  Sentinel │ Investigator │ Store-Ops │ Comms      (one set per chain)      │
│  Tool layer: typed Cypher queries; each tool returns {result, path_ids}    │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼─────────────────────────────────────────┐
│  FalkorDB:  network  │  bazaarmart  │  citymart                            │
└──────────────────────────────────▲─────────────────────────────────────────┘
                                   │
                 Scenario player: complaints, logins/logouts,
                 "Done" taps, transfers (play / pause / step)
```

**Design rules**
- **Tools are fixed Cypher queries.** The LLM picks tools and explains results but never writes Cypher.
- **Every tool returns the graph path IDs** it used, so the UI can highlight the evidence.
- **Notices need human approval**, and nothing is actually sent.

---

## 12. Tech stack
| Layer | Choice |
|---|---|
| Graph | FalkorDB (Docker locally; FalkorDB Cloud for the live demo) |
| Agents | Python, Claude tool calling, simple custom loop |
| API | FastAPI + WebSocket |
| UI | React (or plain HTML + JS), Cytoscape.js |
| Deploy | Render or Fly (API + agents), Vercel (UI), FalkorDB Cloud; `docker compose up` for local |

---

## 13. Schedule
| Date | Work |
|---|---|
| Oct 11–14 | **Planning only (Rule 8):** freeze the schema and tool list, write the demo story with exact names and numbers, sketch the UI, read the FalkorDB docs (multiple graphs, `UNWIND` with parameters), create accounts |
| Oct 15 | Repo + Docker Compose, seed script for all three graphs, outbreak generator, Q1–Q5 tested in a notebook |
| Oct 16 | The four agents working end-to-end from the command line for BazaarMart (scenes 1–4) |
| Oct 17 | Web UI (graph, handheld, feed, approvals), CityMart scene, apparel scene, accuracy run |
| Oct 18 | Deploy, README, video, blog post; **submit by about 6 PM IST** |

**If short on time, cut in this order:** the CityMart scene → the Comms Agent (show a static summary instead) → the injury and rash scenarios in the accuracy check.
**Never cut:** root cause with decoys ruled out (Path A), the faulty-part notice (Path B), severity-based task priority, the pull task to the logged-in associate, escalation and shift handoff, day-2 memory.

---

## 14. Submission checklist (Rule 10)
- [ ] Public GitHub repo with fictional names only
- [ ] README: problem, architecture, both graph models, setup, all Cypher queries, accuracy table
- [ ] Demo video (about 3 minutes)
- [ ] Live URL plus `docker compose up` fallback
- [ ] Tracks named: 01 and 02
- [ ] AI-assistance disclosure
- [ ] Every team member can explain the graph model, the scoring and the agent flow
- [ ] Optional blog post: "Why the salt is never guilty: tracing recalls with a graph"

---

## 15. Pitch for judges
1. **The graph finds the cause.** It links complaints about different products in different cities to one supplier lot and explains why common lots aren't to blame.
2. **The agents act.** Pull tasks go to the person in that section right now, with escalation and shift handoff.
3. **The graph is the agents' memory and coordination layer.** Four agents work only through the graph, the investigation continues across days, and each chain's data stays separate while recall knowledge is shared.
4. **One engine covers every category and reason.** Contamination, faulty parts, labelling errors and quality issues in food, staples, beverages and apparel all use the same model and queries. It works whether the cause is unknown (complaints) or known (notices), and severity decides how fast the agents act.
5. **Accuracy is measured.** 20 outbreaks, compared with a naive baseline.

---

## 16. Team split (3–4 people)
| Person | Owns |
|---|---|
| A | Graph models, seed and outbreak scripts, queries, accuracy check |
| B | Agent runner, the four agents, graph-based coordination and memory |
| C | Web UI: graph view, handheld mock, agent feed, approvals |
| D (or shared) | Deployment, README, video, blog |
