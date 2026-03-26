/**
 * Customer list and detail pages.
 */
async function renderCustomers(container) {
    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Customers</h1>
            <button class="btn btn-primary" onclick="openCustomerForm()">+ New Customer</button>
        </div>
        <div class="filters">
            <select id="filter-status" onchange="reloadCustomers()">
                <option value="">All Statuses</option>
                <option value="active" selected>Active</option>
                <option value="prospect">Prospect</option>
                <option value="inactive">Inactive</option>
                <option value="former">Former</option>
            </select>
            <select id="filter-type" onchange="reloadCustomers()">
                <option value="">All Types</option>
                <option value="general_contractor">General Contractor</option>
                <option value="property_owner">Property Owner</option>
                <option value="property_manager">Property Manager</option>
                <option value="developer">Developer</option>
                <option value="facility_manager">Facility Manager</option>
                <option value="government">Government</option>
                <option value="industrial">Industrial</option>
            </select>
            <input type="text" id="filter-search" placeholder="Search name..." oninput="reloadCustomers()">
        </div>
        <div class="card">
            <div class="card-body">
                <table>
                    <thead><tr>
                        <th>Name</th><th>Type</th><th>Segment</th><th>Tier</th><th>Score</th><th>Status</th>
                    </tr></thead>
                    <tbody id="customers-tbody"><tr><td colspan="6" class="loading-text"><span class="spinner"></span> Loading...</td></tr></tbody>
                </table>
            </div>
        </div>
    `;
    reloadCustomers();
}

async function reloadCustomers() {
    const status = document.getElementById('filter-status')?.value || '';
    const type = document.getElementById('filter-type')?.value || '';
    const search = document.getElementById('filter-search')?.value || '';
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (type) params.set('customer_type', type);
    if (search) params.set('search', search);

    const customers = await API.get(`/api/customers?${params}`);
    const tbody = document.getElementById('customers-tbody');
    if (!tbody) return;

    tbody.innerHTML = customers.length === 0
        ? '<tr><td colspan="6" class="text-muted">No customers found.</td></tr>'
        : customers.map(c => `
            <tr class="clickable" onclick="location.hash='#/customers/${c.id}'">
                <td><strong>${c.name}</strong></td>
                <td>${(c.customer_type || '').replace(/_/g, ' ')}</td>
                <td>${(c.industry_segment || '').replace(/_/g, ' ')}</td>
                <td>${tierBadge(c.relationship_tier)}</td>
                <td>${c.relationship_score || 0}</td>
                <td>${badge(c.status)}</td>
            </tr>
        `).join('');
}

async function renderCustomerDetail(container, id) {
    container.innerHTML = '<div class="loading-text"><span class="spinner"></span> Loading customer...</div>';

    const [customer, interactions, serviceRecords, contracts] = await Promise.all([
        API.get(`/api/customers/${id}`),
        API.get(`/api/interactions?customer_id=${id}`),
        API.get(`/api/service/records?customer_id=${id}`),
        API.get(`/api/service/contracts?customer_id=${id}`),
    ]);

    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">${customer.name}</h1>
            <div class="flex gap-8">
                <button class="btn btn-ai" onclick="runRelationshipAI(${id})">AI Relationship Analysis</button>
                <button class="btn btn-ai" onclick="runNextActionsAI(${id})">AI Next Actions</button>
                <button class="btn btn-secondary" onclick="openEditCustomer(${id})">Edit</button>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-label">Relationship Score</div><div class="kpi-value">${customer.relationship_score || 0}</div></div>
            <div class="kpi-card"><div class="kpi-label">Tier</div><div class="kpi-value">${tierBadge(customer.relationship_tier)}</div></div>
            <div class="kpi-card"><div class="kpi-label">Total Revenue</div><div class="kpi-value">${formatCurrency(customer.total_revenue)}</div></div>
            <div class="kpi-card"><div class="kpi-label">Status</div><div class="kpi-value">${badge(customer.status)}</div></div>
        </div>

        <div class="grid-2">
            <div class="card">
                <div class="card-header">Details</div>
                <div class="card-body">
                    <table>
                        <tr><td class="text-muted">Type</td><td>${(customer.customer_type || '').replace(/_/g, ' ')}</td></tr>
                        <tr><td class="text-muted">Segment</td><td>${(customer.industry_segment || '').replace(/_/g, ' ')}</td></tr>
                        <tr><td class="text-muted">Address</td><td>${[customer.address_line1, customer.city, customer.state, customer.zip_code].filter(Boolean).join(', ')}</td></tr>
                        <tr><td class="text-muted">Phone</td><td>${customer.phone || '—'}</td></tr>
                        <tr><td class="text-muted">Email</td><td>${customer.email || '—'}</td></tr>
                        <tr><td class="text-muted">Website</td><td>${customer.website || '—'}</td></tr>
                        <tr><td class="text-muted">Source</td><td>${(customer.source || '').replace(/_/g, ' ')}</td></tr>
                        <tr><td class="text-muted">Revenue Potential</td><td>${formatCurrency(customer.annual_revenue_potential)}</td></tr>
                    </table>
                </div>
            </div>
            <div class="card">
                <div class="card-header">Contacts
                    <button class="btn btn-sm btn-primary" onclick="openContactForm(${id})">+ Add</button>
                </div>
                <div class="card-body">
                    ${(customer.contacts || []).length === 0 ? '<p class="text-muted">No contacts.</p>' : `
                    <table><tr><th>Name</th><th>Title</th><th>Role</th><th>Primary</th></tr>
                    ${customer.contacts.map(c => `
                        <tr>
                            <td>${c.first_name} ${c.last_name}</td>
                            <td>${c.title || '—'}</td>
                            <td>${(c.role_type || '').replace(/_/g, ' ')}</td>
                            <td>${c.is_primary ? 'Yes' : ''}</td>
                        </tr>
                    `).join('')}
                    </table>`}
                </div>
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <div class="card-header">Projects
                    <button class="btn btn-sm btn-primary" onclick="openProjectForm(${id})">+ Add</button>
                </div>
                <div class="card-body">
                    ${(customer.recent_projects || []).length === 0 ? '<p class="text-muted">No projects.</p>' : `
                    <table><tr><th>Name</th><th>Type</th><th>Stage</th><th>Value</th></tr>
                    ${customer.recent_projects.map(p => `
                        <tr>
                            <td>${p.name}</td>
                            <td>${(p.project_type || '').replace(/_/g, ' ')}</td>
                            <td>${badge(p.stage)}</td>
                            <td>${formatCurrency(p.contract_value || p.bid_amount)}</td>
                        </tr>
                    `).join('')}
                    </table>`}
                </div>
            </div>
            <div class="card">
                <div class="card-header">Recent Interactions
                    <button class="btn btn-sm btn-primary" onclick="openInteractionForm(${id})">+ Log</button>
                </div>
                <div class="card-body">
                    ${interactions.length === 0 ? '<p class="text-muted">No interactions logged.</p>' : `
                    <table><tr><th>Date</th><th>Type</th><th>Subject</th></tr>
                    ${interactions.slice(0, 10).map(i => `
                        <tr>
                            <td>${i.interaction_date?.substring(0, 10) || ''}</td>
                            <td>${(i.interaction_type || '').replace(/_/g, ' ')}</td>
                            <td>${i.subject || i.summary || '—'}</td>
                        </tr>
                    `).join('')}
                    </table>`}
                </div>
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <div class="card-header">Service History</div>
                <div class="card-body">
                    ${serviceRecords.length === 0 ? '<p class="text-muted">No service records.</p>' : `
                    <table><tr><th>Type</th><th>Status</th><th>Satisfaction</th><th>Invoice</th></tr>
                    ${serviceRecords.slice(0, 10).map(s => `
                        <tr>
                            <td>${(s.service_type || '').replace(/_/g, ' ')}</td>
                            <td>${badge(s.status)}</td>
                            <td>${s.customer_satisfaction ? s.customer_satisfaction + '/5' : '—'}</td>
                            <td>${formatCurrency(s.total_invoice)}</td>
                        </tr>
                    `).join('')}
                    </table>`}
                </div>
            </div>
            <div class="card">
                <div class="card-header">Maintenance Contracts</div>
                <div class="card-body">
                    ${contracts.length === 0 ? '<p class="text-muted">No contracts.</p>' : `
                    <table><tr><th>Name</th><th>Type</th><th>Value</th><th>Renewal</th></tr>
                    ${contracts.map(c => `
                        <tr>
                            <td>${c.name}</td>
                            <td>${(c.contract_type || '').replace(/_/g, ' ')}</td>
                            <td>${formatCurrency(c.annual_value)}/yr</td>
                            <td>${c.renewal_date || '—'}</td>
                        </tr>
                    `).join('')}
                    </table>`}
                </div>
            </div>
        </div>
    `;
}

