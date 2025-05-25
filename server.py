from fastmcp import FastMCP
import mysql.connector
from mysql.connector import Error
from PrestashopAPI import PrestashopAPI
from utils import createProductsFile
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("api_key")
SECURE_KEY = os.getenv("secure_key")
available_stores = os.getenv("stores")

ps = PrestashopAPI(API_KEY, SECURE_KEY, available_stores)     
 
mcp = FastMCP("aih_mcp")

@mcp.tool()
def connectionToDB(command:str) -> dict:
    """
    Connection to MySQL database and fetch data\n
    **IMPORTANT**:
        DO NOT TRY TO USE ANY COMMAND THAT UPDATE/DELETE RECORDS BECAUSE YOU CANNOT, YOU ARE ALLOWED TO ONLY FETCH DATA
    Args:
        command: the command to run in mysql (IMPORTANT: DO NOT END COMMAND WITH ";" MYSQL CONNECTOR HANDLES THAT AUTOMATICALLY)
    Returns:
        dict contains hasError and content keys, if successed hasError=False content=list of fetched data else hasError=True and content=error message
    """
    
    try:
        connection = mysql.connector.connect(
            host=os.getenv("server_host"),
            port=3306,
            database=os.getenv("db_name"),
            user=os.getenv("db_user"),
            password=os.getenv("db_password"),
        )

        if connection.is_connected():
            cursor = connection.cursor()
            
            cursor.execute(command)
            
            fetched_data = [ data for data in cursor.fetchall()]
                
            connection.close()
            
            return {
                "hasError": False,
                "content": fetched_data
            }

    except Error as error:
        return {
            "hasError": True,
            "content": f"❌ Error: {error}"
        }
        
        
@mcp.tool()
def downloadInvoices(store: str, from_date: str, to_date: str, from_time:str="00:00:00", payment:str="all") -> dict:
    """
    Get orders ids from store via API using getOrders function with params\n
    then download each invoice and save it in invoices folder\n
    
    Args:
        See getOrders function for params description
    Returns:
        dict contains hasError and content keys, if successed hasError=False content=success message else hasError=True and content=error message
    """ 
    orders = ps.getOrders(store, from_date, to_date, [2,3], from_time, payment)
    
    if orders["hasError"]:
        return {
            "hasError": True,
            "content": orders["content"],
            "feedback": "error in orders"
        }
    
    if not orders["content"]:
        return {
            "hasError": False,
            "content": "No orders found"
        }
    
    print(f"fetching {len(orders['content'])} orders..")
    
    failed_to_download = []
    
    for order_id in orders["content"]:
        print(f"downloading invoice for order {order_id}")
        # NOTE that the invoice generator URL is not an officiel Prestashop URL
        url = f"https://{store}.ma/generatePDF.php?id_order={order_id}&secure_key={SECURE_KEY}"
        pdf_response = requests.get(url)
        if pdf_response.status_code != 200 or pdf_response.headers.get('Content-Type') != 'application/pdf':
            print(f"❌ Failed to download invoice for order {order_id}")
            failed_to_download.append(order_id)
            continue
        
        if not os.path.exists("invoices"): os.makedirs("invoices")
        filename = f"invoices/{store}_{order_id}.pdf"
        with open(filename, "wb") as f:
            f.write(pdf_response.content)
        
    if failed_to_download:
        return {
            "hasError": True,
            "content": f"❌ Failed to download invoices for orders: {failed_to_download}",
            "feedback": "some invoices failed to download"
        }    
        
    return {
        "hasError": False,
        "content": "Invoices downloaded successfully"
    }
    
    
@mcp.tool()
def saveProducts(store: str,from_date: str, to_date: str, from_time:str="00:00:00", payment:str="all") -> dict:
    """
    Get orders from store via API using getOrders function with params\n
    then get order details for each order using getOrderDetails function\n
    then take products ids, names, quantities, and prices from order_rows\n
    then get supplier id for each product by product id using getSupplierId function\n
    then get supplier name by supplier id using getSupplierName function\n
    then create a dict with supplier name as key and products data as value\n
    finally, create a csv file for each supplier with their products data inside products folder\n
   
    NOTE: do not double the product name in the file , instead , add its quantity to the same previous one

    Args:
        See getOrders function for params description
    Returns:
        dict contains hasError and content keys, if successed hasError=False content=success message else hasError=True and content=error message
    """ 
    data = {}
    
    orders = ps.getOrders(store, from_date, to_date, [2,3], from_time, payment)
    
    if orders["hasError"]:
        return {
            "hasError": True,
            "content": orders["content"],
            "feedback": "error in orders"
        }
    
    if not orders["content"]:
        return {
            "hasError": False,
            "content": "No orders found"
        }
    
    print(f"fetching {len(orders['content'])} orders..")
        
    for order_id in orders["content"]:
        print(f"fetching order {order_id}")
        order_details = ps.getOrderDetails(store, order_id)
        
        if order_details["hasError"]:
            return {
                "hasError": True,
                "content": order_details["content"],
                "feedback": f"error while fetching order details with id {order_id}"
            }
        
        for product in order_details["content"]["associations"]["order_rows"]:
            print(f"fetching supplier for product {product['product_name']}")
            supplier_id = ps.getSupplierId(store, product["product_id"])
            
            if supplier_id["hasError"]:
                return {
                    "hasError": True,
                    "content": supplier_id["content"],
                    "feedback": "error when fetching supplier id"
                }
                
            supplier_name = ps.getSupplierName(store, supplier_id["content"])
            
            if supplier_name["hasError"]:
                return {
                    "hasError": True,
                    "content": supplier_name["content"],
                    "feedback": "error when fetching supplier name"
                }
                
            product_name = product["product_name"]
            supplier_name = supplier_name["content"]   
                 
            if supplier_name not in data:
                data[supplier_name] = {}
            
            if product_name not in data[supplier_name]:
                data[supplier_name][product_name] = {
                    "quantity": int(product["product_quantity"]),
                    "price": product["product_price"][:-7]
                }
            else:
                print(f"detected duplicate product {product_name}, adding quantity => ({product['product_quantity']}+{data[supplier_name][product_name]['quantity']})")
                data[supplier_name][product_name]["quantity"] += int(product["product_quantity"])
           
    result = createProductsFile(data)
    
    if result["hasError"]:
        return {
            "hasError": True,
            "content": result["content"],
            "feedback": "error when creating csv files"
        }
        
    return {
        "hasError": False,
        "content": result["content"]
    }
    
if __name__ == "__main__":
    mcp.run(transport="stdio")