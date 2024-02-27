import requests, re, time, json
from pprint import pprint
import os
from logger import logger, settings

PAUSE = 2 # seconds

# Replace with your actual details
BASE_URL_SINESY = "https://api.clienteller.com/platform"
COMPANY_ID = "FRATE"
SITE_ID = "610"
USERNAME = "ECOMMERCE"
PASSWORD = os.environ.get("PASSWORD")
CATALOG_CODE = "ECOMMERCE"
LANGUAGE_ID = "IT"

# Headers
headers = {
    "Content-Type": "application/json",
    "catalogCode": CATALOG_CODE,
    "languageId": LANGUAGE_ID
}

def make_request(url, method='GET', headers=None, data=None):
    """
    Make a request to the Shopify API and handle rate limiting.
    """
    wait = 1  # Initial wait time in seconds
    while True:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, data=data)
        
        #logger.info(f"Status Code: {response.status_code}")
        #logger.info(f"Success: {response.json()['success']}")
        #logger.info(f"Error Code: {response.json()['errorCode']}")
        #logger.info(f"Message: {response.json()['message']}")

        success = response.json()['success']
        if not success:
            logger.info("API Sinesy Failure", extra={'to_console': settings["CONSOLE"]})
            logger.info(f"Error message: {response.json()['message']}", extra={'to_console': settings["CONSOLE"]})
            logger.info("-"*50 + "\n#### FINISH ####\n", extra={'to_console': settings["CONSOLE"]})
            raise Exception("API Sinesy Failure", extra={'to_console': settings["CONSOLE"]})

        """
        if response.status_code != 200 and response.status_code != 404:  # Rate limit error
            wait_time = response.headers.get('Retry-After', wait)
            logger.info(f"Rate limit reached, retrying after {wait_time} seconds...")
            time.sleep(float(wait_time))
            wait *= 2  # Exponential backoff
            continue
        """

        return response  # Return response for successful or other error codes

# Function to get catalog with pagination
def get_full_catalog(start=0):

    logger.info("Fetching catalog from Sinesy API", extra={'to_console': settings["CONSOLE"]})

    full_catalog = []
    more_rows = True

    while more_rows:
        url = f"{BASE_URL_SINESY}/api?cmd=getCatalog_v3&companyId={COMPANY_ID}&siteId={SITE_ID}&username={USERNAME}&password={PASSWORD}&appId=KEEPIT&applicationId=KEEPIT&start={start}"
        response = make_request(url, method="GET", headers=headers)
        data = response.json()

        full_catalog.extend(data.get("valueObjectList", []))
        more_rows = data.get("moreRows", False)
        start += len(data.get("valueObjectList", []))

        # Show progress using tqdm
        logger.info(f"    Retrieved {len(full_catalog):5} barcodes", extra={'to_console': settings["CONSOLE"]})
    
    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})

    return full_catalog

def title_case(string):
    return re.sub(r'\b[a-zA-Z]', lambda match: match.group(0).upper(), string.lower())