function openCustomerForm() {
    openModal(`
        <div class="modal-title">New Customer</div>
        <form onsubmit="submitCustomer(event)">
            <div class="form-row">
                <div class="form-group"><label>Company Name *</label><input name="name" required></div>
                <div class="form-group"><label>Type *</label>
                    <select name="customer_type" required>
                        <option value="general_contractor">General Contractor</option>
                        <option value="property_owner">Property Owner</option>
                        <option value="property_manager">Property Manager</option>
                        <option value="developer">Developer</option>
                        <option value="facility_manager">Facility Manager</option>
                        <option value="government">Government</option>
                        <option value="industrial">Industrial</option>
                        <option value="other">Other</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Industry Segment</label>
                    <select name="industry_segment">
                        <option value="">—</option>
                        <option value="commercial_office">Commercial Office</option>
                        <option value="industrial">Industrial</option>
                        <option value="retail">Retail</option>
                        <option value="healthcare">Healthcare</option>
                        <option value="education">Education</option>
                        <option value="data_center">Data Center</option>
                        <option value="hospitality">Hospitality</option>
                        <option value="government">Government</option>
                        <option value="residential_multi">Residential Multi</option>
                        <option value="mixed_use">Mixed Use</option>
                    </select>
                </div>
                <div class="form-group"><label>Source</label>
                    <select name="source">
                        <option value="">—</option>
                        <option value="referral">Referral</option>
                        <option value="bid_board">Bid Board</option>
                        <option value="cold_outreach">Cold Outreach</option>
                        <option value="repeat">Repeat</option>
                        <option value="website">Website</option>
                        <option value="trade_show">Trade Show</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>City</label><input name="city"></div>
                <div class="form-group"><label>State</label><input name="state"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Phone</label><input name="phone"></div>
                <div class="form-group"><label>Email</label><input name="email" type="email"></div>
            </div>
            <div class="form-group"><label>Annual Revenue Potential ($)</label><input name="annual_revenue_potential" type="number"></div>
            <div class="form-group"><label>Notes</label><textarea name="notes"></textarea></div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Create</button>
            </div>
        </form>
    `);
}

