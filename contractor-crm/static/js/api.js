/**
 * API client wrapper for the Contractor CRM.
 */
const API = {
    async get(url) {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`GET ${url}: ${res.status}`);
        return res.json();
    },

    async post(url, data) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `POST ${url}: ${res.status}`);
        }
        return res.json();
    },

    async put(url, data) {
        const res = await fetch(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error(`PUT ${url}: ${res.status}`);
        return res.json();
    },

    async patch(url, data) {
        const res = await fetch(url, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error(`PATCH ${url}: ${res.status}`);
        return res.json();
    },

    async del(url) {
        const res = await fetch(url, { method: 'DELETE' });
        if (!res.ok) throw new Error(`DELETE ${url}: ${res.status}`);
        return res.json();
    },
};

function formatCurrency(n) {
    if (n == null) return '—';
    return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatPct(n) {
    if (n == null) return '—';
    return Number(n).toFixed(1) + '%';
}

function badge(text, prefix) {
    if (!text) return '';
    const cls = prefix ? `badge-${text}` : `badge-${text}`;
    return `<span class="badge ${cls}">${text.replace(/_/g, ' ')}</span>`;
}

function tierBadge(tier) {
    return `<span class="badge badge-${tier}">${tier}</span>`;
}
