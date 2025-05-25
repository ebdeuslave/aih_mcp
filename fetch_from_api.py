import httpx
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("api_key")
SECURE_KEY = os.getenv("secure_key")
available_stores = os.getenv("stores")
headers = {
   "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
}


def getOrders(store: str,from_date: str, to_date: str, status:list, from_time="00:00:00", payment:str="all") -> dict:
    """
    Get the orders ids for a specific store within filter.
    Args:
        store: store name
        from_date: The starting date (format: YYYY-MM-DD)
        to_date: The ending date (format: YYYY-MM-DD) NOTE that to_date is excluded in result therefor you need to add 1 day to it
        from_time: The starting time (format: "HH:MM:SS")
        payment: payment mode (only cod and cmi, cod=cash on delivery, cmi=prepaid, all=both)
        status: list contains ids of orders status
            Ex : [2,3] (2=payment accepted, 3= "preparation in progress")
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
        url += f"&filter[payment]=[{available_payment.get(payment)}]"

    if status:
        url += f"&filter[current_state]={status}"

    with httpx.Client(http2=True) as client:
        response = client.get(url, auth=(API_KEY, ""))
        
        if response.status_code != 200:
            return {
                "hasError": True,
                "content": response.content
            }
            
        orders = [ order["id"] for order in response.json()["orders"] ]
            
        return {
            "hasError": False,
            "content": orders
        }
        
        
def getOrderDetails(store:str, id_order: int) -> dict:
    """
     Get the order details
    Args:
        store: store name
        id_order: order id
    Returns:
        dict contains hasError and content keys, if successed hasError=False content=order details else hasError=True and content=error message
    """

    url = f"https://{store}.ma/api/orders/{id_order}?output_format=JSON"

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
        

def getProductDetails(store:str, id_product:int) -> dict:
    """
     Get the product details
    Args:
        store: store name
        id_product: product id
    Returns:
        dict contains hasError and content keys, if successed hasError=False content=product details else hasError=True and content=error message
    """
    
    url = f"https://{store}.ma/api/products/{id_product}?output_format=JSON"

    with httpx.Client(http2=True) as client:
        response = client.get(url, auth=(API_KEY, ""))
        
        if response.status_code != 200:
            return {
                "hasError": True,
                "content": response.content
            }
            
        return {
            "hasError": False,
            "content": response.json()["product"]
        }


def getSupplierId(store:str, id_product:str) -> dict:
    """
    Fetch product details from getProductDetails function and get the supplier id 
    Args:
        store: store name
        id_product: product id
    Returns:
        dict contains hasError and content keys, if successed hasError=False content=supplier id else hasError=True and content=error message
    """
    
    product_details = getProductDetails(store, id_product)
    
    if product_details["hasError"]:
        return {
            "hasError": True,
            "content": product_details["content"]
        }
        
    return {
        "hasError": False,
        "content": product_details["content"]["id_supplier"]
    }
    

def getSupplierName(store:str, id_supplier:int) -> dict:
    """
    Get the supplier name
    Args:
        store: store name
        id_supplier: supplier id
    Returns:
        dict contains hasError and content keys, if successed hasError=False content=supplier name else hasError=True and content=error message
    """
    
    if id_supplier == "0":
        return {
            "hasError": False,
            "content": "CDP"
        }
    
    with httpx.Client(http2=True, headers=headers) as client:
        url = f"https://{store}.ma/api/suppliers/{id_supplier}?output_format=JSON"

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
