import os
from flask import Flask, flash, redirect, render_template, request, url_for, jsonify
import db
import models
import pymysql
from config import get_config


app = Flask(__name__)
app.config.from_object(get_config())
# Register database teardown context hook
db.init_app(app)

# OVERVIEW DASHBOARD

@app.route("/")
@app.route("/overview")
def overview():
    return render_template('index.html')

@app.route("/stock")
def stock():
    return render_template('stock.html')

@app.route("/orders")
@app.route("/order")
def orders():
    return render_template('order.html')

# =====================================================================
# JSON STUFF
# =====================================================================

# PRODUCTS
# Get all products
@app.route("/api/products", methods=["GET"])
def api_get_products():
    try:
        products = models.get_products()
        return jsonify({'success':True, 'count': len(products), 'data':products}), 200
    except Exception as e:
        return jsonify({'success':False, 'error':str(e)}), 500


    
# Get single product
@app.route("/api/products/<int:product_id>", methods=["GET"])
def api_get_product(product_id):
    try:
        product = models.get_products(product_id)
        if not product:
            return jsonify({'success':False, 'error':'Product not found'}), 404
        return jsonify({'success':True, 'data':product}), 200
    except Exception as e:
        return jsonify({'success':False, 'error':str(e)}), 500


    
# Create product
@app.route("/api/products", methods=["POST"])
def api_create_product():
    if not request.is_json:
        return jsonify({'success':False, 'error':'Content-Type must be application/json'}), 400
    data = request.get_json()

    if (not data 
        or 'name' not in data
        or 'price' not in data
        or 'holding_cost' not in data
        or 'year_starting_inventory' not in data):
        return jsonify({'success':False, 'error':'Missing required fields (name, price, holding_cost, year_starting_inventory)'}), 400

    try:
      new_product_id = models.insert_product(data['name'], data['price'], data['holding_cost'], data['year_starting_inventory'])
      new_product = {
          'id': new_product_id,
          'name': str(data['name']),
          'price': float(data['price']),
          'holding_cost': float(data['holding_cost']),
          'year_starting_inventory': int(data['year_starting_inventory'])
      }
      return jsonify({'success':True, 'data':new_product}), 201
    except Exception as e:
        return jsonify({'success':False, 'error': str(e)}), 500


    
