from fastmcp import FastMCP
import httpx
import os
import webbrowser
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from datetime import datetime
import csv
import time


load_dotenv()
API_KEY = os.getenv("api_key")
SECURE_KEY = os.getenv("secure_key")
available_stores = os.getenv("stores")
headers = {
   "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
}

mcp = FastMCP("aih_mcp")

@mcp.tool()
def getOrders(store: str,from_date: str, to_date: str, status:list, from_time="00:00:00", payment:str="all") -> dict:
    """
    Get the orders ids for a giving date via API
    Args:
        store: the given store name
        from_date: The starting date (format: YYYY-MM-DD)
        to_date: The ending date (format: YYYY-MM-DD) NOTE that the to_date is excluded in result therefor you need to add 1 day to it
        from_time: The starting time (format: "HH:MM:SS")
        payment: payment mode (only cod and cmi, cod means cash on delivery, cmi means prepaid, all is the default means both)
        status: list contains ids of orders status
            Ex : [2,3] { 2:"paiement accepte or received payment", 3: "preparation encours or not yet shipped"}
    Returns:
        Dict contains hasError and content keys, if successed hasError=False content=list of orders ids else hasError=True and content=error message
    """
    
    available_payment = {
        "cod": "Paiement comptant à la livraison (Cash on delivery)",
        "cmi": "cmi"
    }

    if store not in available_stores:
        return {
            "hasError": True,
            "content": f"Store {store} not found"
        }


    url = f"https://{store}.ma/api/orders?output_format=JSON&filter[invoice_date]=[{from_date} {from_time},{to_date}]"

    if payment != "all" and payment in available_payment:
        url += "&filter[payment]=[{payment}]"

    if status:
        url += f"&filter[current_state]={status}"

    with httpx.Client(http2=True) as client:
        response = client.get(url, auth=(API_KEY, ""))
        
        if response.status_code != 200:
            return {
                "hasError": True,
                "content": response.content
            }
            
        return {
            "hasError": False,
            "content": response.json()["orders"]
        }
        
    
@mcp.tool()
def getOrderDetails(store:str, id: int) -> dict:
    """
     Get the order details via API
    Args:
        store: the given store name
        id: order id
    Returns:
        dict contains hasError and content keys, if successed hasError=False content=order details else hasError=True and content=error message
    """
    
    if store not in available_stores:
        return {
            "hasError": True,
            "content": f"Store {store} not found"
        }

    url = f"https://{store}.ma/api/orders/{id}?output_format=JSON"

    with httpx.Client(http2=True) as client:
        response = client.get(url, auth=(API_KEY, ""))
        
        if response.status_code != 200:
            return {
                "hasError": True,
                "content": response.content
            }
        
        return {
            "hasError": False,
            "content": response.json()["order"]
        }
        

def getSupplierName(id) -> dict:
    """
    Get the supplier name
    Args:
        id: supplier id
    Returns:
        The supplier name
    """
    with httpx.Client(http2=True, headers=headers) as client:
        url = f"https://parapharma.ma/api/suppliers/{id}?output_format=JSON"
        response = client.get(url, auth=(API_KEY, ""), headers=headers)
        if response.status_code != 200:
            return {
                "hasError": True,
                "content": response.content
            }
        return {
            "hasError": False,
            "content": response.json()["supplier"]["name"]
        }


@mcp.tool()
def getProductSupplier(id_product:int) -> dict:
    """
     Get the product supplier
    Args:
        id_product: product id
    Returns:
        dict contains hasError and content keys, if successed hasError=False content=supplier name else hasError=True and content=error message
    """
    
    url = f"https://parapharma.ma/api/products/{id_product}?output_format=JSON"

    with httpx.Client(http2=True) as client:
        response = client.get(url, auth=(API_KEY, ""))
        
        if response.status_code != 200:
            return {
                "hasError": True,
                "content": response.content
            }
            
        supplier_name = getSupplierName(response.json()["product"]["id_supplier"])
        
        if supplier_name["hasError"]:
            return {
                "hasError": True,
                "content": supplier_name["content"]
            }
        
        return {
            "hasError": False,
            "content": supplier_name["content"]
        }


@mcp.tool()
def downloadInvoice(store:str, order_id:int) -> str|None:
    """
    Download the invoice PDF by opening the link in the browser
    Args:
        store: store name
        id: order id
    Returns:
        404 message or None
    """
   
    if store not in available_stores:
        return f"Store {store} not found"
        
    url = f"https://{store}.ma/generatePDF.php?id_order={order_id}&secure_key={SECURE_KEY}"
    
    webbrowser.open(url)
            

