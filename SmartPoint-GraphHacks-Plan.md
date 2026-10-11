# SmartPoint AI: a graph-native store agent
### Graph Hacks: Context for AI Agents (WeMakeDevs × FalkorDB), Oct 15–18, 2026

---

## 1. One-liner

**SmartPoint AI is a team of retail agents that reason over a live FalkorDB "store graph".** The graph connects products, outfits, stock locations, shoppers and associates. The agents turn a shopper's request into an in-stock outfit, send the best associate to fetch it, and explain each decision as a path through the graph.

> Without the graph, the agent can only chat. With the graph, it knows what's in stock, where it is, who should fetch it, and why.

## 2. Track positioning

| Track | Fit | What we show |
|---|---|---|
| **01: Agents That Act on Connected Data** (primary) | Strong | Multi-hop outfit and stock reasoning, shortest-path associate routing, graph algorithms used as agent tools, explainable paths |
| **02: Agent Memory and Coordination** (secondary) | Strong | Shopper memory that persists across visits, kiosk-to-associate agent handoff through shared graph state, one graph per store (separate memory per tenant) |
| 03: Company Brain | No | — |

Enter both 01 and 02 and name both at submission (Rule 5).

## 3. Why the graph does real work (Rule 3)

Every agent decision is a graph query. If FalkorDB is removed, the agents can't answer anything.

| Agent question | Graph operation |
|---|---|
| "What goes with this dress for an outdoor wedding?" | Traversal: `Occasion ← SUITS ← Product → PAIRS_WITH → Product` |
| "Is it in her size, and where?" | `Product → HAS_VARIANT → SKU → STOCKED_AT → Location`, filtered on qty > 0 |
| "Floor or backroom? Which is closer?" | Shortest path over the `Location -[CONNECTS {meters}]-> Location` layout graph |
| "Which associate should go?" | Shortest path from each on-shift associate to the stock, weighted by current task load and skill |
| "Out of stock: what's the best substitute?" | Similar products through shared attributes or vector similarity, then the stock check again |
| "What does this shopper like?" | `Customer → PURCHASED / PREFERS / REJECTED → …` (memory) |
| "Why did you pick this?" | The agent returns the actual path it used, which the UI highlights |

## 4. Architecture

```
┌──────────────┐   ┌──────────────────┐   ┌────────────────────┐
│ Kiosk UI     │   │ Associate UI     │   │ Manager / Graph     │
│ (mock KC50,  │   │ (mock handheld,  │   │ view (live graph,   │
│  web page)   │   │  phone-size web) │   │  path highlighting) │
└──────┬───────┘   └────────┬─────────┘   └─────────┬──────────┘
       │ WebSocket / REST   │                       │
┌──────▼────────────────────▼───────────────────────▼──────────┐
│                  Agent Orchestrator (Python)                  │
│  ┌────────────────┐ ┌──────────────────┐ ┌─────────────────┐  │
│  │ Concierge Agent│ │ Dispatcher Agent │ │ Co-Pilot Agent  │  │
│  │ (shopper-facing│ │ (routes tasks,   │ │ (associate-side,│  │
│  │  outfits, recs)│ │  load balancing) │ │  locate/handoff)│  │
│  └───────┬────────┘ └────────┬─────────┘ └────────┬────────┘  │
│          └──── Graph Tool Layer (typed Cypher tools) ┘        │
└──────────────────────────────┬───────────────────────────────┘
                               │
                ┌──────────────▼──────────────┐
                │ FalkorDB                    │
                │  graph: store_104           │  ← one graph per store
                │  graph: store_207           │    (tenant isolation)
                │  + vector index on Product  │
                └──────────────▲──────────────┘
                               │
                ┌──────────────┴──────────────┐
                │ Event Simulator             │
                │ RFID lift, stock moves,     │
                │ associate movement, POS     │
                └─────────────────────────────┘
```

**Key design choices**
- **The agents share no hidden state.** All coordination goes through `Task`, `Handoff` and `Session` nodes in the graph, so the graph is both the context and the coordination bus (Track 02).
- **Tools are typed Cypher queries**, not free-form LLM-written Cypher. This is safer, faster and easier to explain to judges. Add one optional `ask_graph` tool for ad-hoc text-to-Cypher questions as a bonus.
- **Every tool returns `{result, path}`.** The path (node and edge IDs) streams to the graph view and gets highlighted, which gives explainability.

## 5. Graph data model

