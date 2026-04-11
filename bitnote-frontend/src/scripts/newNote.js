// ===== New Note Modal: Open / Close =====

// Modal
const modal = document.getElementById("newNoteModal");

// Open buttons (Home & Explore)
const openBtn = document.getElementById("openNewNote");

// Close buttons
const closeBtn = document.getElementById("closeNewNote");
const cancelBtn = document.getElementById("cancelNewNote");

// ---- Open modal ----
openBtn?.addEventListener("click", () => {
  modal.classList.remove("hidden");
});

// ---- Close modal ----
closeBtn?.addEventListener("click", closeModal);
cancelBtn?.addEventListener("click", closeModal);

function closeModal() {
  modal.classList.add("hidden");
}
