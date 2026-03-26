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

// Boot
window.addEventListener('hashchange', navigate);
window.addEventListener('DOMContentLoaded', navigate);
