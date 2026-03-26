from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from db.database import Base


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False, unique=True)
    customer_type = Column(Text, nullable=False)  # general_contractor, property_owner, property_manager, developer, facility_manager, government, industrial, other
    status = Column(Text, nullable=False, default="active")  # prospect, active, inactive, former
    industry_segment = Column(Text)  # commercial_office, industrial, retail, healthcare, education, data_center, hospitality, government, residential_multi, mixed_use
    address_line1 = Column(Text)
    address_line2 = Column(Text)
    city = Column(Text)
    state = Column(Text)
    zip_code = Column(Text)
    phone = Column(Text)
    email = Column(Text)
    website = Column(Text)
    annual_revenue_potential = Column(Float)
    relationship_score = Column(Float, default=0.0)
    relationship_tier = Column(Text, default="bronze")  # bronze, silver, gold, platinum
    source = Column(Text)  # referral, bid_board, cold_outreach, repeat, website, trade_show
    notes = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)
    updated_at = Column(Text, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    contacts = relationship("Contact", back_populates="customer", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="customer", cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="customer", cascade="all, delete-orphan")
    service_records = relationship("ServiceRecord", back_populates="customer", cascade="all, delete-orphan")
    maintenance_contracts = relationship("MaintenanceContract", back_populates="customer", cascade="all, delete-orphan")
    revenue_records = relationship("RevenueRecord", back_populates="customer", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------
class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    title = Column(Text)
    role_type = Column(Text)  # decision_maker, influencer, technical, procurement, end_user, gatekeeper
    email = Column(Text)
    phone = Column(Text)
    mobile = Column(Text)
    is_primary = Column(Integer, default=0)
    relationship_owner = Column(Text)
    last_contact_date = Column(Text)
    preferred_contact_method = Column(Text)  # email, phone, in_person, text
    notes = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)
    updated_at = Column(Text, nullable=False, default=_utcnow, onupdate=_utcnow)

    customer = relationship("Customer", back_populates="contacts")
    interactions = relationship("Interaction", back_populates="contact")


# ---------------------------------------------------------------------------
# Projects / Pipeline
# ---------------------------------------------------------------------------
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    project_type = Column(Text, nullable=False)  # new_construction, renovation, tenant_improvement, service_maintenance, design_build, emergency, preventive_maintenance, energy_upgrade, ev_charging, fire_alarm, low_voltage, generator
    stage = Column(Text, nullable=False, default="lead")  # lead, qualified, estimating, bid_submitted, negotiation, won, lost, in_progress, completed, cancelled
    priority = Column(Text, default="medium")  # low, medium, high, critical
    bid_amount = Column(Float)
    estimated_cost = Column(Float)
    contract_value = Column(Float)
    estimated_margin_pct = Column(Float)
    actual_margin_pct = Column(Float)
    general_contractor = Column(Text)
    project_address = Column(Text)
    city = Column(Text)
    state = Column(Text)
    square_footage = Column(Integer)
    bid_due_date = Column(Text)
    estimated_start_date = Column(Text)
    estimated_end_date = Column(Text)
    actual_start_date = Column(Text)
    actual_end_date = Column(Text)
    win_probability = Column(Float, default=0.5)
    loss_reason = Column(Text)  # price, relationship, scope, schedule, competitor, cancelled, other
    assigned_estimator = Column(Text)
    assigned_pm = Column(Text)
    notes = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)
    updated_at = Column(Text, nullable=False, default=_utcnow, onupdate=_utcnow)

    customer = relationship("Customer", back_populates="projects")
    interactions = relationship("Interaction", back_populates="project")
    service_records = relationship("ServiceRecord", back_populates="project")
    revenue_records = relationship("RevenueRecord", back_populates="project")


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------
class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    interaction_type = Column(Text, nullable=False)  # phone_call, email, site_visit, meeting, lunch, trade_show, proposal_delivery, change_order, complaint, compliment, referral_given, referral_received
    direction = Column(Text)  # inbound, outbound
    subject = Column(Text)
    summary = Column(Text)
    outcome = Column(Text)
    interaction_date = Column(Text, nullable=False)
    follow_up_date = Column(Text)
    follow_up_completed = Column(Integer, default=0)
    logged_by = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)

    customer = relationship("Customer", back_populates="interactions")
    contact = relationship("Contact", back_populates="interactions")
    project = relationship("Project", back_populates="interactions")


