#python -m Scratchpad.ingest_cosmos_data
import os
import dotenv
from pathlib import Path 
dotenv.load_dotenv(dotenv_path=Path(__file__).parent.parent / 'server' / '.env' )

from server import utils_logger
console_logger, console_tracer = utils_logger.get_logger_tracer(__name__)

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.documents import Document

azure_openai_api_version: str = "2024-05-01-preview"
azure_deployment: str = "text-embedding-ada-002"

index_store : str = "chroma"
if index_store == "chroma":
    from langchain_chroma import Chroma

    embedding_function: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
        azure_deployment= azure_deployment,
        openai_api_version= azure_openai_api_version 
    )

    vector_store_doc = Chroma(persist_directory="../server/chroma_db_2", embedding_function=embedding_function)
    vector_store_tool = Chroma(persist_directory="../server/chroma_db_tools_2", embedding_function=embedding_function)
else:
    from langchain_community.vectorstores.azuresearch import AzureSearch
    embedding_function: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
        azure_deployment= azure_deployment,
        openai_api_version= azure_openai_api_version 
    )

    azure_endpoint: str = os.getenv("COSMOS_DB_ENDPOINT", "NA")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "NA")


    vector_store_address: str = os.getenv("AZURE_AI_SEARCH_ENDPOINT", "NA")
    vector_store_password: str = os.getenv("AZURE_AI_SEARCH_KEY", "NA")

    doc_index : str = os.getenv("AZURE_AI_SEARCH_INDEX_DOC", "NA")
    tool_index : str = os.getenv("AZURE_AI_SEARCH_INDEX_TOOL", "NA")

    vector_store_doc: AzureSearch = AzureSearch(
            azure_search_endpoint=vector_store_address,
            azure_search_key=vector_store_password,
            index_name=doc_index,
            embedding_function=embedding_function,
        )

    vector_store_tool: AzureSearch = AzureSearch(
            azure_search_endpoint=vector_store_address,
            azure_search_key=vector_store_password,
            index_name=tool_index,
            embedding_function=embedding_function,
        )

def load_documents() :
    print("Loading documents")
    faq_table_files =["docs\\troubleshooting.table.1.md",
                      "docs\\troubleshooting.table.2.md", 
                      "docs\\troubleshooting.table.3.md", 
                      "docs\\troubleshooting.table.4.md",
                      "docs\\troubleshooting.qa.1.md"]

    for faq_table_file in faq_table_files:
        loader = TextLoader(faq_table_file)
        data = loader.load()
        vector_store_doc.add_documents(data)

    print("Documents loaded")

