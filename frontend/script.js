const uploadBtn = document.getElementById("uploadBtn");
const pdfFile = document.getElementById("pdfFile");
const queryBtn = document.getElementById("queryBtn");
const queryText = document.getElementById("queryText");
const resultsDiv = document.getElementById("results");

// Change this if your backend is at a different URL/port
const BASE_URL = "http://127.0.0.1:5001";

uploadBtn.addEventListener("click", async () => {
  if (!pdfFile.files.length) {
    alert("Please select a PDF file first.");
    return;
  }
  const file = pdfFile.files[0];
  
  const formData = new FormData();
  formData.append("file", file);
  
  try {
    const response = await fetch(`${BASE_URL}/upload-pdf`, {
      method: "POST",
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }
    
    const data = await response.json();
    alert(data.message);
  } catch (error) {
    console.error(error);
    alert("Failed to upload and ingest PDF.");
  }
});

queryBtn.addEventListener("click", async () => {
  const query = queryText.value.trim();
  if (!query) {
    alert("Please enter a query.");
    return;
  }
  
  const formData = new FormData();
  formData.append("query", query);
  formData.append("top_k", "5"); // You can make this dynamic
  
  try {
    const response = await fetch(`${BASE_URL}/query`, {
      method: "POST",
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }
    
    const data = await response.json();
    displayResults(data.results);
  } catch (error) {
    console.error(error);
    alert("Query failed.");
  }
});

function displayResults(results) {
  resultsDiv.innerHTML = ""; // clear old results
  if (!results || results.length === 0) {
    resultsDiv.textContent = "No results found.";
    return;
  }
  results.forEach(res => {
    const div = document.createElement("div");
    div.innerHTML = `
      <hr>
      <p><strong>Rank:</strong> ${res.rank}</p>
      <p><strong>Source:</strong> ${res.source}</p>
      <p><strong>Content:</strong> ${res.content}</p>
    `;
    resultsDiv.appendChild(div);
  });
}
