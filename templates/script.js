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

// POPUP
// Get the modal
var modal = document.getElementById("myModal");

// Get the button that opens the modal
var btn = document.getElementById("stockButton1");

// Get the <span> element that closes the modal
var span = document.getElementsByClassName("close")[0];

// When the user clicks on the button, open the modal
btn.onclick = function () {
  modal.style.display = "block";
};

// When the user clicks on <span> (x), close the modal
span.onclick = function () {
  modal.style.display = "none";
};
window.onclick = function (event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
};
// POPUP
