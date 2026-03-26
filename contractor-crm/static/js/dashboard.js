/**
 * Dashboard page — KPIs, concentration chart, pipeline funnel, at-risk list.
 */
async function renderDashboard(container) {
    container.innerHTML = `
        <div class="page-header"><h1 class="page-title">Dashboard</h1></div>
        <div id="ai-status-banner"></div>
        <div id="kpi-row" class="kpi-grid"><div class="loading-text"><span class="spinner"></span> Loading KPIs...</div></div>
        <div class="grid-2">
            <div class="card">
                <div class="card-header">Revenue Concentration
                    <button class="btn btn-ai btn-sm" onclick="runConcentrationAI()">AI Analysis</button>
                </div>
                <div class="card-body">
                    <div class="chart-container"><canvas id="dash-conc-chart"></canvas></div>
                    <div id="dash-conc-flags" class="mt-8"></div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">Pipeline Summary</div>
                <div class="card-body">
                    <div class="chart-container"><canvas id="dash-pipeline-chart"></canvas></div>
                </div>
            </div>
        </div>
        <div class="grid-2">
            <div class="card">
                <div class="card-header">At-Risk Customers</div>
                <div class="card-body" id="dash-at-risk"><div class="loading-text"><span class="spinner"></span> Loading...</div></div>
            </div>
            <div class="card">
                <div class="card-header">Overdue Follow-ups</div>
                <div class="card-body" id="dash-followups"><div class="loading-text"><span class="spinner"></span> Loading...</div></div>
            </div>
        </div>
        <div class="card">
            <div class="card-header">Recent AI Recommendations</div>
            <div class="card-body" id="dash-recs"><div class="loading-text"><span class="spinner"></span> Loading...</div></div>
        </div>
    `;

    // Show AI status banner
    const aiStatus = await API.get('/api/ai/status').catch(() => ({ ai_enabled: false }));
    const banner = document.getElementById('ai-status-banner');
    if (!aiStatus.ai_enabled) {
        banner.innerHTML = `
            <div class="ai-card" style="background:#fef2f2;border-color:#fca5a5;margin-bottom:16px">
                <div class="ai-card-title" style="color:#dc2626">AI features not configured</div>
                <div class="ai-card-body">
                    AI-powered insights (relationship analysis, bid analysis, growth priorities) require an API key.
                    <a href="#/settings" style="color:#1a56db;font-weight:600">Go to Settings</a> to configure securely.
                </div>
            </div>`;
    }

    // Load all data in parallel
    const [summary, conc, pipeline, health, followups, recs] = await Promise.all([
        API.get('/api/dashboard/summary'),
        API.get('/api/dashboard/concentration'),
        API.get('/api/dashboard/pipeline-value'),
        API.get('/api/dashboard/relationship-health'),
        API.get('/api/interactions/overdue-followups'),
        API.get('/api/ai/recommendations?status=pending').catch(() => []),
    ]);

    // KPIs
    document.getElementById('kpi-row').innerHTML = `
        <div class="kpi-card"><div class="kpi-label">YTD Revenue</div><div class="kpi-value">${formatCurrency(summary.ytd_revenue)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Pipeline Value</div><div class="kpi-value">${formatCurrency(summary.pipeline_value)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Active Projects</div><div class="kpi-value">${summary.active_projects}</div></div>
        <div class="kpi-card"><div class="kpi-label">Active Customers</div><div class="kpi-value">${summary.active_customers}</div></div>
        <div class="kpi-card"><div class="kpi-label">Contract ARR</div><div class="kpi-value">${formatCurrency(summary.contract_arr)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Open Service Tickets</div><div class="kpi-value ${summary.open_service_tickets > 5 ? 'warning' : ''}">${summary.open_service_tickets}</div></div>
    `;

    // Concentration chart
    if (conc.customers && conc.customers.length > 0) {
        new Chart(document.getElementById('dash-conc-chart'), {
            type: 'doughnut',
            data: {
                labels: conc.customers.map(c => c.customer_name),
                datasets: [{
                    data: conc.customers.map(c => c.share_pct),
                    backgroundColor: ['#1a56db','#0d9e4f','#e67e00','#dc2626','#7c3aed','#0891b2','#65a30d','#d97706','#be185d','#4338ca','#059669','#ca8a04'],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: `HHI: ${conc.hhi} (${conc.concentration_level.replace(/_/g, ' ')})` },
                    legend: { position: 'right', labels: { font: { size: 11 } } },
                },
            },
        });
        if (conc.flags.length > 0) {
            document.getElementById('dash-conc-flags').innerHTML = conc.flags.map(f =>
                `<div class="ai-card"><div class="ai-card-body">${f}</div></div>`
            ).join('');
        }
    }

    // Pipeline funnel
    const stages = ['lead', 'qualified', 'estimating', 'bid_submitted', 'negotiation', 'won'];
    const pipelineData = stages.map(s => pipeline[s] || { count: 0, weighted_value: 0, raw_value: 0 });
    new Chart(document.getElementById('dash-pipeline-chart'), {
        type: 'bar',
        data: {
            labels: stages.map(s => s.replace(/_/g, ' ')),
            datasets: [{
                label: 'Weighted Value',
                data: pipelineData.map(d => d.weighted_value),
                backgroundColor: '#1a56db',
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            scales: { x: { beginAtZero: true } },
        },
    });

    // At-risk customers
    const atRisk = health.at_risk || [];
    document.getElementById('dash-at-risk').innerHTML = atRisk.length === 0
        ? '<p class="text-muted">No at-risk customers.</p>'
        : `<table><tr><th>Customer</th><th>Score</th><th>Tier</th><th></th></tr>
           ${atRisk.map(c => `
               <tr class="clickable" onclick="location.hash='#/customers/${c.customer_id}'">
                   <td>${c.name}</td>
                   <td>${c.score}</td>
                   <td>${tierBadge(c.tier)}</td>
                   <td><button class="btn btn-ai btn-sm" onclick="event.stopPropagation(); runRelationshipAI(${c.customer_id})">AI Insights</button></td>
               </tr>
           `).join('')}
           </table>`;

    // Overdue follow-ups
    document.getElementById('dash-followups').innerHTML = followups.length === 0
        ? '<p class="text-muted">No overdue follow-ups.</p>'
        : `<table><tr><th>Subject</th><th>Type</th><th>Due</th></tr>
           ${followups.slice(0, 10).map(f => `
               <tr><td>${f.subject || '—'}</td><td>${f.interaction_type}</td><td>${f.follow_up_date}</td></tr>
           `).join('')}
           </table>`;

    // AI Recommendations
    document.getElementById('dash-recs').innerHTML = recs.length === 0
        ? '<p class="text-muted">No pending recommendations.</p>'
        : recs.slice(0, 5).map(r => `
            <div class="ai-card">
                <div class="ai-card-title">${r.title}</div>
                <div class="ai-card-body">${r.detail}</div>
                <div class="mt-8">
                    <button class="btn btn-sm btn-primary" onclick="acceptRec(${r.id})">Accept</button>
                    <button class="btn btn-sm btn-secondary" onclick="dismissRec(${r.id})">Dismiss</button>
                </div>
            </div>
        `).join('');
}

async function runConcentrationAI() {
    openModal('<div class="loading-text"><span class="spinner"></span> Running AI concentration analysis...</div>');
    try {
        const result = await API.post('/api/ai/concentration-review', {});
        openModal(`
            <div class="modal-title">AI Concentration Review</div>
            <p><strong>Risk Level:</strong> ${result.risk_level || 'N/A'}</p>
            ${result.key_insights ? `<h4 class="mt-16">Key Insights</h4><ul>${result.key_insights.map(i => `<li>${i}</li>`).join('')}</ul>` : ''}
            ${result.immediate_actions ? `<h4 class="mt-16">Immediate Actions</h4><ul>${result.immediate_actions.map(a => `<li>${a}</li>`).join('')}</ul>` : ''}
            ${result.strategic_recommendations ? `<h4 class="mt-16">Strategic Recommendations</h4><ul>${result.strategic_recommendations.map(r => `<li>${r}</li>`).join('')}</ul>` : ''}
            ${result.summary ? `<p class="mt-16 text-muted">${result.summary}</p>` : ''}
            <div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Close</button></div>
        `);
    } catch (e) {
        openModal(`<div class="modal-title">AI Unavailable</div><p>${e.message}</p><div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Close</button></div>`);
    }
}

async function runRelationshipAI(customerId) {
    openModal('<div class="loading-text"><span class="spinner"></span> Analyzing relationship...</div>');
    try {
        const result = await API.post(`/api/ai/relationship-analysis/${customerId}`, {});
        openModal(`
            <div class="modal-title">Relationship Analysis: ${result.customer_name || ''}</div>
            <p><strong>Health:</strong> ${result.health_status || 'N/A'} | <strong>Score:</strong> ${result.relationship_score} | <strong>Risk:</strong> ${result.risk_score || 'N/A'}%</p>
            ${result.strengths ? `<h4 class="mt-16">Strengths</h4><ul>${result.strengths.map(s => `<li>${s}</li>`).join('')}</ul>` : ''}
            ${result.risks ? `<h4 class="mt-16">Risks</h4><ul>${result.risks.map(r => `<li>${r}</li>`).join('')}</ul>` : ''}
            ${result.recommendations ? `<h4 class="mt-16">Recommendations</h4><ul>${result.recommendations.map(r => `<li>${r}</li>`).join('')}</ul>` : ''}
            ${result.summary ? `<p class="mt-16 text-muted">${result.summary}</p>` : ''}
            <div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Close</button></div>
        `);
    } catch (e) {
        openModal(`<div class="modal-title">AI Unavailable</div><p>${e.message}</p><div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Close</button></div>`);
    }
}

async function acceptRec(id) {
    await API.patch(`/api/ai/recommendations/${id}`, { status: 'accepted' });
    navigate();
}

async function dismissRec(id) {
    await API.patch(`/api/ai/recommendations/${id}`, { status: 'dismissed' });
    navigate();
}
