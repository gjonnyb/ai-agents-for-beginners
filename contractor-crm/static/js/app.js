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

    container.innerHTML = `
        <div class="page-header"><h1 class="page-title">Settings</h1></div>

        <div class="card">
            <div class="card-header">AI Configuration Status</div>
            <div class="card-body">
                <div class="kpi-grid" style="margin-bottom:20px">
                    <div class="kpi-card">
                        <div class="kpi-label">AI Features</div>
                        <div class="kpi-value ${status.ai_enabled ? 'positive' : 'danger'}">${status.ai_enabled ? 'Active' : 'Not Configured'}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Provider</div>
                        <div class="kpi-value">${status.provider ? status.provider.charAt(0).toUpperCase() + status.provider.slice(1) : 'None'}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Anthropic (Claude)</div>
                        <div class="kpi-value ${status.anthropic_configured ? 'positive' : 'danger'}">${status.anthropic_configured ? 'Configured' : 'Missing'}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">OpenAI (GPT-4o)</div>
                        <div class="kpi-value ${status.openai_configured ? 'positive' : 'danger'}">${status.openai_configured ? 'Configured' : 'Missing'}</div>
                    </div>
                </div>

                ${!status.ai_enabled ? `
                <div class="ai-card" style="background: #fef2f2; border-color: #fca5a5;">
                    <div class="ai-card-title" style="color: #dc2626;">AI features are disabled</div>
                    <div class="ai-card-body">
                        No API key is configured. The CRM works fully without AI, but features like
                        relationship analysis, next-action recommendations, bid analysis, and growth
                        prioritization require an LLM API key.
                    </div>
                </div>
                ` : `
                <div class="ai-card" style="background: #f0fdf4; border-color: #86efac;">
                    <div class="ai-card-title" style="color: #16a34a;">AI features are active</div>
                    <div class="ai-card-body">
                        Using <strong>${status.provider === 'anthropic' ? 'Anthropic Claude' : 'OpenAI GPT-4o'}</strong> for AI-powered insights.
                        Your API key is stored securely in your local <code>.env</code> file and is never exposed to the browser.
                    </div>
                </div>
                `}
            </div>
        </div>

        <div class="card">
            <div class="card-header">How to Configure Your API Key</div>
            <div class="card-body">
                <p style="margin-bottom:16px">
                    API keys are stored in a <code>.env</code> file in the <code>contractor-crm/</code> directory.
                    This file is <strong>gitignored</strong> and never committed to version control.
                    The key is only read server-side — it is never sent to the browser.
                </p>

                <h4 style="margin-bottom:8px">Step 1: Open your terminal</h4>
                <p class="text-muted" style="margin-bottom:12px">Navigate to the contractor-crm directory where the app is running.</p>

                <h4 style="margin-bottom:8px">Step 2: Create the .env file</h4>
                <p class="text-muted" style="margin-bottom:8px">Copy the example file and add your key. Run one of:</p>

                <div style="background:#1f2937;color:#e5e7eb;padding:16px;border-radius:8px;font-family:monospace;font-size:13px;margin-bottom:16px;overflow-x:auto">
                    <div style="color:#9ca3af"># Option A: Use Anthropic (Claude) — recommended</div>
                    <div>cp .env.example .env</div>
                    <div style="color:#9ca3af"># Then edit .env and set:</div>
                    <div>ANTHROPIC_API_KEY=sk-ant-your-key-here</div>
                    <br>
                    <div style="color:#9ca3af"># Option B: Use OpenAI (GPT-4o)</div>
                    <div>OPENAI_API_KEY=sk-your-key-here</div>
                </div>

                <div style="background:#1f2937;color:#e5e7eb;padding:16px;border-radius:8px;font-family:monospace;font-size:13px;margin-bottom:16px;overflow-x:auto">
                    <div style="color:#9ca3af"># Quick one-liner for macOS/Linux:</div>
                    <div>echo 'ANTHROPIC_API_KEY=sk-ant-your-key-here' > .env</div>
                </div>

                <h4 style="margin-bottom:8px">Step 3: Restart the server</h4>
                <p class="text-muted" style="margin-bottom:8px">Stop the server (Ctrl+C) and restart it:</p>
                <div style="background:#1f2937;color:#e5e7eb;padding:16px;border-radius:8px;font-family:monospace;font-size:13px;margin-bottom:16px">
                    <div>python3 main.py</div>
                </div>

                <h4 style="margin-bottom:8px">Step 4: Verify</h4>
                <p class="text-muted">Reload this page. The status above should show "Active".</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header">Security Notes</div>
            <div class="card-body">
                <ul style="line-height:2">
                    <li>The <code>.env</code> file is listed in <code>.gitignore</code> — it will <strong>never</strong> be committed to git</li>
                    <li>The API key is read <strong>server-side only</strong> — it is never sent to the browser or frontend</li>
                    <li>The <code>/api/ai/status</code> endpoint reports whether a key is configured, but never reveals the key itself</li>
                    <li>Only one key is required (Anthropic <em>or</em> OpenAI). Anthropic is used first if both are set</li>
                    <li>Get your Anthropic API key at <strong>console.anthropic.com</strong></li>
                    <li>Get your OpenAI API key at <strong>platform.openai.com</strong></li>
                </ul>
            </div>
        </div>
    `;
}

// Boot
window.addEventListener('hashchange', navigate);
window.addEventListener('DOMContentLoaded', navigate);
