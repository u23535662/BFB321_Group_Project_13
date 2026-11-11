# BFB321 - Supply Chain Overview Dashboard Implementation

This module implements a dynamic Supply Chain Overview Dashboard adhering strictly to the architectural constraints, design patterns, and course principles defined in **`AGENTS.md`** and the **BFB321 Lecture Slides**.

All components and source code are isolated in this `./new_code/` directory to preserve the original repository files.

---

## 1. Directory Structure

```text
new_code/
├── app.py                      # Flask routes and application configuration
├── models.py                   # Business logic, statistical calculations, and EOQ simulation
├── nav_bar.html                # Reusable navigation template (root copy)
├── overview.html               # Main dashboard HTML template (root copy)
├── README.md                   # Complete architectural and pedagogical documentation
├── static/
│   ├── css/
│   │   └── style.css           # Preserves exact Stanway color palette and typography
│   ├── images/
│   │   └── Stanway-Logo-picture.png  # Brand logo
│   └── js/
│       └── overview.js         # Minimal, fully documented chart controller
└── templates/
    ├── nav_bar.html            # Jinja2 include component
    └── overview.html           # Jinja2 dashboard template
```

---

## 2. Key Deliverables & Features

### A. Reusable Navigation Bar (`nav_bar.html`)
- Extracted directly from `Backup/templates/index.html`.
- Implements the Jinja2 component include pattern taught in **Flask Backend Introduction (Class 2, Slide 18 & 21)** and **Class 5 (Slide 50)**.
- Features dynamic active-link highlighting (`pagenames active`, `page_active`) based on `active_page` and `request.endpoint`.
- Retains brand assets: Stanway Logo, navigation links (Overview, Stock, Pricelist, Suppliers), and the user Account box.

### B. Overview Dashboard (`overview.html`)
- Inherits/includes `nav_bar.html` via `{% include 'nav_bar.html' %}`.
- Preserves the exact color scheme from `Backup/css/style.css`:
  - Primary Background: Dark Forest Slate (`#152d2f`)
  - Dashboard Panels & Cards: Deep Sage Teal (`rgb(84, 147, 136)`)
  - Accent Borders & Glows: Mint Aqua (`rgb(155, 255, 237)`)
  - Inner Containers / Pills: Translucent Mist (`rgb(169, 217, 208)`)
  - Typography: Serif Headings (`Gelasio`) and Clean Body (`Noto Sans Display`).

### C. Dynamic Product List & Visual Stock Status Indicators
- Positioned in the left sidebar next to the navigation bar.
- Includes an **"All Products (Portfolio)"** reset option for viewing total aggregated portfolio data.
- Each product card renders real-time stock quantities and one of four distinct **Stock Status Indicators** matching course inventory logic:
  - 🔴 **Red (`badge-danger`)**: **Out of Stock** (`available_stock == 0`).
  - ⚠️ **Warning Icon / Yellow-Orange (`badge-warning`)**: **Safety Stock Level** (`0 < available_stock <= safety_stock`).
  - 🟧 **Orange (`badge-orange`)**: **Low Stock** (`safety_stock < available_stock <= ROP`).
  - 🟢 **Green (`badge-success`)**: **Healthy / OK Stock** (`available_stock > ROP`).

### D. Action Buttons (`Analysis` & `Month End`)
- Positioned in the top right area above the charts.
- **`Analysis`**: Opens an interactive modal evaluating economic order parameters ($Q^*$), holding costs ($H$), ordering costs ($S$), cycle times, and total cost optimization.
- **`Month End`**: Opens an inventory reconciliation modal displaying total physical counts, valuation of available vs. reserved vs. sold items, and cycle service level compliance.

### E. Chart 1: Stacked Bar Chart (Valuation & Allocation)
- **State A (Default - No product selected)**:
  - Displays total stock across all products measured in **Financial / Money format ($)**.
  - Three stacked bar segments:
    - 🟢 Green: Stock Available ($)
    - 🟧 Orange: Reserved Stock for Jobs ($)
    - 🔴 Red: Sold Stock / Satisfied Demand ($)
  - Tooltips format currency values (e.g., `$87,750.00`).
