# Standard Library Imports  
from typing import List, Dict, Any, Optional  
import traceback 

import os  
import uuid  
from datetime import datetime, timezone
  
# Third-Party Imports  
from azure.cosmos import CosmosClient , ContainerProxy, exceptions , DatabaseProxy
import redis  
  
from server import utils_logger
console_logger, console_tracer = utils_logger.get_logger_tracer()
max_history = int(os.getenv("MAX_MESSAGE_HISTORY", "-6"))

@console_tracer.start_as_current_span("get_redis_client")
def get_redis_client() -> redis.Redis:
    """  
    Initializes and returns a Redis client.  
    The Redis host, port, and password are fetched from environment variables.  
    If not set, defaults are used.  
    """     
    console_logger.debug("Initializing Redis client")  
    try:  
        redis_client = redis.Redis(  
            host=os.getenv("REDIS_HOST", "localhost"),  
            port=os.getenv("REDIS_PORT", "6379"),  
            password=os.getenv("REDIS_KEY", None),  
            ssl=True,  
            db=0,  
        )  
        redis_client.ping()  # Test the connection to Redis  
        console_logger.info("Connected to Redis cache")  
        return redis_client  
    except redis.ConnectionError as e:  
        console_logger.error(f"Redis connection error: {e}")  
        raise

# Initialize Redis client
redis_client = get_redis_client()
# Initialize Cosmos DB client

@console_tracer.start_as_current_span("get_cosmos_db")
def get_cosmos_db() -> DatabaseProxy:
    """  
    Initializes and returns a Cosmos DB client.  
    The Cosmos DB endpoint and key are fetched from environment variables.  
    If not set, defaults are used.  
    """
    console_logger.debug("Initializing Cosmos DB client")  
    try:  
        cosmos_client = CosmosClient(  
            url=os.getenv("COSMOS_DB_ENDPOINT", "NA"),  
            credential=os.getenv("COSMOS_DB_KEY", "NA")  
        )  
        
        console_logger.info("Connected to Cosmos DB")  
        return cosmos_client.get_database_client(os.getenv("COSMOS_DB_NAME", "NA"))
    except exceptions.CosmosHttpResponseError as e:  
        console_logger.error(f"Cosmos DB connection error: {e}")  
        raise

# Initialize Cosmos DB client
database = get_cosmos_db()

@console_tracer.start_as_current_span("get_device_info")
def get_device_info(device_id: str) -> Optional[Dict[str, Any]]:  
    """  
    Retrieves device information from the database using the provided device_id.  
  
    Args:  
        device_id (str): The ID of the device to retrieve information for.  
  
    Returns:  
        Optional[Dict[str, Any]]: A dictionary containing device information if found, else None.  
    """  
    console_logger.debug(f"Getting data for device_id: {device_id}")  
    container = database.get_container_client(os.getenv("COSMOS_DB_CONTAINER_DEVICES", "devices")) 
    query = f"SELECT * FROM c WHERE c.deviceId = '{device_id}'"
    console_logger.debug(f'Executing query: {query}')
    try:  
        device_info = list(container.query_items(
            query=query,
            partition_key = device_id
        ))

        console_logger.debug(f"Retrieved device_info: {device_info}")  
        # Return the first device info if available, else None  
        return device_info[0] if device_info else None  
    except Exception as e:
        console_logger.error(f"An error occurred while fetching transactions: {e}")  
        return None

@console_tracer.start_as_current_span("get_transactions")
def get_transactions(device_id)-> Optional[Dict[str, Any]]:  
    """  
    Retrieves transaction information from the database using the provided device_id.  
    
    Args:  
        device_id (str): The ID of the device to retrieve transactions for.  
    
    Returns:  
        Optional[Dict[str, Any]]: A dictionary containing transaction information if found, else None.  
    """  
    console_logger.debug(f"Fetching transactions for device_id: {device_id}")  
      
    # Retrieve the container name from environment variables with a default fallback  
    container = database.get_container_client(os.getenv("COSMOS_DB_CONTAINER_TRANSACTIONS", "transactions")  )  
    query = f"SELECT * FROM c WHERE c.deviceId = '{device_id}'"
    console_logger.debug(f"Executing query: {query} ")
    try:  
        transaction_info = list(container.query_items(  
            query=query,  
            partition_key = device_id
        ))

        console_logger.debug(f"Retrieved transaction_info: {transaction_info}")  
        # Return the first transaction if available, else None  
        return transaction_info[0] if transaction_info else None  
    except Exception as e:
        console_logger.error(f"An error occurred while fetching transactions: {e}")  
        return None


