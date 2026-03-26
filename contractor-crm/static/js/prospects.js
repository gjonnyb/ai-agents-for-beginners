/**
 * Prospects page — growth targeting and conversion.
 */
async function renderProspects(container) {
    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Growth Prospects</h1>
            <div class="flex gap-8">
                <button class="btn btn-ai" onclick="runGrowthAI()">AI Growth Priorities</button>
                <button class="btn btn-primary" onclick="openProspectForm()">+ New Prospect</button>
            </div>
        </div>
        <div class="filters">
            <select id="prospect-status-filter" onchange="reloadProspects()">
                <option value="">All Statuses</option>
                <option value="identified">Identified</option>
                <option value="researching">Researching</option>
                <option value="outreach_started">Outreach Started</option>
                <option value="meeting_scheduled">Meeting Scheduled</option>
                <option value="proposal_pending">Proposal Pending</option>
            </select>
            <select id="prospect-segment-filter" onchange="reloadProspects()">
                <option value="">All Segments</option>
                <option value="commercial_office">Commercial Office</option>
                <option value="industrial">Industrial</option>
                <option value="retail">Retail</option>
                <option value="healthcare">Healthcare</option>
                <option value="education">Education</option>
                <option value="data_center">Data Center</option>
                <option value="hospitality">Hospitality</option>
                <option value="government">Government</option>
            </select>
        </div>
        <div class="card">
            <div class="card-body">
                <table>
                    <thead><tr>
                        <th>Company</th><th>Type</th><th>Segment</th><th>Est. Spend</th><th>Status</th><th>Priority</th><th>Assigned</th><th></th>
                    </tr></thead>
                    <tbody id="prospects-tbody"><tr><td colspan="8" class="loading-text"><span class="spinner"></span> Loading...</td></tr></tbody>
                </table>
            </div>
        </div>
    `;
    reloadProspects();
}

async function reloadProspects() {
    const status = document.getElementById('prospect-status-filter')?.value || '';
    const segment = document.getElementById('prospect-segment-filter')?.value || '';
    const params = new URLSearchParams();
    if (status) params.set('outreach_status', status);
    if (segment) params.set('industry_segment', segment);

    const prospects = await API.get(`/api/prospects?${params}`);
    const tbody = document.getElementById('prospects-tbody');
    if (!tbody) return;

    tbody.innerHTML = prospects.length === 0
        ? '<tr><td colspan="8" class="text-muted">No prospects found.</td></tr>'
        : prospects.map(p => `
            <tr>
                <td><strong>${p.company_name}</strong></td>
                <td>${(p.prospect_type || '').replace(/_/g, ' ')}</td>
                <td>${(p.industry_segment || '').replace(/_/g, ' ')}</td>
                <td>${formatCurrency(p.estimated_annual_spend)}</td>
                <td>${badge(p.outreach_status)}</td>
                <td>${p.priority_score || 0}</td>
                <td>${p.assigned_to || '—'}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="editProspect(${p.id})">Edit</button>
                    <button class="btn btn-sm btn-primary" onclick="convertProspect(${p.id})">Convert</button>
                </td>
            </tr>
        `).join('');
}

function openProspectForm() {
    openModal(`
        <div class="modal-title">New Prospect</div>
        <form onsubmit="submitProspect(event)">
            <div class="form-group"><label>Company Name *</label><input name="company_name" required></div>
            <div class="form-row">
                <div class="form-group"><label>Type</label>
                    <select name="prospect_type">
                        <option value="">—</option>
                        <option value="general_contractor">General Contractor</option>
                        <option value="property_owner">Property Owner</option>
                        <option value="property_manager">Property Manager</option>
                        <option value="developer">Developer</option>
                        <option value="facility_manager">Facility Manager</option>
                        <option value="government">Government</option>
                        <option value="industrial">Industrial</option>
                    </select>
                </div>
                <div class="form-group"><label>Segment</label>
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
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Estimated Annual Spend ($)</label><input name="estimated_annual_spend" type="number"></div>
                <div class="form-group"><label>Assigned To</label><input name="assigned_to"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>City</label><input name="city"></div>
                <div class="form-group"><label>State</label><input name="state"></div>
            </div>
            <h4 class="mt-16 mb-12">Key Contact</h4>
            <div class="form-row">
                <div class="form-group"><label>Name</label><input name="key_contact_name"></div>
                <div class="form-group"><label>Title</label><input name="key_contact_title"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Email</label><input name="key_contact_email" type="email"></div>
                <div class="form-group"><label>Phone</label><input name="key_contact_phone"></div>
            </div>
            <div class="form-group"><label>Next Action</label><input name="next_action"></div>
            <div class="form-group"><label>Next Action Date</label><input name="next_action_date" type="date"></div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Prospect</button>
            </div>
        </form>
    `);
}

async function submitProspect(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    if (data.estimated_annual_spend) data.estimated_annual_spend = parseFloat(data.estimated_annual_spend);
    else delete data.estimated_annual_spend;
    Object.keys(data).forEach(k => { if (data[k] === '') delete data[k]; });
    await API.post('/api/prospects', data);
    closeModal();
    reloadProspects();
}

async function editProspect(id) {
    const p = await API.get(`/api/prospects/${id}`);
    openModal(`
        <div class="modal-title">Edit Prospect</div>
        <form onsubmit="submitEditProspect(event, ${id})">
            <div class="form-group"><label>Company Name</label><input name="company_name" value="${p.company_name || ''}"></div>
            <div class="form-row">
                <div class="form-group"><label>Status</label>
                    <select name="outreach_status">
                        ${['identified','researching','outreach_started','meeting_scheduled','proposal_pending','not_interested','dormant'].map(s =>
                            `<option value="${s}" ${p.outreach_status === s ? 'selected' : ''}>${s.replace(/_/g, ' ')}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="form-group"><label>Priority Score</label><input name="priority_score" type="number" value="${p.priority_score || 0}"></div>
            </div>
            <div class="form-group"><label>Next Action</label><input name="next_action" value="${p.next_action || ''}"></div>
            <div class="form-group"><label>Next Action Date</label><input name="next_action_date" type="date" value="${p.next_action_date || ''}"></div>
            <div class="form-group"><label>Notes</label><textarea name="conversion_notes">${p.conversion_notes || ''}</textarea></div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save</button>
            </div>
        </form>
    `);
}

async function submitEditProspect(e, id) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    if (data.priority_score) data.priority_score = parseFloat(data.priority_score);
    Object.keys(data).forEach(k => { if (data[k] === '') delete data[k]; });
    await API.put(`/api/prospects/${id}`, data);
    closeModal();
    reloadProspects();
}

