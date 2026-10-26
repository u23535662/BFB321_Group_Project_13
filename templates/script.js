//
//
// STOCK PAGE
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
// PRICE LIST PAGE START
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
// PRICE LIST END
//
//

//
//
// SUPPLIERS PRICE LIST PAGE START
//
//

const suppOpenBtn = document.getElementById("sup_Block");
const suppPopup = document.getElementById("supp_popup_Hold");
const suppCloseBtn = document.getElementById("close_supp");

if (suppOpenBtn && suppPopup && suppCloseBtn) {
  // Open Popup
  suppOpenBtn.addEventListener("click", function () {
    suppPopup.style.display = "flex";
  });

  // Close Popup
  suppCloseBtn.addEventListener("click", function () {
    suppPopup.style.display = "none";
  });

  // Close Popup (click outside)
  suppPopup.addEventListener("click", function (event) {
    if (event.target === suppPopup) {
      suppPopup.style.display = "none";
    }
  });
} else if (!suppOpenBtn) {
  console.log("No open Button");
} else if (!suppPopup) {
  console.log("No popup hold...");
} else if (!suppCloseBtn) {
  console.log("No popup close");
}

//
//
// SUPPLIERS PRICE LIST END
//
//
