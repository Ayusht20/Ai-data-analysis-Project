const API_BASE = "https://ai-data-analysis-project.onrender.com";
const PAGE_SIZE = 10;

// Pagination state tracker
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
            throw new Error(data.error || `Upload failed with status ${res.status}`);
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

    // Single scalar value
    if (typeof data !== "object") {
        container.innerHTML = `<p><b>Result:</b> ${escapeHTML(data)}</p>`;
        return;
    }

    // Empty collection
    if (Array.isArray(data) && data.length === 0) {
        container.innerHTML = "<p>No data found</p>";
        return;
    }

    // Array of records (Table) or list of strings
    if (Array.isArray(data)) {
        tableState.data = data;
        tableState.currentPage = 1;
        tableState.totalPages = Math.ceil(data.length / PAGE_SIZE);
        renderPaginatedView();
        return;
    }

    // Single Key-Value dictionary
    const keys = Object.keys(data);
    let table = `<div class="table-wrapper"><table><thead><tr>`;
    keys.forEach(k => { table += `<th>${escapeHTML(k)}</th>`; });
    table += `</tr></thead><tbody><tr>`;
    keys.forEach(k => { table += `<td>${escapeHTML(data[k])}</td>`; });
    table += `</tr></tbody></table></div>`;

    container.innerHTML = table;
}

function renderPaginatedView() {
    const container = document.getElementById("result");
    const { data, currentPage, totalPages } = tableState;

    const startIdx = (currentPage - 1) * PAGE_SIZE;
    const currentSlice = data.slice(startIdx, startIdx + PAGE_SIZE);

    let contentHtml = "";

    // Case A: Array of primitives (e.g. column names or simple lists)
    if (typeof data[0] !== "object") {
        contentHtml += "<ul>";
        currentSlice.forEach(item => {
            contentHtml += `<li>${escapeHTML(item)}</li>`;
        });
        contentHtml += "</ul>";
    } else {
        // Case B: Tabular dataset (array of objects)
        const headers = Object.keys(data[0]);

        contentHtml += `<div class="table-wrapper"><table><thead><tr>`;
        headers.forEach(h => {
            contentHtml += `<th>${escapeHTML(h)}</th>`;
        });
        contentHtml += `</tr></thead><tbody>`;

        currentSlice.forEach(row => {
            contentHtml += "<tr>";
            headers.forEach(h => {
                contentHtml += `<td>${escapeHTML(row[h])}</td>`;
            });
            contentHtml += "</tr>";
        });
        contentHtml += `</tbody></table></div>`;
    }

    // Case C: Add pagination footer if there is more than 1 page
    if (totalPages > 1) {
        const startRecord = startIdx + 1;
        const endRecord = Math.min(startIdx + PAGE_SIZE, data.length);

        contentHtml += `
            <div class="pagination-bar">
                <span>Showing <b>${startRecord}–${endRecord}</b> of <b>${data.length}</b> records</span>
                <div class="pagination-controls">
                    <button class="page-btn" onclick="changePage(-1)" ${currentPage === 1 ? "disabled" : ""}>Previous</button>
                    <span class="page-indicator">${currentPage} / ${totalPages}</span>
                    <button class="page-btn" onclick="changePage(1)" ${currentPage === totalPages ? "disabled" : ""}>Next</button>
                </div>
            </div>
        `;
    }

    container.innerHTML = contentHtml;
}

function changePage(direction) {
    const next = tableState.currentPage + direction;
    if (next >= 1 && next <= tableState.totalPages) {
        tableState.currentPage = next;
        renderPaginatedView();
    }
}

async function getChart() {
    const chartBtn = document.getElementById("chartBtn");
    chartBtn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/chart`);
        if (!res.ok) throw new Error("Chart generation failed");
        alert("Chart saved in backend folder");
    } catch (err) {
        alert(err.message || "Failed to generate chart.");
    } finally {
        chartBtn.disabled = false;
    }
}