import argparse
from src.populate_database import main as populate_database_main
from src.query_data import query_rag
from src.download_pdf import download_main

def populateChroma():
    print("📥 Running PopulateChrom...")
    populate_database_main()


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--download", action="store_true", help="Download data.")
    parser.add_argument("--populate_chroma", action="store_true", help="Reset the database.")
    parser.add_argument("--query", type=str, help="Query data.")

    args = parser.parse_args()

    if args.download:
        download_main()
        return
    
    if args.populate_chroma:
        populateChroma()
        return
    
    if args.query:
        return query_rag(args.query)
        


if __name__ == "__main__":
    main()