### Nodes
| Label | Key properties |
|---|---|
| `Store` | id, name, city |
| `Zone` | id, name (Womenswear, Shoes, Backroom…), type (floor/backroom) |
| `Location` | id, name ("Aisle 2 Bay 3", "Backroom Bay 4 Shelf B-12"), x, y |
| `Kiosk` | id, name |
| `RFIDReader` | id, antenna |
| `Product` | id, name, category, price, color, material, style, season, rating, `embedding` (vector) |
| `SKU` | id, size |
| `Occasion` | name (wedding, office, beach, winter-party…) |
| `Attribute` | name (breathable, formal, waterproof…) |
| `Customer` | id, name, tier (Gold/Silver), saved_size |
| `Associate` | id, name, status (available/busy/break), skills |
| `Task` | id, type (fetch/deliver/assist), status, priority, created_at |
| `Session` | id, channel (kiosk/app), started_at |
| `Interaction` | id, utterance, intent, ts |

### Relationships
```
(Store)-[:HAS_ZONE]->(Zone)-[:HAS_LOCATION]->(Location)
(Location)-[:CONNECTS {meters}]->(Location)          // walkable store layout
(Kiosk)-[:LOCATED_AT]->(Location)
(RFIDReader)-[:COVERS]->(Location)

(Product)-[:HAS_VARIANT]->(SKU)
(SKU)-[:STOCKED_AT {qty}]->(Location)
(Product)-[:PAIRS_WITH {score, source}]->(Product)    // outfit graph
(Product)-[:SUITS]->(Occasion)
(Product)-[:HAS_ATTR]->(Attribute)
(Product)-[:SIMILAR_TO {score}]->(Product)            // substitutes

(Customer)-[:PURCHASED {ts}]->(SKU)
(Customer)-[:PREFERS {weight}]->(Attribute|Product)
(Customer)-[:REJECTED {ts, reason}]->(Product)        // memory of "no"
(Customer)-[:HAD_SESSION]->(Session)-[:INCLUDED]->(Interaction)
(Interaction)-[:ABOUT]->(Product)

(Associate)-[:AT]->(Location)                         // live position
(Associate)-[:SKILLED_IN]->(Zone)
(Task)-[:FOR_CUSTOMER]->(Customer)
(Task)-[:FOR_SKU]->(SKU)
(Task)-[:PICK_FROM]->(Location)
(Task)-[:DELIVER_TO]->(Location|Kiosk)
(Task)-[:ASSIGNED_TO]->(Associate)
(Task)-[:HANDED_OFF {reason, ts}]->(Associate)
(Session)-[:CREATED]->(Task)
```

## 6. Agents and their tools

### 6.1 Concierge Agent (kiosk, shopper-facing)
Goal: understand the request and propose a complete outfit that is **actually available in the shopper's size**.

| Tool | What it does |
|---|---|
| `identify_customer(loyalty_id)` | Loads profile, saved size, preferences and rejections |
| `search_products(text, occasion?, filters?)` | Vector search on Product, then a graph filter by Occasion and Attribute |
| `build_outfit(anchor_product_id, customer_id)` | Multi-hop PAIRS_WITH expansion, excluding REJECTED items and boosting PREFERS |
| `check_availability(product_id, size)` | SKU → STOCKED_AT → Location with floor/backroom split |
| `find_substitute(product_id, size)` | SIMILAR_TO plus shared attributes, then the availability check |
| `remember(customer_id, fact)` | Writes PREFERS / REJECTED / Interaction (memory) |
| `request_associate(task_spec)` | Creates a `Task` node; the Dispatcher picks it up |

### 6.2 Dispatcher Agent (back-office)
Goal: choose the best associate for each new Task and rebalance when something changes.

| Tool | What it does |
|---|---|
| `candidate_associates(task_id)` | Available associates with a skill in the pick zone |
| `route_cost(associate_id, pick_loc, deliver_loc)` | Shortest path over CONNECTS (meters), associate → pick → deliver |
| `associate_load(associate_id)` | Count of open tasks |
| `assign(task_id, associate_id, rationale)` | Writes ASSIGNED_TO with the rationale |
| `reassign(task_id, reason)` | Writes HANDED_OFF and reruns the ranking |

Ranking score = `route_meters + 40 × open_tasks − 20 × zone_skill_match` (tunable). The breakdown is shown in the UI.

### 6.3 Co-Pilot Agent (associate handheld)
Goal: give the associate full context and handle exceptions.

| Tool | What it does |
|---|---|
| `task_brief(task_id)` | Customer tier and history, SKU, exact shelf, route, outfit context |
| `report_not_found(task_id, location_id)` | Sets qty = 0 at that location, finds the next-closest stock, and re-routes |
| `handoff(task_id, reason)` | "On break" or "too far": the Dispatcher reassigns through the graph |
| `complete(task_id)` | Closes the task and writes PURCHASED if the POS event arrives |

