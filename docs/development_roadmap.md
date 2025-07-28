# Kairos v8.0 Development Roadmap

## **Overview**
This document aims to provide a detailed roadmap to transform the Kairos project from its current MVP state into the autonomous, self-improving and context-aware Kairos v8.0.

---

## **Current Assessment: MVP 0.1**

### **Strengths:**
* **UI/UX Excellence:** React-based interface that professionally reflects the project's vision. The dashboard and components like Agent Status and Memory Viewer rightly showcase the intended components.
* **Correct Architectural Skeleton:** The `Controller CLI` + `Daemon (FastAPI)` + `Agent` structure is suitable for the scalable architecture we discussed from the beginning.
* **Modular Code Structure:** The code is logically divided into folders like `agents`, `memory`, `orchestration`, `monitoring`. This is a solid foundation for future development.

### **Main Development Area:**
The prototype currently lacks live dynamics. The UI needs to connect to an advanced backend to truly embody the envisioned living entity.

---

## **Identified Critical Errors and Shortcomings**

**1. `cli.py` - Daemon Startup Error:**
* **Issue:** `start_daemon` function uses `subprocess.run`, which is blocking.
* **Solution:** Use `subprocess.Popen` and manage the process ID for proper stopping.

**2. `agent_coordinator.py` - Workflow Inadequacy:**
* **Issue:** The `execute_workflow` function lacks a state machine for managing complex flows.
* **Solution:** Redesign this using the Flow Engineering concept.

**3. `llm_router.py` - Static and Simple:**
* **Issue:** Model selection is basic and blocking calls harm server performance.
* **Solution:** Use async and develop a scoring algorithm using performance metrics.

**4. Direct Agent Calls:**
* **Issue:** API endpoints in `main.py` directly call agents.
* **Solution:** All agent interactions should be routed through `agent_coordinator`.

**5. Memory Layer - From Prototype to Real:**
* **Issue:** Needs integration with real graph or vector DBs.
* **Solution:** Combine files and create `KnowledgeGraphManager` class with real DB bindings.

---

## **New Direction: Strategic Roadmap for Development**

### **Sprint Plan**

#### **Sprint 0: Core Fixes and Refactoring (1 Week)**

**Objective:** Strengthen the existing codebase.

**Tasks:**
1. **Fix CLI:** Use `subprocess.Popen` in `cli.py` and manage the PID.
2. **Improve Async Infrastructure:** Transition to full async using httpx.
3. **Centralize Agent Calls:** Amend `main.py` to route via `agent_coordinator`.
4. **Unify Memory Layer:** Merge existing files into a new `MemoryManager`.

---

#### **Sprint 1: Flow Engineering and Agent Orchestration (2 Weeks)**

**Objective:** Solve workflow issues and smartly manage agents.

**Tasks:**
1. **Develop Flow Manager:** Convert `agent_coordinator.py` to a Flow Manager.
2. **Standardize Agent Interface:** Create `BaseAgent` superclass.
3. **Add Checkpoints:** Invoke `Integrity Guardian` at each flow step.

---

#### **Sprint 2: Revive Memory and Feed the UI (2 Weeks)**

**Objective:** Fill static UI with dynamic and real data.

**Tasks:**
1. **Integrate Databases:** Use Neo4j and Qdrant with Docker.
2. **Real-time API Endpoints:** Update endpoints to fetch real data.
3. **Connect React Frontend:** Ensure frontend retrieves data from new endpoints.

---

#### **Sprint 3: Autonomous Learning and Smart Routing (3 Weeks)**

**Objective:** Realize the self-improving spirit of Kairos.

**Tasks:**
1. **Metric Engine Development:** Expand `performance_tracker.py`.
2. **Smart LLM Router:** Rewrite `select_model` function.
3. **Round-Robin API Proxy:** Integrate key rotation mechanism.
4. **Fine-Tuning Data Collection:** Establish mechanism for gathering 'wrong -> right' data pairs.

---

This roadmap will transform the current potential of the project into reality with concrete, manageable, and exciting steps.
