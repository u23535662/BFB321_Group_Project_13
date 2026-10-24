const toggleListViewBtn = document.getElementById("toggle_list_view_btn");
const supplierItemExpandedContent = document.querySelector(
  ".supplier_item_expanded_content",
);
const openListIcon = document.querySelector(".open_list");
const closeListIcon = document.querySelector(".close_list");

toggleListViewBtn.addEventListener("click", () => {
  supplierItemExpandedContent.classList.toggle("hidden");
  openListIcon.classList.toggle("hidden");
  closeListIcon.classList.toggle("unhide");
});
