# encoding = utf-8

from os import system
import time
import requests
import csv
import json
import socket
from io import StringIO

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    pass

def get_wiz_access_token(helper, client_id, client_secret):
    """
    Authenticate to Wiz API and get the access token.

    Args:
    client_id (str): The client ID.
    client_secret (str): The client secret.

    Returns:
    str: The access token if authentication is successful, None otherwise.
    """
    
    url = 'https://auth.app.wiz.io/oauth/token'
    
    helper.log_info(f"Obtaining access token for {client_secret}...")
    
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': 'wiz-api'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(url, data=payload, headers=headers)
    
    if response.status_code == 200:
        token_data = response.json()
        helper.log_info(f"Obtaining access token for {client_secret} successful.")
        return token_data['access_token']
    else:
        helper.log_error(f"Failed to obtain access token. Status Code: {response.status_code}. Response: {response.text}")
        return None

def create_cloud_resource_inventory_report(helper, api_url, bearer_token, project_id, report_name):
    
    headers = {
        'Authorization': f'bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    query = {
        "query": "mutation CreateReport($input: CreateReportInput!) {   createReport(input: $input) {     report {       id     }   } }",
        "variables": {
            "input": {
                "name": f"{report_name}",
                "type": "CLOUD_RESOURCE",
                "projectId": f"{project_id}",
                "cloudResourceParams": {
                        "includeCloudNativeJSON": True,
                        "includeWizJSON": True,
                        "entityType": [
                            "VIRTUAL_MACHINE"
                        ]
                }
            }
        }
    }
    
    helper.log_info(f"Creating report: {report_name}. Filter projectId={project_id}")
    
    response = requests.post(api_url, json=query, headers=headers)
    
    if response.status_code == 200:
        rid = response.json()['data']['createReport']['report']['id']
        helper.log_info(f"Report: {report_name} successfully created, id={rid}.")
        return rid
    else:
        helper.log_error(f"Failed to create report. Status Code: {response.status_code}. Response: {response.text}")
        return None

def get_cloud_resource_inventory_report(helper, api_url, bearer_token, rn, report_id):
    headers = {
        'Authorization': f'bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    query = {
        "query": "query ReportDownloadUrl($reportId: ID!) {   report(id: $reportId) {     lastRun {       url       status     }   } }",
        "variables": {
            "reportId": f"{report_id}"
        }
    }
    
    data = []
    
    helper.log_info(f"Obtaining status for report: {rn} ({report_id})")
    
    response = requests.post(api_url, json=query, headers=headers)
    
    if response.status_code == 200:
        
        report_state = response.json()['data']['report']['lastRun']['status']
        
        while report_state != "COMPLETED":
            
            helper.log_info(f"Report status is {report_state}, sleeping for now...")
            time.sleep(10)
            response = requests.post(api_url, json=query, headers=headers)
            
            if response.status_code == 200:
                report_state = response.json()['data']['report']['lastRun']['status']
        
        helper.log_info(f"Report status is {report_state}. Retrieving report as CSV (non-disk, ephemeral).")
        
        report_url = response.json()['data']['report']['lastRun']['url']
        
        report_csv = requests.get(report_url)
        
        if report_csv.status_code == 200:
            
            helper.log_info(f"CSV retrieval was successful. Now parsing data...")
            
            content = report_csv.content.decode('utf-8')
            csv_data = StringIO(content)
            reader = csv.DictReader(csv_data)
            
            for row in reader:
                column_value = row['Cloud Native JSON']

                try:
                    json_object = json.loads(column_value)
                    json_object['lastSeen'] = row['Last Seen']
                    json_object['subscriptionID'] = row['Subscription ID']
                    json_object['projects'] = row['Projects']
                    json_object['region'] = row['Region']
                    data.append(json_object)
                except json.JSONDecodeError as e:
                    helper.log_error(f"Failed to decode JSON. {e}")
            
            return data
        else:
            helper.log_error(f"Failed to retrieve report. Status Code: {response.status_code}. Response: {response.text}")
            return None
    
    else:
        helper.log_error(f"Failed to retrieve report. Status Code: {response.status_code}. Response: {response.text}")
        return None

def collect_events(helper, ew):
    
    global_account = helper.get_arg('global_account')
    CLIENT_ID = global_account['username']
    CLIENT_SECRET= global_account['password']
    url = helper.get_global_setting("api_endpoint_url")
    project_id = helper.get_arg('project_id')
    
    current_epoch = int(time.time())
    this_hostname = socket.gethostname()
    name = helper.get_input_stanza_names()
    rn = f"from_splunk_ta_wiz_vms_{this_hostname}_{name}_{str(current_epoch)}"
    
    helper.log_info(f"Wiz authentication begins here...")
    token = get_wiz_access_token(helper, CLIENT_ID, CLIENT_SECRET)
    
    helper.log_info(f"Report creation phase begins here...")
    report_id = create_cloud_resource_inventory_report(helper, url, token, project_id, rn)
    
    if report_id is None:
        helper.log_error(f"Exiting due to failure to create report.")
        system.exit(1)
    
    meta_source = f"wiz_report_id://{report_id}"
    
    helper.log_info(f"Report creation was successful, now awaiting report run completion.")
    
    data = get_cloud_resource_inventory_report(helper, url, token, rn, report_id)
        
    if data is None:
        helper.log_error(f"Exiting due to failure to retrieve report id {report_id}.")
        system.exit(1)
        
    helper.log_info(f"Collected {len(data)} VMs. Event ingestion phase begins here...")
    
    for d in data:
        data_event = json.dumps(d, separators=(',', ':'))
        event = helper.new_event(source=meta_source, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), host=url, data=data_event)
        ew.write_event(event)
    
    helper.log_info(f"End of collection for report {report_id}.")
    