@console_tracer.start_as_current_span("get_notifications")
def get_notifications(device_id: str) -> Optional[List[Dict[str, Any]]]:  
    """  
    Retrieves notification information from the database using the provided device_id.  
      
    Args:  
        device_id (str): The ID of the device to retrieve notifications for.  
      
    Returns:  
        Optional[List[Dict[str, Any]]]: A list of dictionaries containing notification information if found, else None.  
    """  
    console_logger.debug(f"Fetching notifications for device_id: {device_id}")  
      
    # Retrieve the container name from environment variables with a default fallback      
    container = database.get_container_client(os.getenv("COSMOS_DB_CONTAINER_NOTIFICATIONS", "notifications"))  
    query = f"SELECT * FROM c WHERE c.deviceId = '{device_id}'"
    console_logger.debug(f"Executing query: {query} ")
    try:  
        notifications = list(container.query_items(  
            query=query,  
            partition_key = device_id
        ))

        console_logger.debug(f"Retrieved notifications: {notifications}")
        # Return the list of notifications if available, else None  
        return notifications if notifications else None  
    except Exception as e:  
        console_logger.error(f"An error occurred while fetching notifications: {e}")  
        return None     


@console_tracer.start_as_current_span("create_new_conversation")
def create_new_conversation(device_id: str, session_id: str, title: str) -> Dict[str, Any]:  
    """  
    Creates a new conversation dictionary with the provided device ID, session ID, and title.  
      
    Args:  
        device_id (str): The ID of the device initiating the conversation.  
        session_id (str): The unique session ID for the conversation.  
        title (str): The title of the conversation.  
      
    Returns:  
        Dict[str, Any]: A dictionary representing the new conversation.  
    """  
    console_logger.debug(f"Creating new conversation for device_id: {device_id}, session_id: {session_id}")  
  
    conversation = {  
        "deviceId": device_id,  
        "id": session_id,  
        "title": title,  
        "timestamp": datetime.now(timezone.utc).isoformat(),  
        "messages": []  
    }  
      
    console_logger.debug(f"Created conversation: {conversation}")  
    return conversation 


@console_tracer.start_as_current_span("get_conversation")
def get_conversation(session_id: str, device_id: str) -> Optional[Dict[str, Any]]:  
    """  
    Retrieves a specific conversation from the database using the provided session_id and device_id.  
      
    Args:  
        session_id (str): The unique session ID of the conversation to retrieve.  
        device_id (str): The ID of the device associated with the conversation.  
      
    Returns:  
        Optional[Dict[str, Any]]: A dictionary containing the conversation details if found, else None.  
    """  
    console_logger.debug(f"Fetching conversation for session_id: {session_id} and device_id: {device_id}")  
      
    # Retrieve the container name from environment variables with a default fallback  
    container = database.get_container_client(os.getenv("COSMOS_DB_CONTAINER_CONVERSATIONS", "conversations")  )  
    query = f"SELECT * FROM c WHERE c.id = '{session_id}' AND c.deviceId = '{device_id}'"
    console_logger.debug(f"Executing query: {query} ")

    try:  
        sessions = list(container.query_items(  
            query=query,  
            partition_key = device_id
        ))

        console_logger.debug(f"Retrieved conversations details: {sessions}")  
        # Return the list of sessions if available, else None  
        return sessions[0] if sessions else None  
    except Exception as e:  
        console_logger.error(f"An error occurred while fetching the conversation: {e}")  
        return None  


@console_tracer.start_as_current_span("get_conversation_or_create_new")
def get_conversation_or_create_new(session_id: str, device_id: str, title: str) -> Optional[Dict[str, Any]]:  
    """  
    Retrieves an existing conversation based on session_id and device_id.  
    If no conversation is found, creates a new conversation with the provided title.  
  
    Args:  
        session_id (str): The unique session ID for the conversation.  
        device_id (str): The ID of the device associated with the conversation.  
        title (str): The title of the conversation.  
  
    Returns:  
        Optional[Dict[str, Any]]: The existing conversation if found, otherwise the newly created conversation.  
    """  
    console_logger.debug(f"Attempting to retrieve conversation for session_id: '{session_id}' and device_id: '{device_id}'.")
    session_info = get_conversation(session_id, device_id)

    if session_info:
        return session_info
    else:
        return create_new_conversation(device_id = device_id, session_id = session_id, title = title)
        
