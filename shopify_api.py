import requests
import json
import time
from datetime import datetime
import os
import re
from logger import logger, settings

# Constants
SHOP_NAME = "fratelli-rossi-italy"
API_KEY = os.environ.get("API_KEY")
API_PASSWORD = os.environ.get("API_PASSWORD")
API_VERSION = "2023-04"
BASE_URL = f"https://{API_KEY}:{API_PASSWORD}@{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/"
GRAPHQL_URL = BASE_URL + "graphql.json"
LOCATION_ID = os.environ.get("LOCATION_ID")


PAUSE = 2 # seconds

categories = {
    "Uomo": { #10 
        "Derby": "Derby",
        "Francesine": "Francesine",
        "Doppia Fibbia": "Fibbie",
        "Mocassini Da Barca": "Mocassini Da Barca",
        "Mocassini College": "Mocassini College",
        "Mocassini Con Gommini": "Mocassini Con Gommini",
        "Mocassini Con Nappine": "Mocassini Con Nappine",
        "Polacchine": "Stivaletti",
        "Singola Fibbia": "Fibbie",
        "Sneakers": "Sneakers",
        "Stivaletti Chelsea": "Stivaletti Chelsea",
        "Stivaletti": "Stivaletti"
    },
    "Donna": { #7
        "Ballerine": "Ballerine",
        "Chanel": "Decollete E Chanel",
        "Decollete": "Decollete E Chanel",
        "Mocassini": "Mocassini E Stringate",
        "Mocassini Con Gommini": "Mocassini E Stringate",
        "Stringate E Fibbie": "Mocassini E Stringate",
        "Sandali": "Sandali",
        "Sabot": "Flats E Mules",
        "Slippers": "Flats E Mules",
        "Sneakers": "Sneakers",
        "Stivaletti Chelsea": "Stivaletti E Stivali",
        "Stivaletti Con Lacci": "Stivaletti E Stivali",
        "Stivaletti Con Tacco": "Stivaletti E Stivali",
        "Stivali": "Stivaletti E Stivali",
        "Tronchetti": "Stivaletti E Stivali"
    }
}

# Shopify API functions

def make_request(url, method='GET', data=None):
    """
    Make a request to the Shopify API and handle rate limiting.
    """
    wait = 1  # Initial wait time in seconds
    while True:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        elif method == 'DELETE':
            response = requests.delete(url)
        elif method == 'PUT':
            response = requests.put(url, json=data)

        if response.status_code == 429:  # Rate limit error
            wait_time = response.headers.get('Retry-After', wait)
            logger.info(f"\nRate limit reached, retrying after {wait_time} seconds...\n", extra={'to_console': True}) #settings["CONSOLE"]})
            time.sleep(float(wait_time))
            wait *= 2  # Exponential backoff
            continue

        if response.status_code == 400 or response.status_code == 404:
            logger.info(response.json(), extra={'to_console': True})

        return response  # Return response for successful or other error codes

def get_product_by_id(product_id):
    product_url = BASE_URL + f"products/{product_id}.json"
    metafields_url = BASE_URL + f"products/{product_id}/metafields.json"

    product_response = make_request(product_url)
    metafields_response = make_request(metafields_url)

    product_data = product_response.json()
    metafields_data = metafields_response.json()

    # Add metafields to the product data
    product_data['product']['metafields'] = metafields_data.get('metafields', [])

    return product_data

def get_product_by_handle(product_handle, include_metafields=False):
    url = BASE_URL + f"products.json?handle={product_handle}"
    response = make_request(url)
    products_data = response.json()

    # Extract the first product, return None if no products are found
    product = next(iter(products_data.get('products', [])), None)

    if product and include_metafields:
        # Fetch and add metafields for the product
        product_id = product['id']
        metafields_url = BASE_URL + f"products/{product_id}/metafields.json"
        metafields_response = make_request(metafields_url)
        metafields_data = metafields_response.json()

        # Add metafields to the product
        product['metafields'] = metafields_data.get('metafields', [])

    return product

def get_product_id_by_handle(product_handle):
    """
    Retrieve the product ID using its handle.
    """
    url = BASE_URL + f"products.json?handle={product_handle}"
    response = make_request(url)
    data = response.json()
    products = data.get('products', [])

    return products[0]['id'] if products else None

def get_handle_by_product_id(product_id):
    """
    Retrieve the handle of a product using its product ID.
    """
    url = BASE_URL + f"products/{product_id}.json"
    response = make_request(url)
    product_data = response.json()

    return product_data['product']['handle'] if 'product' in product_data else None

# Function to delete a product
def delete_product(product_id):
    url = BASE_URL + f"products/{product_id}.json"
    response = make_request(url, method='DELETE')
    return response.status_code