async function submitCustomer(e) {
    e.preventDefault();
    const form = e.target;
    const data = Object.fromEntries(new FormData(form));
    if (data.annual_revenue_potential) data.annual_revenue_potential = parseFloat(data.annual_revenue_potential);
    else delete data.annual_revenue_potential;
    // Remove empty strings
    Object.keys(data).forEach(k => { if (data[k] === '') delete data[k]; });
    await API.post('/api/customers', data);
    closeModal();
    reloadCustomers();
}

async function openEditCustomer(id) {
    const c = await API.get(`/api/customers/${id}`);
    openModal(`
        <div class="modal-title">Edit Customer</div>
        <form onsubmit="submitEditCustomer(event, ${id})">
            <div class="form-row">
                <div class="form-group"><label>Company Name *</label><input name="name" value="${c.name || ''}" required></div>
                <div class="form-group"><label>Type *</label>
                    <select name="customer_type" required>
                        ${['general_contractor','property_owner','property_manager','developer','facility_manager','government','industrial','other'].map(t =>
                            `<option value="${t}" ${c.customer_type === t ? 'selected' : ''}>${t.replace(/_/g, ' ')}</option>`
                        ).join('')}
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Phone</label><input name="phone" value="${c.phone || ''}"></div>
                <div class="form-group"><label>Email</label><input name="email" value="${c.email || ''}"></div>
            </div>
            <div class="form-group"><label>Notes</label><textarea name="notes">${c.notes || ''}</textarea></div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save</button>
            </div>
        </form>
    `);
}

async function submitEditCustomer(e, id) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    Object.keys(data).forEach(k => { if (data[k] === '') delete data[k]; });
    await API.put(`/api/customers/${id}`, data);
    closeModal();
    location.hash = `#/customers/${id}`;
    navigate();
}

function openContactForm(customerId) {
    openModal(`
        <div class="modal-title">Add Contact</div>
        <form onsubmit="submitContact(event, ${customerId})">
            <div class="form-row">
                <div class="form-group"><label>First Name *</label><input name="first_name" required></div>
                <div class="form-group"><label>Last Name *</label><input name="last_name" required></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Title</label><input name="title"></div>
                <div class="form-group"><label>Role</label>
                    <select name="role_type">
                        <option value="">—</option>
                        <option value="decision_maker">Decision Maker</option>
                        <option value="influencer">Influencer</option>
                        <option value="technical">Technical</option>
                        <option value="procurement">Procurement</option>
                        <option value="end_user">End User</option>
                        <option value="gatekeeper">Gatekeeper</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Email</label><input name="email" type="email"></div>
                <div class="form-group"><label>Phone</label><input name="phone"></div>
            </div>
            <div class="form-group"><label><input type="checkbox" name="is_primary" value="1"> Primary Contact</label></div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Contact</button>
            </div>
        </form>
    `);
}