### 6.4 Coordination pattern (Track 02 story)
```
Kiosk session ──CREATED──▶ Task ──ASSIGNED_TO──▶ Ana
                              └──HANDED_OFF{reason:"break"}──▶ Raj
```
Each agent reads and writes only the graph. You can replay any customer journey by traversing from the `Session` node.

## 7. Example Cypher (FalkorDB / openCypher)

> Check the procedure names and signatures against the current FalkorDB docs before the event (`algo.SPpaths`, `db.idx.vector.queryNodes`, `vecf32`).

**Vector index and semantic search**
```cypher
CREATE VECTOR INDEX FOR (p:Product) ON (p.embedding)
OPTIONS {dimension: 1536, similarityFunction: 'cosine'};

CALL db.idx.vector.queryNodes('Product', 'embedding', 20, vecf32($q))
YIELD node AS p, score
MATCH (p)-[:SUITS]->(:Occasion {name: $occasion})
RETURN p.id, p.name, score ORDER BY score DESC LIMIT 5;
```

**Outfit builder that respects memory and stock**
```cypher
MATCH (c:Customer {id: $cid})
MATCH (a:Product {id: $anchor})-[pw:PAIRS_WITH]->(m:Product)
WHERE NOT (c)-[:REJECTED]->(m)
MATCH (m)-[:HAS_VARIANT]->(s:SKU {size: c.saved_size})-[st:STOCKED_AT]->(l:Location)
WHERE st.qty > 0
OPTIONAL MATCH (c)-[pr:PREFERS]->(:Attribute)<-[:HAS_ATTR]-(m)
RETURN m.name, s.id, l.name, pw.score + coalesce(sum(pr.weight), 0) AS rank
ORDER BY rank DESC LIMIT 3;
```

**Nearest stock to the shopper's kiosk (weighted shortest path)**
```cypher
MATCH (k:Kiosk {id: $kiosk})-[:LOCATED_AT]->(src:Location)
MATCH (:SKU {id: $sku})-[st:STOCKED_AT]->(dst:Location) WHERE st.qty > 0
CALL algo.SPpaths({sourceNode: src, targetNode: dst,
                   relTypes: ['CONNECTS'], weightProp: 'meters'})
YIELD path, pathWeight
RETURN dst.name, pathWeight, path ORDER BY pathWeight LIMIT 1;
```

**Rank associates for a task**
```cypher
MATCH (t:Task {id: $tid})-[:PICK_FROM]->(pick:Location)
MATCH (a:Associate {status: 'available'})-[:AT]->(pos:Location)
CALL algo.SPpaths({sourceNode: pos, targetNode: pick,
                   relTypes: ['CONNECTS'], weightProp: 'meters'})
YIELD pathWeight
OPTIONAL MATCH (a)<-[:ASSIGNED_TO]-(open:Task {status: 'open'})
OPTIONAL MATCH (a)-[sk:SKILLED_IN]->(:Zone)-[:HAS_LOCATION]->(pick)
WITH a, pathWeight, count(open) AS load, count(sk) AS skill
RETURN a.name, pathWeight, load, skill,
       pathWeight + 40*load - 20*skill AS score
ORDER BY score LIMIT 3;
```

**Explain a decision (journey replay)**
```cypher
MATCH p = (c:Customer {id: $cid})-[:HAD_SESSION]->(:Session {id: $sid})
          -[:CREATED]->(t:Task)-[:ASSIGNED_TO|HANDED_OFF]->(a:Associate)
RETURN p;
```

**Optional graph-algorithm extras (bonus points)**
- **PageRank on PAIRS_WITH** to find "hero" items that anchor the most outfits, shown in the manager view.
- **Community detection on co-purchase** (`Customer-PURCHASED->SKU`) to find style clusters and seed PAIRS_WITH edges.
- **Betweenness on the layout graph** to find congested choke-point aisles and avoid them when routing.

## 8. Demo scenarios (3-minute video)

1. **"Outdoor wedding" (Track 01: multi-hop, act)**
   Gold member Maria taps her loyalty card at the kiosk and says, "Outfit for a friend's outdoor wedding next month, something breathable."
   → The Concierge returns a dress, sandals and clutch, all in her saved size and all in stock. The sandals are only in the backroom.
   → She taps "Bring to Fitting Room 3".
   → The Dispatcher ranks three associates and Ana wins (18 m, 0 open tasks). The graph view highlights the path.

2. **"Not on the shelf" (Track 01: re-plan)**
   Ana scans the shelf on the mock handheld and taps "Not found".
   → The Co-Pilot sets qty to 0 at that location, finds the next stock 30 m away, and re-routes. The graph updates live.