def delete_product_by_handle(product_handle):
    """
    Delete a product using its handle.
    """
    product_id = get_product_id_by_handle(product_handle)
    if product_id:
        url = BASE_URL + f"products/{product_id}.json"
        response = make_request(url, method='DELETE')
        return response.status_code
    else:
        return "Product not found with the given handle."

# Function to create a new product
def create_product(product_data):
    url = BASE_URL + "products.json"
    response = make_request(url, method='POST', data={"product": product_data})
    return response.json(), response.status_code

def update_product_metafields(id, metafield_data):
    url = BASE_URL + f"products/{id}/metafields.json"
    response = make_request(url, method='POST', data=metafield_data)
    return response

def check_if_handle_exists(handle):
    url = BASE_URL + f"products.json?handle={handle}"
    response = make_request(url)
    data = response.json()
    return bool(data['products'])  # Returns True if product exists

# Function to parse the Link header and get the next page URL
def parse_link_header(link_header):
    if not link_header:
        return None

    for part in link_header.split(','):
        url, rel = part.split(';')
        url = url.strip('<> ')
        rel_type = rel.split('=')[1].strip(' "')

        if rel_type == 'next':
            # Extracting the part after API version from the URL
            return url.split(API_VERSION)[1]

    return None

# Function to get all product handles with cursor-based pagination
def get_all_product_handles():
    logger.info("Getting all product handles on Shopify", extra={'to_console': settings["CONSOLE"]})
    handles = []
    url = BASE_URL + "products.json?limit=50"

    while url:
        response = make_request(url)
        data = response.json()
        products = data.get('products', [])
        
        # Appending each product's handle to the list
        handles.extend(product['handle'] for product in products)

        # Extract the URL for the next page and prepare the full URL for the next request
        next_page_url = parse_link_header(response.headers.get('Link'))
        url = BASE_URL + next_page_url if next_page_url else None

    time.sleep(PAUSE)
    logger.info(f"    Number of products: {len(handles)}", extra={'to_console': settings["CONSOLE"]})
    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})

    return handles

def update_product_metafields_with_associations(shopify_handles, catalog_associations):
    
    logger.info("Updating product associations in Shopify", extra={'to_console': settings["CONSOLE"]})
    total_processed = 0
    
    for handle in sorted(shopify_handles):
        total_processed += 1
        # Find associated handles and convert them to product IDs
        associated_handles = catalog_associations.get(handle, [])

        associated_ids = [get_product_id_by_handle(assoc_handle) for assoc_handle in associated_handles if assoc_handle in catalog_associations]

        # Count the number of valid associations
        valid_associations_count = sum(1 for id in associated_ids if id)

        # Prepare the metafield data
        metafield_data = {
            "metafield": {
                "namespace": "custom",
                "key": "colori",
                "value": '[]'
            }
        }
        
        if valid_associations_count > 0:
            # Format the association value
            association_value = json.dumps([f"gid://shopify/Product/{id}" for id in associated_ids if id])

            # create association
            metafield_data["metafield"]["value"] = association_value

        # Update the product metafields
        product_id = get_product_id_by_handle(handle)
        response = update_product_metafields(product_id, metafield_data)
        logger.info(f"    {total_processed:<4}  |  {handle:5} Updated  |  ID: {product_id:13}  |  Status code: {response.status_code}  |  Associations: {valid_associations_count} {[get_handle_by_product_id(id) for id in associated_ids if id]}", extra={'to_console': settings["CONSOLE"]})

    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})

def categorize_itemcodes_in_shopify(shopify_handles, catalog):
    """
    Categorize itemCodes in the catalog as either present or missing in the Shopify store.

    :param shopify_handles: List of product handles (IDs) from Shopify
    :param catalog: The catalog with product associations
    :return: Two lists, one of itemCodes present in Shopify and another of missing itemCodes
    """
    logger.info("Comparing Sinesy Catalog to Shopify", extra={'to_console': settings["CONSOLE"]})

    # Extract itemCodes from the catalog
    catalog_item_codes = set(catalog.keys())

    # Convert Shopify handles to a set for efficient comparison
    shopify_handles_set = set(shopify_handles)

    # Find itemCodes present in Shopify and those missing
    present_itemcodes = catalog_item_codes & shopify_handles_set
    missing_itemcodes = catalog_item_codes - shopify_handles_set
    time.sleep(PAUSE)
    # Log the total number of products in the enhanced catalog
    logger.info(f"    ItemCodes present in Catalog: {len(catalog)}", extra={'to_console': settings["CONSOLE"]})
    logger.info(f"    ItemCodes present in Shopify: {len(present_itemcodes)}", extra={'to_console': settings["CONSOLE"]})
    logger.info(f"    ItemCodes missing in Shopify: {len(missing_itemcodes)}", extra={'to_console': settings["CONSOLE"]})
    assert(len(catalog) == len(present_itemcodes) + len(missing_itemcodes))
    time.sleep(PAUSE)
    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})

    return list(present_itemcodes), list(missing_itemcodes)

