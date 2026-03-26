/**
 * Pipeline page — kanban board view of projects.
 */
async function renderPipeline(container) {
    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Pipeline</h1>
        </div>
        <div id="pipeline-summary" class="kpi-grid mb-12"></div>
        <div id="pipeline-kanban" class="kanban"><div class="loading-text"><span class="spinner"></span> Loading pipeline...</div></div>
    `;

    const [projects, pipelineValue] = await Promise.all([
        API.get('/api/projects'),
        API.get('/api/dashboard/pipeline-value'),
    ]);

    // Summary KPIs
    const totalWeighted = pipelineValue.total_weighted || 0;
    const activeStages = ['lead', 'qualified', 'estimating', 'bid_submitted', 'negotiation'];
    const pipelineProjects = projects.filter(p => activeStages.includes(p.stage));
    document.getElementById('pipeline-summary').innerHTML = `
        <div class="kpi-card"><div class="kpi-label">Pipeline Projects</div><div class="kpi-value">${pipelineProjects.length}</div></div>
        <div class="kpi-card"><div class="kpi-label">Weighted Pipeline</div><div class="kpi-value">${formatCurrency(totalWeighted)}</div></div>
        <div class="kpi-card"><div class="kpi-label">In Progress</div><div class="kpi-value">${projects.filter(p => p.stage === 'in_progress').length}</div></div>
        <div class="kpi-card"><div class="kpi-label">Won (Total)</div><div class="kpi-value positive">${projects.filter(p => p.stage === 'won').length}</div></div>
    `;

    // Kanban
    const stages = [
        { key: 'lead', label: 'Lead' },
        { key: 'qualified', label: 'Qualified' },
        { key: 'estimating', label: 'Estimating' },
        { key: 'bid_submitted', label: 'Bid Submitted' },
        { key: 'negotiation', label: 'Negotiation' },
        { key: 'won', label: 'Won' },
        { key: 'in_progress', label: 'In Progress' },
    ];

    const kanban = document.getElementById('pipeline-kanban');
    kanban.innerHTML = stages.map(stage => {
        const stageProjects = projects.filter(p => p.stage === stage.key);
        return `
            <div class="kanban-column">
                <div class="kanban-header">
                    ${stage.label}
                    <span class="kanban-count">${stageProjects.length}</span>
                </div>
                ${stageProjects.map(p => `
                    <div class="kanban-card" onclick="openProjectDetail(${p.id})">
                        <div class="kanban-card-title">${p.name}</div>
                        <div class="kanban-card-subtitle">${p.customer_name}</div>
                        ${p.bid_amount ? `<div class="kanban-card-value">${formatCurrency(p.bid_amount)}</div>` : ''}
                        ${p.bid_due_date ? `<div class="kanban-card-subtitle">Due: ${p.bid_due_date}</div>` : ''}
                    </div>
                `).join('')}
            </div>
        `;
    }).join('');
}

async function openProjectDetail(projectId) {
    const p = await API.get(`/api/projects/${projectId}`);
    openModal(`
        <div class="modal-title">${p.name}</div>
        <table>
            <tr><td class="text-muted">Customer</td><td>${p.customer_name}</td></tr>
            <tr><td class="text-muted">Type</td><td>${(p.project_type || '').replace(/_/g, ' ')}</td></tr>
            <tr><td class="text-muted">Stage</td><td>${badge(p.stage)}</td></tr>
            <tr><td class="text-muted">Priority</td><td>${badge(p.priority)}</td></tr>
            <tr><td class="text-muted">Bid Amount</td><td>${formatCurrency(p.bid_amount)}</td></tr>
            <tr><td class="text-muted">Estimated Cost</td><td>${formatCurrency(p.estimated_cost)}</td></tr>
            <tr><td class="text-muted">Contract Value</td><td>${formatCurrency(p.contract_value)}</td></tr>
            <tr><td class="text-muted">Margin</td><td>${formatPct(p.estimated_margin_pct)}</td></tr>
            <tr><td class="text-muted">GC</td><td>${p.general_contractor || '—'}</td></tr>
            <tr><td class="text-muted">Bid Due</td><td>${p.bid_due_date || '—'}</td></tr>
            <tr><td class="text-muted">Win Probability</td><td>${formatPct(p.win_probability ? p.win_probability * 100 : null)}</td></tr>
            <tr><td class="text-muted">Estimator</td><td>${p.assigned_estimator || '—'}</td></tr>
            <tr><td class="text-muted">PM</td><td>${p.assigned_pm || '—'}</td></tr>
        </table>
        ${p.description ? `<p class="mt-16">${p.description}</p>` : ''}
        <div class="mt-16">
            <strong>Move Stage:</strong>
            <div class="flex gap-8 mt-8" style="flex-wrap:wrap">
                ${['lead','qualified','estimating','bid_submitted','negotiation','won','lost','in_progress','completed'].map(s =>
                    `<button class="btn btn-sm ${s === p.stage ? 'btn-primary' : 'btn-secondary'}" onclick="moveStage(${p.id}, '${s}')">${s.replace(/_/g, ' ')}</button>`
                ).join('')}
            </div>
        </div>
        <div class="mt-16">
            <button class="btn btn-ai" onclick="runBidAI(${p.id})">AI Bid Analysis</button>
        </div>
        <div class="modal-actions">
            <button class="btn btn-secondary" onclick="closeModal()">Close</button>
        </div>
    `);
}

async function moveStage(projectId, stage) {
    const data = { stage };
    if (stage === 'lost') {
        const reason = prompt('Loss reason (price, relationship, scope, schedule, competitor, cancelled, other):');
        if (reason) data.loss_reason = reason;
    }
    await API.patch(`/api/projects/${projectId}/stage`, data);
    closeModal();
    navigate();
}

async function runBidAI(projectId) {
    openModal('<div class="loading-text"><span class="spinner"></span> Running bid analysis...</div>');
    try {
        const result = await API.post(`/api/ai/bid-analysis/${projectId}`, {});
        openModal(`
            <div class="modal-title">Bid Analysis: ${result.project_name || ''}</div>
            <p><strong>Recommendation:</strong> ${(result.recommendation || '').replace(/_/g, ' ').toUpperCase()}</p>
            <p><strong>Confidence:</strong> ${result.confidence ? (result.confidence * 100).toFixed(0) + '%' : 'N/A'}</p>
            <p><strong>Strategy:</strong> ${(result.bid_strategy || '').replace(/_/g, ' ')}</p>
            ${result.strategy_rationale ? `<p class="text-muted">${result.strategy_rationale}</p>` : ''}
            ${result.key_factors ? `<h4 class="mt-16">Key Factors</h4><ul>${result.key_factors.map(f => `<li>${f}</li>`).join('')}</ul>` : ''}
            ${result.risks ? `<h4 class="mt-16">Risks</h4><ul>${result.risks.map(r => `<li>${r}</li>`).join('')}</ul>` : ''}
            ${result.conditions ? `<h4 class="mt-16">Conditions</h4><ul>${result.conditions.map(c => `<li>${c}</li>`).join('')}</ul>` : ''}
            ${result.summary ? `<p class="mt-16 text-muted">${result.summary}</p>` : ''}
            <div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Close</button></div>
        `);
    } catch (e) {
        openModal(`<div class="modal-title">AI Unavailable</div><p>${e.message}</p><div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Close</button></div>`);
    }
}
