# Databricks notebook source
# DBTITLE 1,JDBC
dwDatabase = "dwhprdsynapseSqlPool01"
dwServer = "datawarehouseprdsynapse.sql.azuresynapse.net"
dwUser = "commercialuser"
dwPass = "C0mm3rc1@lU$3R"
dwJdbcPort = "1433"
dwJdbcExtraOptions = "encrypt=true;trustServerCertificate=true;hostNameInCertificate=*.database.windows.net;loginTimeout=30;"

sqlDwUrl = f"jdbc:sqlserver://{dwServer}:{dwJdbcPort};database={dwDatabase};user={dwUser};password={dwPass};${dwJdbcExtraOptions}"

tableName = 'predicta.FOURSOURCE_ALL_31_05_2023'

dft = (spark
  .read
  .format("jdbc")
  .option("url", sqlDwUrl)
  .option("dbtable", tableName)
  .load()
     )

#display(dft)
#dft.count() 
#input('write warning!')
dft.write.mode("overwrite").parquet("/dbfs/mnt/databricks/master_table_mnemosyne_2023_05_31.parquet")  #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!  <<

# COMMAND ----------

dft= spark.read.parquet("/dbfs/mnt/databricks/predicta_master_2023_05_31_j.parquet")  
dft.display()
dft.count()

# COMMAND ----------

# MAGIC %sh
# MAGIC curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
# MAGIC curl https://packages.microsoft.com/config/ubuntu/16.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
# MAGIC sudo apt-get update
# MAGIC sudo ACCEPT_EULA=Y apt-get -q -y install msodbcsql17
# MAGIC pip install sqlalchemy
# MAGIC

# COMMAND ----------

# DBTITLE 1,ODBC
#https://github.com/mkleehammer/pyodbc/wiki/Getting-started
import pyodbc

dwDatabase = ['dwhstagingsynapseSqlPool01', 'dwhprdsynapseSqlPool01']\
[1]
dwServer = ['datawarehousestagingsynapse.sql.azuresynapse.net','datawarehouseprdsynapse.sql.azuresynapse.net']\
[1]
dwUser = "commercialuser"
dwPass = "C0mm3rc1@lU$3R"

#encrypt = Yes? 
cursor =pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+dwServer+';DATABASE='+dwDatabase+';ENCRYPT=no;UID='+dwUser+';PWD='+ dwPass, autocommit=True).cursor()

cursor.execute('select top 10 * from predicta.SOURCE_SAP_GR_31_05_2023')
res = cursor.fetchall()
# for row in cursor:
#     print(row)

# COMMAND ----------



# COMMAND ----------


## create DF from cursor results
# doesnt work.....
df=spark.createDataFrame( list(res[i][:20]  for i in range(3)) )


# COMMAND ----------

list(res[i][:10]  for i in range(3))

# COMMAND ----------

# write to sql server 
# doesnt work... needs analysis

df_to_write = df  # the dataframe 
table= "xxxxxxxxxxxxxxxxxxx"
schema = "xxxxxxxxxxxxxxxxx"
write_mode = [ 'append','replace','fail'][0] #  0:append   1:overwrite   
n_partitions = 100

dwDatabase = ['dwhstagingsynapseSqlPool01', 'dwhprdsynapseSqlPool01']\
[0]
dwServer = ['datawarehousestagingsynapse.sql.azuresynapse.net','datawarehouseprdsynapse.sql.azuresynapse.net']\
[0]

dwUser = "commercialuser"
dwPass = "C0mm3rc1@lU$3R"


import pandas as pd
import pyodbc
#from pyspark.sql.functions import *

df_to_write = df_to_write.repartition(n_partitions)
def write_partition(partition):
    print('writing partition',partition)
    
    pdf = partition.toPandas()

    conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+dwServer+';DATABASE='+dwDatabase+';UID='+dwUser+';PWD='+ dwPass, autocommit=True)

    pdf.to_sql(table, conn, schema=schema, if_exists=write_mode, index=False,chunksize=100000)

df_to_write.foreachPartition(write_partition)

# COMMAND ----------


