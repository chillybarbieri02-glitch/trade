const money = (n) => `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const PROVIDER_LABELS = { quickbooks: "QuickBooks", xero: "Xero" };

function riskClass(score) {
  if (score >= 60) return "risk-high";
  if (score >= 30) return "risk-med";
  return "risk-low";
}

async function loadDataSourcePanel() {
  const res = await fetch("/api/integrations/status");
  const status = await res.json();

  const buttons = Object.entries(status)
    .map(([provider, info]) => {
      const label = PROVIDER_LABELS[provider];
      if (info.connected) {
        return `
          <span class="provider-group">
            <span class="connected-pill">${label} connected</span>
            <button class="sync-btn" data-provider="${provider}">Sync now</button>
            <button class="disconnect-btn" data-provider="${provider}">Disconnect</button>
          </span>`;
      }
      if (info.configured) {
        return `<a class="connect-btn" href="/api/integrations/${provider}/authorize">Connect ${label}</a>`;
      }
      return `<span class="connect-btn disabled" title="Set ${provider.toUpperCase()}_CLIENT_ID/SECRET/REDIRECT_URI to enable">Connect ${label} (not configured)</span>`;
    })
    .join("");

  document.getElementById("data-source").innerHTML = `
    <div class="data-source-row">
      ${buttons}
      <label class="upload-btn">
        Or import a CSV
        <input type="file" id="csv-input" accept=".csv" hidden />
      </label>
    </div>`;

  document.getElementById("csv-input").addEventListener("change", handleCsvUpload);
  document.querySelectorAll(".sync-btn").forEach((btn) =>
    btn.addEventListener("click", (e) => syncProvider(e.target.dataset.provider))
  );
  document.querySelectorAll(".disconnect-btn").forEach((btn) =>
    btn.addEventListener("click", (e) => disconnectProvider(e.target.dataset.provider))
  );
}

async function syncProvider(provider) {
  const res = await fetch(`/api/integrations/${provider}/sync`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    alert(data.detail || `Sync with ${PROVIDER_LABELS[provider]} failed`);
    return;
  }
  alert(`${PROVIDER_LABELS[provider]} sync: ${data.created} new, ${data.updated} updated, ${data.skipped} skipped`);
  refresh();
}

async function disconnectProvider(provider) {
  await fetch(`/api/integrations/${provider}/disconnect`, { method: "POST" });
  loadDataSourcePanel();
}

async function handleCsvUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/invoices/import", { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "Import failed");
  }
  e.target.value = "";
  refresh();
}

async function loadDashboard() {
  const res = await fetch("/api/dashboard");
  const d = await res.json();
  const cards = [
    ["Total outstanding", money(d.total_outstanding)],
    ["At risk (score >= 50)", money(d.at_risk_amount)],
    ["Overdue invoices", d.overdue_count],
    ["Avg days late", d.avg_days_late],
  ];
  document.getElementById("dashboard").innerHTML = cards
    .map(([label, value]) => `<div class="card"><div class="label">${label}</div><div class="value">${value}</div></div>`)
    .join("");
}

async function loadInvoices() {
  const res = await fetch("/api/invoices?status=open");
  const invoices = await res.json();
  const body = document.getElementById("invoice-body");

  document.getElementById("invoice-table").hidden = invoices.length === 0;
  document.getElementById("empty-state").hidden = invoices.length > 0;

  body.innerHTML = invoices
    .map(
      (inv) => `
      <tr data-id="${inv.id}">
        <td><span class="risk-pill ${riskClass(inv.risk_score)}">${inv.risk_score}</span></td>
        <td>${inv.customer_name}</td>
        <td>${inv.invoice_number}</td>
        <td>${money(inv.amount)}</td>
        <td>${inv.due_date}</td>
        <td>${inv.days_overdue}</td>
        <td>${inv.stage_label}</td>
        <td>
          <button class="draft-btn">Draft reminder</button>
          <button class="paid-btn">Mark paid</button>
        </td>
      </tr>`
    )
    .join("");

  body.querySelectorAll(".draft-btn").forEach((btn) =>
    btn.addEventListener("click", (e) => draftReminder(e.target.closest("tr").dataset.id))
  );
  body.querySelectorAll(".paid-btn").forEach((btn) =>
    btn.addEventListener("click", async (e) => {
      const id = e.target.closest("tr").dataset.id;
      await fetch(`/api/invoices/${id}/mark_paid`, { method: "POST" });
      refresh();
    })
  );
}

async function draftReminder(id) {
  const res = await fetch(`/api/invoices/${id}/draft`, { method: "POST" });
  const data = await res.json();
  document.getElementById("draft-title").textContent = `Draft - ${data.stage_label}`;
  document.getElementById("draft-text").value = data.draft;
  document.getElementById("draft-dialog").showModal();
  refresh();
}

document.getElementById("close-dialog").addEventListener("click", () => {
  document.getElementById("draft-dialog").close();
});

document.getElementById("copy-draft").addEventListener("click", () => {
  navigator.clipboard.writeText(document.getElementById("draft-text").value);
});

function refresh() {
  loadDataSourcePanel();
  loadDashboard();
  loadInvoices();
}

const justConnected = new URLSearchParams(window.location.search).get("connected");
if (justConnected) {
  window.history.replaceState({}, "", window.location.pathname);
  syncProvider(justConnected);
}

refresh();
