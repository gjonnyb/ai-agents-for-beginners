"""
Seed script — populates the CRM with realistic demo data for a $50M
commercial electrical contractor.

Run:  cd contractor-crm && python -m db.seed
"""
from __future__ import annotations

import os
import sys
import random
from datetime import datetime, timedelta

# Add parent dir to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import init_db, SessionLocal
from db.models import (
    Customer, Contact, Project, Interaction, ServiceRecord,
    MaintenanceContract, RevenueRecord, Prospect,
)

random.seed(42)


def seed():
    init_db()
    db = SessionLocal()

    # Clear existing data
    for model in [RevenueRecord, Interaction, ServiceRecord, MaintenanceContract,
                  Project, Contact, Prospect, Customer]:
        db.query(model).delete()
    db.commit()

    # ---- Customers ----
    customers_data = [
        # Concentrated customers (top 3 represent ~55% of revenue = concentration risk)
        {"name": "Turner Construction", "customer_type": "general_contractor", "industry_segment": "commercial_office",
         "city": "Dallas", "state": "TX", "phone": "(214) 555-0100", "annual_revenue_potential": 5000000,
         "source": "referral", "status": "active"},
        {"name": "Hines Property Management", "customer_type": "property_manager", "industry_segment": "commercial_office",
         "city": "Houston", "state": "TX", "phone": "(713) 555-0200", "annual_revenue_potential": 4000000,
         "source": "repeat", "status": "active"},
        {"name": "Prologis Industrial", "customer_type": "property_owner", "industry_segment": "industrial",
         "city": "Fort Worth", "state": "TX", "phone": "(817) 555-0300", "annual_revenue_potential": 3500000,
         "source": "referral", "status": "active"},
        # Mid-tier customers
        {"name": "CBRE Facility Services", "customer_type": "facility_manager", "industry_segment": "commercial_office",
         "city": "Dallas", "state": "TX", "phone": "(214) 555-0400", "annual_revenue_potential": 2000000,
         "source": "bid_board", "status": "active"},
        {"name": "Lincoln Property Company", "customer_type": "property_manager", "industry_segment": "mixed_use",
         "city": "Dallas", "state": "TX", "phone": "(214) 555-0500", "annual_revenue_potential": 2500000,
         "source": "cold_outreach", "status": "active"},
        {"name": "Trammell Crow Company", "customer_type": "developer", "industry_segment": "commercial_office",
         "city": "Dallas", "state": "TX", "phone": "(214) 555-0600", "annual_revenue_potential": 3000000,
         "source": "trade_show", "status": "active"},
        {"name": "McCarthy Building Companies", "customer_type": "general_contractor", "industry_segment": "healthcare",
         "city": "Dallas", "state": "TX", "phone": "(214) 555-0700", "annual_revenue_potential": 2000000,
         "source": "referral", "status": "active"},
        {"name": "Stream Data Centers", "customer_type": "property_owner", "industry_segment": "data_center",
         "city": "Richardson", "state": "TX", "phone": "(469) 555-0800", "annual_revenue_potential": 4000000,
         "source": "website", "status": "active"},
        # Smaller / newer customers
        {"name": "Dallas ISD", "customer_type": "government", "industry_segment": "education",
         "city": "Dallas", "state": "TX", "phone": "(214) 555-0900", "annual_revenue_potential": 1500000,
         "source": "bid_board", "status": "active"},
        {"name": "Marriott Select Service", "customer_type": "property_owner", "industry_segment": "hospitality",
         "city": "Plano", "state": "TX", "phone": "(972) 555-1000", "annual_revenue_potential": 800000,
         "source": "cold_outreach", "status": "active"},
        {"name": "Amazon Fulfillment", "customer_type": "industrial", "industry_segment": "industrial",
         "city": "Haslet", "state": "TX", "phone": "(817) 555-1100", "annual_revenue_potential": 2000000,
         "source": "bid_board", "status": "active"},
        {"name": "Kroger Southwest", "customer_type": "facility_manager", "industry_segment": "retail",
         "city": "Dallas", "state": "TX", "phone": "(214) 555-1200", "annual_revenue_potential": 600000,
         "source": "referral", "status": "active"},
        # At-risk / former
        {"name": "Hillwood Development", "customer_type": "developer", "industry_segment": "mixed_use",
         "city": "Fort Worth", "state": "TX", "phone": "(817) 555-1300", "annual_revenue_potential": 1500000,
         "source": "trade_show", "status": "active"},
    ]

    customers = []
    for cd in customers_data:
        c = Customer(**cd)
        db.add(c)
        db.flush()
        customers.append(c)

    # ---- Contacts ----
    contacts_data = [
        # Turner Construction
        (0, "Mike", "Reynolds", "VP of Operations", "decision_maker", "mike.reynolds@turner.example.com", "(214) 555-0101", 1, "Bob Martinez"),
        (0, "Sarah", "Chen", "Project Manager", "influencer", "sarah.chen@turner.example.com", "(214) 555-0102", 0, "Bob Martinez"),
        (0, "David", "Park", "Estimator", "technical", "david.park@turner.example.com", "(214) 555-0103", 0, "Bob Martinez"),
        # Hines
        (1, "Jennifer", "Walsh", "Regional Director", "decision_maker", "j.walsh@hines.example.com", "(713) 555-0201", 1, "Carlos Gutierrez"),
        (1, "Tom", "Bradley", "Facility Manager", "technical", "t.bradley@hines.example.com", "(713) 555-0202", 0, "Carlos Gutierrez"),
        # Prologis
        (2, "Robert", "Kim", "Director of Construction", "decision_maker", "r.kim@prologis.example.com", "(817) 555-0301", 1, "Bob Martinez"),
        (2, "Lisa", "Nguyen", "Project Coordinator", "influencer", "l.nguyen@prologis.example.com", "(817) 555-0302", 0, "Bob Martinez"),
        # CBRE
        (3, "Amanda", "Foster", "Account Manager", "decision_maker", "a.foster@cbre.example.com", "(214) 555-0401", 1, "Maria Torres"),
        # Lincoln Property
        (4, "James", "Morton", "VP Construction", "decision_maker", "j.morton@lincolnprop.example.com", "(214) 555-0501", 1, "Carlos Gutierrez"),
        # Trammell Crow
        (5, "Patricia", "Owens", "Development Manager", "decision_maker", "p.owens@trammellcrow.example.com", "(214) 555-0601", 1, "Bob Martinez"),
        (5, "Kevin", "Hughes", "Construction Manager", "influencer", "k.hughes@trammellcrow.example.com", "(214) 555-0602", 0, "Bob Martinez"),
        # McCarthy
        (6, "Brian", "Thompson", "Preconstruction Director", "decision_maker", "b.thompson@mccarthy.example.com", "(214) 555-0701", 1, "Maria Torres"),
        # Stream Data Centers
        (7, "Rachel", "Green", "Director of Engineering", "decision_maker", "r.green@stream.example.com", "(469) 555-0801", 1, "Carlos Gutierrez"),
        (7, "Marcus", "Wilson", "Critical Facilities Manager", "technical", "m.wilson@stream.example.com", "(469) 555-0802", 0, "Carlos Gutierrez"),
        # Dallas ISD
        (8, "Diane", "Rodriguez", "Facilities Director", "decision_maker", "d.rodriguez@dallasisd.example.com", "(214) 555-0901", 1, "Maria Torres"),
        # Marriott
        (9, "Steve", "Anderson", "Area Engineer", "decision_maker", "s.anderson@marriott.example.com", "(972) 555-1001", 1, "Maria Torres"),
        # Amazon
        (10, "Priya", "Patel", "Maintenance Manager", "decision_maker", "p.patel@amazon.example.com", "(817) 555-1101", 1, "Bob Martinez"),
        # Kroger
        (11, "Greg", "Simmons", "Facilities Coordinator", "influencer", "g.simmons@kroger.example.com", "(214) 555-1201", 1, "Maria Torres"),
        # Hillwood
        (12, "Nancy", "Clark", "VP Development", "decision_maker", "n.clark@hillwood.example.com", "(817) 555-1301", 1, "Carlos Gutierrez"),
    ]

    contacts = []
    for ci, first, last, title, role, email, phone, primary, owner in contacts_data:
        ct = Contact(
            customer_id=customers[ci].id, first_name=first, last_name=last,
            title=title, role_type=role, email=email, phone=phone,
            is_primary=primary, relationship_owner=owner,
        )
        db.add(ct)
        db.flush()
        contacts.append(ct)

    # ---- Projects (mix of historical, active, and pipeline) ----
    base_date = datetime(2025, 1, 1)

    projects_data = [
        # Turner — big ongoing relationship
        (0, "One Arts Plaza Renovation", "renovation", "completed", 2800000, 2400000, 2800000, 14.3, "2024-06-01", "2025-03-15", "Bob Martinez", "Jim Lee"),
        (0, "McKinney & Olive Tower TI", "tenant_improvement", "in_progress", 1200000, 1000000, 1150000, 13.0, "2025-06-01", "2025-12-30", "Bob Martinez", "Jim Lee"),
        (0, "Victory Park Office Phase 2", "new_construction", "bid_submitted", 3500000, 3000000, None, 14.3, None, None, "Bob Martinez", None),
        # Hines — steady
        (1, "Galleria Tower Lighting Retrofit", "energy_upgrade", "completed", 950000, 800000, 950000, 15.8, "2024-09-01", "2025-02-28", "Maria Torres", "Jim Lee"),
        (1, "Uptown Office EV Charging", "ev_charging", "won", 420000, 350000, 420000, 16.7, "2025-08-01", "2025-11-30", "Maria Torres", "Jim Lee"),
        (1, "Post Oak Building Renovation", "renovation", "estimating", 1800000, None, None, None, None, None, "Maria Torres", None),
        # Prologis — largest single customer
        (2, "Alliance Gateway Warehouse 12", "new_construction", "completed", 4200000, 3600000, 4200000, 14.3, "2024-01-15", "2024-11-30", "Bob Martinez", "Sarah Kim"),
        (2, "Alliance Gateway Warehouse 14", "new_construction", "in_progress", 3800000, 3300000, 3800000, 13.2, "2025-03-01", "2026-01-15", "Bob Martinez", "Sarah Kim"),
        (2, "DFW Logistics Hub", "new_construction", "negotiation", 5500000, 4700000, None, 14.5, None, None, "Bob Martinez", None),
        # CBRE
        (3, "Chase Tower PM Contract", "service_maintenance", "completed", 180000, 140000, 180000, 22.2, "2024-01-01", "2024-12-31", "Maria Torres", "Jim Lee"),
        (3, "Fountain Place Generator Install", "generator", "won", 340000, 280000, 340000, 17.6, "2025-07-01", "2025-09-30", "Maria Torres", "Jim Lee"),
        # Lincoln Property
        (4, "The Crescent Office TI Suite 400", "tenant_improvement", "completed", 650000, 550000, 650000, 15.4, "2024-08-01", "2025-01-31", "Carlos Gutierrez", "Sarah Kim"),
        (4, "The Crescent Fire Alarm Upgrade", "fire_alarm", "qualified", 890000, None, None, None, None, None, "Carlos Gutierrez", None),
        # Trammell Crow
        (5, "Park District Mixed Use Phase 1", "new_construction", "completed", 2100000, 1800000, 2100000, 14.3, "2023-06-01", "2024-12-31", "Bob Martinez", "Sarah Kim"),
        (5, "Park District Phase 2 Electrical", "new_construction", "lead", 2800000, None, None, None, None, None, "Bob Martinez", None),
        # McCarthy
        (6, "Baylor Medical Center Wing B", "new_construction", "in_progress", 1800000, 1550000, 1800000, 13.9, "2025-01-15", "2025-12-31", "Maria Torres", "Jim Lee"),
        (6, "Children's Health Expansion", "new_construction", "lead", 2200000, None, None, None, None, None, "Maria Torres", None),
        # Stream Data Centers
        (7, "Stream DFW1 Power Distribution", "new_construction", "completed", 3200000, 2700000, 3200000, 15.6, "2024-03-01", "2025-01-31", "Carlos Gutierrez", "Sarah Kim"),
        (7, "Stream DFW2 Buildout", "new_construction", "bid_submitted", 4800000, 4100000, None, 14.6, None, None, "Carlos Gutierrez", None),
        # Dallas ISD
        (8, "Hillcrest HS Electrical Upgrade", "renovation", "in_progress", 980000, 850000, 980000, 13.3, "2025-05-01", "2025-08-15", "Maria Torres", "Jim Lee"),
        (8, "Skyline HS Gym Lighting", "energy_upgrade", "lead", 220000, None, None, None, None, None, "Maria Torres", None),
        # Marriott
        (9, "Marriott Plano Renovation", "renovation", "completed", 380000, 320000, 380000, 15.8, "2024-10-01", "2025-03-31", "Maria Torres", "Jim Lee"),
        # Amazon
        (10, "Haslet FC Electrical Expansion", "new_construction", "won", 1600000, 1380000, 1600000, 13.8, "2025-09-01", "2026-06-30", "Bob Martinez", "Sarah Kim"),
        # Kroger
        (11, "Kroger #247 Lighting Remodel", "energy_upgrade", "completed", 85000, 70000, 85000, 17.6, "2025-01-15", "2025-03-15", "Maria Torres", "Jim Lee"),
        # Hillwood — declining relationship
        (12, "Hillwood Phase 3 Infrastructure", "new_construction", "lost", 2400000, 2050000, None, None, None, None, "Carlos Gutierrez", None),
    ]

    projects = []
    for ci, name, ptype, stage, bid, cost, contract, margin, start, end, estimator, pm in projects_data:
        p = Project(
            customer_id=customers[ci].id, name=name, project_type=ptype,
            stage=stage, bid_amount=bid, estimated_cost=cost,
            contract_value=contract, estimated_margin_pct=margin,
            estimated_start_date=start, estimated_end_date=end,
            assigned_estimator=estimator, assigned_pm=pm,
            win_probability={"lead": 0.15, "qualified": 0.25, "estimating": 0.35,
                            "bid_submitted": 0.45, "negotiation": 0.65, "won": 1.0,
                            "lost": 0, "in_progress": 1.0, "completed": 1.0}.get(stage, 0.5),
            loss_reason="price" if stage == "lost" else None,
        )
        db.add(p)
        db.flush()
        projects.append(p)

    # ---- Interactions ----
    interaction_types = ["phone_call", "email", "site_visit", "meeting", "lunch", "proposal_delivery"]
    for ci, cust in enumerate(customers):
        # More interactions for top customers, fewer for smaller ones
        count = random.randint(8, 20) if ci < 3 else random.randint(3, 10)
        for _ in range(count):
            days_ago = random.randint(1, 365)
            date = (base_date + timedelta(days=365) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            itype = random.choice(interaction_types)
            contact = random.choice([c for c in contacts if c.customer_id == cust.id]) if any(c.customer_id == cust.id for c in contacts) else None
            inter = Interaction(
                customer_id=cust.id,
                contact_id=contact.id if contact else None,
                interaction_type=itype,
                direction=random.choice(["inbound", "outbound"]),
                subject=f"{itype.replace('_', ' ').title()} with {cust.name}",
                summary=f"Discussed ongoing projects and upcoming opportunities.",
                interaction_date=date,
                logged_by=random.choice(["Bob Martinez", "Carlos Gutierrez", "Maria Torres"]),
                follow_up_date=(datetime.strptime(date, "%Y-%m-%d") + timedelta(days=random.randint(7, 30))).strftime("%Y-%m-%d") if random.random() > 0.6 else None,
                follow_up_completed=random.choice([0, 1]) if random.random() > 0.6 else 0,
            )
            db.add(inter)

    # Add some complaint interactions for Hillwood (at-risk)
    for i in range(3):
        db.add(Interaction(
            customer_id=customers[12].id,
            interaction_type="complaint",
            direction="inbound",
            subject="Complaint about response time",
            summary="Customer expressed frustration with service response times.",
            interaction_date=(base_date + timedelta(days=200 + i * 30)).strftime("%Y-%m-%d"),
            logged_by="Carlos Gutierrez",
        ))

    # ---- Service Records ----
    service_types = ["scheduled_maintenance", "troubleshooting", "lighting_repair", "wiring_repair", "inspection"]
    for ci in [0, 1, 2, 3, 7, 8, 11]:  # Customers with service history
        count = random.randint(3, 8)
        for _ in range(count):
            days_ago = random.randint(1, 400)
            sr = ServiceRecord(
                customer_id=customers[ci].id,
                service_type=random.choice(service_types),
                status=random.choice(["completed", "invoiced"]),
                priority=random.choice(["normal", "normal", "high"]),
                description="Routine service work",
                completed_date=(base_date + timedelta(days=365) - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                assigned_technician=random.choice(["Mike Torres", "Dave Kim", "Chris Patel"]),
                hours_worked=random.uniform(2, 16),
                material_cost=random.uniform(200, 3000),
                labor_cost=random.uniform(400, 4000),
                total_invoice=random.uniform(800, 8000),
                customer_satisfaction=random.choice([4, 4, 5, 5, 5, 3]),
            )
            db.add(sr)

    # Warranty/emergency for Hillwood (bad experience)
    for _ in range(2):
        db.add(ServiceRecord(
            customer_id=customers[12].id,
            service_type="emergency_call",
            status="completed",
            priority="emergency",
            description="Emergency power outage at construction site",
            completed_date=(base_date + timedelta(days=random.randint(100, 300))).strftime("%Y-%m-%d"),
            assigned_technician="Dave Kim",
            hours_worked=12,
            material_cost=1500,
            labor_cost=3600,
            total_invoice=5100,
            customer_satisfaction=2,
        ))

    # ---- Maintenance Contracts ----
    contracts = [
        (1, "Hines Portfolio PM", "preventive_maintenance", 180000, "2025-01-01", "2025-12-31", "2025-11-01", "quarterly"),
        (3, "CBRE Chase Tower", "full_service", 96000, "2025-01-01", "2025-12-31", "2025-10-15", "monthly"),
        (7, "Stream DFW1 Critical Systems", "full_service", 240000, "2025-01-01", "2025-12-31", "2025-10-01", "monthly"),
        (8, "Dallas ISD Annual Inspections", "inspection", 45000, "2025-08-01", "2026-07-31", "2026-05-01", "semi_annual"),
        (11, "Kroger Store PM", "preventive_maintenance", 24000, "2025-03-01", "2026-02-28", "2025-12-01", "quarterly"),
    ]
    for ci, name, ctype, value, start, end, renewal, freq in contracts:
        db.add(MaintenanceContract(
            customer_id=customers[ci].id, name=name, contract_type=ctype,
            annual_value=value, start_date=start, end_date=end,
            renewal_date=renewal, status="active", visit_frequency=freq,
        ))

    # ---- Revenue Records (FY2024 and FY2025) ----
    # This creates the concentration risk scenario:
    # Top 3 (Turner, Hines, Prologis) = ~55% of revenue
    revenue_data = [
        # FY2024
        (0, 2024, [(1, 700000), (2, 750000), (3, 680000), (4, 670000)]),  # Turner: $2.8M
        (1, 2024, [(1, 240000), (2, 230000), (3, 250000), (4, 230000)]),  # Hines: $950K
        (2, 2024, [(1, 1050000), (2, 1100000), (3, 1050000), (4, 1000000)]),  # Prologis: $4.2M
        (3, 2024, [(1, 45000), (2, 45000), (3, 45000), (4, 45000)]),  # CBRE: $180K
        (4, 2024, [(3, 325000), (4, 325000)]),  # Lincoln: $650K
        (5, 2024, [(1, 525000), (2, 525000), (3, 525000), (4, 525000)]),  # Trammell: $2.1M
        (6, 2024, [(4, 200000)]),  # McCarthy: $200K (new start)
        (7, 2024, [(1, 800000), (2, 800000), (3, 800000), (4, 800000)]),  # Stream: $3.2M
        (8, 2024, [(3, 200000), (4, 200000)]),  # Dallas ISD: $400K
        (9, 2024, [(4, 380000)]),  # Marriott: $380K
        (12, 2024, [(1, 400000), (2, 400000)]),  # Hillwood: $800K (declining)
        # FY2025 (partial)
        (0, 2025, [(1, 400000), (2, 380000)]),  # Turner: tracking to $1.5M
        (1, 2025, [(1, 350000), (2, 370000)]),  # Hines: growing
        (2, 2025, [(1, 950000), (2, 950000)]),  # Prologis: strong
        (3, 2025, [(1, 130000), (2, 110000)]),  # CBRE: growing with generator
        (6, 2025, [(1, 450000), (2, 450000)]),  # McCarthy: ramping up
        (7, 2025, [(1, 200000)]),  # Stream: between projects
        (8, 2025, [(1, 250000), (2, 250000)]),  # Dallas ISD: HS upgrade
        (10, 2025, [(1, 200000)]),  # Amazon: starting
        (11, 2025, [(1, 85000)]),  # Kroger: small
    ]

    for ci, year, quarters in revenue_data:
        for quarter, amount in quarters:
            db.add(RevenueRecord(
                customer_id=customers[ci].id,
                revenue_type="project",
                amount=amount,
                cost=amount * random.uniform(0.82, 0.88),
                invoice_date=f"{year}-{(quarter - 1) * 3 + 2:02d}-15",
                fiscal_year=year,
                fiscal_quarter=quarter,
            ))

    # Maintenance contract revenue
    for ci, _, _, value, _, _, _, _ in contracts:
        quarterly = value / 4
        for q in range(1, 3):  # Q1 and Q2 2025
            db.add(RevenueRecord(
                customer_id=customers[ci].id,
                revenue_type="maintenance_contract",
                amount=quarterly,
                cost=quarterly * 0.65,
                invoice_date=f"2025-{(q - 1) * 3 + 1:02d}-01",
                fiscal_year=2025,
                fiscal_quarter=q,
            ))

    # ---- Prospects (growth targets) ----
    prospects_data = [
        ("JLL Property Management", "property_manager", "commercial_office", 2000000, "Dallas", "TX",
         "Karen White", "Regional Director", "k.white@jll.example.com", "(214) 555-2001",
         "researching", "Bob Martinez", 75),
        ("Cushman & Wakefield", "facility_manager", "commercial_office", 1500000, "Dallas", "TX",
         "Tom Harris", "Account Director", "t.harris@cushwake.example.com", "(214) 555-2002",
         "outreach_started", "Carlos Gutierrez", 70),
        ("Medical City Healthcare", "property_owner", "healthcare", 3000000, "Dallas", "TX",
         "Dr. Susan Lee", "VP Facilities", "s.lee@medcity.example.com", "(214) 555-2003",
         "identified", "Maria Torres", 80),
        ("Allen ISD", "government", "education", 800000, "Allen", "TX",
         "Mark Johnson", "Facilities Director", "m.johnson@allenisd.example.com", "(214) 555-2004",
         "meeting_scheduled", "Maria Torres", 60),
        ("Tesla Gigafactory Texas", "industrial", "industrial", 5000000, "Austin", "TX",
         "Ryan Chang", "Construction Director", "r.chang@tesla.example.com", "(512) 555-2005",
         "identified", "Bob Martinez", 85),
        ("Digital Realty Trust", "property_owner", "data_center", 4000000, "Dallas", "TX",
         "Amy Martinez", "VP Data Center Ops", "a.martinez@digitalrealty.example.com", "(214) 555-2006",
         "researching", "Carlos Gutierrez", 82),
        ("Whole Foods Market", "facility_manager", "retail", 500000, "Austin", "TX",
         "Jake Cooper", "Regional Facilities", "j.cooper@wholefoods.example.com", "(512) 555-2007",
         "outreach_started", "Maria Torres", 40),
        ("UT Southwestern Medical", "government", "healthcare", 2500000, "Dallas", "TX",
         "Patricia Gomez", "Director of Engineering", "p.gomez@utsw.example.com", "(214) 555-2008",
         "proposal_pending", "Bob Martinez", 78),
    ]

    for name, ptype, segment, spend, city, state, cname, ctitle, cemail, cphone, status, assigned, priority in prospects_data:
        db.add(Prospect(
            company_name=name, prospect_type=ptype, industry_segment=segment,
            estimated_annual_spend=spend, city=city, state=state,
            key_contact_name=cname, key_contact_title=ctitle,
            key_contact_email=cemail, key_contact_phone=cphone,
            outreach_status=status, assigned_to=assigned, priority_score=priority,
            next_action="Schedule introductory meeting" if status == "identified" else "Follow up on proposal",
            next_action_date=(base_date + timedelta(days=random.randint(370, 400))).strftime("%Y-%m-%d"),
        ))

    db.commit()
    db.close()
    print("Seed data loaded successfully!")
    print(f"  - {len(customers_data)} customers")
    print(f"  - {len(contacts_data)} contacts")
    print(f"  - {len(projects_data)} projects")
    print(f"  - {len(prospects_data)} prospects")
    print(f"  - Revenue records, service records, and contracts created")
    print(f"\nConcentration risk scenario:")
    print(f"  - Top 3 customers (Turner, Hines, Prologis) represent ~55% of FY2024 revenue")
    print(f"  - Hillwood is an at-risk/declining customer")
    print(f"  - 8 growth prospects in pipeline")


if __name__ == "__main__":
    seed()
