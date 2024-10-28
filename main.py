from meps_parser import MEPSFileParser

# Example usage
def process_meps_file(file_path: str):
    parser = MEPSFileParser()
    try:
        result = parser.parse_file(file_path)

        # Print summary
        print(f"File: {result['header'].idfich}")
        print(f"Entity: {result['header'].entidade}")
        print(f"Number of transactions: {len(result['details'])}")
        print(f"Total amount: {result['trailer'].montranps}")
        print(f"Total fees: {result['trailer'].tottarps}")
        print(f"VAT amount: {result['trailer'].valiva}")

        return result

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise

if __name__ == "__main__":
    file_path = "files/MEPS_00029_20241027011323_1"
    process_meps_file(file_path)
