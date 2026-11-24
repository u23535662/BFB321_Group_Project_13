from flask import Flask, jsonify, render_template, request
import pymysql

from config import get_config
import db
import models



app = Flask(__name__)
app.config.from_object(get_config())
db.init_app(app)

# =========================================================================
# PAGE ROUTES
# =========================================================================

@app.route("/")
@app.route("/overview")
@app.route("/index")
def overview():
    return render_template("index.html")

@app.route("/stock")
def stock():
    return render_template("stock.html")

@app.route("/orders")
@app.route("/order")
def orders():
    return render_template("order.html")

@app.route("/suppliers")
@app.route("/supplier")
def suppliers():
    return render_template("suppliers.html")

# =========================================================================
# CHART & SIMULATION API
# =========================================================================

@app.route("/api/products/<int:product_id>/eoq-chart", methods=["GET"])
def api_get_product_eoq_chart(product_id: int):
    try:
        zoom = request.args.get("zoom", "year").strip().lower()
        if zoom not in ("month", "year"):
            zoom = "month"

        result = models.get_product_eoq_simulation(product_id=product_id, zoom=zoom)
        if not result.get("product"):
            return jsonify({"success": False, "error": "Product not found"}), 404

        return jsonify({
            "success": True,
            "zoom": zoom,
            "product": result["product"],
            "simulation": result["forecast_inventory"],
            "current_inventory": result['current_inventory'],
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/allocation-chart", methods=["GET"])
def api_get_allocation_chart():
    try:
        raw_product_id = request.args.get("product_id", "").strip()
        product_id = int(raw_product_id) if raw_product_id else 1

        if product_id is not None and not models.get_products(product_id):
            return jsonify({"success": False, "error": "Product not found"}), 404

        result = models.get_allocation_breakdown(product_id=product_id)
        return jsonify({
            "success": True,
            "data": result,
            "product_id":product_id,}), 200
    except ValueError:
        return jsonify({"success": False, "error": "Invalid product_id parameter"}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

# =========================================================================
# PRODUCT API
# =========================================================================

@app.route("/api/products", methods=["GET"])
def api_get_products():
    try:
        products = models.get_products()

        low_stock= 0
        for r in products:
            if r['current_inventory'] <= r['rop']:
                low_stock += 1

        return jsonify({"success": True, "count": len(products), "low_stock":low_stock, "data": products}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/products/<int:product_id>", methods=["GET"])
def api_get_product(product_id: int):
    try:
        product = models.get_products(product_id)
        if not product:
            return jsonify({"success": False, "error": "Product not found"}), 404
        return jsonify({"success": True, "data": product}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/products", methods=["POST"])
def api_create_product():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    required_fields = ("name", "price", "holding_cost", "year_starting_inventory", "supplier_id")
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return jsonify({
            "success": False,
            "error": f"Missing required fields: {', '.join(missing)}",
        }), 400

    try:
        name = str(data["name"]).strip()
        if not name:
            return jsonify({"success": False, "error": "Product name cannot be empty"}), 400

        supplier_id = int(data["supplier_id"])
        price = float(data["price"])
        holding_cost = float(data["holding_cost"])
        starting_inv = int(data["year_starting_inventory"])
        supplier_price = float(data.get("supplier_price", 0.0))
        units_per_package = int(data.get("units_per_package", 1))
        storage_location = str(data.get("storage_location", ""))

        new_product_id = models.insert_product(
            name=name,
            price=price,
            holding_cost=holding_cost,
            starting_inventory=starting_inv,
            storage_location=storage_location,
            supplier_id=supplier_id,
            supplier_price=supplier_price,
            units_per_package=units_per_package,
        )
        created = models.get_products(new_product_id)
        return jsonify({"success": True, "data": created}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid field value: {exc}"}), 400
    except pymysql.err.IntegrityError as exc:
        return jsonify({
            "success": False,
            "error": f"Database constraint error (check supplier_id and non-negative values): {exc}",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/products/<int:product_id>", methods=["PUT"])
def api_update_product(product_id: int):
    product = models.get_products_raw(product_id)
    if not product:
        return jsonify({"success": False, "error": "Product not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    try:
        n_name = str(data.get("name", product["name"])).strip()
        if not n_name:
            return jsonify({"success": False, "error": "Product name cannot be empty"}), 400

        n_price = float(data.get("price", product["sell_price"]))
        n_hc = float(data.get("holding_cost", product["holding_cost"]))
        n_si = int(data.get("year_starting_inventory", product["year_starting_inventory"]))
        n_location = str(data.get("storage_location", product["storage_location"]))
        n_supplier_id = (
            int(data["supplier_id"]) if "supplier_id" in data and data["supplier_id"] is not None else product["supplier_id"]
        )
        n_cost_price = (
            float(data["supplier_price"]) if "supplier_price" in data and data["supplier_price"] is not None else product["cost_price"]
        )
        n_units = (
            int(data["units_per_package"]) if "units_per_package" in data and data["units_per_package"] is not None else product["units_per_package"]
        )

        models.update_product(
            name=n_name,
            price=n_price,
            holding_cost=n_hc,
            starting_inventory=n_si,
            product_id=product_id,
            storage_location=n_location,
            supplier_id=n_supplier_id,
            supplier_price=n_cost_price,
            units_per_package=n_units,
        )
        updated = models.get_products(product_id)
        return jsonify({"success": True, "data": updated}), 200
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid field value: {exc}"}), 400
    except pymysql.err.IntegrityError as exc:
        return jsonify({"success": False, "error": f"Database constraint error: {exc}"}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def api_delete_product(product_id: int):
    product = models.get_products_raw(product_id)
    if not product:
        return jsonify({"success": False, "error": "Product not found"}), 404

    try:
        models.delete_product(product_id)
        return jsonify({"success": True, "message": "Product deleted successfully"}), 200
    except pymysql.err.IntegrityError:
        return jsonify({
            "success": False,
            "error": "Cannot delete product because it is referenced by sales, purchase orders, or inventory updates.",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

# =========================================================================
# SUPPLIER API
# =========================================================================

@app.route("/api/suppliers", methods=["GET"])
def api_get_suppliers():
    try:
        suppliers = models.get_suppliers()
        return jsonify({"success": True, "count": len(suppliers), "data": suppliers}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/suppliers/<int:supplier_id>", methods=["GET"])
def api_get_supplier(supplier_id: int):
    try:
        supplier = models.get_suppliers(supplier_id)
        if not supplier:
            return jsonify({"success": False, "error": "Supplier not found"}), 404
        return jsonify({"success": True, "data": supplier}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/suppliers/<int:supplier_id>/products", methods=["GET"])
def api_get_products_for_supplier(supplier_id: int):
    try:
        data = models.get_products_supplier(supplier_id)
        if not data:
            return jsonify({"success": False, "error": "Supplier not found"}), 404
        return jsonify({"success": True, "data": data}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/suppliers", methods=["POST"])
def api_create_supplier():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    required_fields = ("name", "from_date", "contact_email")
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return jsonify({
            "success": False,
            "error": f"Missing required fields: {', '.join(missing)}",
        }), 400

    try:
        name = str(data["name"]).strip()
        from_date = str(data["from_date"]).strip()
        contact_email = str(data["contact_email"]).strip()
        change_reason = str(data.get("change_reason") or "").strip()
        contact_phone = str(data.get("contact_phone") or "").strip()
        replaces_supplier_id = (
            int(data["replaces_supplier_id"])
            if data.get("replaces_supplier_id") not in (None, "")
            else None
        )

        if not name or not from_date or not contact_email:
            return jsonify({"success": False, "error": "Supplier name, from_date, and contact email are required"}), 400

        new_id = models.insert_supplier(
            name=name,
            from_date=from_date,
            change_reason=change_reason,
            contact_email=contact_email,
            contact_phone=contact_phone,
            replaces_supplier_id=replaces_supplier_id,
        )
        created = models.get_suppliers(new_id)
        return jsonify({"success": True, "data": created}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid field value: {exc}"}), 400
    except pymysql.err.IntegrityError as exc:
        return jsonify({"success": False, "error": f"Database constraint error: {exc}"}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/suppliers/<int:supplier_id>", methods=["PUT"])
def api_update_supplier(supplier_id: int):
    supplier = models.get_suppliers(supplier_id)
    if not supplier:
        return jsonify({"success": False, "error": "Supplier not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    try:
        n_name = str(data["name"] if data.get("name") is not None else supplier["name"]).strip()
        n_date = str(data["from_date"] if data.get("from_date") is not None else supplier["from_date"]).strip()
        n_email = str(data["contact_email"] if data.get("contact_email") is not None else supplier["contact_email"]).strip()
        n_reason = str((data["change_reason"] if "change_reason" in data else supplier["change_reason"]) or "").strip()
        n_phone = str((data["contact_phone"] if "contact_phone" in data else supplier["contact_phone"]) or "").strip()
        if "replaces_supplier_id" in data:
            raw_replaces = data["replaces_supplier_id"]
            n_replaces = int(raw_replaces) if raw_replaces not in (None, "") else None
        else:
            n_replaces = supplier.get("replaces_supplier_id")

        if not n_name or not n_date or not n_email:
            return jsonify({
                "success": False, 
                "error": "Supplier name, from_date, and contact email are required"
            }), 400

        models.update_supplier(
            name=n_name,
            from_date=n_date,
            change_reason=n_reason,
            supplier_id=supplier_id,
            contact_email=n_email,
            contact_phone=n_phone,
            replaces_supplier_id=n_replaces,
        )
        updated = models.get_suppliers(supplier_id)
        return jsonify({
            "success": True,
            "message": "Supplier updated successfully",
            "data": updated,
        }), 200
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid field value: {exc}"}), 400
    except pymysql.err.IntegrityError as exc:
        return jsonify({"success": False, "error": f"Database constraint error: {exc}"}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/suppliers/<int:supplier_id>", methods=["DELETE"])
def api_delete_supplier(supplier_id: int):
    supplier = models.get_suppliers(supplier_id)
    if not supplier:
        return jsonify({"success": False, "error": "Supplier not found"}), 404

    try:
        models.delete_supplier(supplier_id)
        return jsonify({"success": True, "message": "Supplier deleted successfully"}), 200
    except pymysql.err.IntegrityError:
        return jsonify({
            "success": False,
            "error": "Cannot delete supplier because it is linked to products, purchase orders, or replacement records.",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

# =========================================================================
# SALES API
# =========================================================================

@app.route("/api/sales", methods=["GET"])
def api_get_sales():
    try:
        sales = models.get_sales()
        return jsonify({"success": True, "count": len(sales), "data": sales}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/sales/<int:sale_id>", methods=["GET"])
def api_get_sale(sale_id: int):
    try:
        sale = models.get_sales(sale_id)
        if not sale:
            return jsonify({"success": False, "error": "Sale not found"}), 404
        return jsonify({"success": True, "data": sale}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/sales", methods=["POST"])
def api_create_sale():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    required_fields = ("product_id", "sale_qty", "sale_date")
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return jsonify({
            "success": False,
            "error": f"Missing required fields: {', '.join(missing)}",
        }), 400

    try:
        product_id = int(data["product_id"])
        sale_qty = int(data["sale_qty"])
        sale_date = str(data["sale_date"]).strip()

        if sale_qty <= 0:
            return jsonify({"success": False, "error": "sale_qty must be greater than 0"}), 400
        if not sale_date:
            return jsonify({"success": False, "error": "sale_date is required"}), 400

        new_id = models.insert_sale(product_id=product_id, sale_qty=sale_qty, sale_date=sale_date)
        new_sale = models.get_sales(new_id)
        return jsonify({"success": True, "data": new_sale}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid field value: {exc}"}), 400
    except pymysql.err.IntegrityError as exc:
        return jsonify({
            "success": False,
            "error": f"Invalid product_id or database constraint violation: {exc}",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/sales/<int:sale_id>", methods=["PUT"])
def api_update_sale(sale_id: int):
    sale = models.get_sales(sale_id)
    if not sale:
        return jsonify({"success": False, "error": "Sale not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    try:
        n_product_id = int(data.get("product_id", sale["product_id"]))
        n_sale_qty = int(data.get("sale_qty", sale["sale_qty"]))
        n_sale_date = str(data.get("sale_date", sale["sale_date"])).strip()

        if n_sale_qty <= 0:
            return jsonify({"success": False, "error": "sale_qty must be greater than 0"}), 400
        if not n_sale_date:
            return jsonify({"success": False, "error": "sale_date is required"}), 400

        models.update_sale(
            product_id=n_product_id,
            sale_qty=n_sale_qty,
            sale_date=n_sale_date,
            sale_id=sale_id,
        )
        updated_sale = models.get_sales(sale_id)
        return jsonify({
            "success": True,
            "message": "Sale updated successfully",
            "data": updated_sale,
        }), 200
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid field value: {exc}"}), 400
    except pymysql.err.IntegrityError as exc:
        return jsonify({
            "success": False,
            "error": f"Invalid product_id or database constraint violation: {exc}",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/sales/<int:sale_id>", methods=["DELETE"])
def api_delete_sale(sale_id: int):
    sale = models.get_sales(sale_id)
    if not sale:
        return jsonify({"success": False, "error": "Sale not found"}), 404

    try:
        models.delete_sale(sale_id)
        return jsonify({"success": True, "message": "Sale deleted successfully"}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

# =========================================================================
# PURCHASE ORDER API
# =========================================================================

@app.route("/api/purchase_orders", methods=["GET"])
def api_get_purchase_orders():
    try:
        purchase_orders = models.get_purchase_order()
        open_orders = 0

        for r in purchase_orders:
            if r["status"] == "Pending":
                open_orders += 1

        return jsonify({
            "success": True,
            "count": len(purchase_orders),
            "open_orders": open_orders,
            "data": purchase_orders,
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/purchase_orders/<int:order_id>", methods=["GET"])
def api_get_purchase_order(order_id: int):
    try:
        purchase_order = models.get_purchase_order(order_id)
        if not purchase_order:
            return jsonify({"success": False, "error": "Purchase order not found"}), 404
        return jsonify({"success": True, "data": purchase_order}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/purchase_orders", methods=["POST"])
def api_create_purchase_order():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    required_fields = ("supplier_id", "items")
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return jsonify({
            "success": False,
            "error": f"Missing required fields: {', '.join(missing)}",
        }), 400

    try:
        supplier_id = int(data["supplier_id"])
        order_date = str(data.get("order_date") or data.get("date") or "").strip()
        order_status = str(data.get("order_status") or data.get("status") or "Pending").strip()
        raw_items = data["items"]

        if order_status not in ("Pending", "Received", "Cancelled"):
            return jsonify({
                "success": False,
                "error": "Invalid order_status. Must be one of: Pending, Received, Cancelled",
            }), 400

        if not isinstance(raw_items, list) or len(raw_items) == 0:
            return jsonify({"success": False, "error": "items must be a non-empty list"}), 400

        parsed_items = []
        for item in raw_items:
            if not isinstance(item, dict) or item.get("product_id") is None or item.get("order_amount") is None:
                return jsonify({
                    "success": False,
                    "error": "Each item must include product_id and order_amount",
                }), 400
            prod_id = int(item["product_id"])
            qty = int(item["order_amount"])
            if qty <= 0:
                return jsonify({"success": False, "error": "order_amount must be greater than 0"}), 400
            parsed_items.append({"product_id": prod_id, "order_amount": qty})

        new_id = models.insert_purchase_order(
            supplier_id=supplier_id,
            order_date=order_date or None,
            order_status=order_status,
            items=parsed_items,
        )
        created = models.get_purchase_order(new_id)
        return jsonify({"success": True, "data": created}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid field value: {exc}"}), 400
    except pymysql.err.IntegrityError as exc:
        return jsonify({
            "success": False,
            "error": f"Database constraint error (check supplier_id, product_id, or duplicate products in order): {exc}",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/purchase_orders/<int:order_id>", methods=["PUT"])
def api_update_purchase_order(order_id: int):
    purchase_order = models.get_purchase_order(order_id)
    if not purchase_order:
        return jsonify({"success": False, "error": "Purchase order not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    try:
        n_supplier_id = int(data["supplier_id"]) if "supplier_id" in data and data["supplier_id"] is not None else purchase_order["supplier_id"]
        raw_date = data.get("order_date") if "order_date" in data else data.get("date", purchase_order["date"])
        n_order_date = str(raw_date or "").strip()
        raw_status = data.get("order_status") if "order_status" in data else data.get("status", purchase_order["status"])
        n_order_status = str(raw_status or "").strip()

        if not n_order_date:
            return jsonify({"success": False, "error": "order_date is required"}), 400
        if n_order_status not in ("Pending", "Received", "Cancelled"):
            return jsonify({
                "success": False,
                "error": "Invalid order_status. Must be one of: Pending, Received, Cancelled",
            }), 400

        parsed_items = None
        if "items" in data and data["items"] is not None:
            if not isinstance(data["items"], list) or len(data["items"]) == 0:
                return jsonify({"success": False, "error": "items must be a non-empty list"}), 400
            parsed_items = []
            for item in data["items"]:
                if not isinstance(item, dict) or item.get("product_id") is None or item.get("order_amount") is None:
                    return jsonify({
                        "success": False,
                        "error": "Each item must include product_id and order_amount",
                    }), 400
                prod_id = int(item["product_id"])
                qty = int(item["order_amount"])
                if qty <= 0:
                    return jsonify({"success": False, "error": "order_amount must be greater than 0"}), 400
                parsed_items.append({"product_id": prod_id, "order_amount": qty})

        models.update_purchase_order(
            order_id=order_id,
            supplier_id=n_supplier_id,
            order_date=n_order_date,
            order_status=n_order_status,
            items=parsed_items,
        )
        updated = models.get_purchase_order(order_id)
        return jsonify({
            "success": True,
            "message": "Purchase order updated successfully",
            "data": updated,
        }), 200
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid field value: {exc}"}), 400
    except pymysql.err.IntegrityError as exc:
        return jsonify({
            "success": False,
            "error": f"Database constraint error: {exc}",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/purchase_orders/<int:order_id>", methods=["DELETE"])
def api_delete_purchase_order(order_id: int):
    purchase_order = models.get_purchase_order(order_id)
    if not purchase_order:
        return jsonify({"success": False, "error": "Purchase order not found"}), 404

    try:
        models.delete_purchase_order(order_id)
        return jsonify({"success": True, "message": "Purchase order deleted successfully"}), 200
    except pymysql.err.IntegrityError:
        return jsonify({
            "success": False,
            "error": "Cannot delete purchase order because it is referenced by inventory updates.",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

# =========================================================================
# INVENTORY UPDATE API
# =========================================================================

@app.route("/api/inventory_updates", methods=["GET"])
def api_get_inventory_updates():
    try:
        updates = models.get_inventory_update()
        return jsonify({"success": True, "count": len(updates), "data": updates}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/inventory_updates/<int:update_id>", methods=["GET"])
def api_get_inventory_update(update_id: int):
    try:
        update = models.get_inventory_update(update_id)
        if not update:
            return jsonify({"success": False, "error": "Inventory update not found"}), 404
        return jsonify({"success": True, "data": update}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/inventory_updates", methods=["POST"])
def api_create_inventory_update():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    required_fields = ("order_id", "items")
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return jsonify({
            "success": False,
            "error": f"Missing required fields: {', '.join(missing)}",
        }), 400

    try:
        order_id = int(data["order_id"])
        update_date = str(data.get("update_date") or data.get("date") or "").strip()
        update_note = str(data.get("update_note") or data.get("note") or "").strip()
        raw_items = data["items"]

        if not isinstance(raw_items, list) or len(raw_items) == 0:
            return jsonify({"success": False, "error": "items must be a non-empty list"}), 400

        parsed_items = []
        for item in raw_items:
            if not isinstance(item, dict) or item.get("product_id") is None or item.get("update_amount") is None:
                return jsonify({
                    "success": False,
                    "error": "Each item must include product_id and update_amount",
                }), 400
            prod_id = int(item["product_id"])
            qty = int(item["update_amount"])
            if qty <= 0:
                return jsonify({"success": False, "error": "update_amount must be greater than 0"}), 400
            raw_expiry = item.get("expiry_date")
            expiry_date = str(raw_expiry).strip() if raw_expiry not in (None, "") else None
            parsed_items.append({
                "product_id": prod_id,
                "update_amount": qty,
                "expiry_date": expiry_date,
            })

        new_id = models.insert_inventory_update(
            order_id=order_id,
            update_date=update_date or None,
            update_note=update_note,
            items=parsed_items,
        )
        created = models.get_inventory_update(new_id)
        return jsonify({"success": True, "data": created}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid field value: {exc}"}), 400
    except pymysql.err.IntegrityError as exc:
        return jsonify({
            "success": False,
            "error": f"Database constraint error (check order_id, product_id, or non-positive update_amount): {exc}",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/inventory_updates/<int:update_id>", methods=["PUT"])
def api_update_inventory_update(update_id: int):
    existing = models.get_inventory_update(update_id)
    if not existing:
        return jsonify({"success": False, "error": "Inventory update not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    try:
        n_order_id = int(data["order_id"]) if "order_id" in data and data["order_id"] is not None else existing["order_id"]
        raw_date = data.get("update_date") if "update_date" in data else data.get("date", existing["update_date"])
        n_update_date = str(raw_date or "").strip()
        raw_note = data.get("update_note") if "update_note" in data else data.get("note", existing["update_note"])
        n_update_note = str(raw_note or "").strip()

        if not n_update_date:
            return jsonify({"success": False, "error": "update_date is required"}), 400

        parsed_items = None
        if "items" in data and data["items"] is not None:
            if not isinstance(data["items"], list) or len(data["items"]) == 0:
                return jsonify({"success": False, "error": "items must be a non-empty list"}), 400
            parsed_items = []
            for item in data["items"]:
                if not isinstance(item, dict) or item.get("product_id") is None or item.get("update_amount") is None:
                    return jsonify({
                        "success": False,
                        "error": "Each item must include product_id and update_amount",
                    }), 400
                prod_id = int(item["product_id"])
                qty = int(item["update_amount"])
                if qty <= 0:
                    return jsonify({"success": False, "error": "update_amount must be greater than 0"}), 400
                raw_expiry = item.get("expiry_date")
                expiry_date = str(raw_expiry).strip() if raw_expiry not in (None, "") else None
                parsed_items.append({
                    "product_id": prod_id,
                    "update_amount": qty,
                    "expiry_date": expiry_date,
                })

        models.update_inventory_update(
            update_id=update_id,
            order_id=n_order_id,
            update_date=n_update_date,
            update_note=n_update_note,
            items=parsed_items,
        )
        updated = models.get_inventory_update(update_id)
        return jsonify({
            "success": True,
            "message": "Inventory update updated successfully",
            "data": updated,
        }), 200
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid field value: {exc}"}), 400
    except pymysql.err.IntegrityError as exc:
        return jsonify({
            "success": False,
            "error": f"Database constraint error: {exc}",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/inventory_updates/<int:update_id>", methods=["DELETE"])
def api_delete_inventory_update(update_id: int):
    existing = models.get_inventory_update(update_id)
    if not existing:
        return jsonify({"success": False, "error": "Inventory update not found"}), 404

    try:
        models.delete_inventory_update(update_id)
        return jsonify({"success": True, "message": "Inventory update deleted successfully"}), 200
    except pymysql.err.IntegrityError:
        return jsonify({
            "success": False,
            "error": "Cannot delete inventory update due to database references.",
        }), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    
    
if __name__ == "__main__":
    app.run(debug=True)