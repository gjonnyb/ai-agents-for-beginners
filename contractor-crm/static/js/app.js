/**
 * SPA Router — maps hash routes to page render functions.
 */
const routes = {
    '/': renderDashboard,
    '/customers': renderCustomers,
    '/customers/:id': renderCustomerDetail,
    '/pipeline': renderPipeline,
    '/service': renderService,
    '/prospects': renderProspects,
    '/reports': renderReports,
    '/settings': renderSettings,
};

function navigate() {
    const hash = location.hash || '#/';
    const path = hash.slice(1); // remove #

    // Update active nav link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.getAttribute('href') === hash || (hash === '#/' && link.getAttribute('href') === '#/'));
    });

    // Match route
    const container = document.getElementById('page-container');

    // Check for parameterized routes like /customers/:id
    const customerMatch = path.match(/^\/customers\/(\d+)$/);
    if (customerMatch) {
        renderCustomerDetail(container, parseInt(customerMatch[1]));
        return;
    }

    const handler = routes[path];
    if (handler) {
        handler(container);
    } else {
        container.innerHTML = '<h2>Page not found</h2>';
    }
}

// Modal helpers
function openModal(html) {
    document.getElementById('modal-content').innerHTML = html;
    document.getElementById('modal-overlay').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
}

document.getElementById('modal-overlay').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeModal();
});

