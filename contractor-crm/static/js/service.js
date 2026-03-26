/**
 * Service page — service records and maintenance contracts.
 */
async function renderService(container) {
    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Service & Maintenance</h1>
            <button class="btn btn-primary" onclick="openServiceRecordForm()">+ New Service Record</button>
        </div>
        <div id="service-metrics" class="kpi-grid mb-12"></div>
        <div class="grid-2">
            <div class="card">
                <div class="card-header">Service Records
                    <select id="svc-status-filter" onchange="reloadServiceRecords()" style="font-size:13px;padding:4px 8px;border:1px solid #d1d5db;border-radius:4px">
                        <option value="">All</option>
                        <option value="open">Open</option>
                        <option value="scheduled">Scheduled</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                        <option value="invoiced">Invoiced</option>
                    </select>
                </div>
                <div class="card-body" id="service-records-body"><div class="loading-text"><span class="spinner"></span> Loading...</div></div>
            </div>
            <div class="card">
                <div class="card-header">Maintenance Contracts
                    <button class="btn btn-sm btn-primary" onclick="openContractForm()">+ New Contract</button>
                </div>
                <div class="card-body" id="contracts-body"><div class="loading-text"><span class="spinner"></span> Loading...</div></div>
            </div>
        </div>
        <div class="card">
            <div class="card-header">Upcoming Renewals (90 days)</div>
            <div class="card-body" id="renewals-body"><div class="loading-text"><span class="spinner"></span> Loading...</div></div>
        </div>
    `;

    const [metrics, records, contracts, renewals] = await Promise.all([
        API.get('/api/dashboard/service-metrics'),
        API.get('/api/service/records'),
        API.get('/api/service/contracts'),
        API.get('/api/service/contracts/renewals'),
    ]);

    // Metrics
    document.getElementById('service-metrics').innerHTML = `
        <div class="kpi-card"><div class="kpi-label">Total Records</div><div class="kpi-value">${metrics.total_records}</div></div>
        <div class="kpi-card"><div class="kpi-label">Completed</div><div class="kpi-value">${metrics.completed}</div></div>
        <div class="kpi-card"><div class="kpi-label">Avg Satisfaction</div><div class="kpi-value">${metrics.avg_satisfaction ? metrics.avg_satisfaction + '/5' : '—'}</div></div>
        <div class="kpi-card"><div class="kpi-label">Service Revenue</div><div class="kpi-value">${formatCurrency(metrics.total_service_revenue)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Warranty Jobs</div><div class="kpi-value">${metrics.warranty_count}</div></div>
    `;

    // Records
    renderServiceTable(records);

    // Contracts
    document.getElementById('contracts-body').innerHTML = contracts.length === 0
        ? '<p class="text-muted">No contracts.</p>'
        : `<table><tr><th>Name</th><th>Type</th><th>Annual Value</th><th>Status</th><th>Renewal</th></tr>
           ${contracts.map(c => `
               <tr>
                   <td>${c.name}</td>
                   <td>${(c.contract_type || '').replace(/_/g, ' ')}</td>
                   <td>${formatCurrency(c.annual_value)}</td>
                   <td>${badge(c.status)}</td>
                   <td>${c.renewal_date || '—'}</td>
               </tr>
           `).join('')}
           </table>`;

    // Renewals
    document.getElementById('renewals-body').innerHTML = renewals.length === 0
        ? '<p class="text-muted">No upcoming renewals.</p>'
        : `<table><tr><th>Name</th><th>Value</th><th>Renewal Date</th><th>Auto-Renew</th></tr>
           ${renewals.map(c => `
               <tr>
                   <td>${c.name}</td>
                   <td>${formatCurrency(c.annual_value)}</td>
                   <td>${c.renewal_date}</td>
                   <td>${c.auto_renew ? 'Yes' : 'No'}</td>
               </tr>
           `).join('')}
           </table>`;
}

function renderServiceTable(records) {
    const body = document.getElementById('service-records-body');
    if (!body) return;
    body.innerHTML = records.length === 0
        ? '<p class="text-muted">No records found.</p>'
        : `<table><tr><th>Type</th><th>Status</th><th>Priority</th><th>Satisfaction</th><th>Invoice</th></tr>
           ${records.map(r => `
               <tr>
                   <td>${(r.service_type || '').replace(/_/g, ' ')}</td>
                   <td>${badge(r.status)}</td>
                   <td>${badge(r.priority)}</td>
                   <td>${r.customer_satisfaction ? r.customer_satisfaction + '/5' : '—'}</td>
                   <td>${formatCurrency(r.total_invoice)}</td>
               </tr>
           `).join('')}
           </table>`;
}

async function reloadServiceRecords() {
    const status = document.getElementById('svc-status-filter')?.value || '';
    const params = status ? `?status=${status}` : '';
    const records = await API.get(`/api/service/records${params}`);
    renderServiceTable(records);
}

function openServiceRecordForm() {
    openModal(`
        <div class="modal-title">New Service Record</div>
        <form onsubmit="submitServiceRecord(event)">
            <div class="form-group"><label>Customer ID *</label><input name="customer_id" type="number" required></div>
            <div class="form-row">
                <div class="form-group"><label>Service Type *</label>
                    <select name="service_type" required>
                        <option value="emergency_call">Emergency Call</option>
                        <option value="scheduled_maintenance">Scheduled Maintenance</option>
                        <option value="warranty_repair">Warranty Repair</option>
                        <option value="troubleshooting">Troubleshooting</option>
                        <option value="inspection">Inspection</option>
                        <option value="panel_upgrade">Panel Upgrade</option>
                        <option value="lighting_repair">Lighting Repair</option>
                        <option value="wiring_repair">Wiring Repair</option>
                    </select>
                </div>
                <div class="form-group"><label>Priority</label>
                    <select name="priority">
                        <option value="normal">Normal</option>
                        <option value="low">Low</option>
                        <option value="high">High</option>
                        <option value="emergency">Emergency</option>
                    </select>
                </div>
            </div>
            <div class="form-group"><label>Description</label><textarea name="description"></textarea></div>
            <div class="form-group"><label>Scheduled Date</label><input name="scheduled_date" type="date"></div>
            <div class="form-group"><label>Assigned Technician</label><input name="assigned_technician"></div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Create</button>
            </div>
        </form>
    `);
}

async function submitServiceRecord(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.customer_id = parseInt(data.customer_id);
    Object.keys(data).forEach(k => { if (data[k] === '') delete data[k]; });
    await API.post('/api/service/records', data);
    closeModal();
    navigate();
}

function openContractForm() {
    openModal(`
        <div class="modal-title">New Maintenance Contract</div>
        <form onsubmit="submitContract(event)">
            <div class="form-group"><label>Customer ID *</label><input name="customer_id" type="number" required></div>
            <div class="form-group"><label>Contract Name *</label><input name="name" required></div>
            <div class="form-row">
                <div class="form-group"><label>Type</label>
                    <select name="contract_type">
                        <option value="preventive_maintenance">Preventive Maintenance</option>
                        <option value="full_service">Full Service</option>
                        <option value="emergency_only">Emergency Only</option>
                        <option value="inspection">Inspection</option>
                    </select>
                </div>
                <div class="form-group"><label>Annual Value ($)</label><input name="annual_value" type="number"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Start Date *</label><input name="start_date" type="date" required></div>
                <div class="form-group"><label>Renewal Date</label><input name="renewal_date" type="date"></div>
            </div>
            <div class="form-group"><label>Visit Frequency</label>
                <select name="visit_frequency">
                    <option value="monthly">Monthly</option>
                    <option value="quarterly" selected>Quarterly</option>
                    <option value="semi_annual">Semi-Annual</option>
                    <option value="annual">Annual</option>
                </select>
            </div>
            <div class="form-group"><label>Scope</label><textarea name="scope_description"></textarea></div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Create Contract</button>
            </div>
        </form>
    `);
}

async function submitContract(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.customer_id = parseInt(data.customer_id);
    if (data.annual_value) data.annual_value = parseFloat(data.annual_value);
    Object.keys(data).forEach(k => { if (data[k] === '') delete data[k]; });
    await API.post('/api/service/contracts', data);
    closeModal();
    navigate();
}
