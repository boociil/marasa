import argparse
from src.populate_database import main as populate_database_main
from src.query_data import query_rag
from src.download_pdf import download_pdf_main
from src.download_data import download_main_data
from src.graph.db.init_db import init_db

def populateChroma():
    print("📥 Running PopulateChrom...")
    populate_database_main()


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--download_pdf", action="store_true", help="Download data.")
    parser.add_argument("--download_data", action="store_true", help="Reset the database.")
    parser.add_argument("--populate_chroma", action="store_true", help="Reset the database.")
    parser.add_argument("--query", type=str, help="Query data.")
    parser.add_argument("--create_db", action="store_true", help="Reset the database.")


    args = parser.parse_args()

    if args.download_pdf:
        download_pdf_main()
        return
    if args.download_data:
        download_main_data()
        return
    
    if args.populate_chroma:
        populateChroma()
        return
    
    if args.query:
        return query_rag(args.query)
    
    if args.create_db:
        return init_db()
        


if __name__ == "__main__":
    main()