# ---------------------------------------------------------------------------
# Service Records
# ---------------------------------------------------------------------------
class ServiceRecord(Base):
    __tablename__ = "service_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    service_type = Column(Text, nullable=False)  # emergency_call, scheduled_maintenance, warranty_repair, troubleshooting, inspection, panel_upgrade, lighting_repair, wiring_repair
    status = Column(Text, nullable=False, default="open")  # open, scheduled, in_progress, completed, invoiced, cancelled
    priority = Column(Text, default="normal")  # low, normal, high, emergency
    description = Column(Text)
    location = Column(Text)
    scheduled_date = Column(Text)
    completed_date = Column(Text)
    assigned_technician = Column(Text)
    hours_worked = Column(Float)
    material_cost = Column(Float)
    labor_cost = Column(Float)
    total_invoice = Column(Float)
    is_warranty = Column(Integer, default=0)
    customer_satisfaction = Column(Integer)  # 1-5
    resolution_notes = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)
    updated_at = Column(Text, nullable=False, default=_utcnow, onupdate=_utcnow)

    customer = relationship("Customer", back_populates="service_records")
    project = relationship("Project", back_populates="service_records")
    revenue_records = relationship("RevenueRecord", back_populates="service_record")


# ---------------------------------------------------------------------------
# Maintenance Contracts
# ---------------------------------------------------------------------------
class MaintenanceContract(Base):
    __tablename__ = "maintenance_contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    name = Column(Text, nullable=False)
    contract_type = Column(Text)  # preventive_maintenance, full_service, emergency_only, inspection
    annual_value = Column(Float)
    start_date = Column(Text, nullable=False)
    end_date = Column(Text)
    renewal_date = Column(Text)
    auto_renew = Column(Integer, default=0)
    status = Column(Text, default="active")  # active, expired, cancelled, pending_renewal
    scope_description = Column(Text)
    visit_frequency = Column(Text)  # monthly, quarterly, semi_annual, annual
    notes = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)
    updated_at = Column(Text, nullable=False, default=_utcnow, onupdate=_utcnow)

    customer = relationship("Customer", back_populates="maintenance_contracts")


# ---------------------------------------------------------------------------
# Revenue Records
# ---------------------------------------------------------------------------
class RevenueRecord(Base):
    __tablename__ = "revenue_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    service_record_id = Column(Integer, ForeignKey("service_records.id"), nullable=True)
    revenue_type = Column(Text, nullable=False)  # project, service, maintenance_contract, change_order
    amount = Column(Float, nullable=False)
    cost = Column(Float)
    invoice_date = Column(Text, nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer, nullable=False)
    notes = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)

    customer = relationship("Customer", back_populates="revenue_records")
    project = relationship("Project", back_populates="revenue_records")
    service_record = relationship("ServiceRecord", back_populates="revenue_records")


# ---------------------------------------------------------------------------
# Prospects
# ---------------------------------------------------------------------------
class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(Text, nullable=False)
    industry_segment = Column(Text)
    prospect_type = Column(Text)
    estimated_annual_spend = Column(Float)
    city = Column(Text)
    state = Column(Text)
    website = Column(Text)
    key_contact_name = Column(Text)
    key_contact_title = Column(Text)
    key_contact_email = Column(Text)
    key_contact_phone = Column(Text)
    outreach_status = Column(Text, default="identified")  # identified, researching, outreach_started, meeting_scheduled, proposal_pending, converted, not_interested, dormant
    assigned_to = Column(Text)
    priority_score = Column(Float, default=0.0)
    conversion_notes = Column(Text)
    next_action = Column(Text)
    next_action_date = Column(Text)
    converted_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    created_at = Column(Text, nullable=False, default=_utcnow)
    updated_at = Column(Text, nullable=False, default=_utcnow, onupdate=_utcnow)


# ---------------------------------------------------------------------------
# AI Recommendations
# ---------------------------------------------------------------------------
class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_type = Column(Text, nullable=False)  # relationship_health, next_action, bid_analysis, concentration_alert, growth_opportunity
    entity_type = Column(Text)  # customer, contact, project, prospect
    entity_id = Column(Integer)
    title = Column(Text, nullable=False)
    detail = Column(Text, nullable=False)
    priority = Column(Text, default="medium")
    status = Column(Text, default="pending")  # pending, accepted, dismissed, completed
    confidence = Column(Float)
    generated_at = Column(Text, nullable=False, default=_utcnow)
    acted_on_at = Column(Text)
    acted_on_by = Column(Text)
