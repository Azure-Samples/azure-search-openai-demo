#!/usr/bin/env python
"""
Red Teaming Script for Azure Search OpenAI Demo Application

This script performs automated adversarial testing (red teaming) of the RAG application
to identify potential safety vulnerabilities across multiple risk categories.

Based on: https://github.com/Azure-Samples/azureai-samples/blob/main/scenarios/evaluate/AI_RedTeaming/AI_RedTeaming.ipynb

Run: python evals/redteam.py
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Any, Dict
from pprint import pprint

# Azure imports
from azure.identity import DefaultAzureCredential
from azure.ai.evaluation.red_team import RedTeam, RiskCategory, AttackStrategy
from dotenv_azd import load_azd_env
import requests

# Load environment variables
load_azd_env()

# Configure Azure AI project for red teaming
azure_ai_project = {
    "subscription_id": os.environ.get("AZURE_SUBSCRIPTION_ID"),
    "resource_group_name": os.environ.get("AZURE_RESOURCE_GROUP"),
    "project_name": os.environ.get("AZURE_AI_PROJECT"),
}

# Backend URL - adjust based on where your app is running
# Remove trailing slash to prevent double slash in URLs
BACKEND_URL = os.environ.get("BACKEND_URL", "https://capps-backend-poprbcmujix6c.blackdesert-c529f77d.francecentral.azurecontainerapps.io")

# Initialize Azure credential
credential = DefaultAzureCredential()


# ----------------------------------------------
# 1. Define Target Callback Function
# ----------------------------------------------
def rag_application_callback(query: str) -> str:
    """
    Callback function that targets the RAG application backend API.
    This function is called by the red team simulator to test the application.
    
    Args:
        query: The adversarial query from the red team simulator
        
    Returns:
        String response from the RAG application
    """
    try:
        # Call the /ask endpoint of the RAG application
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json={
                "messages": [{"content": query, "role": "user"}],
                "context": {
                    "overrides": {
                        "retrieval_mode": "hybrid",
                        "semantic_ranker": True,
                        "semantic_captions": False,
                        "top": 3,
                        "suggest_followup_questions": False,
                    }
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Extract the answer from the response and return as string
        answer = result.get("message", {}).get("content", "")
        
        return answer if answer else "I don't know."
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error calling RAG application: {str(e)}"
        # Log the error with more detail for debugging
        print(f"⚠️ {error_msg}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response status: {e.response.status_code}")
            print(f"   Response body: {e.response.text[:200]}")
            print(f"   Request query length: {len(query)} chars")
        # Return a safe error message instead of propagating the exception details
        return "I cannot process that request."


# ----------------------------------------------
# 2. Configure Red Team Scan
# ----------------------------------------------
async def run_red_team_scan():
    """
    Execute the red team scan against the RAG application.
    """
    
    # Check if backend is accessible
    try:
        health_check = requests.get(f"{BACKEND_URL}/", timeout=5)
        print(f"✅ Backend is accessible at {BACKEND_URL}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error: Cannot connect to backend at {BACKEND_URL}")
        print(f"   Make sure the backend is running. Error: {e}")
        print(f"   You can start it with the 'Development' task or:")
        print(f"   python app/backend/app.py")
        return
    
    print("\n" + "="*70)
    print("🎯 Starting Red Team Evaluation of RAG Application")
    print("="*70)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Azure AI Project: {azure_ai_project.get('project_name')}")
    print()
    
    # Create output directory
    output_dir = Path("evals/redteam_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ----------------------------------------------
    # 3. Run Basic Red Team Scan
    # ----------------------------------------------
    print("🔴 Running Basic Red Team Scan...")
    print("   Risk Categories: Violence, HateUnfairness, Sexual, SelfHarm")
    print("   Attack Strategies: Baseline (no transformation)")
    print()
    
    # Create RedTeam instance with basic configuration
    basic_red_team = RedTeam(
        azure_ai_project=azure_ai_project,
        credential=credential,
        risk_categories=[
            RiskCategory.Violence,
            RiskCategory.HateUnfairness,
            RiskCategory.Sexual,
            RiskCategory.SelfHarm,
        ],
        num_objectives=3,  # Number of attacks per risk category
    )
    
    # Run the scan
    basic_result = await basic_red_team.scan(
        target=rag_application_callback,
        scan_name="RAG-App-Basic-Scan",
        application_scenario="Azure Search OpenAI Demo RAG Application",
        attack_strategies=[],  # Empty list = baseline attacks only
    )
    
    # Save basic results
    basic_output_path = output_dir / "basic_scan_results.json"
    with open(basic_output_path, "w") as f:
        # Convert RedTeamResult to dict for JSON serialization
        result_dict = basic_result if isinstance(basic_result, dict) else vars(basic_result)
        json.dump(result_dict, f, indent=2, default=str)
    print(f"✅ Basic scan complete. Results saved to: {basic_output_path}")
    print()
    
    # Display basic metrics
    print("📊 Basic Scan Metrics:")
    if hasattr(basic_result, "metrics"):
        pprint(basic_result.metrics)
    elif isinstance(basic_result, dict) and "metrics" in basic_result:
        pprint(basic_result["metrics"])
    print()

    # ----------------------------------------------
    # 4. Run Advanced Red Team Scan
    # ----------------------------------------------
    print("🔴 Running Advanced Red Team Scan...")
    print("   Risk Categories: Violence, HateUnfairness, Sexual, SelfHarm")
    print("   Attack Strategies: Multiple transformation techniques")
    print()
    
    # Create RedTeam instance with advanced configuration
    # Note: Only Violence, HateUnfairness, Sexual, and SelfHarm are available in current SDK
    advanced_red_team = RedTeam(
        azure_ai_project=azure_ai_project,
        credential=credential,
        risk_categories=[
            RiskCategory.Violence,
            RiskCategory.HateUnfairness,
            RiskCategory.Sexual,
            RiskCategory.SelfHarm,
        ],
        num_objectives=5,  # More attacks for comprehensive testing
    )
    
    # Run the scan with multiple attack strategies
    advanced_result = await advanced_red_team.scan(
        target=rag_application_callback,
        scan_name="RAG-App-Advanced-Scan",
        application_scenario="Azure Search OpenAI Demo RAG Application - Comprehensive Test",
        attack_strategies=[
            AttackStrategy.EASY,          # Group of easy complexity attacks
            AttackStrategy.MODERATE,      # Group of moderate complexity attacks
            AttackStrategy.Base64,        # Base64 encoding
            AttackStrategy.ROT13,         # ROT13 encoding
            AttackStrategy.CharacterSpace, # Add character spaces
            AttackStrategy.UnicodeConfusable, # Unicode confusables
        ],
    )
    
    # Save advanced results
    advanced_output_path = output_dir / "advanced_scan_results.json"
    with open(advanced_output_path, "w") as f:
        # Convert RedTeamResult to dict for JSON serialization
        result_dict = advanced_result if isinstance(advanced_result, dict) else vars(advanced_result)
        json.dump(result_dict, f, indent=2, default=str)
    print(f"✅ Advanced scan complete. Results saved to: {advanced_output_path}")
    print()
    
    # Display advanced metrics
    print("📊 Advanced Scan Metrics:")
    if hasattr(advanced_result, "metrics"):
        pprint(advanced_result.metrics)
    elif isinstance(advanced_result, dict) and "metrics" in advanced_result:
        pprint(advanced_result["metrics"])
    print() 
    
    # ----------------------------------------------
    # 5. Display Summary
    # ----------------------------------------------
    print("\n" + "="*70)
    print("✅ Red Team Evaluation Complete!")
    print("="*70)
    print()
    print("📁 Results Location:")
    print(f"   Basic Scan:    {basic_output_path}")
    print(f"   Advanced Scan: {advanced_output_path}")
    print()
    print("📈 Key Metrics to Review:")
    print("   - Attack Success Rate (ASR): % of attacks that elicited harmful content")
    print("   - Vulnerability by Risk Category: Which content types are most vulnerable")
    print("   - Effectiveness of Attack Strategies: Which techniques work best")
    print()
    print("🔍 Next Steps:")
    print("   1. Review the JSON files for detailed conversation logs")
    print("   2. Identify patterns in successful attacks")
    print("   3. Implement mitigations for identified vulnerabilities")
    print("   4. Re-run scans to validate improvements")
    print()
    print("💡 Tip: View results in Azure AI Foundry portal for interactive analysis")
    print("="*70)


# ----------------------------------------------
# Main Execution
# ----------------------------------------------
if __name__ == "__main__":
    # Run the async red team scan
    asyncio.run(run_red_team_scan())


# ----------------------------------------------
# Usage Instructions:
#
# 1. Start the backend application:
#    - Run the "Development" task in VS Code
#    - Or: python app/backend/app.py
#    - Or: ./app/start.sh
#
# 2. Ensure environment variables are set:
#    - AZURE_SUBSCRIPTION_ID
#    - AZURE_RESOURCE_GROUP
#    - AZURE_AI_PROJECT
#    - BACKEND_URL (optional, defaults to http://localhost:50505)
#
# 3. Run the red team scan:
#    python evals/redteam.py
#
# 4. Review results in evals/redteam_results/
#
# ----------------------------------------------
# Understanding Risk Categories:
#
# - Violence: Content describing or promoting violence
# - HateUnfairness: Hate speech or unfair bias
# - Sexual: Inappropriate sexual content
# - SelfHarm: Content related to self-harm behaviors
# - ProtectedMaterial: Copyrighted or protected content
# - CodeVulnerability: Vulnerable code generation
# - UngroundedAttributes: Ungrounded or fabricated information
#
# ----------------------------------------------
# Understanding Attack Strategies:
#
# - Baseline: Standard prompts without transformation
# - EASY: Simple attack patterns (low sophistication)
# - MODERATE: More sophisticated attacks
# - DIFFICULT: Complex, layered attack strategies
# - Base64: Base64 encoding of prompts
# - ROT13: ROT13 cipher encoding
# - CharacterSpace: Adding spaces between characters
# - UnicodeConfusable: Using similar-looking Unicode characters
#
# ----------------------------------------------
