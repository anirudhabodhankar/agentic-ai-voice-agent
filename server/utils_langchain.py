import os
from datetime import datetime

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from server import utils_db  
from server import utils_logger
console_logger, console_tracer = utils_logger.get_logger_tracer()

azure_openai_api_version: str = "2024-05-01-preview"
azure_embedding_deployment: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "NA")

doc_index : str = os.getenv("AZURE_AI_SEARCH_INDEX_DOC", "NA")
tool_index : str = os.getenv("AZURE_AI_SEARCH_INDEX_TOOL", "NA")

embedding_function = AzureOpenAIEmbeddings(
        azure_deployment= azure_embedding_deployment,
        openai_api_version= azure_openai_api_version 
    )

llm_gpt_4o = AzureChatOpenAI(
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "NA"),
        api_version = azure_openai_api_version,
        temperature=0,
        max_tokens=200,
        timeout=None,
        max_retries=2,
    )

vector_store_doc = AzureSearch(
            azure_search_endpoint=os.getenv("AZURE_AI_SEARCH_ENDPOINT", "NA"),
            azure_search_key=os.getenv("AZURE_AI_SEARCH_KEY", "NA"),
            index_name=doc_index,
            embedding_function=embedding_function,
        )

vector_store_tool = AzureSearch(
            azure_search_endpoint=os.getenv("AZURE_AI_SEARCH_ENDPOINT", "NA"),
            azure_search_key=os.getenv("AZURE_AI_SEARCH_KEY", "NA"),
            index_name=tool_index,
            embedding_function=embedding_function,
    )

agent_system_prompt_instructions = """
    You are a helpful AI audio device assistant named SoundPod. generate feminine response. 
    Use the provided context to answer the user's question concisely and informatively. 
    Respond in plain text without links, references, code snippets, images, or diagrams. 
    Utilize all available tools as much possible. Avoid providing reasoning behind the answer. 
    Ask questions based on the given context if necessary 
    
    Important : 
    1. If user disagrees with the infomration you have provided using tools you have, again repeat what you told and also suggest to raise a ticket if that helps        
    2. Before raising a ticket or updating any details in backend ask for confirmation from user, if you havent asked already. 
    3. While responding with a function call or tool call, also include message content saying "wait a minute, I am checking for more information"
    4. If you are not able to find any information, respond with "I am sorry, I am not able to find any information on this. Can you please provide more details on the issue you are facing?"    
    5. Check language of user query. Respond in the same language. 
    6. For any sound box query that you dont konw answer for, ask for more details. if even after more details you cant answer, ask politely to raise a ticket. 
    7. Respond only with information provided to you in context or you got using tools. 
    8. For any controversial, political, 'repeate after me' or sensitive topics, respond politely with "I am sorry, I am not able to provide information on this. Can I help you with anything else?"
    9  For return/ replacement queries, ask for more details and suggest first and then to raise a ticket.

    ##example  1
    user : Device not working properly
    Answer: It might be light indicator issue, network issue or sound issue. Can you provide more details on the issue you are facing?

"""
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", agent_system_prompt_instructions),
    ("system", "device-id  : {device_id}"),
    ("system", "session_id  : {session_id}"),
    ("system", "conversation language- {user_language}"),
    ("system" , "device info- {device_info}"),
    ("system" , "currancy INR thousand seperator"),
    ("system", f"today  : {datetime.now()}"),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

@tool
def get_device_info(device_id: str) -> str:
    """  
    Retrieves 
    device information (Device identifier, Device ID, Associated customer's name, Purchase,  Announcement Language, binding status, 
        Battery level, Network status, Charging state, Last connection timestamp,Last pulse timestamp, Conversation langauge)
    Plan information (Plan description, plan cost)
    Model Information(Model name, features, battery life, Network type, chaging connection type)
    Device status
    """
    console_logger.debug(f'get_device_info wrapper called with device_id: {device_id}')
    deivce_info = utils_db.get_device_info(device_id = device_id)
    return deivce_info

@tool
def get_transactions_info(device_id: str) -> str:
    """  
    Retrieve all transactions for a specified device.  
            - deviceId (str): Unique identifier of the device.  
            - dailyCollection (float): Total transaction amount for the day.  
            - weeklyCollection (float): Total transaction amount for the week.  
            - monthlyCollection (float): Total transaction amount for the month.  
            - last10Transactions (list): List of the last 10 transactions:  
                - transactionTime (str): Timestamp in "yyyy:mm:dd hh:mm:ss" format.  
                - amount (float): Amount involved in the transaction (50-1000).  
                - announcementTime (str): Timestamp 1-15 seconds after the transaction time.  
    """  
    console_logger.debug(f'get_transactions_info wrapper called with device_id: {device_id}')
    transaction_info = utils_db.get_transactions(device_id = device_id)
    return transaction_info

@tool
def get_notification_info(device_id: str) -> str:
    """  
     Retrieve all notification/announcements for a specified device.  
    
    Returns:  
        dict: Notification/announcements data with the following structure:  
    
            - deviceId (str): Unique identifier of the device.  
            - notification_id (str): Unique identifier of the notification.
            - notificationType (str): Type/category of the notification.  
            - status (str): Current status of the notification.  
            - notificationTime (str): Scheduled time for the notification /annoncement using cron job format.  
    """  
    console_logger.debug(f'get_notification_info wrapper called with device_id: {device_id}')
    notification_info = utils_db.get_notifications(device_id = device_id)
    return notification_info

