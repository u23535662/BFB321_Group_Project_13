import db

def get_products(product_id=None):
    if product_id == '' or product_id is None:
        sql = """
        SELECT 
            p.product_id AS id,
            p.product_name AS name,
            p.product_price AS price,   
            p.stock_quantity AS starting_inv,
            p.product_holding_cost AS hc
        FROM product p
        """
        products = db.query_all(sql)
        db.close_db()
        formatted_products = []
        for p in products:
            formatted_products.append({
                'id': int(p['id']),
                'name': str(p['name']),
                'price': float(p['price']),
                'year_starting_inventory': int(p['starting_inv']),
                'holding_cost': float(p['hc'])
            })
        return formatted_products
    else:
        sql = """
        SELECT 
            p.product_id AS id,
            p.product_name AS name,
            p.product_price AS price,   
            p.stock_quantity AS starting_inv,
            p.product_holding_cost AS hc
        FROM product p
        WHERE p.product_id = %s
        """
        p = db.query_one(sql, product_id)
        db.close_db()
        if not p:
            return None
        return {
            'id': int(p['id']),
            'name': str(p['name']),
            'price': float(p['price']),
            'year_starting_inventory': int(p['starting_inv']),
            'holding_cost': float(p['hc'])
        }

def insert_product(name:str = '', price:str = '', holding_cost:str ='', starting_inventory: str = ''):
    sql = """
    INSERT INTO product (product_name, product_price, product_holding_cost, stock_quantity)
    VALUES (%s, %s, %s, %s)
    """
    id = db.execute(sql, (name, price, holding_cost, starting_inventory))
    db.close_db
    return id

def update_product(name:str, price:float, holding_cost:float, starting_inventory:int, product_id: str):
    sql = """
    UPDATE product
    SET product_name = %s, product_price= %s, product_holding_cost= %s, stock_quantity=%s
    WHERE product_id = %s
    """
    id = db.execute(sql, (name, price, holding_cost, starting_inventory, product_id))
    db.close_db()
    return id

def delete_product(product_id: str):
    sql = """
    DELETE FROM product WHERE product_id=%s
    """
    id = db.execute(sql, product_id)
    db.close_db()
    return id
