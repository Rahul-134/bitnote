export class Cell {
    constructor(type = "text") {
        this.id = Date.now();
        this.type = type;
        this.content = "";
    }
}

export function renderTextCell(cell, container) {
    const cellDiv = document.createElement("div");
    cellDiv.className = "cell";

    /* Toolbar */
    const toolbar = document.createElement("div");
    toolbar.className = "cell-toolbar";

    toolbar.innerHTML = `
      <button class="toolbar-btn" title="Move Up">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 15l-6-6-6 6"/></svg>
      </button>
      <button class="toolbar-btn" title="Move Down">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
      </button>
      <button class="toolbar-btn delete-btn" title="Delete">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    `;

    /* Content wrapper (IMPORTANT) */
    const content = document.createElement("div");
    content.className = "cell-content";

    const textarea = document.createElement("textarea");
    textarea.placeholder = "Start typing...";
    textarea.rows = 2;
    textarea.value = cell.content || "";

    textarea.addEventListener("input", () => {
        cell.content = textarea.value;
        textarea.style.height = "auto";
        textarea.style.height = textarea.scrollHeight + "px";
    });

    content.appendChild(textarea);
    cellDiv.append(toolbar, content);
    container.appendChild(cellDiv);

    /* Wiring (already added earlier) */
    const [moveUpBtn, moveDownBtn, deleteBtn] =
        toolbar.querySelectorAll("button");

    deleteBtn.addEventListener("click", () => {
        const index = window.notebook.cells.indexOf(cell);
        if (index !== -1) {
            window.notebook.cells.splice(index, 1);
            window.renderAllCells();
        }
    });

    moveUpBtn.addEventListener("click", () => {
        const index = window.notebook.cells.indexOf(cell);
        if (index > 0) {
            [window.notebook.cells[index - 1], window.notebook.cells[index]] =
                [window.notebook.cells[index], window.notebook.cells[index - 1]];
            window.renderAllCells();
        }
    });

    moveDownBtn.addEventListener("click", () => {
        const index = window.notebook.cells.indexOf(cell);
        if (index < window.notebook.cells.length - 1) {
            [window.notebook.cells[index + 1], window.notebook.cells[index]] =
                [window.notebook.cells[index], window.notebook.cells[index + 1]];
            window.renderAllCells();
        }
    });
}

