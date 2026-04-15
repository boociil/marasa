import argparse
from src.populate_database import main as populate_database_main
from src.query_data import query_rag

def populateChroma():
    print("📥 Running PopulateChrom...")
    populate_database_main()


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--populate_chroma", action="store_true", help="Reset the database.")
    parser.add_argument("--query", type=str, help="Query data.")

    args = parser.parse_args()
    if args.populate_chroma:
        populateChroma()
        return
    
    if args.query:
        return query_rag(args.query)
        


if __name__ == "__main__":
    main()