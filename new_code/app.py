"""
=============================================================================
Course: BFB321 - Supply Chain Web Application
Module: new_code/app.py
Description:
    Flask web application for the Supply Chain Overview Dashboard.
    
    Principles adhered to (from BFB321 Lecture Slides):
    1. Separation of Concerns (Class 5, Slide 6):
       - app.py defines route handlers and coordinates HTTP requests/responses.
       - Business logic, database interactions, and EOQ calculations live in models.py.
       - Database connection lifecycle is managed via db.py with teardown hooks.
    2. Request Handling & Routing (Class 1 & Class 3, Slides 8, 23, 26):
       - Uses @app.route('/overview') and @app.route('/')
       - Uses request.args.get() for safe query parameter reading (e.g., ?product_id=2).
    3. Template Rendering (Class 2, Slide 14 & 18):
       - render_template('overview.html', ...) passes structured data dictionaries
         to Jinja2 templates without embedding raw HTML in Python code.
=============================================================================
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Ensure project root is available to import db.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# Prioritize current directory (./new_code/) for local models, then ROOT_DIR for db.py
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import db

# Import models specifically from new_code
try:
    import new_code.models as models
except ImportError:
    import models

# Configure Flask app with explicit template and static paths inside ./new_code/
app = Flask(
    __name__,
    template_folder=os.path.join(CURRENT_DIR, "templates"),
    static_folder=os.path.join(CURRENT_DIR, "static"),
)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "bfb321-overview-secret-key")

# Register database teardown context hook (Class 5, Slide 35)
db.init_app(app)


# =============================================================================
# ROUTES & VIEW FUNCTIONS
# =============================================================================

@app.route("/")
@app.route("/overview")
def overview():
    """
    Overview Dashboard Route:
    - Reads optional 'product_id' filter from URL query parameters (GET).
    - Calls models.get_overview_data() to aggregate real-time metrics, simulation
      curves, and stock status indicators.
    - Renders overview.html using Jinja2 template engine.
    """
    product_id = request.args.get("product_id", default=None, type=str)
    if product_id:
        product_id = product_id.strip()

    overview_data = models.get_overview_data(selected_id=product_id)

    return render_template(
        "overview.html",
        overview_data=overview_data,
        active_page="overview",
    )


@app.route("/api/overview-data")
def api_overview_data():
    """
    JSON API Endpoint for Real-Time Client-Side Updates:
    Allows dynamic AJAX fetching if needed while maintaining full server-side
    computation integrity.
    """
    product_id = request.args.get("product_id", default=None, type=str)
    data = models.get_overview_data(selected_id=product_id)
    return jsonify(data)


@app.route("/stock")
def stock_placeholder():
    """Placeholder route for Stock management navigation link."""
    return redirect(url_for("overview"))


@app.route("/pricelists")
def pricelists_placeholder():
    """Placeholder route for Pricelist navigation link."""
    return redirect(url_for("overview"))


@app.route("/suppliers")
def suppliers_placeholder():
    """Placeholder route for Suppliers navigation link."""
    return redirect(url_for("overview"))


if __name__ == "__main__":
    # Debug mode reloads the server automatically when changes are saved (Class 5, Slide 75)
    app.run(debug=True, port=5000)