@console_tracer.start_as_current_span("add_messages_to_conversation")  
def add_messages_to_conversation(conversation: Dict[str, Any], messages: List[Dict[str, str]]) -> bool:  
    """  
    Adds a list of messages to an existing conversation and updates it in the database.  
  
    Args:  
        conversation (Conversation): The conversation to which messages will be added.  
        messages (List[Dict[str, str]]): A list of messages, each containing 'content' and 'role'.  
  
    Returns:  
        bool: True if the operation was successful, False otherwise.  
    """  
    console_logger.debug(f"Adding {len(messages)} messages to conversation ID: {conversation['id']} for device ID: {conversation['deviceId']}.")  
    container = database.get_container_client(os.getenv("COSMOS_DB_CONTAINER_CONVERSATIONS", "conversations")  )  
    for message in messages:
        conversation["messages"].append({"content": message["content"], "role": message["role"], "timestamp": datetime.now(timezone.utc).isoformat()})
    try:  
        container.upsert_item(conversation)
        return True
    except Exception as e:  
        console_logger.error(f"An error occurred while adding messages to the conversation: {e}")  
        return False  


@console_tracer.start_as_current_span("raise_customer_ticket")
def raise_customer_ticket(device_id: str, 
                          title:str, 
                          description:str) -> bool:
    """  
    Raises a customer support ticket for a specific device.  
  
    This function creates a new ticket with a unique ID, storing details such as the device ID,  
    title, and description in the specified Cosmos DB container.  
  
    Args:  
        device_id (str): The unique identifier of the device associated with the ticket.  
        title (str): The title or summary of the issue.  
        description (str): A detailed description of the issue.  
  
    Returns:  
        str: The unique ID of the created ticket.  
  
    Raises:  
        ValueError: If any of the required parameters are empty.  
        Exception: If there is an issue with database connectivity or operations.  
    """ 
    # Input Validation  
    if not device_id.strip():  
        raise ValueError("device_id cannot be empty.")  
    if not title.strip():  
        raise ValueError("title cannot be empty.")  
    if not description.strip():  
        raise ValueError("description cannot be empty.")  
    try:
        console_logger.debug(f'raising ticket for device id device_id: {device_id}')
        container = database.get_container_client(os.getenv("COSMOS_DB_CONTAINER_CONVERSATIONS", "tickets") )

        # Create the ticket dictionary  
        ticket_id = str(uuid.uuid4()) 
        ticket = {
            "id": ticket_id,
            "deviceId": device_id,
            "title": title,
            "description": description,
        }

        container.upsert_item(ticket)
        console_logger.debug("Successfully raised ticket with ID: %s", ticket_id)  
        return True
    except exceptions.CosmosHttpResponseError as cosmos_err:  
        console_logger.error("Cosmos DB HTTP response error: %s", cosmos_err)  
    except Exception as e:  
        console_logger.error("An unexpected error occurred while raising ticket: %s", e)  
    
    return False


@console_tracer.start_as_current_span("update_device_language")
def update_device_language(device_id: str, language: str) -> bool:  
    """  
    Updates the language setting for a specific device in the Cosmos DB.  
  
    Args:  
        device_id (str): The unique identifier of the device.  
        language (str): The language to set for the device.   
                        Must be one of ["English", "Hindi", "Marathi", "Kannada", "Tamil"].  
  
    Returns:  
        bool:   
            - True if the update was successful.  
            - False if the update failed due to a Cosmos DB error or if the device was not found.  
  
    Raises:  
        ValueError:   
            - If `device_id` is empty.  
            - If `language` is empty or not among the allowed languages.  
    """  
    # Allowed languages  
    allowed_languages = ["English", "Hindi", "Marathi", "Kannada", "Tamil"]  
  
    # Input Validation    
    if not device_id.strip():    
        raise ValueError("device_id cannot be empty.")    
    if not language.strip():    
        raise ValueError("language cannot be empty.")  
    if language.strip() not in allowed_languages:    
        raise ValueError(  
            f"language must be one of the following: {', '.join(allowed_languages)}."  
        )  
  
    try:  
        console_logger.debug(f"Updating device language for device_id: {device_id}, language: {language}")  
          
        # Retrieve the container client from environment variables or default to "devices"  
        container_name = os.getenv("COSMOS_DB_CONTAINER_DEVICES", "devices")  
        container = database.get_container_client(container_name)  
          
        query = f"SELECT * FROM c WHERE c.deviceId = '{device_id}'"  
        console_logger.debug(f"Executing query: {query}")  
          
        # Fetch devices matching the device_id  
        devices = list(  
            container.query_items(  
                query=query,    
                partition_key=device_id  
            )  
        )  
  
        console_logger.debug(f"Retrieved devices: {devices}")  
          
        if not devices:  
            console_logger.warning(f"No device found with device_id: {device_id}")  
            return False  
          
        # Assume the first device is the target for update  
        device = devices[0]  
          
        # Update the language field  
        device["language"] = language  
          
        # Upsert the updated device back into the container  
        container.upsert_item(device)  
        console_logger.debug(f"Successfully updated device with ID: {device_id}")  
        return True  
  
    except exceptions.CosmosHttpResponseError as cosmos_err:    
        console_logger.error(f"Cosmos DB HTTP response error: {cosmos_err}")    
    except Exception as e:    
        console_logger.error(f"An unexpected error occurred while updating the language: {e}")     
      
    return False  


