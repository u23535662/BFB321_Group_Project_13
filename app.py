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

if __name__ == '__main__':
    app.run(debug=True)