def organize_catalog_by_item_code(catalog):
    logger.info("Organize catalog by product ID", extra={'to_console': settings["CONSOLE"]})

    organized_catalog = {}

    for item in catalog:
        item_code = item.get('itemCode')
        if item_code not in organized_catalog:
            organized_catalog[item_code] = {
                'Genere': '',
                'Merceologia': '',
                'Categoria': '',
                'Prezzo': '',
                'Prezzo Retail': '',
                'Codice Fornitore': '',
                'Fornitore': '',
                'Colore': '',
                'Materiale': '',
                'Suola': '',
                'Tacco': '',
                'Taglie': {}
            }

            description_parts = title_case(item.get('dimensionGroupDescription1', '')).split()
            organized_catalog[item_code]['Merceologia'] = description_parts[0]
            organized_catalog[item_code]['Genere'] = description_parts[-1] if len(description_parts) >= 2 else title_case(item.get('hierarchyLevelDescription1', ''))
            organized_catalog[item_code]['Categoria'] = title_case(item.get('hierarchyLevelDescription3', ''))
            organized_catalog[item_code]['Fornitore'] = title_case(item.get('mainSupplier', ''))
            organized_catalog[item_code]['Colore'] = title_case(item.get('dimensionDescription2', ''))
            organized_catalog[item_code]['Materiale'] = title_case(item.get('attributeLevelDescription1', ''))
            organized_catalog[item_code]['Suola'] = title_case(item.get('attributeLevelDescription2', ''))
            organized_catalog[item_code]['Tacco'] = title_case(item.get('attributeLevelDescription3', ''))
            organized_catalog[item_code]['Prezzo'] = item.get('price', '')
            organized_catalog[item_code]['Prezzo Retail'] = item.get('priceRetail', '')
            organized_catalog[item_code]['Codice Fornitore'] = item.get('itemSupplier', '')
        
        organized_catalog[item_code]['Taglie'][title_case(item.get('dimensionDescription1', ''))] = item.get('barcode', '')

    # Sort 'Taglie' after processing all items
    for item_code in organized_catalog:
        organized_catalog[item_code]['Taglie'] = dict(sorted(organized_catalog[item_code]['Taglie'].items()))

    time.sleep(PAUSE)
    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})
    return organized_catalog

def extract_item_codes(organized_catalog):
    # Extracting the item codes, which are the keys of the organized_catalog dictionary
    item_codes = list(organized_catalog.keys())
    return item_codes

def create_associations_map(organized_catalog):
    associations_map = {}
    for item_code, details in organized_catalog.items():
        codice_fornitore = details['Codice Fornitore']
        parts = codice_fornitore.split('/')[:-1]  # Exclude color
        key = tuple(parts)
        if key not in associations_map:
            associations_map[key] = []
        associations_map[key].append(item_code)
    return associations_map

def add_associations_to_catalog(organized_catalog):

    logger.info("Add product associations to catalog", extra={'to_console': settings["CONSOLE"]})
    
    associations_map = create_associations_map(organized_catalog)
#
    for item_code, details in organized_catalog.items():
        codice_fornitore = details['Codice Fornitore']
        parts = codice_fornitore.split('/')[:-1]  # Exclude color
        key = tuple(parts)

        # Exclude the item itself from its associations
        associated_items = [code for code in associations_map[key] if code != item_code]
        details['Associations'] = associated_items

    time.sleep(PAUSE)
    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})

    return organized_catalog

def query_catalog_by_itemcode(catalog, item_code, printt=False):
    item_details = catalog.get(item_code, "Item not found in catalog")
    if printt: 
        logger.info(f"Example product: {item_code}", extra={'to_console': True})
        time.sleep(PAUSE)
        pprint(item_details, indent=0)
        logger.info("-"*50, extra={'to_console': True}) # just to print
    return item_details

def retrieve_all_associations(catalog):
    logger.info("Retrieving all product associations", extra={'to_console': True})
    all_associations = {}
    for item_code, item_details in catalog.items():
        # Retrieve associations, which can be an empty list
        associations = item_details.get('Associations', [])
        all_associations[item_code] = associations

    time.sleep(PAUSE)
    logger.info("Completed\n" + "-"*50, extra={'to_console': True})
    return all_associations

def fetch_stock_from_sinesy(item_code):
    url = f"{BASE_URL_SINESY}/api?cmd=getStocks_v4&username={USERNAME}&password={PASSWORD}&companyId={COMPANY_ID}&siteId={SITE_ID}&appId=KEEPIT&applicationId=KEEPIT"
    payload = json.dumps({"item": {"itemCode": f"{item_code}"}})
    response = make_request(url, method='POST', headers=headers, data=payload)
    stock_data = response.json()
    # Extracting sizes and quantities
    sizes_and_quantities = {}

    for item in stock_data['valueObjectList']:
        size = item.get('desDim1')
        quantity = item.get('quantity')
        sizes_and_quantities[size] = quantity
    return sizes_and_quantities