@console_tracer.start_as_current_span("update_device_notification")
def update_device_notification(device_id: str, notification_id: str, notification_time: str, status: str) -> bool:  
    """  
    Updates the status and notification time for a specific notification associated with a device in Cosmos DB.  
  
    Args:  
        device_id (str): The unique identifier of the device.  
        notification_id (str): The unique identifier of the notification to be updated.  
        notification_time (str): The new notification time to set.  
        status (str): The new status for the notification. Must be either "enabled" or "disabled".  
  
    Returns:  
        bool:  
            - True if the update was successful.  
            - False if the update failed due to a Cosmos DB error, the notification was not found, or input validation failed.  
  
    Raises:  
        ValueError:  
            - If `device_id` is empty.  
            - If `notification_id` is empty.  
            - If `notification_time` is empty.  
            - If `status` is empty or not among the allowed statuses ("enabled", "disabled").  
    """  
    # Allowed statuses  
    allowed_statuses = ["enabled", "disabled"]  
  
    # Input Validation  
    if not device_id.strip():  
        raise ValueError("device_id cannot be empty.")  
    if not notification_id.strip():  
        raise ValueError("notification_id cannot be empty.")  
    if not notification_time.strip():  
        raise ValueError("notification_time cannot be empty.")  
    if not status.strip() or status.strip().lower() not in allowed_statuses:  
        raise ValueError(  
            f"status must be one of the following: {', '.join(allowed_statuses)}."  
        )  
  
    # Normalize status to lowercase to maintain consistency  
    status = status.strip().lower()  
  
    try:  
        console_logger.debug(f"Updating notification status for device_id: {device_id}, notification_id: {notification_id}")  
  
        # Retrieve the container client from environment variables or default to "notifications"  
        container_name = os.getenv("COSMOS_DB_CONTAINER_NOTIFICATIONS", "notifications")  
        container = database.get_container_client(container_name)  
  
        # Corrected the query string by adding the missing closing quote and properly handling both deviceId and id  
        query = f"SELECT * FROM c WHERE c.deviceId = '{device_id}' AND c.notification_id = '{notification_id}'"  
        console_logger.debug(f"Executing query: {query}")  
  
        # Fetch notifications matching the device_id and notification_id  
        notifications = list(  
            container.query_items(  
                query=query,  
                partition_key=device_id  
            )  
        )  
  
        console_logger.debug(f"Retrieved notifications: {notifications}")  
  
        if not notifications:  
            console_logger.warning(f"No notification found with device_id: {device_id} and notification_id: {notification_id}")  
            return False  
  
        # Assume the first notification is the target for update  
        notification = notifications[0]  
  
        # Update the status and notificationTime fields  
        notification["status"] = status  
        notification["notificationTime"] = notification_time  
  
        # Upsert the updated notification back into the container  
        container.upsert_item(notification)  
        console_logger.info(f"Successfully updated notification with ID: {notification_id}")  
        return True  
  
    except exceptions.CosmosHttpResponseError as cosmos_err:  
        console_logger.error(f"Cosmos DB HTTP response error: {cosmos_err}")  
    except Exception as e:  
        console_logger.error(f"An unexpected error occurred while updating the notification: {e}")  
  
    return False  


