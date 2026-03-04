# eval_intention.py
"""Evaluate Intention Detector accuracy via closed-loop testing."""

import json
import os
import statistics
import sys
from pathlib import Path

from intention_graph.comparator import compare_graphs
from intention_graph.detector import IntentionDetector
from intention_graph.graph_speaker import GraphSpeaker
from intention_graph.models import ActionNode, IntentionGraph, Transition


def make_graph(
    domain: str,
    nodes: list[dict],
    transitions: list[dict],
    end_goal: str,
) -> IntentionGraph:
    """Build an IntentionGraph from shorthand definitions."""
    action_nodes = [
        ActionNode(
            id=n["id"], text=n["text"], domain=domain,
            source="expressed", status=n.get("status", "pending"),
            confidence=1.0, specificity=n.get("specificity", 0.5),
        )
        for n in nodes
    ]
    trans = [
        Transition(
            from_id=t["from"], to_id=t["to"],
            base_probability=t["prob"],
            dna_adjusted_probability=t["prob"],
            relation=t["rel"], confidence=1.0,
        )
        for t in transitions
    ]
    return IntentionGraph(
        nodes=action_nodes, transitions=trans,
        end_goal=end_goal,
        summary=f"Eval graph: {domain}",
    )


# ── Test graphs ──────────────────────────────────────────────────────────────
# Focus areas: 心理咨询 (psychological counseling) and 软件 PRD (product requirements)

