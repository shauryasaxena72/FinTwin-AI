
import React, { useMemo, useState } from "react";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  FileSpreadsheet,
  FileText,
  Landmark,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  Trash2,
  Upload,
  X,
} from "lucide-react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

function suggestCategory(description) {
  const text = (description || "").toLowerCase();
  if (text.includes("loan") || text.includes("emi") || text.includes("repayment")) return "loan";
  if (text.includes("invoice") || text.includes("customer") || text.includes("sales") || text.includes("receipt")) return "revenue";
  if (text.includes("rent") || text.includes("salary") || text.includes("utilities") || text.includes("supplier")) return "opex";
  if (text.includes("opening")) return "other";
  return "other";
}

const INITIAL_FILES = {
  bank: null,
  invoices: null,
};

const INITIAL_VENDOR = {
  vendor: "",
  amount: "",
  deposit: "",
  purchaseMonth: "1",
  description: "",
};

const INITIAL_LOAN = {
  lender: "",
  amount: "",
  interestRate: "",
  tenureMonths: "",
  monthlyPayment: "",
};

const STEPS = [
  {
    number: "01",
    title: "Import records",
    description: "Bank statement and invoices",
  },
  {
    number: "02",
    title: "Verify records",
    description: "Confirm transaction classifications",
  },
  {
    number: "03",
    title: "Run analysis",
    description: "Evaluate plans with the engine",
  },
];

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function parseCSV(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"' && quoted && next === '"') {
      cell += '"';
      i += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell.trim());
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(cell.trim());

      if (row.some((value) => value !== "")) rows.push(row);

      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }

  if (cell || row.length) {
    row.push(cell.trim());
    if (row.some((value) => value !== "")) rows.push(row);
  }

  if (quoted) {
    throw new Error("The CSV contains an unclosed quoted field.");
  }

  if (rows.length < 2) {
    throw new Error(
      "The CSV must contain a header and at least one data row."
    );
  }

  const headers = rows[0].map((header) => header.trim());

  if (headers.some((header) => !header)) {
    throw new Error("Every CSV column must have a header.");
  }

  return rows.slice(1).map((values, index) => ({
    id: `${index}-${values.join("|")}`,
    values: headers.map((_, columnIndex) => values[columnIndex] ?? ""),
    headers,
    category: "other",
    reviewed: false,
  }));
}

