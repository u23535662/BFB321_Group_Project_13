from flask import Flask, jsonify, render_template, request
import pymysql

from config import get_config
import db
import models


def create_app() -> Flask:
    flask_app = Flask(__name__)
    flask_app.config.from_object(get_config())
    db.init_app(flask_app)

    # =========================================================================
    # PAGE ROUTES
    # =========================================================================

    @flask_app.route("/")
    @flask_app.route("/overview")
    def overview():
        return render_template("index.html")

    @flask_app.route("/stock")
    def stock():
        return render_template("stock.html")

    @flask_app.route("/orders")
    @flask_app.route("/order")
    def orders():
        return render_template("order.html")

    # =========================================================================
    # PRODUCT API
    # =========================================================================

    @flask_app.route("/api/products", methods=["GET"])
    def api_get_products():
        try:
            products = models.get_products()
            return jsonify({"success": True, "count": len(products), "data": products}), 200
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @flask_app.route("/api/products/<int:product_id>", methods=["GET"])
    def api_get_product(product_id: int):
        try:
            product = models.get_products(product_id)
            if not product:
                return jsonify({"success": False, "error": "Product not found"}), 404
            return jsonify({"success": True, "data": product}), 200
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @flask_app.route("/api/products", methods=["POST"])
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

    @flask_app.route("/api/products/<int:product_id>", methods=["PUT"])
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

    @flask_app.route("/api/products/<int:product_id>", methods=["DELETE"])
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

    @flask_app.route("/api/suppliers", methods=["GET"])
    def api_get_suppliers():
        try:
            suppliers = models.get_suppliers()
            return jsonify({"success": True, "count": len(suppliers), "data": suppliers}), 200
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @flask_app.route("/api/suppliers/<int:supplier_id>", methods=["GET"])
    def api_get_supplier(supplier_id: int):
        try:
            supplier = models.get_suppliers(supplier_id)
            if not supplier:
                return jsonify({"success": False, "error": "Supplier not found"}), 404
            return jsonify({"success": True, "data": supplier}), 200
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @flask_app.route("/api/suppliers/<int:supplier_id>/products", methods=["GET"])
    def api_get_products_for_supplier(supplier_id: int):
        try:
            data = models.get_products_supplier(supplier_id)
            if not data:
                return jsonify({"success": False, "error": "Supplier not found"}), 404
            return jsonify({"success": True, "data": data}), 200
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @flask_app.route("/api/suppliers", methods=["POST"])
    def api_create_supplier():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

        required_fields = ("name", "from_date", "change_reason")
        missing = [field for field in required_fields if field not in data or data[field] is None]
        if missing:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing)}",
            }), 400

        try:
            name = str(data["name"]).strip()
            from_date = str(data["from_date"]).strip()
            change_reason = str(data["change_reason"]).strip()
            contact_email = str(data.get("contact_email", "")).strip()
            contact_phone = str(data.get("contact_phone", "")).strip()
            replaces_supplier_id = (
                int(data["replaces_supplier_id"])
                if data.get("replaces_supplier_id") not in (None, "")
                else None
            )

            if not name or not from_date:
                return jsonify({"success": False, "error": "Supplier name and from_date are required"}), 400

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

    @flask_app.route("/api/suppliers/<int:supplier_id>", methods=["PUT"])
    def api_update_supplier(supplier_id: int):
        supplier = models.get_suppliers(supplier_id)
        if not supplier:
            return jsonify({"success": False, "error": "Supplier not found"}), 404

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

        try:
            n_name = str(data.get("name", supplier["name"])).strip()
            n_date = str(data.get("from_date", supplier["from_date"])).strip()
            n_reason = str(data.get("change_reason", supplier["change_reason"])).strip()
            n_email = str(data.get("contact_email", supplier["contact_email"])).strip()
            n_phone = str(data.get("contact_phone", supplier["contact_phone"])).strip()
            n_replaces = (
                int(data["replaces_supplier_id"])
                if "replaces_supplier_id" in data and data["replaces_supplier_id"] not in (None, "")
                else supplier.get("replaces_supplier_id")
            )

            if not n_name or not n_date:
                return jsonify({"success": False, "error": "Supplier name and from_date are required"}), 400

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

    @flask_app.route("/api/suppliers/<int:supplier_id>", methods=["DELETE"])
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

    @flask_app.route("/api/sales", methods=["GET"])
    def api_get_sales():
        try:
            sales = models.get_sales()
            return jsonify({"success": True, "count": len(sales), "data": sales}), 200
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @flask_app.route("/api/sales/<int:sale_id>", methods=["GET"])
    def api_get_sale(sale_id: int):
        try:
            sale = models.get_sales(sale_id)
            if not sale:
                return jsonify({"success": False, "error": "Sale not found"}), 404
            return jsonify({"success": True, "data": sale}), 200
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @flask_app.route("/api/sales", methods=["POST"])
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

    @flask_app.route("/api/sales/<int:sale_id>", methods=["PUT"])
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

    @flask_app.route("/api/sales/<int:sale_id>", methods=["DELETE"])
    def api_delete_sale(sale_id: int):
        sale = models.get_sales(sale_id)
        if not sale:
            return jsonify({"success": False, "error": "Sale not found"}), 404

        try:
            models.delete_sale(sale_id)
            return jsonify({"success": True, "message": "Sale deleted successfully"}), 200
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    return flask_app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)