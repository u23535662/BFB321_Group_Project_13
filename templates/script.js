//
//
// INDEX PAGE START
//
//

// Get the modal
const indexModal = document.getElementById("myModal");

// Get the button that opens the modal
const indexOpenBtn = document.getElementById("indexButton1");

// Get the <span> element that closes the modal
const indexCloseBtn = document.getElementById("close_index_popup");

if (indexModal && indexOpenBtn && indexCloseBtn) {
  // Open Popup
  indexOpenBtn.addEventListener("click", function () {
    indexModal.style.display = "block";
  });

  // Close Popup
  indexCloseBtn.addEventListener("click", function (event) {
    event.preventDefault();
    event.stopPropagation();
    indexModal.style.display = "none";
  });

  // Close Popup (click outside)
  indexModal.addEventListener("click", function (event) {
    if (event.target === indexModal) {
      indexModal.style.display = "none";
    }
  });
}

//
// POPUP END
//

//
//
// INDEX PAGE END
//
//

//
//
// STOCK PAGE START
//
//

//
// List View Expanding start
//

const toggleListViewBtn = document.getElementById("toggle_list_view_btn");

if (toggleListViewBtn) {
  const supplierItemExpandedContent = document.querySelector(
    ".supplier_item_expanded_content",
  );
  const openListIcon = document.querySelector(".open_list");
  const closeListIcon = document.querySelector(".close_list");

  // Toggle list view between open and close
  toggleListViewBtn.addEventListener("click", () => {
    supplierItemExpandedContent.classList.toggle("hidden");
    openListIcon.classList.toggle("hidden");
    closeListIcon.classList.toggle("unhide");
  });
}

//
// List View expanding end
//

//
// POPUP START
//

// Get the modal
const stockModal = document.getElementById("myModal");

// Get the button that opens the modal
const stockOpenBtn = document.getElementById("stockButton1");

// Get the <span> element that closes the modal
const stockCloseBtn = document.getElementById("close_stock_popup");

if (stockModal && stockOpenBtn && stockCloseBtn) {
  // Open Popup
  stockOpenBtn.addEventListener("click", function () {
    stockModal.style.display = "block";
  });

  // Close Popup
  stockCloseBtn.addEventListener("click", function (event) {
    event.preventDefault();
    event.stopPropagation();
    stockModal.style.display = "none";
  });

  // Close Popup (click outside)
  stockModal.addEventListener("click", function (event) {
    if (event.target === stockModal) {
      stockModal.style.display = "none";
    }
  });
}

//
// POPUP END
//

//
//
// STOCK PAGE END
//
//

//
//
// ORDER PAGE START
//
//

const plOpenBtn = document.getElementById("pl_Block");
const plPopup = document.getElementById("pl_popup_Hold");
const plCloseBtn = document.getElementById("close_pl");

if (plOpenBtn && plPopup && plCloseBtn) {
  // Open Popup
  plOpenBtn.addEventListener("click", function () {
    plPopup.style.display = "flex";
  });

  // Close Popup
  plCloseBtn.addEventListener("click", function () {
    plPopup.style.display = "none";
  });

  // Close Popup (click outside)
  plPopup.addEventListener("click", function (event) {
    if (event.target === plPopup) {
      plPopup.style.display = "none";
    }
  });
} else if (!plOpenBtn) {
  console.log("No open Button");
} else if (!plPopup) {
  console.log("No popup hold...");
} else if (!plCloseBtn) {
  console.log("No popup close");
}


//
//
// ORDER PAGE END
//
//

//
//
// SUPPLIERS PRICE LIST PAGE START
//
//

const supOpenBtn = document.getElementById("sup_Block");
const supPopup = document.getElementById("sup_popup_Hold");
const supCloseBtn = document.getElementById("close_sup");

if (supOpenBtn && supPopup && supCloseBtn) {
  // Open Popup
  supOpenBtn.addEventListener("click", function () {
    supPopup.style.display = "flex";
  });

  // Close Popup
  supCloseBtn.addEventListener("click", function () {
    supPopup.style.display = "none";
  });

  // Close Popup (click outside)
  supPopup.addEventListener("click", function (event) {
    if (event.target === supPopup) {
      supPopup.style.display = "none";
    }
  });
} else if (!supOpenBtn) {
  console.log("No open Button");
} else if (!supPopup) {
  console.log("No popup hold...");
} else if (!supCloseBtn) {
  console.log("No popup close");
}

//
//
// SUPPLIERS PRICE LIST END
//
//

//
//
// SUPPLIERS ADD MODAL START
//
//
// Get the modal

//
//
// SUPPLIERS ADD MODAL END
//
//
