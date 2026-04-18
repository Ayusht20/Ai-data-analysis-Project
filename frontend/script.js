async function uploadFile() {
    let fileInput = document.getElementById("file");
    let formData = new FormData();
    formData.append("file", fileInput.files[0]);

    let res = await fetch("https://ai-data-analysis-project.onrender.com//upload", {
        method: "POST",
        body: formData
    });

    let data = await res.json();
    alert(data.message);
}
async function askQuery() {
    let query = document.getElementById("query").value;

    let resultDiv = document.getElementById("result");
    resultDiv.innerHTML = "⏳ Processing...";
    let res = await fetch(`https://ai-data-analysis-project.onrender.com//ai-query?q=${query}`);
    let data = await res.json();

    displayResult(data.result);
    let container = document.getElementById("chartContainer");

    if (data.charts && data.charts.length > 0) {
        container.style.display = "block";
        container.innerHTML = "<h4>Visualization</h4>";

        data.charts.forEach(chart => {
            container.innerHTML += `
                <img src="https://ai-data-analysis-project.onrender.com//chart-image/${chart}?t=${Date.now()}" 
                     style="width:100%; margin-top:10px;">
            `;
        });
    } else {
        container.style.display = "none";
    }
}
function displayResult(data) {
    let container = document.getElementById("result");

    // 🔥 Case 1: Single value (number/string)
    if (typeof data !== "object") {
        container.innerHTML = `<p><b>Result:</b> ${data}</p>`;
        return;
    }

    // 🔥 Case 2: List of strings (like column names)
    if (Array.isArray(data) && typeof data[0] === "string") {
        let list = "<ul>";
        data.forEach(item => list += `<li>${item}</li>`);
        list += "</ul>";
        container.innerHTML = list;
        return;
    }

    // 🔥 Case 3: Empty result
    if (Array.isArray(data) && data.length === 0) {
        container.innerHTML = "<p>No data found</p>";
        return;
    }

    // 🔥 Case 4: Table (array of objects)
    if (Array.isArray(data)) {
        let table = "<table><tr>";

        Object.keys(data[0]).forEach(key => {
            table += `<th>${key}</th>`;
        });

        table += "</tr>";

        data.forEach(row => {
            table += "<tr>";
            Object.values(row).forEach(val => {
                table += `<td>${val}</td>`;
            });
            table += "</tr>";
        });

        table += "</table>";

        container.innerHTML = table;
        return;
    }

    // 🔥 Case 5: Object (like dict)
    if (typeof data === "object") {
        let table = "<table><tr>";

        Object.keys(data).forEach(key => {
            table += `<th>${key}</th>`;
        });

        table += "</tr><tr>";

        Object.values(data).forEach(val => {
            table += `<td>${val}</td>`;
        });

        table += "</tr></table>";

        container.innerHTML = table;
    }
}

async function getChart() {
    await fetch("https://ai-data-analysis-project.onrender.com//chart");
    alert("Chart saved in backend folder");
}