async function submitContact(e, customerId) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.customer_id = customerId;
    data.is_primary = data.is_primary ? 1 : 0;
    Object.keys(data).forEach(k => { if (data[k] === '') delete data[k]; });
    await API.post('/api/contacts', data);
    closeModal();
    navigate();
}

function openProjectForm(customerId) {
    openModal(`
        <div class="modal-title">New Project</div>
        <form onsubmit="submitProject(event, ${customerId})">
            <div class="form-group"><label>Project Name *</label><input name="name" required></div>
            <div class="form-row">
                <div class="form-group"><label>Type *</label>
                    <select name="project_type" required>
                        <option value="new_construction">New Construction</option>
                        <option value="renovation">Renovation</option>
                        <option value="tenant_improvement">Tenant Improvement</option>
                        <option value="design_build">Design Build</option>
                        <option value="energy_upgrade">Energy Upgrade</option>
                        <option value="ev_charging">EV Charging</option>
                        <option value="fire_alarm">Fire Alarm</option>
                        <option value="low_voltage">Low Voltage</option>
                        <option value="generator">Generator</option>
                    </select>
                </div>
                <div class="form-group"><label>Stage</label>
                    <select name="stage">
                        <option value="lead" selected>Lead</option>
                        <option value="qualified">Qualified</option>
                        <option value="estimating">Estimating</option>
                        <option value="bid_submitted">Bid Submitted</option>
                        <option value="negotiation">Negotiation</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Bid Amount ($)</label><input name="bid_amount" type="number"></div>
                <div class="form-group"><label>Bid Due Date</label><input name="bid_due_date" type="date"></div>
            </div>
            <div class="form-group"><label>Description</label><textarea name="description"></textarea></div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Create Project</button>
            </div>
        </form>
    `);
}

async function submitProject(e, customerId) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.customer_id = customerId;
    if (data.bid_amount) data.bid_amount = parseFloat(data.bid_amount);
    else delete data.bid_amount;
    Object.keys(data).forEach(k => { if (data[k] === '') delete data[k]; });
    await API.post('/api/projects', data);
    closeModal();
    navigate();
}

function openInteractionForm(customerId) {
    const today = new Date().toISOString().slice(0, 10);
    openModal(`
        <div class="modal-title">Log Interaction</div>
        <form onsubmit="submitInteraction(event, ${customerId})">
            <div class="form-row">
                <div class="form-group"><label>Type *</label>
                    <select name="interaction_type" required>
                        <option value="phone_call">Phone Call</option>
                        <option value="email">Email</option>
                        <option value="site_visit">Site Visit</option>
                        <option value="meeting">Meeting</option>
                        <option value="lunch">Lunch</option>
                        <option value="proposal_delivery">Proposal Delivery</option>
                        <option value="trade_show">Trade Show</option>
                    </select>
                </div>
                <div class="form-group"><label>Date *</label><input name="interaction_date" type="date" value="${today}" required></div>
            </div>
            <div class="form-group"><label>Subject</label><input name="subject"></div>
            <div class="form-group"><label>Summary</label><textarea name="summary"></textarea></div>
            <div class="form-group"><label>Follow-up Date</label><input name="follow_up_date" type="date"></div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Log Interaction</button>
            </div>
        </form>
    `);
}

async function submitInteraction(e, customerId) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.customer_id = customerId;
    Object.keys(data).forEach(k => { if (data[k] === '') delete data[k]; });
    await API.post('/api/interactions', data);
    closeModal();
    navigate();
}

async function runNextActionsAI(customerId) {
    openModal('<div class="loading-text"><span class="spinner"></span> Generating next-action recommendations...</div>');
    try {
        const result = await API.post(`/api/ai/next-actions/${customerId}`, {});
        openModal(`
            <div class="modal-title">Next Actions: ${result.customer_name || ''}</div>
            ${result.account_strategy ? `<p class="text-muted mb-12">${result.account_strategy}</p>` : ''}
            ${(result.actions || []).map(a => `
                <div class="ai-card">
                    <div class="ai-card-title">${badge(a.priority)} ${a.action}</div>
                    <div class="ai-card-body">${a.reasoning || ''}</div>
                    <div class="text-sm text-muted mt-8">Timeline: ${a.timeline || '—'} | Owner: ${a.owner_suggestion || '—'}</div>
                </div>
            `).join('')}
            <div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Close</button></div>
        `);
    } catch (e) {
        openModal(`<div class="modal-title">AI Unavailable</div><p>${e.message}</p><div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Close</button></div>`);
    }
}