def create_products_in_shopify(missing_itemcodes, catalog, image_urls):
    
    logger.info("Creating products on Shopify", extra={'to_console': settings["CONSOLE"]})
    
    shopify_handles_created = []
    total_processed = 0
    total_successfully_created = 0
    
    for item_code in sorted(missing_itemcodes):
        
        total_processed += 1
        
        if check_if_handle_exists(item_code):
            logger.info(f"    {total_processed:<4}  |  {item_code:5} Skipped  |  Handle already exists in Shopify", extra={'to_console': settings["CONSOLE"]})
            continue
        
        num_images = len(image_urls[item_code])
        if num_images == 0:
            logger.info(f"    {total_processed:<4}  |  {item_code:5} Failed   |  -----------------  |  Status code: 400  |  Images: {num_images}", extra={'to_console': settings["CONSOLE"]})
            continue
        
        details = catalog[item_code]
        new_product_data = {
            "title": item_code,
            "body_html": "Le calzature Fratelli Rossi, frutto di una sapiente maestria artigianale italiana, \
                          incarnano l'eccellenza nella qualità e nell'eleganza. Ciascuna creazione è un capolavoro, \
                          plasmato e rifinito da esperti calzolai, custodi di un'eredità tramandata attraverso generazioni. \
                          La loro passione, abilità manuale e profonda conoscenza del mestiere si riflettono in ogni \
                          pezzo, testimoniando l'antica tradizione del 'saper fare' nel mondo calzaturiero.",
            "vendor": "Fratelli Rossi",
            "product_type": categories[details['Genere']][details['Categoria']],
            "status": "active", #if len(image_urls[item_code]) > 0 else "draft",
            "tags": [details['Genere'], details['Merceologia']],
            "published_at": datetime.utcnow().isoformat(),
            "options": [
                {
                    "name": "Size",
                    #"values": men_sizes  # Convert to list
                    "values": list(details['Taglie'].keys())  # Convert to list
                }
            ],
            "variants": [
                {
                    "option1": size, 
                    "price": details['Prezzo Retail'] if details['Prezzo Retail'] else str(round(float(details['Prezzo'])*1.25/10)*10),
                    "inventory_quantity": 0,
                    "barcode": details['Taglie'][size],
                    "inventory_management": "shopify",
                    "sku": None
                } for size in details['Taglie'].keys()
            ],
            "metafields": [
                {
                    "namespace": "custom",
                    "key": "color_name",
                    "value": details['Colore'],
                    "type": "single_line_text_field"
                },
                {
                    "namespace": "custom",
                    "key": "size_guide",
                    "value": "gid://shopify/Metaobject/24776048921" if details['Genere'] == 'Uomo' else "gid://shopify/Metaobject/33228030233"
                },
                {
                    "namespace": "custom",
                    "key": "shipping",
                    "value": "gid://shopify/Metaobject/24775917849"
                },
                {
                    "namespace": "custom",
                    "key": "materiale",
                    "value": details['Materiale'],
                    "type": "single_line_text_field"
                },
                {
                    "namespace": "custom",
                    "key": "suola",
                    "value": details['Suola'],
                    "type": "single_line_text_field"
                },
                {
                    "namespace": "custom",
                    "key": "tacco",
                    "value": details['Tacco'],
                    "type": "single_line_text_field"
                }
            ],
            "images": [
                {
                    "src": url, 
                } for url in image_urls[item_code]
            ]
        }
        
        create_product_response, status_code = create_product(new_product_data)
        if status_code == 201 and 'product' in create_product_response:
            total_successfully_created += 1
            shopify_handles_created.append(create_product_response['product']['handle'])
            logger.info(f"    {total_processed:<4}  |  {create_product_response['product']['handle']:5} Created  |  ID: {create_product_response['product']['id']:13}  |  Status code: {status_code}  |  Images: {num_images}", extra={'to_console': settings["CONSOLE"]})
        else:
            logger.info(f"    {total_processed:<4}  |  {item_code:5} Failed   |  Status code: {status_code}", extra={'to_console': settings["CONSOLE"]})
            
    logger.info(f"    Products created/processed: {total_successfully_created}/{total_processed}", extra={'to_console': settings["CONSOLE"]})
    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})

    return shopify_handles_created

def update_shopify_stock(location_id, item_id, quantity):
    # Set the endpoint URL
    url = f"{BASE_URL}inventory_levels/set.json"
    # Prepare the data payload
    data = {
        "location_id": location_id,
        "inventory_item_id": item_id,
        "available": quantity
    }
    # Make the POST request
    response = make_request(url, method='POST', data=data)
    return response