// Reports page (uses dashboard components)
async function renderReports(container) {
    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Reports</h1>
        </div>
        <div class="grid-2">
            <div class="card">
                <div class="card-header">Revenue Concentration</div>
                <div class="card-body">
                    <div class="chart-container"><canvas id="conc-chart"></canvas></div>
                    <div id="conc-flags" class="mt-16"></div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">Revenue Trend</div>
                <div class="card-body">
                    <div class="chart-container"><canvas id="rev-trend-chart"></canvas></div>
                </div>
            </div>
        </div>
        <div class="grid-2">
            <div class="card">
                <div class="card-header">Win/Loss Analysis</div>
                <div class="card-body" id="win-loss-body"><div class="loading-text"><span class="spinner"></span> Loading...</div></div>
            </div>
            <div class="card">
                <div class="card-header">Relationship Health Distribution</div>
                <div class="card-body" id="health-body"><div class="loading-text"><span class="spinner"></span> Loading...</div></div>
            </div>
        </div>
    `;

    // Load data
    const [conc, trend, winLoss, health] = await Promise.all([
        API.get('/api/dashboard/concentration'),
        API.get('/api/dashboard/revenue-trend'),
        API.get('/api/projects/win-loss'),
        API.get('/api/dashboard/relationship-health'),
    ]);

    // Concentration donut
    if (conc.customers && conc.customers.length > 0) {
        new Chart(document.getElementById('conc-chart'), {
            type: 'doughnut',
            data: {
                labels: conc.customers.map(c => c.customer_name),
                datasets: [{
                    data: conc.customers.map(c => c.revenue),
                    backgroundColor: ['#1a56db','#0d9e4f','#e67e00','#dc2626','#7c3aed','#0891b2','#65a30d','#d97706','#be185d','#4338ca','#059669','#ca8a04'],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { font: { size: 11 } } },
                },
            },
        });
        const flagsDiv = document.getElementById('conc-flags');
        if (conc.flags.length > 0) {
            flagsDiv.innerHTML = conc.flags.map(f => `<div class="ai-card"><div class="ai-card-body">${f}</div></div>`).join('');
        }
    }

    // Revenue trend
    if (trend.length > 0) {
        new Chart(document.getElementById('rev-trend-chart'), {
            type: 'bar',
            data: {
                labels: trend.map(r => `${r.fiscal_year} Q${r.fiscal_quarter}`),
                datasets: [
                    { label: 'Revenue', data: trend.map(r => r.revenue), backgroundColor: '#1a56db' },
                    { label: 'Cost', data: trend.map(r => r.cost), backgroundColor: '#e5e7eb' },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } },
            },
        });
    }

    // Win/Loss
    document.getElementById('win-loss-body').innerHTML = `
        <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-label">Win Rate</div><div class="kpi-value">${winLoss.win_rate}%</div></div>
            <div class="kpi-card"><div class="kpi-label">Won</div><div class="kpi-value positive">${winLoss.won}</div></div>
            <div class="kpi-card"><div class="kpi-label">Lost</div><div class="kpi-value danger">${winLoss.lost}</div></div>
        </div>
        ${Object.keys(winLoss.loss_reasons).length > 0 ? `
            <h4 class="mt-16 mb-12">Loss Reasons</h4>
            <table><tr><th>Reason</th><th>Count</th></tr>
            ${Object.entries(winLoss.loss_reasons).map(([r, c]) => `<tr><td>${r}</td><td>${c}</td></tr>`).join('')}
            </table>
        ` : ''}
    `;

    // Health distribution
    document.getElementById('health-body').innerHTML = `
        <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-label">Platinum</div><div class="kpi-value">${health.platinum_count}</div></div>
            <div class="kpi-card"><div class="kpi-label">Gold</div><div class="kpi-value">${health.gold_count}</div></div>
            <div class="kpi-card"><div class="kpi-label">Silver</div><div class="kpi-value">${health.silver_count}</div></div>
            <div class="kpi-card"><div class="kpi-label">Bronze (at risk)</div><div class="kpi-value danger">${health.bronze_count}</div></div>
        </div>
    `;
}

// Settings page
async function renderSettings(container) {
    container.innerHTML = '<div class="loading-text"><span class="spinner"></span> Checking AI configuration...</div>';

    const status = await API.get('/api/ai/status');

    function statusBanner(s) {
        if (!s.ai_enabled) {
            return `<div class="ai-card" style="background:#fef2f2;border-color:#fca5a5;">
                <div class="ai-card-title" style="color:#dc2626;">AI features are disabled</div>
                <div class="ai-card-body">Enter at least one API key below to activate AI-powered insights.</div>
            </div>`;
        }
        return `<div class="ai-card" style="background:#f0fdf4;border-color:#86efac;">
            <div class="ai-card-title" style="color:#16a34a;">AI features are active</div>
            <div class="ai-card-body">Using <strong>${s.provider === 'anthropic' ? 'Anthropic Claude' : 'OpenAI GPT-4o'}</strong> for AI-powered insights.</div>
        </div>`;
    }

    function statusCards(s) {
        return `<div class="kpi-grid" style="margin-bottom:20px">
            <div class="kpi-card">
                <div class="kpi-label">AI Features</div>
                <div class="kpi-value ${s.ai_enabled ? 'positive' : 'danger'}">${s.ai_enabled ? 'Active' : 'Not Configured'}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Provider</div>
                <div class="kpi-value">${s.provider ? s.provider.charAt(0).toUpperCase() + s.provider.slice(1) : 'None'}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Anthropic (Claude)</div>
                <div class="kpi-value ${s.anthropic_configured ? 'positive' : 'danger'}">${s.anthropic_configured ? 'Configured' : 'Missing'}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">OpenAI (GPT-4o)</div>
                <div class="kpi-value ${s.openai_configured ? 'positive' : 'danger'}">${s.openai_configured ? 'Configured' : 'Missing'}</div>
            </div>
        </div>`;
    }

    container.innerHTML = `
        <div class="page-header"><h1 class="page-title">Settings</h1></div>

        <div class="card">
            <div class="card-header">AI Configuration</div>
            <div class="card-body">
                <div id="settings-status-cards">${statusCards(status)}</div>
                <div id="settings-status-banner">${statusBanner(status)}</div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">API Keys</div>
            <div class="card-body">
                <p style="margin-bottom:16px;color:#6b7280">
                    Keys are saved to a local <code>.env</code> file on the server. They are <strong>never</strong>
                    committed to git or exposed to the browser. Only one key is required — Anthropic is used first if both are set.
                </p>
                <form id="api-key-form" autocomplete="off">
                    <div class="form-group" style="margin-bottom:16px">
                        <label style="display:block;font-weight:600;margin-bottom:6px">Anthropic API Key (Claude) — recommended</label>
                        <input type="password" id="anthropic-key-input" class="form-control"
                            placeholder="${status.anthropic_configured ? 'Key is configured — enter new value to replace' : 'sk-ant-...'}"
                            style="font-family:monospace;max-width:520px">
                    </div>
                    <div class="form-group" style="margin-bottom:20px">
                        <label style="display:block;font-weight:600;margin-bottom:6px">OpenAI API Key (GPT-4o) — fallback</label>
                        <input type="password" id="openai-key-input" class="form-control"
                            placeholder="${status.openai_configured ? 'Key is configured — enter new value to replace' : 'sk-...'}"
                            style="font-family:monospace;max-width:520px">
                    </div>
                    <div style="display:flex;align-items:center;gap:16px">
                        <button type="submit" class="btn btn-primary" id="save-keys-btn">Save Keys</button>
                        <span id="save-keys-msg" style="font-size:14px"></span>
                    </div>
                </form>
            </div>
        </div>

        <div class="card">
            <div class="card-header">Security</div>
            <div class="card-body">
                <ul style="line-height:2">
                    <li>Keys are stored in <code>.env</code> which is <strong>gitignored</strong> — never committed to version control</li>
                    <li>Keys are read <strong>server-side only</strong> and never returned to the browser</li>
                    <li>This app is designed to run on <strong>localhost</strong> — do not expose it to the public internet without adding authentication</li>
                    <li>Get your Anthropic API key at <strong>console.anthropic.com</strong></li>
                    <li>Get your OpenAI API key at <strong>platform.openai.com</strong></li>
                </ul>
            </div>
        </div>
    `;

    document.getElementById('api-key-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('save-keys-btn');
        const msg = document.getElementById('save-keys-msg');
        const anthropicVal = document.getElementById('anthropic-key-input').value.trim();
        const openaiVal = document.getElementById('openai-key-input').value.trim();

        if (!anthropicVal && !openaiVal) {
            msg.style.color = '#dc2626';
            msg.textContent = 'Enter at least one key.';
            return;
        }

        btn.disabled = true;
        btn.textContent = 'Saving...';
        msg.textContent = '';

        const payload = {};
        if (anthropicVal) payload.anthropic_api_key = anthropicVal;
        if (openaiVal) payload.openai_api_key = openaiVal;

        try {
            const result = await API.post('/api/ai/configure-keys', payload);
            msg.style.color = '#16a34a';
            msg.textContent = result.ai_enabled ? 'Saved! AI features are now active.' : 'Saved. Add a valid key to enable AI.';
            document.getElementById('anthropic-key-input').value = '';
            document.getElementById('openai-key-input').value = '';
            document.getElementById('anthropic-key-input').placeholder = result.anthropic_configured ? 'Key is configured — enter new value to replace' : 'sk-ant-...';
            document.getElementById('openai-key-input').placeholder = result.openai_configured ? 'Key is configured — enter new value to replace' : 'sk-...';
            document.getElementById('settings-status-cards').innerHTML = statusCards(result);
            document.getElementById('settings-status-banner').innerHTML = statusBanner(result);
        } catch (err) {
            msg.style.color = '#dc2626';
            msg.textContent = 'Error saving keys. Check the server logs.';
        }
        btn.disabled = false;
        btn.textContent = 'Save Keys';
    });
}

// Boot
window.addEventListener('hashchange', navigate);
window.addEventListener('DOMContentLoaded', navigate);