@mcp.tool()
def connectionToDB(command:str) -> dict:
    """
    Connection to mysql database and fetch data\n
    **IMPORTANT**:
        DO NOT TRY TO USE ANY COMMAND THAT UPDATE/DELETE RECORDS BECAUSE YOU CANNOT, YOU ARE ALLOWED TO ONLY FETCH DATA
    Args:
        command: the command to run in mysql (IMPORTANT: DO NOT END COMMAND WITH ";" MYSQL CONNECTOR HANDLES THAT AUTOMATICALY)
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

    except Error as e:
        return {
            "hasError": True,
            "content": f"❌ Error while connecting to MySQL: {e}"
        }
        

@mcp.tool()
def saveProducts(store: str,from_date: str, to_date: str, from_time="00:00:00", payment:str="all") -> dict:
    """
    Get orders details from store via API, and take products ids, names, quantities, and prices
    then fetch products from database by id_product and take id_supplier from each product
    then fetch it from pp_suppliers table (pp could be ps or other) and get the supplier name
    then create a folder called "products" if not exist, inside it create csv file for each supplier, name it supplierName_todayDate(YYYY-MM-DD-HH-Min-Sec).csv and put their products, quantities and prices\n
    NOTE: do not double the product name in the file , instead , add its quantity to the same previous one
        it is better to give a feedback about this point, Ex : "i found another PRODUCT_NAME i will add its quantity to the previous one"
    Args:
        store: the given store name
        from_date: The starting date (format: YYYY-MM-DD)
        to_date: The ending date (format: YYYY-MM-DD) NOTE that the to_date is excluded
        from_time: The starting time (format: "HH:MM:SS")
        payment: payment mode (only cod and cmi, cod means cash on delivery, cmi means prepaid, all is the default means both)
        current_states: list contains ids of orders status
            list of status {ID:NAME} : { 2:"paiement accepte or received payment", 3: "preparation encours or not yet shipped"}
            
    Returns:
        dict contains hasError and content keys, if successed hasError=False content=success message else hasError=True and content=error message
    """ 
    
    orders = getOrders(store, from_date, to_date, [2,3], from_time, payment)
    
    if orders["hasError"]:
        return {
            "hasError": True,
            "content": orders["content"],
            "feedback": "error in orders"
        }
    
    if not orders:
        return {
            "hasError": False,
            "content": "No orders found"
        }
    
    data = {}
    
    for order_id in orders["content"]:
        order_details = getOrderDetails(store, order_id)
        time.sleep(3)
        
        if order_details["hasError"]:
            return {
                "hasError": True,
                "content": order_details["content"],
                "feedback": "error in orders details"
            }
        
        for product in order_details["content"]["associations"]["order_rows"]:
            supplier = connectionToDB(f"SELECT name FROM pp_supplier WHERE id_supplier = {product['product_id']}") #getProductSupplier(product["product_id"])
            if supplier["hasError"]:
                return {
                    "hasError": True,
                    "content": supplier["content"],
                    "feedback": "error in supplier name"
                }
                
            supplier = "CDP" if supplier["content"] == "0" else supplier["content"]
            
            if supplier not in data:
                data[supplier] = {}
            
            product_name = product["product_name"]
            
            if product_name not in data[supplier]:
                data[supplier][product_name] = {
                    "quantity": int(product["product_quantity"]),
                    "price": product["product_price"][:-7]
                }
            else:
                data[supplier][product_name]["quantity"] += int(product["product_quantity"])
           
    createCSVFile(data)
    
    return {
        "hasError": False,
        "content": "Products saved successfully"
    }
        
        
def createCSVFile(data:dict) -> None:
    """
    Create a csv file for the supplier and write the products data in it
    Args:
        data: the data to write in the csv file contains the supplier name and the products data
    Returns:
        None
    """
    
    if not os.path.exists("products"):
        os.makedirs("products")
        
    
    for supplier, product_data in data.items():
        filename = f"products/{supplier}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv"
        with open(filename, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Quantity", "Price"])
            for product_name, product_data in product_data.items():
                writer.writerow([product_name, product_data["quantity"], product_data["price"]])


# resource

# prompt


if __name__ == "__main__":
    mcp.run()