def add_image_to_product(product_handle, image_url):
    """
    Add an image to a product given its handle and the image URL.
    """
    # First, get the product ID using the handle
    product_id = get_product_id_by_handle(product_handle)
    if not product_id:
        return "Product not found with the given handle."

    # Prepare the URL for adding an image to the product
    add_image_url = BASE_URL + f"products/{product_id}/images.json"

    # Prepare the image data
    image_data = {
        "image": {
            "src": image_url
        }
    }

    # Make the POST request to add the image
    response = make_request(add_image_url, method='POST', data=image_data)

    # Return the response
    return response.json(), response.status_code

def fetch_all_files(n=250):

    logger.info("Fetching all image files", extra={'to_console': settings["CONSOLE"]})

    all_files = []

    def fetch_files(cursor=None):
        after_argument = f', after: "{cursor}"' if cursor else ""
        query = {
            "query": f"""
            query {{
                files(first: {n}{after_argument}) {{
                    edges {{
                        cursor
                        node {{
                            ... on MediaImage {{
                                image {{ 
                                    originalSrc: url 
                                }}
                            }}
                        }}
                    }}
                    pageInfo {{
                        hasNextPage
                    }}
                }}
            }}
            """
        }

        response = make_request(GRAPHQL_URL, method='POST', data=query)
        return response.json()

    cursor = None
    while True:
        data = fetch_files(cursor)
        try:
            edges = data['data']['files']['edges']
            for edge in edges:
                # Extracting the originalSrc and appending to all_files
                image_data = edge['node'].get('image', {})
                all_files.append(image_data['originalSrc'])

            if not data['data']['files']['pageInfo']['hasNextPage']:
                break
            
            cursor = edges[-1]['cursor']
        except Exception as e:
            sleep = 5
            logger.info(f"    Fetching...", extra={'to_console': settings["CONSOLE"]})
            logger.info(f"Rate limit reached, retrying after {sleep} seconds...", extra={'to_console': True})
            time.sleep(sleep)
    
    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})

    return all_files

def find_matches_in_urls(item_codes, image_links):

    logger.info("Match image urls", extra={'to_console': settings["CONSOLE"]})

    # Dictionary to hold the product IDs and their associated images
    product_images = {code: [] for code in item_codes}
    items_with_images = 0

    # Iterate over each image link
    for link in image_links:
        for code in item_codes:
            # Create a pattern that matches the exact product ID
            pattern = re.compile(rf"mod_{code}(?:-\\d+)?(?![\d])")
            match = pattern.search(link)

            if match:
                # Append the image link to the corresponding product ID
                if not product_images[code]: items_with_images += 1 # count items with images
                product_images[code].append(link)
                break  # Stop checking other codes if a match is found

    # Sort the images for each product by their sequence
    for product_id in product_images:
        # Extracting sequence number from the link for sorting
        product_images[product_id].sort(key=lambda link: int(re.search(r"_(\d+)\.jpg", link).group(1)) if re.search(r"_(\d+)\.jpg", link) else -1)

    logger.info(f"    ItemCodes with images: {items_with_images}/{len(item_codes)}", extra={'to_console': settings["CONSOLE"]})
    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})

    return product_images

def update_product_variant(id, new_price):
    """
    Update the price of a Shopify product.

    :param product_id: The ID of the product to update.
    :param new_price: The new price to set for the product.
    """
    # Construct the URL for updating the product
    url = f"{BASE_URL}variants/{id}.json"

    # Prepare the data payload with the new price
    data = {
        "variant": {
            "id": id,
            "price": new_price
        }
    }

    # Make the PUT request to update the product
    response = make_request(url, method='PUT', data=data)
    return response.json(), response.status_code

def update_shopify_prices(catalog):

    logger.info(f"Updating prices of items in Shopify", extra={'to_console': settings["CONSOLE"]})

    # iterate over the products
    counter = 0
    for item in catalog:
        counter += 1

        product_data = get_product_by_handle(item)

        # iterate over variants
        for variant in product_data['variants']:
            id = variant['id']
            current_price = variant['price']
            retail_price = catalog[item]['Prezzo Retail']
            
            if retail_price and (float(retail_price) != float(current_price)):
                _, status_code = update_product_variant(id, retail_price)

            else: # no update
                status_code = None

        if status_code:
            logger.info(f"    {counter:<8}{item:5}  |  updated  |  new:old  {float(retail_price):5}:{float(current_price):<5}  |  Status Code: {status_code}", extra={'to_console': settings["CONSOLE"]})
        else:
            logger.info(f"    {counter:<8}{item:5}  |  -------  |  new:old  {float(current_price):5}:{float(current_price):<5}  |  {'Retail Price: None' if retail_price is None else ''}", extra={'to_console': settings["CONSOLE"]})

    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})

    return None
