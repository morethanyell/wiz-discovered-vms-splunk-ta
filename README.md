# Wiz Discovered Virtual Machines Splunk Technology Add-on (TA)

## Overview
The Wiz Virtual Machines Splunk TA is designed to collect and ingest logs from Wiz's Cloud Resource Inventory, specifically targeting discovered Virtual Machines. This TA simplifies the process of retrieving and analyzing your cloud infrastructure data within Splunk.

## Features
- Automated creation and retrieval of Wiz reports.
- Ingests discovered Virtual Machines from Wiz as individual Splunk events.
- Extracts and uses the "Last Seen" timestamp from the CSV report for each event.

## Requirements
- Splunk Enterprise 9.x or later
- Access to Wiz's Cloud Resource Inventory
- Wiz Client ID credentials with permissions to create and retrieve reports

## Installation
- Download the Wiz Virtual Machines Splunk TA package.
- Log in to your Splunk instance.
- Navigate to Apps > Manage Apps.
- Click Install app from file.
- Upload the downloaded package and click Upload.
- Restart Splunk if prompted.

## Configuration
- After installation, navigate to the TA's configuration page.
- Enter your Wiz API credentials.
    - Wiz API Client ID in the Username field
    - The associated Client Secret in the Password field
- Go to Inputs tab to create a collection (inputs stanza)
    - Give it a unique name
    - Set the desired interval for report generation and retrieval (recommendation: not less than 12400)
    - Select the index
    - Select the Client ID you just created under the Global Account dropdown menu
    - Enter the Project ID to filter your results, leave the asterisk to collect everything
- Save the configuration.

## How It Works
- The TA generates a report in Wiz's Cloud Resource Inventory.
- It waits for the report to be completed.
- Once the report is complete, it retrieves the report in CSV format.
- Each row of the CSV is ingested as an individual Splunk event.
- The timestamp for each event is derived from the "Last Seen" field in the CSV.


## Support
For support, please contact me at daniel.l.astillero@gmail.com (same email for my beer funds 😉)