@console_tracer.start_as_current_span("get_chat_from_conversation")
def get_chat_from_conversation(  
    conversation: Dict[str, Any]
) -> List[Dict[str, str]]:  
    """  
    Extracts a chat history from a conversation dictionary, filtering only user and assistant messages.  
  
    This function processes the messages in the provided conversation, extracting only those messages  
    where the role is either 'user' or 'assistant'. It then returns the latest `max_history` messages  
    from the filtered chat history.  
  
    Args:  
        conversation (Dict[str, Any]): A dictionary containing conversation data. Expected to have a "messages" key  
            which is a list of message dictionaries. Each message should have at least "role" and "content" keys.  
  
    Returns:  
        List[Dict[str, str]]: A list of dictionaries representing the chat history. Each dictionary contains:  
            - "role": either "user" or "assistant"  
            - "content": the content of the message  
  
    Raises:  
        ValueError: If the conversation does not contain the expected "messages" key or if it's not a list.  
    """
    messages = conversation.get("messages")  
    if messages is None:  
        raise ValueError('The conversation dictionary must contain a "messages" key.')  
    
    chat_history: List[Dict[str, str]] = []  
    valid_roles = {"user", "assistant"}  

    for message in messages:
        role = message.get("role")  
        content = message.get("content", "")  
  
        if role in valid_roles:  
            chat_history.append({"role": role, "content": content})  

    #return last max_history messages
    return chat_history[max_history:]


@console_tracer.start_as_current_span("get_langchain_chat_from_conversation")
def get_langchain_chat_from_conversation(  
    conversation: Dict[str, Any]
) -> List[Dict[str, str]]:  
    """  
    Transforms a conversation dictionary into a chat history format compatible with LangChain.  
  
    This function processes the messages in the provided conversation, mapping the roles  
    from 'user' and 'assistant' to 'human' and 'ai' respectively. It then returns the  
    latest `max_history` messages from the chat history.  
  
    Args:  
        conversation (Dict[str, Any]): A dictionary containing conversation data. Expected to have a "messages" key  
            which is a list of message dictionaries. Each message should have at least "role" and "content" keys.  
  
    Returns:  
        List[Dict[str, str]]: A list of dictionaries representing the chat history. Each dictionary contains:  
            - "role": either "human" or "ai"  
            - "content": the content of the message  
  
    Raises:  
        ValueError: If the conversation does not contain the expected "messages" key or if it's not a list.  
    """  
    chat_history: List[Dict[str, str]] = []  
    messages = conversation.get("messages")  
    if messages is None:  
        raise ValueError('The conversation dictionary must contain a "messages" key.')  

    for message in messages:
        role = message.get("role")  
        content = message.get("content", "")  
  
        if role == "user":  
            chat_history.append({"role": "human", "content": content})  
        elif role == "assistant":  
            chat_history.append({"role": "ai", "content": content})  

    #return last max_history messages
    return chat_history[max_history:]


@console_tracer.start_as_current_span("get_session_id")
def get_session_id(device_id: str) -> Optional[str]:  
    """  
    Retrieves the session ID for a given device ID from Redis. If no session ID exists,  
    generates a new UUID as the session ID, stores it in Redis with an expiration time,  
    and returns it.  
  
    Args:  
        device_id (str): The unique identifier of the device.  
  
    Returns:  
        Optional[str]: The session ID associated with the device, or None if an error occurs.  
    """  
    console_logger.debug(f"Retrieving session ID for device_id: '{device_id}'.")  
    try:  
        # Attempt to get the session ID from Redis  
        session_id = redis_client.get(device_id)  
  
        if session_id is None:  
            # No existing session ID found; create a new one  
            session_id = str(uuid.uuid4())  
            console_logger.debug(f"Generated new session ID: '{session_id}' for device_id: '{device_id}'.")  
        else:  
            # Existing session ID found; decode it from bytes to string  
            session_id = session_id.decode('utf-8')  
            console_logger.debug(f"Found existing session ID: '{session_id}' for device_id: '{device_id}'.")  
  
        # Retrieve session timeout from environment variables, defaulting to 60 seconds (1 minute)  
        redis_client.set(name = device_id, value = session_id, ex = os.getenv("SESSION_TIMOUT", 60))    
     
        return session_id
    
    except redis.RedisError as re:  
        console_logger.error(f"Redis error while retrieving/setting session ID for device_id: '{device_id}': {re}")  
        return None  
    except Exception as e:  
        console_logger.error(f"Unexpected error while retrieving/setting session ID for device_id: '{device_id}': {e}")  
        return None  

