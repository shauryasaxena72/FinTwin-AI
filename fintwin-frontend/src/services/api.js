const USE_API = import.meta.env.VITE_USE_API !== 'false';
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

async function request(path, options = {}) {
  if (!USE_API) throw new Error('Backend is not connected yet. Configure VITE_USE_API and implement the matching endpoint.');
  const url = BASE_URL ? `${BASE_URL}${path}` : path;
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`Engine request failed (${response.status}). Check the backend logs and API contract.`);
  return response.json();
}

export const api = {
  uploadFiles: async ({ bankStatement, invoices, reviewRows, vendorQuote, loanOffer }) => {
    const body = new FormData();
    if (bankStatement) body.append('bank_statement', bankStatement);
    if (invoices) body.append('invoices', invoices);
    body.append('review_rows', JSON.stringify(reviewRows || []));
    body.append('vendor_quote', JSON.stringify(vendorQuote || {}));
    body.append('loan_offer', JSON.stringify(loanOffer || {}));
    return request('/api/v1/intake', { method: 'POST', body });
  },
  getResults: () => request('/api/v1/results'),
  runScenario: (scenario) => request('/api/v1/scenario', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(scenario) }),
  askCopilot: (question) => request('/api/v1/copilot', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }) }),
};
export const apiEnabled = USE_API;