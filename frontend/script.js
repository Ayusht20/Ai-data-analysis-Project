const API_BASE = "http://127.0.0.1:8000";
const PAGE_SIZE = 10;
// "https://ai-data-analysis-project.onrender.com"||"http://localhost:8000" || 

let tableState = {
    data: [],
    currentPage: 1,
    totalPages: 1
};

function escapeHTML(str) {
    return String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

async function uploadFile() {
    const fileInput = document.getElementById("file");
    const file = fileInput?.files[0];
    const uploadBtn = document.getElementById("uploadBtn");

    if (!file) {
        alert("Please choose a CSV file first.");
        return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
        alert("Only CSV files are supported.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    uploadBtn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/upload`, {
            method: "POST",
            body: formData
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || data.detail || `Upload failed with status ${res.status}`);
        }

        alert(data.message || "File uploaded successfully");
    } catch (err) {
        alert(err.message || "Network error while uploading file.");
    } finally {
        uploadBtn.disabled = false;
    }
}

async function askQuery() {
    const queryInput = document.getElementById("query");
    const query = queryInput.value.trim();
    const resultDiv = document.getElementById("result");
    const askBtn = document.getElementById("askBtn");
    const container = document.getElementById("chartContainer");

    if (!query) {
        alert("Please enter a query before analyzing.");
        return;
    }

    resultDiv.innerHTML = `
        <div class="loader">
            <div class="dots"><span></span><span></span><span></span></div>
            <span>Analyzing your data…</span>
        </div>
    `;
    askBtn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/ai-query?q=${encodeURIComponent(query)}`);
        const data = await res.json();

        if (!res.ok || data.error) {
            const errorMsg = data.error || `Request failed with status ${res.status}`;
            resultDiv.innerHTML = `<p style="color:var(--danger);">${escapeHTML(errorMsg)}</p>`;
            return;
        }

        if (data.result === undefined || data.result === null) {
            resultDiv.innerHTML = "<p>No result found</p>";
        } else {
            displayResult(data.result);
        }

        resultDiv.classList.remove("fade-in");
        void resultDiv.offsetWidth;
        resultDiv.classList.add("fade-in");

        if (data.charts && data.charts.length > 0) {
            container.style.display = "block";
            let chartHtml = "<h4>Visualization</h4>";

            data.charts.forEach(chart => {
                chartHtml += `
                    <img src="${API_BASE}/chart-image/${encodeURIComponent(chart)}?t=${Date.now()}" 
                         alt="Generated Chart"
                         loading="lazy">
                `;
            });

            container.innerHTML = chartHtml;
            container.classList.remove("fade-in");
            void container.offsetWidth;
            container.classList.add("fade-in");
        } else if (container) {
            container.style.display = "none";
        }
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger);">${escapeHTML(err.message || "Failed to fetch response.")}</p>`;
    } finally {
        askBtn.disabled = false;
    }
}

function displayResult(data) {
    const container = document.getElementById("result");

    if (data === null || data === undefined) {
        container.innerHTML = "<p>No result found</p>";
        return;
    }

    if (typeof data !== "object") {
        container.innerHTML = `<p><b>Result:</b> ${escapeHTML(data)}</p>`;
        return;
    }

    if (Array.isArray(data) && data.length === 0) {
        container.innerHTML = "<p>No data found</p>";
        return;
    }

    if (Array.isArray(data)) {
        tableState.data = data;
        tableState.currentPage = 1;
        tableState.totalPages = Math.ceil(data.length / PAGE_SIZE);
        renderPaginatedView("result");
        return;
    }

    // Compound Object Handling (e.g. {least_skill, question_count, records: [...]})
    if (typeof data === "object") {
        const nestedKey = Object.keys(data).find(k => Array.isArray(data[k]));

        if (nestedKey && Array.isArray(data[nestedKey])) {
            let metaHtml = `<div style="display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap;">`;
            Object.keys(data).forEach(k => {
                if (k !== nestedKey && typeof data[k] !== "object") {
                    metaHtml += `
                        <div style="background: var(--panel-raised); border: 1px solid var(--line-strong); padding: 6px 12px; border-radius: 4px; font-size: 13px;">
                            <span style="color: var(--muted); text-transform: capitalize;">${escapeHTML(k.replace(/_/g, " "))}:</span>
                            <b style="color: var(--brass); margin-left: 4px;">${escapeHTML(data[k])}</b>
                        </div>
                    `;
                }
            });
            metaHtml += `</div><div id="nestedTableContainer"></div>`;
            container.innerHTML = metaHtml;

            tableState.data = data[nestedKey];
            tableState.currentPage = 1;
            tableState.totalPages = Math.ceil(data[nestedKey].length / PAGE_SIZE);
            renderPaginatedView("nestedTableContainer");
            return;
        }

        // Standard Key-Value
        const keys = Object.keys(data);
        let table = `<div class="table-wrapper"><table><thead><tr>`;
        keys.forEach(k => { table += `<th>${escapeHTML(k)}</th>`; });
        table += `</tr></thead><tbody><tr>`;
        keys.forEach(k => {
            const val = typeof data[k] === "object" ? JSON.stringify(data[k]) : data[k];
            table += `<td>${escapeHTML(val)}</td>`;
        });
        table += `</tr></tbody></table></div>`;
        container.innerHTML = table;
    }
}

function renderPaginatedView(targetId = "result") {
    const container = document.getElementById(targetId);
    if (!container) return;

    const { data, currentPage, totalPages } = tableState;
    const startIdx = (currentPage - 1) * PAGE_SIZE;
    const currentSlice = data.slice(startIdx, startIdx + PAGE_SIZE);

    let contentHtml = "";

    if (typeof data[0] !== "object") {
        contentHtml += "<ul>";
        currentSlice.forEach(item => {
            contentHtml += `<li>${escapeHTML(item)}</li>`;
        });
        contentHtml += "</ul>";
    } else {
        const headers = Object.keys(data[0]);

        contentHtml += `<div class="table-wrapper"><table><thead><tr>`;
        headers.forEach(h => {
            contentHtml += `<th>${escapeHTML(h)}</th>`;
        });
        contentHtml += `</tr></thead><tbody>`;

        currentSlice.forEach(row => {
            contentHtml += "<tr>";
            headers.forEach(h => {
                const cellVal = typeof row[h] === "object" ? JSON.stringify(row[h]) : row[h];
                contentHtml += `<td>${escapeHTML(cellVal)}</td>`;
            });
            contentHtml += "</tr>";
        });
        contentHtml += `</tbody></table></div>`;
    }

    if (totalPages > 1) {
        const startRecord = startIdx + 1;
        const endRecord = Math.min(startIdx + PAGE_SIZE, data.length);

        contentHtml += `
            <div class="pagination-bar">
                <span>Showing <b>${startRecord}–${endRecord}</b> of <b>${data.length}</b> records</span>
                <div class="pagination-controls">
                    <button class="page-btn" onclick="changePage(-1, '${targetId}')" ${currentPage === 1 ? "disabled" : ""}>Previous</button>
                    <span class="page-indicator">${currentPage} / ${totalPages}</span>
                    <button class="page-btn" onclick="changePage(1, '${targetId}')" ${currentPage === totalPages ? "disabled" : ""}>Next</button>
                </div>
            </div>
        `;
    }

    container.innerHTML = contentHtml;
}

function changePage(direction, targetId = "result") {
    const next = tableState.currentPage + direction;
    if (next >= 1 && next <= tableState.totalPages) {
        tableState.currentPage = next;
        renderPaginatedView(targetId);
    }
}