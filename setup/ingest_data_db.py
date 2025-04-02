# az resource update --resource-group "vendorpa" --name "vpacosmosdb" --resource-type "Microsoft.DocumentDB/databaseAccounts" --set properties.disableLocalAuth=false
# az resource update --resource-group "vendorpa" --name "vpacosmosdb" --resource-type "Microsoft.DocumentDB/databaseAccounts" --set properties.publicNetworkAccess="Enabled"

import os
import dotenv
from pathlib import Path 
dotenv.load_dotenv(dotenv_path=Path(__file__).parent.parent / 'server' / '.env' )

from azure.cosmos import CosmosClient, PartitionKey
import json
from time import sleep
from server import utils_logger
console_logger, console_tracer = utils_logger.get_logger_tracer()

import dotenv
from pathlib import Path 
dotenv.load_dotenv(dotenv_path=Path(__file__).parent.parent / 'server' / '.env' )

device_data_file = "data\\device.data.json"
notification_data_file = "data\\notification.data.json"
transactions_data_file = "data\\transactions.data.json"
plans_data_file = "data\\plan.data.json"
khatabook_data_file = "data\\khatabook.data.json"


client = CosmosClient(os.getenv("COSMOS_DB_ENDPOINT", "NA"), os.getenv("COSMOS_DB_KEY", "NA"))

database_name = 'demodb'
database = client.create_database_if_not_exists(id=database_name)

def create_container(container_name, parthion_key='/deviceid'):
    console_logger.info(f'Creating container {container_name} with partition key {parthion_key}')
    container = database.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path=parthion_key),
    )
    
    return container


def insert_data(data_file, container_name, parthion_key='/deviceid'):
    console_logger.info(f'Inserting data from {data_file} into {container_name} container')
    container = create_container(container_name, parthion_key)        
    
    data_objects = json.load(open(data_file))
    for data in data_objects:
        container.upsert_item(data)
    
    sleep(1)

insert_data(device_data_file, 'devices', '/deviceId')
insert_data(notification_data_file, 'notifications', '/deviceId')
insert_data(transactions_data_file, 'transactions', '/deviceId')
insert_data(khatabook_data_file, 'khatabook', '/deviceId')
insert_data(plans_data_file, 'plans', '/planId')
create_container('conversations', '/deviceId')
create_container('tickets', '/deviceId')
