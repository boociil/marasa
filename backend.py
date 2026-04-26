import argparse
from src.download_pdf import download_pdf_main
from src.populate_pdf import populate_pdf
from src.populate_data import populate_table
from src.populate_image import populate_image
from src.query_data import query_rag
from src.graph.main import main_chat_cmd

from src.graph.db.init_db import init_db
    


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--download_pdf", action="store_true", help="Download data.")
    parser.add_argument("--populate_table", action="store_true", help="Populate table.")
    parser.add_argument("--populate_pdf", action="store_true", help="Populate pdf.")
    parser.add_argument("--populate_image", action="store_true", help="Populate image.")
    parser.add_argument("--query", type=str, help="Query data.")
    parser.add_argument("--create_db", action="store_true", help="Create DB.")
    parser.add_argument("--start_chat", action="store_true", help="Start Chating.")


    args = parser.parse_args()

    if args.download_pdf:
        download_pdf_main()
        return    
    if args.populate_pdf:
        print("📥 Running PopulateChrom...")
        populate_pdf()
        return
    if args.populate_table:
        populate_table()
        return
    if args.populate_image:
        populate_image()
        return
    
    if args.query:
        return query_rag(args.query)
    
    if args.create_db:
        return init_db()
    
    if args.start_chat:
        print("--- Chatbot Started (Type 'quit' to exit) ---")
        chat_history = []
        while True:
            # 1. User Input
            user_input = input("You: ")
            
            # Check for exit condition
            if user_input.lower() == 'quit':
                print("Bot: Goodbye!")
                break

           
                
            # 2. Bot Response Logic
            # You can replace this with complex logic or an API call

            answer =  main_chat_cmd([user_input], chat_history)
            chat_history.append("user :"+user_input)
            for item_answer in answer:
                if item_answer.file_path is None :
                    print(f"Bot: {item_answer.text}")
                else :
                    print(f"Bot: {item_answer.file_path}")
        
            # 3. Loop returns to step 1 automatically
        return ""
        


if __name__ == "__main__":
    main()