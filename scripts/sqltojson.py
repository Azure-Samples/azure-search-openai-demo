import pyodbc
import json
import os

server = 'etrackr-db'
database = 'mich'
username = 'nkcai'
password = 'Mikimiki087029'

try:
    conn = pyodbc.connect(f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}')
    print("Connection to the database has been established successfully.")
except pyodbc.Error as ex:
    print("Failed to connect to the database.")
    print("Error:", ex)
    exit(1)

query = "SELECT TOP (1000) [surname],[firstname] ,[job_title],[dept],[cn] as Fullname ,[mail],[samaccountname],[Phone],[managername],[managermail] FROM [Mich].[dbo].[ManagerDeptAD]"
cursor = conn.cursor()
cursor.execute(query)

# Get column names from cursor description
columns = [column[0] for column in cursor.description]

# Fetch all rows as a list of dictionaries
data = []
for row in cursor.fetchall():
    data.append(dict(zip(columns, row)))

# Specify the path for the output JSON file
output_file_path = 'c:/NKCAI/nkcai/data/managerdept/ManagerDeptAD.json'

# Convert the entire data list to JSON
all_records_json = json.dumps(data, indent=4)

# Write the JSON data to a single file
with open(output_file_path, 'w') as f:
    f.write(all_records_json)

print(f"All records written to {output_file_path}")