3. **"Handoff and memory" (Track 02)**
   Ana goes on break, so the task is HANDED_OFF to Raj with full context.
   Maria rejects the clutch ("too formal") and the agent writes a REJECTED edge.
   **Next visit:** Maria comes back a week later and asks for a beach outfit. The agent avoids formal accessories and remembers her size without asking.
   Switching to `store_207` shows separate tenant data: different stock, different associates, same agents.

4. **(Optional) RFID lift and learn:** A simulated tag lift triggers the Concierge to suggest pairings for the lifted item.

## 9. Synthetic data plan (Rule 6)
A seed script generates repeatable synthetic data (fixed seed):
- **2 stores**, each with about 6 zones, about 40 locations, and a CONNECTS layout graph with meters.
- **About 250 products** across 8 categories, 3–6 sizes each, about 1,000 SKUs, and stock spread across floor and backroom.
- **About 12 occasions and 25 attributes.** PAIRS_WITH and SUITS come from rules (category × color × style compatibility) plus about 30 hand-curated "golden" outfits for the demo.
- **About 60 customers** with purchase histories, and **about 10 associates per store** with shifts and skills.
- Product embeddings are computed once from name and description, then cached.

## 10. Tech stack
| Layer | Choice |
|---|---|
| Graph | FalkorDB (Docker locally; FalkorDB Cloud for the live demo) |
| Agents | Python, Claude (Opus or Sonnet) with tool use; a light orchestrator, or LangGraph if the team knows it |
| API | FastAPI, with WebSocket for live updates |
| UI | React or Next.js (or plain HTML reused from the existing deck styling): kiosk page, phone-sized associate page, manager graph page |
| Graph viz | Cytoscape.js or vis-network, highlighting the `path` IDs returned by tools |
| Embeddings | Any embedding API, or a local sentence-transformer |
| Deploy | Vercel (UI), Render or Fly (API), FalkorDB Cloud |

## 11. Build plan

**Oct 10–14, before the event (planning only; no main coding, per Rule 8)**
- Finalize the schema, tools list, demo script and UI wireframes.
- Prepare accounts (FalkorDB Cloud, LLM API key, deploy targets) and read the FalkorDB algorithm and vector docs.
- Write the "golden outfits" list and the demo customer personas on paper or in a doc.

**Day 1 (Oct 15): graph and data**
- Repo skeleton, FalkorDB up, seed generator, schema and indexes.
- All Cypher tool queries working and tested in isolation.

**Day 2 (Oct 16): agents**
- Concierge and Dispatcher agents with typed tools; every tool returns `{result, path}`.
- End-to-end in the CLI: request → outfit → task → assignment.

**Day 3 (Oct 17): UI and coordination**
- Kiosk, associate and graph-view pages over WebSocket.
- Co-Pilot "not found" and handoff flows, memory writes, second-store tenant.

**Day 4 (Oct 18): polish and submit (deadline 11:59 PM IST)**
- Deploy, README with the data model and Cypher, record the demo video, write the blog post (side prize).
- **Submit by evening**, not at 11:50 PM.

**If you fall behind, cut in this order:** RFID scenario → second store → PageRank and community extras → text-to-Cypher tool. **Never cut:** the outfit-and-stock traversal, associate routing, handoff and memory, path highlighting.

## 12. Submission checklist (Rule 10)
- [ ] Public GitHub repo
- [ ] README: problem, architecture diagram, **graph data model**, setup steps
- [ ] `/queries` folder or README section with every Cypher query and algorithm used
- [ ] Demo video (3 minutes, the scenarios above)
- [ ] Live deployment URL, plus `docker compose up` local fallback
- [ ] Tracks named: **01 and 02**
- [ ] AI-assistance disclosure (Rule 11)
- [ ] Every team member can explain the schema, queries and agent decisions (Rule 12)
- [ ] Blog post (optional, AirPods side prize)

## 13. Pitch for judges
- **The graph is the brain, not decoration.** Every recommendation, route and assignment is a traversal or a graph algorithm.
- **Agents act, not just answer.** They create, assign, re-route and hand off real tasks.
- **Explainable by construction.** Every decision comes with the path that produced it.
- **Memory is in the graph.** Preferences, rejections and journeys persist and are separated per store.
- **Real-world grounding.** This is the in-store assistance gap retailers face today, using kiosks and handhelds that already exist.

## 14. Team split (if 3–4 people)
| Person | Owns |
|---|---|
| A | Graph schema, seed data, Cypher tools, algorithms |
| B | Agent orchestrator, prompts, tool wiring, memory |
| C | Kiosk and associate UIs, WebSocket, graph viz |
| D (or shared) | Deployment, README, video, blog |
