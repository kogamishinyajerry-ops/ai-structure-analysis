"""Autonomous Agentic Benchmark for GS-001.

This script feeds a natural language request to the LangGraph pipeline
and expects the agents to model, mesh, solve, and analyze it autonomously.
"""

import asyncio
import logging
from pathlib import Path
import sys

# Ensure project root is in path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.graph import build_graph
from schemas.sim_state import FaultClass

# Configure logging to see individual node logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgenticBenchmark")

GS001_PROMPT = (
    "Run a static analysis on a cantilever beam with the following specs: "
    "Geometry: 100m long, 10m x 10m rectangular section. "
    "Material: Steel (Young's Modulus: 210 GPa, Poisson Ratio: 0.3). "
    "Boundary Conditions: Fixed at the left end (Nroot). "
    "Loads: Total 400N concentrated force downwards (-Y) at the right end (Ntip). "
    "Goal: Verify if the autonomous pipeline can reach within 10% of the analytical displacement of 0.49m."
)

async def run_benchmark():
    # 1. Build the graph
    workflow = build_graph()
    app = workflow.compile()

    # 2. Initial State
    initial_state = {
        "user_request": GS001_PROMPT,
        "plan": None,
        "geometry_path": None,
        "mesh_path": None,
        "frd_path": None,
        "verdict": None,
        "fault_class": FaultClass.NONE,
        "retry_budgets": {},
        "history": [],
        "reports": {},
        "artifacts": []
    }

    logger.info("Starting Autonomous Agentic Pipeline for GS-001...")
    
    try:
        # Use ainvoke to get the final complete state
        final_state = await app.ainvoke(initial_state)

        # 4. Final Summary
        print("\n" + "="*50)
        print("AGENTIC BENCHMARK COMPLETE")
        print("="*50)
        
        # Log the full history for debugging
        print("\nExecution History:")
        for entry in final_state.get("history", []):
            node = entry.get("node", "unknown")
            fault = entry.get("fault", "none")
            msg = entry.get("msg", "")
            print(f" - [{node}] fault={fault}: {msg}")

        print(f"\nFinal Verdict: {final_state.get('verdict')}")
        print(f"Fault Class: {final_state.get('fault_class')}")
        
        plan = final_state.get('plan')
        if plan:
            print(f"Case ID: {plan.case_id}")
            print(f"Material: {plan.material.name} (E={plan.material.youngs_modulus})")
        
        reports = final_state.get("reports", {})
        if "markdown" in reports:
            print(f"\nFinal Report Summary:\n{reports['markdown'][:1000]}...")
            
        frd_path = final_state.get("frd_path")
        if frd_path:
            print(f"\nResult Path: {frd_path}")
            
    except Exception as e:
        logger.exception(f"Pipeline crashed: {e}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