# # Azure Synapse Connection Configuration
# dwDatabase = "dwhprdsynapseSqlPool01"
# dwServer = "datawarehouseprdsynapse.sql.azuresynapse.net"
# dwUser = "commercialuser"
# dwPass = "C0mm3rc1@lU$3R"
# dwJdbcPort = "1433"
# dwJdbcExtraOptions = "encrypt=true;trustServerCertificate=true;hostNameInCertificate=*.database.windows.net;loginTimeout=30;useBulkCopyForBatchInsert=true;"
# #Connection c = DriverManager.getConnection("jdbc:mysql://host:3306/db?useServerPrepStmts=false&rewriteBatchedStatements=true", "username", "password")
# sqlDwUrl = f"jdbc:sqlserver://{dwServer}:{dwJdbcPort};database={dwDatabase};user={dwUser};password={dwPass};${dwJdbcExtraOptions}"
# batchsize = 500_000_000
# OUTPUT_FILE_PATH = "[dataanalysis].[kallikratikoi_dhmoi]"
# batchsize = 500_000_000

# df.write.mode("append").format("jdbc").option("url", sqlDwUrl).option("dbtable", OUTPUT_FILE_PATH).option("schemaCheckEnabled", "True").option("batchSize", batchsize).option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver").save()

# COMMAND ----------

# test

df_to_write = df  # the dataframe 
schema = "dataanalysis"
table= "test"
write_mode = [ 'append','replace','fail'][1] #  0:append   1:overwrite   
n_partitions = 4

dwDatabase = ['dwhstagingsynapseSqlPool01', 'dwhprdsynapseSqlPool01']\
[0]
dwServer = ['datawarehousestagingsynapse.sql.azuresynapse.net','datawarehouseprdsynapse.sql.azuresynapse.net']\
[0]

dwUser = "commercialuser"
dwPass = "C0mm3rc1@lU$3R"

import pandas as pd
import pyodbc
import sqlalchemy

#conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+dwServer+';DATABASE='+dwDatabase+';UID='+dwUser+';PWD='+ dwPass, autocommit=True)

conn = sqlalchemy.create_engine("mssql+pyodbc://%s:%s@%s/%s?driver=%s"%(dwUser,dwPass,dwServer,dwDatabase,'ODBC+Driver+17+for+SQL+Server'),echo=False)
df_to_write.toPandas().to_sql(table, conn, schema=schema, if_exists=write_mode, index=False,chunksize=100)

# df_to_write = df_to_write.repartition(n_partitions)
# def write_partition(partition):
#     print('writing partition',partition, dir(partition))
#     pdf = partition.toPandas()        

#     conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+dwServer+';DATABASE='+dwDatabase+';UID='+dwUser+';PWD='+ dwPass, autocommit=True)

#     pdf.to_sql(table, conn, schema=schema, if_exists=write_mode, index=False,chunksize=100000)

# df_to_write.mapInPandas(write_partition)

# def f2(wtf):
#     pdf = wtf.toPandas()
#     print(pdf.head(1))
 
#     # for e in wtf:
#     #     pdf = e.toPandas()
#     #     print(pdf.head(1))
#     #     print('hello')

# df_to_write.rdd.mapPartitions(f2)

# COMMAND ----------

df_to_write.display()

# COMMAND ----------

# !!!!!!! WRITE !!!!!!!

# Azure Synapse Connection Configuration
dwDatabase = "dwhprdsynapseSqlPool01"
dwServer = "datawarehouseprdsynapse.sql.azuresynapse.net"
dwUser = "commercialuser"
dwPass = "C0mm3rc1@lU$3R"
dwJdbcPort = "1433"
dwJdbcExtraOptions = "encrypt=true;trustServerCertificate=true;hostNameInCertificate=*.database.windows.net;loginTimeout=30;"

sqlDwUrl = f"jdbc:sqlserver://{dwServer}:{dwJdbcPort};database={dwDatabase};user={dwUser};password={dwPass};${dwJdbcExtraOptions}"
tableName = 'predicta.PR_Municipalities_Army'

input('❗ WRITE WARNING ❗')

dft .repartition(256)\
    .write\
    .mode("append") \
    .format("jdbc") \
    .option("url", sqlDwUrl) \
    .option("dbtable", tableName) \
    .option("schemaCheckEnabled","False")\
    .option("batchSize", 10485760)\
    .option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver") \
    .save()