@console_tracer.start_as_current_span("get_khatabook")
def get_khatabook(device_id)-> Optional[Dict[str, Any]]:  
    """  
    Retrieves khatabook information from the database using the provided device_id.  
    
    Args:  
        device_id (str): The ID of the device to retrieve khatabook for.  
    
    Returns:  
        Optional[Dict[str, Any]]: A dictionary containing khatabook information if found, else None.  
    """  
    console_logger.debug(f"Fetching khatabook for device_id: {device_id}")  
      
    # Retrieve the container name from environment variables with a default fallback  
    container = database.get_container_client(os.getenv("COSMOS_DB_CONTAINER_KHATABOOK", "khatabook"))  
    query = f"SELECT * FROM c WHERE c.deviceId = '{device_id}'"
    console_logger.debug(f"Executing query: {query} ")
    try:  
        khatabook_info = list(container.query_items(  
            query=query,  
            partition_key = device_id
        ))

        console_logger.debug(f"Retrieved khatabook_info: {khatabook_info}")  
        # Return the first khatabook if available, else None  
        return khatabook_info[0] if khatabook_info else None  
    except Exception as e:
        console_logger.error(f"An error occurred while fetching khatabook: {e}")  
        return None

@console_tracer.start_as_current_span("update_khatabook")
def update_khatabook(device_id: str, receivedFrom: str, amount : int) -> str:  
    """  
    Updates the khatabook with given name/amount associated with a device in Cosmos DB.  
  
    Args:  
        device_id (str): The unique identifier of the device.  
        receivedFrom (str): name of the person who gave the amount.
        amount (int): The amount given by the person. 
  
    Returns:  
        str: message indicating the khatabook update is successful or not.

    Raises:  
        ValueError:  
            - If `device_id` is empty.  
            - If `receivedFrom` is empty.  
            - If `amount` is 0.   
    """  
  
    # Input Validation  
    if not device_id.strip():  
        raise ValueError("device_id cannot be empty.")  
    if not receivedFrom.strip():  
        raise ValueError("receivedFrom cannot be empty.")  
    if amount == 0:
        raise ValueError("amount cannot be zero.") 

    try:  
        console_logger.debug(f"Updating khatabook for device_id: {device_id}, received form : {receivedFrom}, amount: {amount}")  
  
        # Retrieve the container client from environment variables or default to "khatabook"  
        container_name = os.getenv("COSMOS_DB_CONTAINER_KHATABOOK", "khatabook")
        container = database.get_container_client(container_name)  
  
        query = f"SELECT * FROM c WHERE c.deviceId = '{device_id}'"  
        console_logger.debug(f"Executing query: {query}")  
  
        # Fetch khatabooks matching the device_id 
        khatabook_list = list(  
            container.query_items(  
                query=query,  
                partition_key=device_id  
            )  
        )  
  
        console_logger.debug(f"Retrieved khatabooks : {khatabook_list}")  
  
        if not khatabook_list:  
            console_logger.warning(f"No khatabook found with device_id: {device_id} ")  
            return False  
  
        # Assume the first khatabook is the target for update  
        khatabook = khatabook_list[0]  
  
        # Update the status and khatabook fields  
        khatabook["totalCollection"] += amount  
        khatabook["last10Transactions"].append({"receivedFrom": receivedFrom, "amount": amount, "transactionTime": datetime.now(timezone.utc).strftime("%Y:%m:%d %H:%M:%S")})

        print(khatabook["last10Transactions"])

        # sort khatabook["last10Transactions"] based on transactionTime descending order and retain max 10 transactions
        khatabook["last10Transactions"] = sorted(khatabook["last10Transactions"], key = lambda x: x["transactionTime"], reverse = True)[:10]
        print(khatabook["last10Transactions"])
          
        # Upsert the updated khatabook back into the container  
        container.upsert_item(khatabook)  
        console_logger.info(f"Successfully updated khatabook for device id : {device_id}")  

        return f'Successfully updated khatabook with amout {amount} received from {receivedFrom}'
  
    except exceptions.CosmosHttpResponseError as cosmos_err:  
        console_logger.error(f"Cosmos DB HTTP response error: {cosmos_err}")  
    except Exception as e:  
        traceback.print_exc() 
        console_logger.error(f"An unexpected error occurred while updating the khatabook: {e}")  
  
    return 'issue in updating the khatabook. please raise a ticket'
    

#print(get_device_info(device_id= "864068071000005"))
#print(get_transactions(device_id= "864068071000005"))
#print(get_notifications(device_id= "864068071000005"))
#print(get_conversation(session_id="123", device_id= "864068071000005"))