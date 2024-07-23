import pyodbc
import json
import os

server = 'etrackr-db'
database = 'mich'
username = 'nkcai'
password = 'Mikimiki087029'

conn = pyodbc.connect(f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}')

query = "SELECT  [surname] as staff_surname ,[forename1] as staff_forename, [dept_party_nm]as dept, [job_title],[boss_surname] as manager_surname FROM [Mich].[dbo].[ManagerDept]"
cursor = conn.cursor()
cursor.execute(query)

# Get column names from cursor description
columns = [column[0] for column in cursor.description]

# Fetch all rows as a list of dictionaries
data = []
for row in cursor.fetchall():
    data.append(dict(zip(columns, row)))

# Specify the directory where you want to save the JSON files
output_dir_path = 'c:/NKCAI/nkcaichat/data/'

# Make sure the directory exists
os.makedirs(output_dir_path, exist_ok=True)

# Loop through the data list
for i, record in enumerate(data):
    # Convert dictionary to JSON
    json_data = json.dumps(record, indent=4)
    
    # Create a unique file name for each record
    output_file_path = os.path.join(output_dir_path, f'output_{i}.json')
    
    # Write JSON data to a file
    with open(output_file_path, 'w') as f:
        f.write(json_data)

Copilot
Executing Task:

write a Python code to execute the given task


Thank you for sharing the Python

You
can you change the above code so that iti produces on eJSON file
Copilot
Executing Task:

change the given code to produce one JSON file


Certainly! I’ve modified the code to produce a single JSON file. Here’s the updated version:

Python

import pyodbc
import json
import os

server = 'etrackr-db'
database = 'mich'
username = 'nkcai'
password = 'Mikimiki087029'

conn = pyodbc.connect(f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}')

query = "SELECT [surname] as staff_surname, [forename1] as staff_forename, [dept_party_nm] as dept, [job_title], [boss_surname] as manager_surname FROM [Mich].[dbo].[ManagerDept]"
cursor = conn.cursor()
cursor.execute(query)

# Get column names from cursor description
columns = [column[0] for column in cursor.description]

# Fetch all rows as a list of dictionaries
data = []
for row in cursor.fetchall():
    data.append(dict(zip(columns, row)))

# Convert the entire data list to a single JSON object
json_data = json.dumps(data, indent=4)

# Specify the directory where you want to save the JSON file
output_file_path = 'c:/NKCAI/nkcaichat/data/output.json'

# Write the JSON data to the file
with open(output_file_path, 'w') as f:
    f.write(json_data)

print(f"Data successfully saved as {output_file_path}")