def load_tools():
    print("Loading tools")

    docs = [
        # Document(page_content="""
        #         Retrieves device information (Device identifier, Device ID, Associated customer's name, Purchase,  Announcement Language, binding status, 
        #             Battery level, Network status, Charging state, Last connection timestamp,Last pulse timestamp, Conversation langauge)
        #         Plan information (Plan description, plan cost)
        #         Model Information(Model name, features, battery life, Network type, chaging connection type)
        #         Device status
        #         """,
        #     metadata={"tool": "get_device_info"},
        # ),
        Document(id = "1",
                page_content= """  
                Retrieve all transactions for a specified device.  
                        - deviceId (str): Unique identifier of the device.  
                        - dailyCollection (float): Total transaction amount for the day.  
                        - weeklyCollection (float): Total transaction amount for the week.  
                        - monthlyCollection (float): Total transaction amount for the month.  
                        - last10Transactions (list): List of the last 10 transactions:  
                            - transactionTime (str): Timestamp in "yyyy:mm:dd hh:mm:ss" format.  
                            - amount (float): Amount involved in the transaction (50-1000).  
                            - announcementTime (str): Timestamp 1-15 seconds after the transaction time.  
                """ ,
            metadata={"tool": "get_transactions_info"},
        ),
        Document(id = "2",
                page_content= """  
                Retrieve all notification/announcements for a specified device.  
                
                Returns:  
                    dict: Notification data with the following structure:  
                
                        - deviceId (str): Unique identifier of the device.  
                        - notification_id (str): Unique identifier of the notification.
                        - notificationType (str): Type/category of the notification.  
                        - status (str): Current status of the notification.  
                        - nnotificationTime (str): Scheduled time for the notification /annoncement using cron job format.  
                """  ,
            metadata={"tool": "get_notification_info"},
        ),
        Document(id = "3",
                page_content= """  
                Get troubleshooting guide for the given query.  
                    common issues 
                        - light blinking, 
                        - no light, 
                        - batter drain, 
                        - repeat transaction, 
                        - charger related, 
                        - sound related 
                        - key/button not working, 
                        - damage to device etc 
                        - bank transfers
                        - collection settlements
                        - upgrades to device, update to car payments etc
                """  ,
            metadata={"tool": "get_troubleshooting_guide"},
        ),
        Document(id = "4",
                page_content= """  
                Scenarios:
                    1. Create a support ticket for a specific device and user query.  
                    2. user followed all steps for troubleshooting but still facing issue.
                    3. Disagreement with the information provided by the assistant.
                    4. User wants to raise a ticket for a specific issue.
                    
                    Parameters:  
                        device_id (str): The ID of the device for which the ticket is being raised.  
                        session_id (str): The session ID associated with the conversation.  
                        title (str) : should be a concise summary of the issue. this is created form chat history.
                        description (str) :  should detailed summary of conversation. this is created form chat history.
                """  ,
            metadata={"tool": "raise_ticket"},
        ),
        Document(id = "5",
                page_content= """  
                Updates the language setting for a specific device in the Cosmos DB.  
  
                Args:  
                    device_id (str): The unique identifier of the device.  
                    language (str): The language to set for the device.   
                """  ,
            metadata={"tool": "update_device_language"},
        ),
        Document(id = "6",
                page_content= """  
                Updates the status and notification/announcement time for a specific notification/announcement associated with a device in Cosmos DB.  
  
                Args:  
                    device_id (str): The unique identifier of the device.  
                    notification_id (str): The unique identifier consisting of all digits. if you dont have it, get it from get_notification_info tool.
                    notification_time (str): The new notification/ announcement time to set in cron format.  
                    status (str): The new status for the notification/ announcement. Must be either "enabled" or "disabled".    
                """  ,
            metadata={"tool": "update_device_notifications"},
        ),
        Document(id = "7",
                page_content= """  
                user this function only when user specifically asks for khatabook/ledger/cash transaction entries.
                Retrieve all khatabook / ledger / cash transaction entries for a specified device.     

                Returns:  
                    dict: Khatabook data with the following structure:  
                
                        - deviceId (str): Unique identifier of the device.  
                        - khatabook_id (str): Unique identifier of the khatabook entry.
                        - list of transactions (list): List of transactions:
                            - transactionTime (str): Timestamp in "yyyy:mm:dd hh:mm:ss" format.
                            - amount (float): Amount involved in the transaction (50-1000).
                            - received_from: Name of the person from whom the amount was received.    
                """  ,
            metadata={"tool": "get_khatabook"},
        ),
        Document(id = "8",
                page_content= """  
                use this function only when user specifically asks questions like
                    -  update khatabook / ledger / cash transaction entries for a specified device. 
                    - add amount from received from in khatabook
                    - received amount from received_from in khatabook
                update khatabook / ledger / cash transaction entries for a specified device. 
                Args:  
                    device_id (str): The ID of the device for which the khatabook is being updated.  
                    receivedFrom (str): The name of the person from whom the amount was received. 
                        just keep the name, dont use titles like Mr, Mrs, etc. for names like Sharmaji, Guptaji, etc Just say Sharma, Gupta etc.
                    amount (int): The amount involved in the transaction     

                Returns:  
                    string : description of khatabook update.
                """  ,
            metadata={"tool": "update_khatabook"},
        ),
    ]
   
    vector_store_tool.add_documents(docs)

    print("Tools loaded")

# load_documents()
# load_tools()

def query_tool():

    tools = vector_store_tool.similarity_search(query = """user : the problem is still not solved
                           assistant : do you want me to raise a support ticket for you?
                           user: yes""", 
                           k = 2)
    
    for filtered_tool in tools:
        print(filtered_tool.metadata["tool"])


    tools = vector_store_tool.similarity_search(query = """user : Sharmaji khatabook me kitane paise jama kiye""", 
                           k = 2)
    
    # search_type="hybrid" for the azure ai search
    
    for filtered_tool in tools:
        print(filtered_tool.metadata["tool"])

query_tool()