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

query = "SELECT  [surname] as staff_surname ,[forename1] as staff_forename, [dept_party_nm]as dept, [job_title],[boss_surname] as manager_surname FROM [Mich].[dbo].[ManagerDept]"
cursor = conn.cursor()
cursor.execute(query)

# Get column names from cursor description
columns = [column[0] for column in cursor.description]

# Fetch all rows as a list of dictionaries
data = []
for row in cursor.fetchall():
    data.append(dict(zip(columns, row)))

# Print the number of records fetched
print(f"Number of records fetched: {len(data)}")

# Specify the directory where you want to save the JSON files
output_dir_path = 'c:/NKCAI/nkcai/data/managerdept/'

# Make sure the directory exists
os.makedirs(output_dir_path, exist_ok=True)

# Loop through the data list
for i, record in enumerate(data):
    # Convert dictionary to JSON
    json_data = json.dumps(record, indent=4)
    
    
     # Create a unique file name for each record using the surname
    output_file_path = os.path.join(output_dir_path, f'{record["staff_surname"]}_{i}.json')
    
    # Write JSON data to a file
    with open(output_file_path, 'w') as f:
        f.write(json_data)
    print(f"Data written to {output_file_path}")