# Update product
@app.route("/api/products/<int:product_id>", methods=["PUT"])
def api_update_product(product_id):
    product = models.get_products_raw(product_id)
    
    if not product:
        return jsonify({'success':False, 'error':'Product not found'}), 404
    if not request.is_json:
        return jsonify({'success':False, 'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    try:
        n_name = data.get('name', product['name'])
        n_price = float(data.get('price', product['price']))
        n_hc = float(data.get('holding_cost', product['holding_cost']))
        n_si = int(data.get('year_starting_inventory', product['year_starting_inventory']))

        models.update_product(n_name, n_price, n_hc, n_si, product_id)
        updated_data = {
            'product_id':product_id,
            'name':n_name,
            'price':n_price,
            'holding_cost':n_hc,
            'year_starting_inventory':n_si
        }

        return jsonify({'success':True, 'data':updated_data}),200
    except Exception as e:
        return jsonify({'success':False, 'error':str(e)}), 500


    
# Delete product
@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def api_delete_product(product_id):
    product = models.get_products_raw(product_id)
    if not product:
        return jsonify({'success':False, 'error':'Product not found'}), 404
    try:
        models.delete_product(product_id)
        return jsonify({'success': True, 'message': 'Product deleted successfully'}), 200
    except pymysql.err.IntegrityError:
        return jsonify({
            'success': False, 
            'error': 'Cannot delete this product because it is linked to existing jobs, sales, or order records.'
        }), 400
    except Exception as e:
        return jsonify({'success':False, 'error':str(e)}), 500



# SUPPLIERS 
# Get all suppliers 
@app.route("/api/suppliers", methods=["GET"])
def api_get_suppliers():
    try:
        suppliers = models.get_suppliers()
        return jsonify({'success': True, 'count': len(suppliers), 'data': suppliers}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Get single supplier (including linked products)
@app.route("/api/suppliers/<int:supplier_id>", methods=["GET"])
def api_get_supplier(supplier_id):
    try:
        supplier = models.get_suppliers(supplier_id)
        if not supplier:
            return jsonify({'success': False, 'error': 'Supplier not found'}), 404
        return jsonify({'success': True, 'data': supplier}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
   
# Create supplier
@app.route("/api/suppliers", methods=["POST"])
def api_create_supplier():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
    data = request.get_json()
    
    if not data or 'name' not in data or 'from_date' not in data or 'change_reason' not in data:
        return jsonify({'success': False, 'error': 'Missing required fields (name, from_date, change_reason)'}), 400
    
    try:
        name = str(data['name'])
        from_date = str(data['from_date'])
        change_reason = str(data['change_reason'])
        contact_email = str(data.get('contact_email', ''))
        contact_phone = str(data.get('contact_phone', ''))

        new_id = models.insert_supplier(
            name, from_date, change_reason, contact_email, contact_phone
        )
        new_supplier = models.get_suppliers(new_id)
        return jsonify({'success': True, 'data': new_supplier}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Update supplier
@app.route("/api/suppliers/<int:supplier_id>", methods=["PUT"])
def api_update_supplier(supplier_id):
    supplier = models.get_suppliers(supplier_id)
    
    if not supplier:
        return jsonify({'success': False, 'error': 'Supplier not found'}), 404
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    try:
        n_name = str(data.get('name', supplier['name']))
        n_date = str(data.get('from_date', supplier['from_date']))
        n_reason = str(data.get('change_reason', supplier['change_reason']))
        n_email = str(data.get('contact_email', supplier['contact_email']))
        n_phone = str(data.get('contact_phone', supplier['contact_phone']))

        models.update_supplier(
            name=n_name, 
            from_date=n_date, 
            change_reason=n_reason, 
            supplier_id=supplier_id, 
            contact_email=n_email, 
            contact_phone=n_phone
        )

        updated_supplier = models.get_suppliers(supplier_id)
        return jsonify({'success': True, 'message': 'Supplier updated successfully', 'data': updated_supplier}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Delete supplier
@app.route("/api/suppliers/<int:supplier_id>", methods=["DELETE"])
def api_delete_supplier(supplier_id):
    supplier = models.get_suppliers(supplier_id)
    if not supplier:
        return jsonify({'success': False, 'error': 'Supplier not found'}), 404
    try:
        models.delete_supplier(supplier_id)
        return jsonify({'success': True, 'message': 'Supplier deleted successfully'}), 200
    except pymysql.err.IntegrityError:
        return jsonify({
            'success': False, 
            'error': 'Cannot delete this supplier because it is linked to existing products or orders.'
        }), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# SALES
# Get all sales
@app.route("/api/sales", methods=["GET"])
def api_get_sales():
    try:
        sales = models.get_sales()
        return jsonify({'success': True, 'count': len(sales), 'data': sales}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Get single sale
@app.route("/api/sales/<int:sale_id>", methods=["GET"])
def api_get_sale(sale_id):
    try:
        sale = models.get_sales(sale_id)
        if not sale:
            return jsonify({'success': False, 'error': 'Sale not found'}), 404
        return jsonify({'success': True, 'data': sale}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Create sale
@app.route("/api/sales", methods=["POST"])
def api_create_sale():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
    data = request.get_json()
    
    if not data or 'product_id' not in data or 'sale_qty' not in data or 'sale_date' not in data:
        return jsonify({'success': False, 'error': 'Missing required fields (product_id, sale_qty, sale_date)'}), 400
    
    try:
        product_id = int(data['product_id'])
        sale_qty = int(data['sale_qty'])
        sale_date = str(data['sale_date'])

        new_id = models.insert_sale(product_id, sale_qty, sale_date)
        new_sale = models.get_sales(new_id)
        return jsonify({'success': True, 'data': new_sale}), 201
    except pymysql.err.IntegrityError as e:
        return jsonify({'success': False, 'error': 'Invalid product_id or other integrity constraint violation: ' + str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Update sale
@app.route("/api/sales/<int:sale_id>", methods=["PUT"])
def api_update_sale(sale_id):
    sale = models.get_sales(sale_id)
    
    if not sale:
        return jsonify({'success': False, 'error': 'Sale not found'}), 404
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    
    try:
        n_product_id = int(data.get('product_id', sale['product_id']))
        n_sale_qty = int(data.get('sale_qty', sale['sale_qty']))
        n_sale_date = str(data.get('sale_date', sale['sale_date']))

        models.update_sale(
            product_id = n_product_id, 
            sale_qty = n_sale_qty, 
            sale_date = n_sale_date, 
            sale_id = sale_id
        )
        updated_sale = models.get_sales(sale_id)
        return jsonify({'success': True, 'message': 'Sale updated successfully', 'data': updated_sale}), 200
    except pymysql.err.IntegrityError as e:
        return jsonify({'success': False, 'error': 'Invalid product_id or other integrity constraint violation: ' + str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Delete sale
@app.route("/api/sales/<int:sale_id>", methods=["DELETE"])
def api_delete_sale(sale_id):
    sale = models.get_sales(sale_id)
    if not sale:
        return jsonify({'success': False, 'error': 'Sale not found'}), 404

    try:
        models.delete_sale(sale_id)
        return jsonify({'success': True, 'message': 'Sale deleted successfully'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500








if __name__ == '__main__':
    app.run(debug=True)    