function FileUploadCard({ title, description, file, onFile, onRemove }) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");

  function acceptFile(candidate) {
    setError("");

    if (!candidate) return;

    if (!candidate.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a CSV file.");
      return;
    }

    onFile(candidate);
  }

  return (
    <div className="ft-upload-card">
      <div className="ft-upload-heading">
        <div className="ft-file-icon">
          <FileSpreadsheet size={19} strokeWidth={1.7} />
        </div>
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>

      {file ? (
        <div className="ft-selected-file">
          <div className="ft-selected-file-icon">
            <FileText size={18} />
          </div>

          <div className="ft-file-info">
            <strong title={file.name}>{file.name}</strong>
            <span>{formatBytes(file.size)} · CSV file</span>
          </div>

          <button
            className="ft-icon-button"
            type="button"
            aria-label={`Remove ${file.name}`}
            onClick={onRemove}
          >
            <Trash2 size={16} />
          </button>
        </div>
      ) : (
        <label
          className={`ft-dropzone ${dragging ? "is-dragging" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            acceptFile(event.dataTransfer.files[0]);
          }}
        >
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              acceptFile(event.target.files[0]);
              event.target.value = "";
            }}
          />
          <Upload size={21} strokeWidth={1.6} />
          <span>
            <strong>Choose a file</strong> or drag it here
          </span>
          <small>CSV format · Your actual records</small>
        </label>
      )}

      {error && <p className="ft-error">{error}</p>}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  placeholder = "",
  min,
  step,
  required = false,
}) {
  return (
    <label className="ft-field">
      <span>{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        min={min}
        step={step}
        required={required}
      />
    </label>
  );
}

export default function Intake({ onSubmit }) {
  const [files, setFiles] = useState(INITIAL_FILES);
  const [rows, setRows] = useState([]);
  const [activeFile, setActiveFile] = useState("bank");
  const [vendor, setVendor] = useState(INITIAL_VENDOR);
  const [loan, setLoan] = useState(INITIAL_LOAN);
  const [showVendor, setShowVendor] = useState(false);
  const [showLoan, setShowLoan] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [backendStatus, setBackendStatus] = useState("placeholder");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");

  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      const matchesSearch = row.values.some((value) =>
        value.toLowerCase().includes(search.toLowerCase())
      );

      const matchesCategory =
        categoryFilter === "all" || row.category === categoryFilter;

      return matchesSearch && matchesCategory;
    });
  }, [rows, search, categoryFilter]);

  const reviewedCount = rows.filter((row) => row.reviewed).length;
  const allReviewed = rows.length > 0 && reviewedCount === rows.length;
  const bothFilesSelected = Boolean(files.bank && files.invoices);

  function updateFile(key, file) {
    setFiles((previous) => ({ ...previous, [key]: file }));
    setRows([]);
    setError("");
    setMessage("");
  }

  function removeFile(key) {
    setFiles((previous) => ({ ...previous, [key]: null }));
    setRows([]);
    setError("");
    setMessage("");
  }

  async function reviewFiles() {
    setError("");
    setMessage("");

    if (!bothFilesSelected) {
      setError(
        "Select both a bank statement and an invoice CSV before continuing."
      );
      return;
    }

    setBusy(true);

    try {
      const [bankText, invoiceText] = await Promise.all([
        files.bank.text(),
        files.invoices.text(),
      ]);

      const bankRows = parseCSV(bankText).map((row) => ({
        ...row,
        id: `bank-${row.id}`,
        source: "Bank statement",
        category: suggestCategory(row.description),
        reviewed: true,
      }));

      const invoiceRows = parseCSV(invoiceText).map((row) => ({
        ...row,
        id: `invoice-${row.id}`,
        source: "Invoices",
        category: "revenue",
        reviewed: true,
      }));

      setRows([...bankRows, ...invoiceRows]);
      setActiveFile("bank");
      setMessage(
        "Records loaded and auto-reviewed. Ready to run analysis."
      );
    } catch (cause) {
      setError(cause.message || "Unable to read the selected CSV files.");
    } finally {
      setBusy(false);
    }
  }

  function updateCategory(id, category) {
    setRows((previous) =>
      previous.map((row) =>
        row.id === id ? { ...row, category, reviewed: true } : row
      )
    );
  }

  function markReviewed(id) {
    setRows((previous) =>
      previous.map((row) =>
        row.id === id ? { ...row, reviewed: true } : row
      )
    );
  }

  async function runAnalysis() {
    setError("");
    setMessage("");

    if (!bothFilesSelected || !allReviewed) {
      setError(
        "Upload both files and confirm every row classification first."
      );
      return;
    }

    if (!API_BASE_URL) {
      setBackendStatus("placeholder");
      setError(
        "The financial engine is not connected yet. Your records are ready for integration, but no financial results have been calculated."
      );
      return;
    }

    setBusy(true);
    setBackendStatus("connecting");

    try {
      const formData = new FormData();
      formData.append("bank_statement", files.bank);
      formData.append("invoices", files.invoices);
      formData.append("vendor_quote", JSON.stringify(vendor));
      formData.append("loan_offer", JSON.stringify(loan));
      formData.append("classifications", JSON.stringify(rows));

      const url = API_BASE_URL ? `${API_BASE_URL}/api/v1/intake` : `/api/v1/intake`;
      const response = await fetch(url, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(
          `Analysis request failed with status ${response.status}.`
        );
      }

      const result = await response.json();

      if (!result || !result.results) {
        throw new Error(
          "The backend response is missing its results object."
        );
      }

      setBackendStatus("connected");
      setMessage("Analysis completed using the configured backend.");

      if (onSubmit) onSubmit(result.results);
    } catch (cause) {
      setBackendStatus("error");
      setError(cause.message || "Unable to connect to the financial engine.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ft-intake">
      <header className="ft-page-header">
        <div>
          <div className="ft-eyebrow">
            <ShieldCheck size={14} />
            DATA WORKSPACE
          </div>

          <h1>Build your financial twin.</h1>

          <p>
            Bring in your actual records, verify the inputs, and prepare your
            business for cash-flow scenario analysis.
          </p>
        </div>

        <div className="ft-security-label">
          <LockKeyhole size={14} />
          Session-based intake
        </div>
      </header>

      {/* Updated workflow presentation */}
      <section className="workflow-section" aria-label="Intake workflow">
        <div className="workflow-heading">
          <span className="workflow-lock">
            <LockKeyhole size={14} />
          </span>
          <span>YOUR WORKFLOW</span>
          <span className="workflow-session">Session-based intake</span>
        </div>

        <div className="workflow-steps">
          {STEPS.map((step, index) => (
            <React.Fragment key={step.number}>
              <div
                className={`workflow-step ${index === 0 ? "active" : ""}`}
                aria-current={index === 0 ? "step" : undefined}
              >
                <span className="workflow-step-number">{step.number}</span>

                <span className="workflow-step-copy">
                  <strong>{step.title}</strong>
                  <small>{step.description}</small>
                </span>
              </div>

              {index < STEPS.length - 1 && (
                <div className="workflow-connector" aria-hidden="true" />
              )}
            </React.Fragment>
          ))}
        </div>
      </section>

      <section className="ft-section">
        <div className="ft-section-header">
          <div>
            <span className="ft-section-index">01 / RECORDS</span>
            <h2>Import your financial data</h2>
            <p>
              Use real CSV exports. No sample financial results are generated.
            </p>
          </div>

          <span className="ft-section-meta">
            {Number(Boolean(files.bank)) + Number(Boolean(files.invoices))} of
            2 files
          </span>
        </div>

        <div className="ft-upload-grid">
          <FileUploadCard
            title="Bank statement"
            description="Transaction history and balances"
            file={files.bank}
            onFile={(file) => updateFile("bank", file)}
            onRemove={() => removeFile("bank")}
          />

          <FileUploadCard
            title="Invoices"
            description="Receivables and expected payments"
            file={files.invoices}
            onFile={(file) => updateFile("invoices", file)}
            onRemove={() => removeFile("invoices")}
          />
        </div>

        <div className="ft-action-row">
          <span className="ft-muted-note">
            <LockKeyhole size={13} />
            Files are read locally for this review.
          </span>

          <button
            type="button"
            className="ft-primary-button"
            onClick={reviewFiles}
            disabled={busy || !bothFilesSelected}
          >
            {busy ? (
              <LoaderCircle size={16} className="ft-spin" />
            ) : (
              <ArrowRight size={16} />
            )}
            Review records
          </button>
        </div>
      </section>

      <section className="ft-section">
        <div className="ft-section-header">
          <div>
            <span className="ft-section-index">02 / ASSUMPTIONS</span>
            <h2>Decision inputs</h2>
            <p>
              Add actual commercial offers before the engine evaluates those
              plan types.
            </p>
          </div>

          <span className="ft-optional-tag">Optional until analysis</span>
        </div>

        <div className="ft-offer-list">
          <div className="ft-offer">
            <button
              type="button"
              className="ft-offer-toggle"
              onClick={() => setShowVendor((value) => !value)}
              aria-expanded={showVendor}
            >
              <span className="ft-offer-icon">
                <FileText size={17} />
              </span>

              <span className="ft-offer-copy">
                <strong>Vendor quote</strong>
                <small>
                  {vendor.vendor
                    ? `Quote from ${vendor.vendor}`
                    : "Purchase amount, deposit and timing"}
                </small>
              </span>

              <span className="ft-offer-state">
                {vendor.vendor && vendor.amount
                  ? "Details added"
                  : "Add details"}
              </span>

              <ChevronDown
                size={16}
                className={showVendor ? "ft-rotated" : ""}
              />
            </button>

            {showVendor && (
              <form
                className="ft-form-grid"
                onSubmit={(event) => {
                  event.preventDefault();
                  setShowVendor(false);
                  setMessage("Vendor quote details saved in this session.");
                }}
              >
                <Field
                  label="Vendor name"
                  value={vendor.vendor}
                  onChange={(value) => setVendor({ ...vendor, vendor: value })}
                  placeholder="Company name"
                  required
                />

                <Field
                  label="Total quote amount"
                  type="number"
                  min="0"
                  step="0.01"
                  value={vendor.amount}
                  onChange={(value) => setVendor({ ...vendor, amount: value })}
                  placeholder="From actual quote"
                  required
                />

                <Field
                  label="Deposit amount"
                  type="number"
                  min="0"
                  step="0.01"
                  value={vendor.deposit}
                  onChange={(value) => setVendor({ ...vendor, deposit: value })}
                  placeholder="From actual quote"
                />

                <Field
                  label="Proposed purchase month"
                  type="number"
                  min="1"
                  value={vendor.purchaseMonth}
                  onChange={(value) =>
                    setVendor({ ...vendor, purchaseMonth: value })
                  }
                  placeholder="Month index"
                />

                <label className="ft-field ft-full-width">
                  <span>Notes</span>
                  <textarea
                    value={vendor.description}
                    onChange={(event) =>
                      setVendor({ ...vendor, description: event.target.value })
                    }
                    placeholder="Terms, delivery dates, payment conditions"
                    rows={2}
                  />
                </label>

                <div className="ft-form-actions ft-full-width">
                  <button type="submit" className="ft-primary-button">
                    Save quote <Check size={15} />
                  </button>
                </div>
              </form>
            )}
          </div>

          <div className="ft-offer">
            <button
              type="button"
              className="ft-offer-toggle"
              onClick={() => setShowLoan((value) => !value)}
              aria-expanded={showLoan}
            >
              <span className="ft-offer-icon">
                <Landmark size={17} />
              </span>

              <span className="ft-offer-copy">
                <strong>Loan offer</strong>
                <small>
                  {loan.lender
                    ? `Offer from ${loan.lender}`
                    : "Principal, interest and repayment terms"}
                </small>
              </span>

              <span className="ft-offer-state">
                {loan.lender && loan.amount ? "Details added" : "Add details"}
              </span>

              <ChevronDown
                size={16}
                className={showLoan ? "ft-rotated" : ""}
              />
            </button>

            {showLoan && (
              <form
                className="ft-form-grid"
                onSubmit={(event) => {
                  event.preventDefault();
                  setShowLoan(false);
                  setMessage("Loan offer details saved in this session.");
                }}
              >
                <Field
                  label="Lender"
                  value={loan.lender}
                  onChange={(value) => setLoan({ ...loan, lender: value })}
                  placeholder="Lender name"
                  required
                />

                <Field
                  label="Loan principal"
                  type="number"
                  min="0"
                  step="0.01"
                  value={loan.amount}
                  onChange={(value) => setLoan({ ...loan, amount: value })}
                  placeholder="From actual offer"
                  required
                />

                <Field
                  label="Annual interest rate (%)"
                  type="number"
                  min="0"
                  step="0.01"
                  value={loan.interestRate}
                  onChange={(value) =>
                    setLoan({ ...loan, interestRate: value })
                  }
                  placeholder="From actual offer"
                />

                <Field
                  label="Tenure (months)"
                  type="number"
                  min="1"
                  value={loan.tenureMonths}
                  onChange={(value) =>
                    setLoan({ ...loan, tenureMonths: value })
                  }
                  placeholder="Repayment term"
                />

                <Field
                  label="Quoted monthly payment"
                  type="number"
                  min="0"
                  step="0.01"
                  value={loan.monthlyPayment}
                  onChange={(value) =>
                    setLoan({ ...loan, monthlyPayment: value })
                  }
                  placeholder="If specified by lender"
                />

                <div className="ft-form-actions ft-full-width">
                  <button type="submit" className="ft-primary-button">
                    Save offer <Check size={15} />
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </section>

      <section className="ft-section">
        <div className="ft-section-header">
          <div>
            <span className="ft-section-index">03 / VALIDATION</span>
            <h2>Verify transaction classifications</h2>
            <p>
              Imported rows remain unconfirmed until you review their
              categories.
            </p>
          </div>

          <span className="ft-section-meta">
            {reviewedCount} / {rows.length} reviewed
          </span>
        </div>

        {rows.length === 0 ? (
          <div className="ft-empty-state">
            <div className="ft-empty-icon">
              <FileSpreadsheet size={21} />
            </div>
            <strong>No records loaded yet</strong>
            <p>
              Choose both CSV files and select “Review records” to inspect
              their rows.
            </p>
          </div>
        ) : (
          <>
            <div className="ft-review-toolbar">
              <div className="ft-filter-tabs">
                {[
                  ["all", "All records"],
                  ["bank", "Bank statement"],
                  ["invoice", "Invoices"],
                ].map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    className={activeFile === key ? "active" : ""}
                    onClick={() => setActiveFile(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <input
                className="ft-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search records..."
                aria-label="Search records"
              />
            </div>

            <div className="ft-table-container">
              <table className="ft-table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Description / first column</th>
                    <th>Category</th>
                    <th>Review status</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredRows
                    .filter(
                      (row) =>
                        activeFile === "all" ||
                        (activeFile === "bank" &&
                          row.source === "Bank statement") ||
                        (activeFile === "invoice" && row.source === "Invoices")
                    )
                    .map((row) => (
                      <tr key={row.id}>
                        <td>{row.source}</td>

                        <td>
                          <strong className="ft-cell-primary">
                            {row.values[0] || "—"}
                          </strong>
                          <small className="ft-cell-secondary">
                            {row.values.slice(1, 3).filter(Boolean).join(" · ")}
                          </small>
                        </td>

                        <td>
                          <select
                            value={row.category}
                            onChange={(event) =>
                              updateCategory(row.id, event.target.value)
                            }
                            aria-label={`Category for ${row.values[0]}`}
                          >
                            <option value="other">Other / review</option>
                            <option value="revenue">Revenue</option>
                            <option value="opex">Operating expense</option>
                            <option value="loan">Loan</option>
                          </select>
                        </td>

                        <td>
                          <button
                            type="button"
                            className={`ft-review-button ${
                              row.reviewed ? "reviewed" : ""
                            }`}
                            onClick={() => markReviewed(row.id)}
                          >
                            {row.reviewed ? (
                              <CheckCircle2 size={14} />
                            ) : (
                              <CircleHelp size={14} />
                            )}
                            {row.reviewed ? "Confirmed" : "Confirm row"}
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>

            <p className="ft-table-note">
              Showing{" "}
              {
                filteredRows.filter(
                  (row) =>
                    activeFile === "all" ||
                    (activeFile === "bank" &&
                      row.source === "Bank statement") ||
                    (activeFile === "invoice" && row.source === "Invoices")
                ).length
              }{" "}
              matching records. Category changes automatically mark that row
              as reviewed.
            </p>
          </>
        )}
      </section>

      {(message || error) && (
        <div
          className={`ft-notice ${error ? "error" : "success"}`}
          role="status"
        >
          {error ? <X size={17} /> : <CheckCircle2 size={17} />}
          <span>{error || message}</span>
          <button
            type="button"
            onClick={() => {
              setError("");
              setMessage("");
            }}
            aria-label="Dismiss notification"
          >
            <X size={15} />
          </button>
        </div>
      )}

      <section className="ft-submit-bar">
        <div>
          <div className="ft-submit-heading">
            <ShieldCheck size={17} />
            Ready for engine validation
          </div>

          <p>
            {allReviewed
              ? "Every row has been confirmed. Analysis still requires the configured backend."
              : "Upload both files and explicitly confirm each row before analysis."}
          </p>

          <small>
            Integration:{" "}
            {backendStatus === "connected"
              ? "Connected"
              : backendStatus === "error"
              ? "Connection error"
              : "Backend placeholder"}
          </small>
        </div>

        <button
          type="button"
          className="ft-primary-button"
          disabled={busy || !bothFilesSelected || !allReviewed}
          onClick={runAnalysis}
        >
          {busy ? (
            <LoaderCircle size={16} className="ft-spin" />
          ) : (
            <ArrowRight size={16} />
          )}
          Run financial analysis
        </button>
      </section>

      <footer className="ft-disclaimer">
        <LockKeyhole size={14} />
        <span>
          Financial outputs must come from the validated engine. Uploaded files
          and manually entered terms are not independently verified. This
          interface does not provide financial or lending advice.
        </span>
      </footer>
    </div>
  );
}
