// ===== Load note data =====
const note = JSON.parse(sessionStorage.getItem("newNote") || "{}");

document.getElementById("notebookTitle").textContent =
    note.title || "Untitled Note";

document.getElementById("notebookType").textContent =
    note.type === "educational"
        ? "Educational Note"
        : "General Note";

// ===== Cells =====
const cellsContainer = document.getElementById("cellsContainer");
const addCellBtn = document.getElementById("addCellBtn");

addCellBtn.addEventListener("click", addCell);

// Add first cell by default
addCell();

function addCell() {
    const cell = document.createElement("div");
    cell.className = "cell group bg-white border rounded-lg p-4";

    cell.innerHTML = `
    <textarea
      class="w-full resize-none outline-none text-gray-800"
      rows="3"
      placeholder="Start writing here..."></textarea>

    <div
      class="mt-2 flex gap-3 text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition">
      <button class="hover:text-black">Ask AI</button>
      <button class="hover:text-black">Summarize</button>
      <button class="hover:text-red-500">Delete</button>
    </div>
  `;

    // Delete logic
    cell.querySelector("button:last-child").addEventListener("click", () => {
        cell.remove();
    });

    cellsContainer.appendChild(cell);
    cell.querySelector("textarea").focus();
}