- **State B (Single Product Selected)**:
  - Dynamic unit switch from Money ($) to **Actual Quantity / Stock Units**.
  - Isolates the bar to display the exact unit counts (Available, Reserved, Sold) for that product.

### F. Chart 2: Real-Time EOQ Simulation Chart
- Connected to `simulation_eoq()` in `models.py`.
- **State A (Default - No product selected)**:
  - Renders the continuous daily inventory replenishment trajectories for **all products simultaneously** over a 365-day operational horizon.
- **State B (Single Product Selected)**:
  - Focuses on the selected product while non-selected product lines are grayed out with low opacity.
  - Displays **Forecasted Data** (from `simulation_eoq()`) overlapping with **Actual Historical Inventory Progression**.
  - Overlays the **Reorder Point (ROP)** (blue dashed line) and **Safety Stock (SS)** (red dashed line) thresholds.

---

## 3. Mapping to Course Principles & Lecture Slides

| Requirement / Pattern | Course Material Reference | Implementation Details |
| :--- | :--- | :--- |
| **Separation of Concerns** | *Class 5: Flask + MySQL*, Slide 6: *"Each file has ONE job. app.py never contains SQL; models.py never touches HTML."* | `app.py` handles route dispatching; `models.py` executes SQL and calculations; `db.py` handles connections; templates handle HTML presentation. |
| **Component Reusability** | *Class 2: Jinja2 Templates*, Slides 18 & 21; *Class 5*, Slide 50. | Extracted `nav_bar.html` and included via Jinja2 `{% include 'nav_bar.html' %}`. |
| **Safe Parameter Querying** | *Class 3: Request Handling*, Slide 26 & 31: `request.args.get('item')` | `request.args.get('product_id')` safely reads the URL query parameter for product filtering. |
| **Calculated Answers Rule** | *Class 5: Schema Design*, Slide 22: *"Rule: store facts once, calculate everything else."* | Stock levels, financial valuations, safety stocks, and status badges are computed on page load rather than hardcoded in the database. |
| **Dynamic Stock Badges** | *Class 5: Overview*, Slide 42: `def stock_status(stock, reorder_level)` | Extended 4-tier stock status indicator returning badge classes, icons, and labels. |
| **Safe Template Serialization** | *Class 5: Template Patterns*, Slide 52: `|tojson` | Server data injected into the frontend using `{{ overview_data|tojson }}` to prevent XSS and syntax errors. |
| **EOQ & Simulation Formulas** | *EOQ Tutorial - Supply Chain Technology*, Slides 1–3 & `models.py` | Implementation of $Q = \sqrt{\frac{2DS}{H}}$, $ROP = d \cdot L_{\text{eff}} + SS$, $SS = z \cdot \sigma \cdot \sqrt{L}$, and `simulation_eoq()`. |

---

## 4. JavaScript Usage Justification (AGENTS.md Policy)

Under `AGENTS.md`, Python/Flask backend logic must be prioritized for all application logic, and JavaScript is restricted to essential presentation requirements.

The JavaScript code in `static/js/overview.js` is strictly justified because:
1. **Interactive Real-Time Toggling Without Full Page Reload**:
   - Seamlessly switching Chart 1 between **State A (Financial $)** and **State B (Stock Units)** on click without causing a jarring page reload or losing the user's scroll position.
2. **Interactive Multi-Line Canvas Rendering**:
   - Pure HTML/CSS cannot render an interactive 365-day simulation line chart with tooltips, dynamic curve highlighting, line graying, and overlapping forecast curves. Chart.js (an industry-standard HTML5 Canvas library) provides this capability.
3. **Zero Business Logic in JavaScript**:
   - The JavaScript performs **no calculations or business logic**. All data, points, thresholds, and financial amounts are calculated 100% server-side by Python/Flask in `models.py` and passed as pre-computed datasets.

---

## 5. How to Run the Application

Activate the virtual environment and execute the Flask application:

```powershell
# From the repository root:
.\venv\Scripts\python.exe new_code\app.py
```

Then open your browser to:
- `http://127.0.0.1:5000/` or `http://127.0.0.1:5000/overview`
- To test server-side product filtering directly: `http://127.0.0.1:5000/overview?product_id=2`