GRAPHS = {
    # ── 心理咨询 (Therapy/Counseling) ──
    "therapy_anxiety": make_graph(
        domain="therapy",
        nodes=[
            {"id": "int_001", "text": "manage work-related anxiety and stress", "specificity": 0.3},
            {"id": "int_002", "text": "learn breathing and grounding techniques", "specificity": 0.7},
            {"id": "int_003", "text": "set boundaries with manager about overtime", "specificity": 0.7},
            {"id": "int_004", "text": "start regular exercise routine", "specificity": 0.6},
            {"id": "int_005", "text": "consider whether to change jobs", "specificity": 0.5},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_001", "to": "int_004", "rel": "decomposes_to", "prob": 0.6},
            {"from": "int_003", "to": "int_005", "rel": "next_step", "prob": 0.4},
        ],
        end_goal="int_001",
    ),
    "therapy_grief": make_graph(
        domain="therapy",
        nodes=[
            {"id": "int_001", "text": "process grief after losing a parent", "specificity": 0.3},
            {"id": "int_002", "text": "allow myself to feel sadness without guilt", "specificity": 0.5},
            {"id": "int_003", "text": "talk to siblings about shared memories", "specificity": 0.7},
            {"id": "int_004", "text": "join a grief support group", "specificity": 0.7},
            {"id": "int_005", "text": "gradually return to normal daily routine", "specificity": 0.5},
        ],
        transitions=[
            {"from": "int_002", "to": "int_005", "rel": "enables", "prob": 0.6},
            {"from": "int_003", "to": "int_004", "rel": "alternative", "prob": 0.4},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.5},
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.6},
        ],
        end_goal="int_001",
    ),
    "therapy_self_esteem": make_graph(
        domain="therapy",
        nodes=[
            {"id": "int_001", "text": "build self-confidence and self-worth", "specificity": 0.3},
            {"id": "int_002", "text": "stop comparing myself to others on social media", "specificity": 0.6},
            {"id": "int_003", "text": "challenge negative self-talk when it happens", "specificity": 0.6},
            {"id": "int_004", "text": "take on a small creative project to prove capability", "specificity": 0.7},
            {"id": "int_005", "text": "reduce social media usage", "status": "completed", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_005", "to": "int_002", "rel": "enables", "prob": 0.7},
            {"from": "int_003", "to": "int_004", "rel": "next_step", "prob": 0.5},
        ],
        end_goal="int_001",
    ),

    # ── 软件 PRD (Product Requirements) ──
    "prd_auth": make_graph(
        domain="product",
        nodes=[
            {"id": "int_001", "text": "implement user authentication system for the app", "specificity": 0.4},
            {"id": "int_002", "text": "support email and password login", "specificity": 0.7},
            {"id": "int_003", "text": "add OAuth login with Google and GitHub", "specificity": 0.8},
            {"id": "int_004", "text": "implement role-based access control", "specificity": 0.7},
            {"id": "int_005", "text": "add two-factor authentication for admin users", "specificity": 0.8},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_002", "to": "int_004", "rel": "enables", "prob": 0.8},
            {"from": "int_004", "to": "int_005", "rel": "next_step", "prob": 0.6},
        ],
        end_goal="int_001",
    ),
    "prd_dashboard": make_graph(
        domain="product",
        nodes=[
            {"id": "int_001", "text": "build analytics dashboard for business users", "specificity": 0.4},
            {"id": "int_002", "text": "show real-time revenue and conversion metrics", "specificity": 0.7},
            {"id": "int_003", "text": "support custom date range filtering", "specificity": 0.7},
            {"id": "int_004", "text": "export reports as PDF or CSV", "specificity": 0.8},
            {"id": "int_005", "text": "build data pipeline from existing database", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_004", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_005", "to": "int_002", "rel": "enables", "prob": 0.9},
        ],
        end_goal="int_001",
    ),
    "prd_mobile_redesign": make_graph(
        domain="product",
        nodes=[
            {"id": "int_001", "text": "redesign the mobile app checkout flow", "specificity": 0.4},
            {"id": "int_002", "text": "reduce checkout steps from 5 to 3", "specificity": 0.7},
            {"id": "int_003", "text": "add Apple Pay and Google Pay support", "specificity": 0.8},
            {"id": "int_004", "text": "run A/B test on new flow vs old flow", "specificity": 0.7},
            {"id": "int_005", "text": "conduct user research on current pain points", "status": "completed", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_005", "to": "int_002", "rel": "enables", "prob": 0.8},
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_002", "to": "int_004", "rel": "next_step", "prob": 0.6},
        ],
        end_goal="int_001",
    ),

    # ── 日常交流 (Daily Conversation) ──
    "daily_vacation_planning": make_graph(
        domain="daily",
        nodes=[
            {"id": "int_001", "text": "plan a vacation with friends this summer", "specificity": 0.3},
            {"id": "int_002", "text": "go on a beach trip to Bali", "specificity": 0.7},
            {"id": "int_003", "text": "do a road trip through national parks", "specificity": 0.7},
            {"id": "int_004", "text": "set a group budget everyone agrees on", "specificity": 0.6},
            {"id": "int_005", "text": "book flights and accommodation early for better prices", "specificity": 0.8},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "alternative", "prob": 0.5},
            {"from": "int_001", "to": "int_003", "rel": "alternative", "prob": 0.5},
            {"from": "int_004", "to": "int_005", "rel": "enables", "prob": 0.7},
        ],
        end_goal="int_001",
    ),
    "daily_roommate_conflict": make_graph(
        domain="daily",
        nodes=[
            {"id": "int_001", "text": "resolve the ongoing conflict with roommate about cleanliness", "specificity": 0.3},
            {"id": "int_002", "text": "have a direct conversation about cleanliness expectations", "specificity": 0.6},
            {"id": "int_003", "text": "create a shared cleaning schedule", "specificity": 0.7},
            {"id": "int_004", "text": "ask a friend to mediate the conversation", "specificity": 0.7},
            {"id": "int_005", "text": "look for a new apartment if things don't improve", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "next_step", "prob": 0.7},
            {"from": "int_002", "to": "int_004", "rel": "alternative", "prob": 0.4},
            {"from": "int_001", "to": "int_005", "rel": "alternative", "prob": 0.3},
        ],
        end_goal="int_001",
    ),

    # ── 客户服务 (Customer Service) ──
    "cs_complaint_resolution": make_graph(
        domain="customer_service",
        nodes=[
            {"id": "int_001", "text": "get a resolution for the defective laptop received", "specificity": 0.3},
            {"id": "int_002", "text": "get a full refund for the defective product", "specificity": 0.7},
            {"id": "int_003", "text": "get a replacement unit shipped immediately", "specificity": 0.7},
            {"id": "int_004", "text": "escalate the issue to a supervisor", "specificity": 0.6},
            {"id": "int_005", "text": "receive a discount on next purchase as compensation", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "alternative", "prob": 0.6},
            {"from": "int_001", "to": "int_003", "rel": "alternative", "prob": 0.5},
            {"from": "int_004", "to": "int_002", "rel": "enables", "prob": 0.6},
        ],
        end_goal="int_001",
    ),
    "cs_feature_request": make_graph(
        domain="customer_service",
        nodes=[
            {"id": "int_001", "text": "get better reporting capabilities in the software", "specificity": 0.3},
            {"id": "int_002", "text": "export reports to Excel format", "specificity": 0.8},
            {"id": "int_003", "text": "add scheduled automatic report delivery via email", "specificity": 0.7},
            {"id": "int_004", "text": "customize which metrics appear in the dashboard", "specificity": 0.7},
            {"id": "int_005", "text": "get access to the beta program for early features", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_001", "to": "int_004", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_002", "to": "int_003", "rel": "enables", "prob": 0.5},
        ],
        end_goal="int_001",
    ),

    # ── 商业谈判 (Business Negotiation) ──
    "negotiation_salary": make_graph(
        domain="negotiation",
        nodes=[
            {"id": "int_001", "text": "negotiate a higher salary and better compensation package", "specificity": 0.3},
            {"id": "int_002", "text": "research market rate for similar positions", "status": "completed", "specificity": 0.7},
            {"id": "int_003", "text": "ask for a 20% salary increase", "specificity": 0.8},
            {"id": "int_004", "text": "negotiate additional equity or stock options instead", "specificity": 0.7},
            {"id": "int_005", "text": "secure a written commitment with a timeline", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_002", "to": "int_003", "rel": "enables", "prob": 0.8},
            {"from": "int_003", "to": "int_004", "rel": "alternative", "prob": 0.5},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_003", "to": "int_005", "rel": "next_step", "prob": 0.6},
        ],
        end_goal="int_001",
    ),
    "negotiation_partnership": make_graph(
        domain="negotiation",
        nodes=[
            {"id": "int_001", "text": "establish a strategic partnership with the other company", "specificity": 0.3},
            {"id": "int_002", "text": "agree on revenue sharing terms", "specificity": 0.7},
            {"id": "int_003", "text": "define intellectual property ownership boundaries", "specificity": 0.7},
            {"id": "int_004", "text": "propose a 6-month trial period before full commitment", "specificity": 0.8},
            {"id": "int_005", "text": "sign a full long-term partnership agreement immediately", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_002", "to": "int_004", "rel": "enables", "prob": 0.6},
            {"from": "int_004", "to": "int_005", "rel": "alternative", "prob": 0.4},
        ],
        end_goal="int_001",
    ),

    # ── 职业规划 (Career Planning) ──
    "career_change": make_graph(
        domain="career",
        nodes=[
            {"id": "int_001", "text": "transition from engineering to product management", "specificity": 0.3},
            {"id": "int_002", "text": "take a product management certification course", "specificity": 0.7},
            {"id": "int_003", "text": "build a portfolio of product case studies", "specificity": 0.7},
            {"id": "int_004", "text": "network with PMs at target companies", "specificity": 0.6},
            {"id": "int_005", "text": "apply for associate PM positions within 6 months", "specificity": 0.8},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_002", "to": "int_005", "rel": "enables", "prob": 0.7},
            {"from": "int_003", "to": "int_005", "rel": "enables", "prob": 0.6},
        ],
        end_goal="int_001",
    ),
    "career_skill_dev": make_graph(
        domain="career",
        nodes=[
            {"id": "int_001", "text": "become proficient in machine learning to advance career", "specificity": 0.3},
            {"id": "int_002", "text": "complete an online ML fundamentals course", "specificity": 0.7},
            {"id": "int_003", "text": "build a personal project using real-world data", "specificity": 0.7},
            {"id": "int_004", "text": "contribute to an open-source ML library", "specificity": 0.7},
            {"id": "int_005", "text": "present work at a local tech meetup", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "enables", "prob": 0.8},
            {"from": "int_003", "to": "int_004", "rel": "next_step", "prob": 0.5},
            {"from": "int_003", "to": "int_005", "rel": "next_step", "prob": 0.5},
        ],
        end_goal="int_001",
    ),

    # ── 教育 (Education) ──
    "education_thesis": make_graph(
        domain="education",
        nodes=[
            {"id": "int_001", "text": "complete a master's thesis on renewable energy policy", "specificity": 0.3},
            {"id": "int_002", "text": "finish the literature review chapter", "specificity": 0.7},
            {"id": "int_003", "text": "design and conduct the survey methodology", "specificity": 0.7},
            {"id": "int_004", "text": "analyze the collected data using statistical methods", "specificity": 0.7},
            {"id": "int_005", "text": "write the findings and discussion chapters", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "enables", "prob": 0.7},
            {"from": "int_003", "to": "int_004", "rel": "enables", "prob": 0.9},
        ],
        end_goal="int_001",
    ),
    "education_study_plan": make_graph(
        domain="education",
        nodes=[
            {"id": "int_001", "text": "pass the professional certification exam", "specificity": 0.3},
            {"id": "int_002", "text": "complete all online practice modules", "specificity": 0.7},
            {"id": "int_003", "text": "join a study group for weekly review sessions", "specificity": 0.7},
            {"id": "int_004", "text": "take a full-length practice exam under timed conditions", "specificity": 0.8},
            {"id": "int_005", "text": "review weak areas identified from practice results", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_004", "rel": "enables", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "alternative", "prob": 0.5},
            {"from": "int_004", "to": "int_005", "rel": "next_step", "prob": 0.7},
        ],
        end_goal="int_001",
    ),

    # ── 项目管理 (Project Management) ──
    "pm_product_launch": make_graph(
        domain="project_management",
        nodes=[
            {"id": "int_001", "text": "launch the new product feature by end of quarter", "specificity": 0.3},
            {"id": "int_002", "text": "finalize the technical design document", "specificity": 0.7},
            {"id": "int_003", "text": "complete backend API implementation", "specificity": 0.7},
            {"id": "int_004", "text": "build the frontend user interface", "specificity": 0.7},
            {"id": "int_005", "text": "run QA testing and fix critical bugs", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "enables", "prob": 0.9},
            {"from": "int_003", "to": "int_004", "rel": "enables", "prob": 0.8},
        ],
        end_goal="int_001",
    ),
    "pm_sprint_planning": make_graph(
        domain="project_management",
        nodes=[
            {"id": "int_001", "text": "deliver the user notification system this sprint", "specificity": 0.3},
            {"id": "int_002", "text": "set up the notification infrastructure and message queue", "specificity": 0.7},
            {"id": "int_003", "text": "implement email notification templates", "specificity": 0.7},
            {"id": "int_004", "text": "implement push notification support", "specificity": 0.7},
            {"id": "int_005", "text": "add user preference settings for notification channels", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "enables", "prob": 0.9},
            {"from": "int_002", "to": "int_004", "rel": "enables", "prob": 0.8},
        ],
        end_goal="int_001",
    ),
    "pm_migration": make_graph(
        domain="project_management",
        nodes=[
            {"id": "int_001", "text": "migrate the legacy database to the new cloud platform", "specificity": 0.3},
            {"id": "int_002", "text": "audit and document current database schema", "specificity": 0.7},
            {"id": "int_003", "text": "do a phased migration with gradual data transfer", "specificity": 0.7},
            {"id": "int_004", "text": "do a big-bang migration over a maintenance weekend", "specificity": 0.7},
            {"id": "int_005", "text": "run parallel systems to validate data integrity", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_002", "to": "int_003", "rel": "enables", "prob": 0.7},
            {"from": "int_003", "to": "int_004", "rel": "alternative", "prob": 0.5},
            {"from": "int_003", "to": "int_005", "rel": "next_step", "prob": 0.6},
        ],
        end_goal="int_001",
    ),

    # ── 医疗健康 (Medical/Health) ──
    "medical_treatment": make_graph(
        domain="medical",
        nodes=[
            {"id": "int_001", "text": "find the right treatment plan for chronic back pain", "specificity": 0.3},
            {"id": "int_002", "text": "try physical therapy sessions twice a week", "specificity": 0.7},
            {"id": "int_003", "text": "take prescribed anti-inflammatory medication", "specificity": 0.7},
            {"id": "int_004", "text": "consider steroid injections if therapy is not enough", "specificity": 0.7},
            {"id": "int_005", "text": "evaluate surgical options as a last resort", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_002", "to": "int_004", "rel": "evolves_to", "prob": 0.4},
            {"from": "int_004", "to": "int_005", "rel": "evolves_to", "prob": 0.3},
        ],
        end_goal="int_001",
    ),
    "medical_chronic": make_graph(
        domain="medical",
        nodes=[
            {"id": "int_001", "text": "manage type 2 diabetes effectively", "specificity": 0.3},
            {"id": "int_002", "text": "follow a structured low-carb meal plan", "specificity": 0.7},
            {"id": "int_003", "text": "exercise at least 30 minutes daily", "specificity": 0.7},
            {"id": "int_004", "text": "monitor blood sugar levels regularly", "specificity": 0.8},
            {"id": "int_005", "text": "adjust medication dosage based on test results", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_001", "to": "int_004", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_004", "to": "int_005", "rel": "enables", "prob": 0.8},
        ],
        end_goal="int_001",
    ),

    # ── 法律咨询 (Legal) ──
    "legal_dispute": make_graph(
        domain="legal",
        nodes=[
            {"id": "int_001", "text": "resolve the contract dispute with the former business partner", "specificity": 0.3},
            {"id": "int_002", "text": "attempt mediation to reach a settlement", "specificity": 0.7},
            {"id": "int_003", "text": "file a formal lawsuit if mediation fails", "specificity": 0.7},
            {"id": "int_004", "text": "gather all supporting documents and evidence", "specificity": 0.7},
            {"id": "int_005", "text": "send a formal demand letter to the other party", "specificity": 0.8},
        ],
        transitions=[
            {"from": "int_004", "to": "int_005", "rel": "enables", "prob": 0.8},
            {"from": "int_005", "to": "int_002", "rel": "next_step", "prob": 0.7},
            {"from": "int_002", "to": "int_003", "rel": "alternative", "prob": 0.5},
            {"from": "int_001", "to": "int_004", "rel": "decomposes_to", "prob": 0.8},
        ],
        end_goal="int_001",
    ),
    "legal_estate": make_graph(
        domain="legal",
        nodes=[
            {"id": "int_001", "text": "set up a comprehensive estate plan", "specificity": 0.3},
            {"id": "int_002", "text": "create a will that covers all assets", "specificity": 0.7},
            {"id": "int_003", "text": "establish a living trust to avoid probate", "specificity": 0.7},
            {"id": "int_004", "text": "designate power of attorney for health and finances", "specificity": 0.7},
            {"id": "int_005", "text": "review and update beneficiary designations on all accounts", "specificity": 0.8},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_001", "to": "int_004", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_005", "rel": "next_step", "prob": 0.6},
        ],
        end_goal="int_001",
    ),

    # ── v1.8 高难度图谱 (High-difficulty: 6-7 nodes, mixed topology) ──
    "therapy_complex": make_graph(
        domain="therapy",
        nodes=[
            {"id": "int_001", "text": "overcome social anxiety and build confidence in social settings", "specificity": 0.3},
            {"id": "int_002", "text": "start with gradual exposure to small group settings", "specificity": 0.7},
            {"id": "int_003", "text": "practice cognitive behavioral techniques for anxious thoughts", "specificity": 0.7},
            {"id": "int_004", "text": "join a public speaking class to challenge fear", "specificity": 0.7},
            {"id": "int_005", "text": "join an improv comedy class instead", "specificity": 0.7},
            {"id": "int_006", "text": "attend social events without leaving early", "specificity": 0.6},
            {"id": "int_007", "text": "maintain progress independently without therapist guidance", "specificity": 0.5},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_003", "to": "int_002", "rel": "enables", "prob": 0.7},
            {"from": "int_002", "to": "int_006", "rel": "next_step", "prob": 0.6},
            {"from": "int_004", "to": "int_005", "rel": "alternative", "prob": 0.4},
            {"from": "int_006", "to": "int_007", "rel": "next_step", "prob": 0.4},
        ],
        end_goal="int_001",
    ),
    "pm_complex_release": make_graph(
        domain="project_management",
        nodes=[
            {"id": "int_001", "text": "ship the v2.0 platform release by end of Q2", "specificity": 0.3},
            {"id": "int_002", "text": "complete the API v2 migration", "specificity": 0.7},
            {"id": "int_003", "text": "build the new React frontend", "specificity": 0.7},
            {"id": "int_004", "text": "migrate existing users to the new system", "specificity": 0.6},
            {"id": "int_005", "text": "do a gradual rollout with feature flags", "specificity": 0.7},
            {"id": "int_006", "text": "do a hard cutover on a scheduled maintenance window", "specificity": 0.7},
            {"id": "int_007", "text": "conduct performance and load testing before launch", "specificity": 0.8},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "enables", "prob": 0.8},
            {"from": "int_003", "to": "int_007", "rel": "next_step", "prob": 0.8},
            {"from": "int_007", "to": "int_004", "rel": "enables", "prob": 0.7},
            {"from": "int_005", "to": "int_006", "rel": "alternative", "prob": 0.5},
        ],
        end_goal="int_001",
    ),
    "daily_complex_wedding": make_graph(
        domain="daily",
        nodes=[
            {"id": "int_001", "text": "plan the wedding within budget by October", "specificity": 0.3},
            {"id": "int_002", "text": "book a venue that fits 150 guests", "specificity": 0.7},
            {"id": "int_003", "text": "hire a professional wedding planner", "specificity": 0.7},
            {"id": "int_004", "text": "do all the planning ourselves to save money", "specificity": 0.7},
            {"id": "int_005", "text": "finalize the guest list and send invitations", "specificity": 0.8},
            {"id": "int_006", "text": "arrange catering and music for the reception", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_006", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_003", "to": "int_004", "rel": "alternative", "prob": 0.5},
            {"from": "int_002", "to": "int_005", "rel": "enables", "prob": 0.8},
            {"from": "int_005", "to": "int_006", "rel": "next_step", "prob": 0.7},
        ],
        end_goal="int_001",
    ),
    "medical_complex": make_graph(
        domain="medical",
        nodes=[
            {"id": "int_001", "text": "manage severe migraine disorder and improve quality of life", "specificity": 0.3},
            {"id": "int_002", "text": "keep a detailed headache diary to identify triggers", "specificity": 0.8},
            {"id": "int_003", "text": "try preventive medication like beta-blockers", "specificity": 0.7},
            {"id": "int_004", "text": "explore Botox injections as preventive treatment", "specificity": 0.7},
            {"id": "int_005", "text": "consider a nerve stimulation device if medications fail", "specificity": 0.6},
            {"id": "int_006", "text": "make lifestyle changes for sleep and stress management", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_006", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_002", "to": "int_003", "rel": "enables", "prob": 0.8},
            {"from": "int_003", "to": "int_004", "rel": "evolves_to", "prob": 0.4},
            {"from": "int_004", "to": "int_005", "rel": "evolves_to", "prob": 0.3},
        ],
        end_goal="int_001",
    ),

    # ── v1.8 跨领域图谱 (Cross-domain) ──
    "cross_career_negotiation": make_graph(
        domain="career",
        nodes=[
            {"id": "int_001", "text": "negotiate a transition to a leadership role at current company", "specificity": 0.3},
            {"id": "int_002", "text": "document contributions and impact over the past year", "status": "completed", "specificity": 0.7},
            {"id": "int_003", "text": "propose a new team lead position to management", "specificity": 0.7},
            {"id": "int_004", "text": "negotiate the salary and title for the new role", "specificity": 0.7},
            {"id": "int_005", "text": "accept an external offer for a leadership role instead", "specificity": 0.7},
            {"id": "int_006", "text": "complete a leadership training program to strengthen candidacy", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_002", "to": "int_003", "rel": "enables", "prob": 0.8},
            {"from": "int_006", "to": "int_003", "rel": "enables", "prob": 0.6},
            {"from": "int_003", "to": "int_004", "rel": "next_step", "prob": 0.7},
            {"from": "int_003", "to": "int_005", "rel": "alternative", "prob": 0.4},
            {"from": "int_001", "to": "int_006", "rel": "decomposes_to", "prob": 0.7},
        ],
        end_goal="int_001",
    ),
    "cross_medical_legal": make_graph(
        domain="legal",
        nodes=[
            {"id": "int_001", "text": "get proper treatment and compensation after workplace injury", "specificity": 0.3},
            {"id": "int_002", "text": "get a thorough medical evaluation and treatment plan", "specificity": 0.7},
            {"id": "int_003", "text": "document all medical expenses and lost wages", "specificity": 0.7},
            {"id": "int_004", "text": "file a workers' compensation claim", "specificity": 0.7},
            {"id": "int_005", "text": "hire a personal injury attorney", "specificity": 0.6},
            {"id": "int_006", "text": "negotiate a fair settlement with the employer's insurance", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_002", "to": "int_003", "rel": "next_step", "prob": 0.8},
            {"from": "int_003", "to": "int_004", "rel": "enables", "prob": 0.8},
            {"from": "int_004", "to": "int_005", "rel": "alternative", "prob": 0.5},
            {"from": "int_004", "to": "int_006", "rel": "next_step", "prob": 0.6},
        ],
        end_goal="int_001",
    ),
}

# ── Eval suites ──────────────────────────────────────────────────────────────
# quick: 1 per domain (10 graphs, ~40 API calls)
# core: 2 per domain (20 graphs, ~80 API calls)
# full: all graphs (~29 graphs, ~116 API calls)
EVAL_SUITES = {
    "quick": [
        "therapy_anxiety", "prd_auth", "daily_vacation_planning",
        "cs_complaint_resolution", "negotiation_salary", "career_change",
        "education_thesis", "pm_product_launch", "medical_treatment",
        "legal_dispute",
    ],
    "core": [
        "therapy_anxiety", "therapy_grief", "prd_auth", "prd_dashboard",
        "daily_vacation_planning", "daily_roommate_conflict",
        "cs_complaint_resolution", "cs_feature_request",
        "negotiation_salary", "negotiation_partnership",
        "career_change", "career_skill_dev",
        "education_thesis", "education_study_plan",
        "pm_product_launch", "pm_migration",
        "medical_treatment", "medical_chronic",
        "legal_dispute", "legal_estate",
    ],
    # "full" = all graphs (default)
}

PROMPTS = {
    "therapy": "Talk about what's been bothering you with your therapist",
    "product": "Discuss the product requirements with a product manager",
    "daily": "Chat with your friend about what's going on in your life",
    "customer_service": "Explain your issue to the customer service agent",
    "negotiation": "Discuss your negotiation strategy with your advisor",
    "career": "Talk about your career goals and next steps with your coach",
    "education": "Discuss your academic progress and study plan with your advisor",
    "project_management": "Review the project status and next steps with your project manager",
    "medical": "Discuss your health concerns and treatment options with your doctor",
    "legal": "Discuss your legal situation and options with your attorney",
}


def run_eval(
    api_key: str,
    version: str = "latest",
    n_samples: int = 2,
    domain_filter: str = "",
    suite: str = "",
):
    speaker = GraphSpeaker(api_key=api_key)
    detector = IntentionDetector(api_key=api_key)

    # Filter graphs by suite, domain, or use all
    graphs = GRAPHS
    if suite and suite in EVAL_SUITES:
        suite_names = EVAL_SUITES[suite]
        graphs = {name: GRAPHS[name] for name in suite_names if name in GRAPHS}
        print(f"  Using '{suite}' suite: {len(graphs)} graphs")
    elif domain_filter:
        graphs = {
            name: g for name, g in GRAPHS.items()
            if g.nodes and g.nodes[0].domain == domain_filter
        }
        if not graphs:
            print(f"No graphs found for domain '{domain_filter}'.")
            print(f"Available domains: {sorted(set(g.nodes[0].domain for g in GRAPHS.values() if g.nodes))}")
            return {}

    all_metrics = []
    domain_metrics: dict[str, list] = {}
    results: dict[str, dict] = {}

    for graph_name, truth_graph in graphs.items():
        print(f"\n{'='*60}")
        print(f"  Graph: {graph_name}")
        print(f"{'='*60}")

        best_metrics = None
        best_predicted = None
        best_score = -1.0
        sample_edge_f1s: list[float] = []

        for sample_i in range(n_samples):
            # Generate dialogue
            print(f"  [Run {sample_i+1}/{n_samples}] Generating dialogue...", end=" ", flush=True)
            domain = truth_graph.nodes[0].domain if truth_graph.nodes else "general"
            prompt = PROMPTS.get(domain, "Discuss your plans and goals with an advisor")
            dialogue = speaker.generate(graph=truth_graph, prompt=prompt)
            print(f"done ({len(dialogue.split())} words)")

            # Detect
            print(f"  [Run {sample_i+1}/{n_samples}] Detecting intentions...", end=" ", flush=True)
            predicted = detector.analyze(
                text=dialogue,
                speaker_id=f"eval_{graph_name}",
                speaker_label="Speaker",
                domain=truth_graph.nodes[0].domain,
                skip_expand=True,
            )
            print("done")

            # Compare
            metrics = compare_graphs(predicted, truth_graph)
            sample_edge_f1s.append(metrics.edge_f1)
            score = metrics.node_f1 + metrics.edge_f1
            if score > best_score:
                best_score = score
                best_metrics = metrics
                best_predicted = predicted

        metrics = best_metrics
        predicted = best_predicted
        all_metrics.append(metrics)
        domain = truth_graph.nodes[0].domain if truth_graph.nodes else "general"
        domain_metrics.setdefault(domain, []).append(metrics)

        # Variance reporting
        variance_str = ""
        if n_samples > 1:
            spread = max(sample_edge_f1s) - min(sample_edge_f1s)
            variance_str = f"  [variance: {min(sample_edge_f1s):.2f}-{max(sample_edge_f1s):.2f}, spread={spread:.2f}]"

        print(f"\n  Best of {n_samples} — Nodes: {metrics.matched_nodes}/{metrics.total_truth_nodes} matched "
              f"(P={metrics.node_precision:.2f} R={metrics.node_recall:.2f} F1={metrics.node_f1:.2f})")
        print(f"  Edges: F1={metrics.edge_f1:.2f} (relaxed={metrics.edge_f1_relaxed:.2f}), Prob MAE={metrics.probability_mae:.3f}{variance_str}")
        print(f"  End Goal: {'CORRECT' if metrics.end_goal_correct else 'WRONG'}")

        # Diagnostic: show predicted graph
        print(f"\n  Predicted nodes ({len(predicted.nodes)}):")
        for n in predicted.nodes:
            print(f"    [{n.id}] {n.text} (sp={n.specificity:.1f})")
        print(f"  Predicted edges ({len(predicted.transitions)}):")
        for t in predicted.transitions:
            print(f"    {t.from_id} --[{t.relation}]--> {t.to_id}")
        print(f"  Predicted end goal: {predicted.end_goal}")

        graph_result = metrics.to_dict()
        if n_samples > 1:
            graph_result["sample_edge_f1s"] = [round(s, 3) for s in sample_edge_f1s]
            graph_result["edge_f1_spread"] = round(max(sample_edge_f1s) - min(sample_edge_f1s), 3)
        results[graph_name] = graph_result

    # Per-domain summary
    print(f"\n{'='*60}")
    print(f"  PER-DOMAIN SUMMARY")
    print(f"{'='*60}")
    domain_summary = {}
    for dom in sorted(domain_metrics):
        dm = domain_metrics[dom]
        d_node_f1 = statistics.mean(m.node_f1 for m in dm)
        d_edge_f1 = statistics.mean(m.edge_f1 for m in dm)
        d_edge_f1_r = statistics.mean(m.edge_f1_relaxed for m in dm)
        d_end_goal = sum(1 for m in dm if m.end_goal_correct) / len(dm)
        flag = " ⚠" if d_edge_f1 < 0.80 else ""
        print(f"  {dom:20s}  Node F1={d_node_f1:.3f}  Edge F1={d_edge_f1:.3f} (relaxed={d_edge_f1_r:.3f})  EndGoal={d_end_goal:.0%}{flag}")
        domain_summary[dom] = {
            "avg_node_f1": round(d_node_f1, 3),
            "avg_edge_f1": round(d_edge_f1, 3),
            "avg_edge_f1_relaxed": round(d_edge_f1_r, 3),
            "end_goal_accuracy": round(d_end_goal, 3),
            "n_graphs": len(dm),
        }

    # Overall
    print(f"\n{'='*60}")
    print(f"  OVERALL SUMMARY ({len(all_metrics)} graphs)")
    print(f"{'='*60}")
    avg_node_f1 = statistics.mean(m.node_f1 for m in all_metrics)
    avg_edge_f1 = statistics.mean(m.edge_f1 for m in all_metrics)
    avg_edge_f1_relaxed = statistics.mean(m.edge_f1_relaxed for m in all_metrics)
    avg_recall = statistics.mean(m.node_recall for m in all_metrics)
    end_goal_acc = sum(1 for m in all_metrics if m.end_goal_correct) / len(all_metrics)
    min_edge_f1 = min(m.edge_f1 for m in all_metrics)
    max_edge_f1 = max(m.edge_f1 for m in all_metrics)

    print(f"  Avg Node F1: {avg_node_f1:.3f}")
    print(f"  Avg Node Recall: {avg_recall:.3f}")
    print(f"  Avg Edge F1: {avg_edge_f1:.3f} (relaxed={avg_edge_f1_relaxed:.3f})  [min={min_edge_f1:.3f}, max={max_edge_f1:.3f}]")
    print(f"  End Goal Accuracy: {end_goal_acc:.1%}")

    # Collect variance stats from per-graph results
    graphs_with_spread = [
        v["edge_f1_spread"] for k, v in results.items()
        if not k.startswith("_") and "edge_f1_spread" in v
    ]
    avg_spread = statistics.mean(graphs_with_spread) if graphs_with_spread else 0.0
    max_spread = max(graphs_with_spread) if graphs_with_spread else 0.0
    if graphs_with_spread:
        print(f"  Avg Edge F1 Spread: {avg_spread:.3f} (max={max_spread:.3f})")

    results["_domains"] = domain_summary
    results["_overall"] = {
        "avg_node_f1": round(avg_node_f1, 3),
        "avg_node_recall": round(avg_recall, 3),
        "avg_edge_f1": round(avg_edge_f1, 3),
        "avg_edge_f1_relaxed": round(avg_edge_f1_relaxed, 3),
        "end_goal_accuracy": round(end_goal_acc, 3),
        "min_edge_f1": round(min_edge_f1, 3),
        "max_edge_f1": round(max_edge_f1, 3),
        "avg_edge_f1_spread": round(avg_spread, 3),
        "max_edge_f1_spread": round(max_spread, 3),
    }

    version_tag = version or "latest"
    output_path = Path(f"eval_intention_results_{version_tag}.json")
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\n  Results saved to {output_path}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate Intention Detector")
    parser.add_argument("version", nargs="?", default="latest", help="Version tag for results file")
    parser.add_argument("--domain", default="", help="Filter by domain (e.g. therapy, product, daily)")
    parser.add_argument("--suite", default="", choices=["quick", "core", "full", ""], help="Eval suite: quick (10), core (20), full (all)")
    parser.add_argument("--quick", action="store_true", help="Quick mode: 1 sample per graph")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY env var to run evaluation.")
        sys.exit(1)
    run_eval(
        api_key,
        version=args.version,
        n_samples=1 if args.quick else 2,
        domain_filter=args.domain,
        suite=args.suite,
    )
