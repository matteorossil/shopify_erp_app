from shopify_api import *
from sinesy_api import *
import random
from update_stock import update_stock

def update_catalog():

    try:
        # Get catalog from Sinesy
        catalog_sinesy = get_full_catalog(start=0)

        # Organize the catalog by itemCode
        organized_catalog = organize_catalog_by_item_code(catalog_sinesy)

        # Enhance catalog with product associations based on 'Codice fornitore'
        organized_catalog_with_product_associations = add_associations_to_catalog(organized_catalog)

        # Example query
        item_code = random.choice(list(organized_catalog_with_product_associations.keys())) # pick item code at random
        _ = query_catalog_by_itemcode(organized_catalog_with_product_associations, item_code, printt=True)

        # Returns all the product handles in Shopify
        shopify_handles = get_all_product_handles()

        # Returns products in catalofg present and missing in Shopify
        _, missing_itemcodes = categorize_itemcodes_in_shopify(shopify_handles, organized_catalog_with_product_associations)

        # fetch all files urls
        all_file_urls = fetch_all_files(n=250)

        matches_image_urls = find_matches_in_urls(missing_itemcodes, all_file_urls)

        # Create products in Shopify
        shopify_handles_created = create_products_in_shopify(missing_itemcodes, organized_catalog_with_product_associations, matches_image_urls)
        
        if len(shopify_handles_created) > 0: # if products have been created on shopify
            # Get all catalog associations 
            catalog_associations = retrieve_all_associations(organized_catalog_with_product_associations)

            # Get all handles on Shopify
            all_shopify_handles = get_all_product_handles()

            # Updated products on Shopify with associations
            update_product_metafields_with_associations(all_shopify_handles, catalog_associations)

        # update stock after uploading new catalog
        update_stock()
    except Exception as e:
        logger.info(f"An error occurred: {e}", extra={'to_console': True})

if __name__ == '__main__':
    update_catalog()