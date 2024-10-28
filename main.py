import logging
from pathlib import Path
from pprint import pprint
from typing import Union
from meps_parser import MEPSError, MEPSFile, MEPSFileParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MEPSParser')

def process_meps_file(file_path: Union[str, Path], export_csv: bool = False) -> MEPSFile:
    """Process MEPS file and optionally export to CSV"""
    parser = MEPSFileParser()
    try:
        result = parser.parse_file(file_path)

        # Print summary
        logger.info(f"File: {result.header.idfich}")
        logger.info(f"Entity: {result.header.entidade}")
        logger.info(f"Number of transactions: {len(result.details)}")
        logger.info(f"Total amount: {result.trailer.montranps}")
        logger.info(f"Total fees: {result.trailer.tottarps}")
        logger.info(f"VAT amount: {result.trailer.valiva}")

        # Export to CSV if requested
        if export_csv:
            csv_path = Path(file_path).with_suffix('.csv')
            result.export_transactions_csv(csv_path)
            logger.info(f"Exported transactions to: {csv_path}")

        return result

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise

# Example usage
if __name__ == "__main__":
    # Example usage with error handling
    try:
        file_path = "files/MEPS_00029_20241027011323_1"
        result = process_meps_file(file_path, export_csv=True)

        # Export to JSON
        json_path = Path(file_path).with_suffix('.json')
        with open(json_path, 'w') as f:
            f.write(result.to_json())

        print(f"Processing completed. Check {json_path} for JSON output")

    except MEPSError as e:
        print(f"MEPS Processing Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