async function convertProspect(id) {
    if (!confirm('Convert this prospect to a customer? This will create a new customer and primary contact.')) return;
    try {
        const result = await API.post(`/api/prospects/${id}/convert`, {});
        alert(`Prospect converted! New customer ID: ${result.customer_id}`);
        reloadProspects();
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function runGrowthAI() {
    openModal('<div class="loading-text"><span class="spinner"></span> Analyzing growth priorities...</div>');
    try {
        const result = await API.post('/api/ai/growth-priorities', {});
        openModal(`
            <div class="modal-title">AI Growth Priorities</div>
            ${result.summary ? `<p class="text-muted mb-12">${result.summary}</p>` : ''}
            ${result.priority_prospects ? `
                <h4>Priority Prospects</h4>
                ${result.priority_prospects.map(p => `
                    <div class="ai-card">
                        <div class="ai-card-title">${badge(p.priority)} ${p.prospect_name}</div>
                        <div class="ai-card-body">${p.reasoning || ''}</div>
                        ${p.approach ? `<div class="text-sm text-muted mt-8">Approach: ${p.approach}</div>` : ''}
                    </div>
                `).join('')}
            ` : ''}
            ${result.segment_opportunities ? `<h4 class="mt-16">Segment Opportunities</h4><ul>${result.segment_opportunities.map(s => `<li>${s}</li>`).join('')}</ul>` : ''}
            ${result.strategic_recommendations ? `<h4 class="mt-16">Strategic Recommendations</h4><ul>${result.strategic_recommendations.map(r => `<li>${r}</li>`).join('')}</ul>` : ''}
            <div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Close</button></div>
        `);
    } catch (e) {
        openModal(`<div class="modal-title">AI Unavailable</div><p>${e.message}</p><div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Close</button></div>`);
    }
}