@tool
def get_troubleshooting_guide(query: str) -> str:
    """Get troubleshooting guide for the given query.  
    common issues 
        - light blinking, 
        - no light, 
        - battery drain, 
        - repeat transaction, 
        - charger related, 
        - sound related 
        - key/button not working, 
        - damage to device etc 
        - When will my collections be transferred into my bank account
        - I want my money to be settled now
        - Can I accept card payments 
    """    
    console_logger.debug(f'get_troubleshooting_guide wrapper called with query: {query}')
    # troubleshooting_docs =  doc_retriever.invoke(query)
    troubleshooting_docs =  vector_store_doc.similarity_search(query = query, k = 2)
    console_logger.debug(f'troubleshooting_docs: {troubleshooting_docs}')
    return troubleshooting_docs

@tool
def raise_ticket(session_id:str, device_id: str, title:str, description:str) -> bool:
    """
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
    """
    console_logger.debug(f'raise_ticket wrapper called with device_id: {device_id}')
    console_logger.debug(f'raise_ticket wrapper called with session_id: {session_id}')
    console_logger.debug(f'raise_ticket wrapper called with title: {title}')
    console_logger.debug(f'raise_ticket wrapper called with description: {description}')
    
    return utils_db.raise_customer_ticket(device_id = device_id, title = title, description = description)

@tool
def update_device_language(device_id: str, language:str) -> bool:
    """
    Updates the language setting for a specific device in the Cosmos DB.  
  
    Args:  
        device_id (str): The unique identifier of the device.  
        language (str): The language to set for the device.   
                        Must be one of ["English", "Hindi", "Marathi", "Kannada", "Tamil"].  
    """
    console_logger.debug(f'raise_ticket wrapper called with device_id: {device_id}')
    console_logger.debug(f'raise_ticket wrapper called with session_id: {language}')
    
    return utils_db.update_device_language(device_id = device_id, language = language)

@tool
def update_device_notifications(device_id:str, notification_id: str, notification_time:str, status:str) -> bool:
    """
    Updates the status and notification/announcement time for a specific notification/announcement associated with a device in Cosmos DB.  
  
    Args:  
        device_id (str): The unique identifier of the device.  
        notification_id (str): The unique identifier consisting of all digits. if you dont have it, get it from get_notification_info tool.
        notification_time (str): The new notification/ announcement time to set in cron format.  
        status (str): The new status for the notification/ announcement. Must be either "enabled" or "disabled".  
    """
    console_logger.debug(f'update_device_notifications wrapper called with device_id: {device_id}')
    console_logger.debug(f'update_device_notifications wrapper called with session_id: {notification_id}')
    console_logger.debug(f'update_device_notifications wrapper called with title: {notification_time}')
    console_logger.debug(f'update_device_notifications wrapper called with description: {status}')
    
    return utils_db.update_device_notification(device_id = device_id, notification_id = notification_id, notification_time = notification_time, status = status)

@tool
def get_khatabook(device_id: str) -> str:
    """  
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
    """  
    console_logger.debug(f'get_khatabook wrapper called with device_id: {device_id}')

    khatabook_info = utils_db.get_khatabook(device_id = device_id)
    return khatabook_info

@tool
def update_khatabook(device_id: str, receivedFrom:str, amount: int) -> str:
    """  
    use this function only when user specifically asks questions like
        -  update khatabook / ledger / cash transaction entries for a specified device. 
        - add amount from received from in khatabook
        - received amount from received_from in khatabook
    Args:  
        device_id (str): The ID of the device for which the khatabook is being updated.  
        receivedFrom (str): The name of the person from whom the amount was received. 
            just keep the name, dont use titles like Mr, Mrs, etc. for names like Sharmaji, Guptaji, etc Just say Sharma, Gupta etc.
        amount (int): The amount involved in the transaction     

    Returns:  
        string : description tus of khatabook update
    """  
    console_logger.debug(f'update_khatabook wrapper called with device_id: {device_id}')
    console_logger.debug(f'update_khatabook wrapper called with receivedFrom: {receivedFrom}')
    console_logger.debug(f'update_khatabook wrapper called with amount: {amount}')
    msg = utils_db.update_khatabook(device_id = device_id, receivedFrom = receivedFrom, amount = amount)
    console_logger.debug(f'update_khatabook returned msg: {msg}')
    return msg

tool_map = {
    "get_device_info": get_device_info,
    "get_transactions_info": get_transactions_info,
    "get_notification_info": get_notification_info,
    "get_troubleshooting_guide": get_troubleshooting_guide,
    "raise_ticket": raise_ticket,
    "update_device_notifications": update_device_notifications,
    "update_device_language": update_device_language,
    "get_khatabook": get_khatabook,
    "update_khatabook": update_khatabook
}

@console_tracer.start_as_current_span("get_agent_executor")
def get_agent_executor(query: str):
    filtered_tools = vector_store_tool.similarity_search(query = query, k = 3)
    print(f"filtered_tools: {filtered_tools}")
    
    tools = []
    for filtered_tool in filtered_tools:
        console_logger.info(f'filtered_tool: {filtered_tool.metadata["tool"]}')
        tools.append(tool_map[filtered_tool.metadata["tool"]])

    agent = create_tool_calling_agent(llm_gpt_4o, tools, agent_prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor