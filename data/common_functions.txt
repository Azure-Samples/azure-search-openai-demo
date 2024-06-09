# Databricks notebook source
# Databricks notebook source
from pyspark.sql.functions import current_timestamp
import pyodbc
from pandas import DataFrame
import pyspark.sql.functions as F

def add_ingestion_date(input_df):
  output_df = input_df.withColumn("ingestion_date", current_timestamp())
  return output_df

# COMMAND ----------

def re_arrange_partition_column(input_df, partition_column):
  column_list = []
  for column_name in input_df.schema.names:
    if column_name != partition_column:
      column_list.append(column_name)
  column_list.append(partition_column)
  output_df = input_df.select(column_list)
  return output_df

# COMMAND ----------

def overwrite_partition(input_df, db_name, table_name, partition_column):
  output_df = re_arrange_partition_column(input_df, partition_column)
  spark.conf.set("spark.sql.sources.partitionOverwriteMode","dynamic")
  if (spark._jsparkSession.catalog().tableExists(f"{db_name}.{table_name}")):
    output_df.write.mode("overwrite").insertInto(f"{db_name}.{table_name}")
  else:
    output_df.write.mode("overwrite").partitionBy(partition_column).format("parquet").saveAsTable(f"{db_name}.{table_name}")

# COMMAND ----------

def df_column_to_list(input_df, column_name):
  df_row_list = input_df.select(column_name) \
                        .distinct() \
                        .collect()
  
  column_value_list = [row[column_name] for row in df_row_list]
  return column_value_list

# COMMAND ----------

def merge_delta_data(input_df, db_name, table_name, folder_path, merge_condition, partition_column):
  spark.conf.set("spark.databricks.optimizer.dynamicPartitionPruning","true")

  from delta.tables import DeltaTable
  if (spark._jsparkSession.catalog().tableExists(f"{db_name}.{table_name}")):
    deltaTable = DeltaTable.forPath(spark, f"{folder_path}/{table_name}")
    deltaTable.alias("tgt").merge(
        input_df.alias("src"),
        merge_condition) \
      .whenMatchedUpdateAll()\
      .whenNotMatchedInsertAll()\
      .execute()
  else:
    input_df.write.mode("overwrite").partitionBy(partition_column).format("delta").saveAsTable(f"{db_name}.{table_name}")

def readfromsynapsetodelta(tableName,destinationtable,partitionfield="SOURCE", addfield="GR_Customer_Code"):
    #read from synapse, write to parquet.

    # 1.1 hours for dataanalysis.gr_cleansed_customers_31_05_2023
    dwDatabase = "dwhprdsynapseSqlPool01"
    dwServer = "datawarehouseprdsynapse.sql.azuresynapse.net"
    dwUser = "commercialuser"
    dwPass = "C0mm3rc1@lU$3R"
    dwJdbcPort = "1433"
    dwJdbcExtraOptions = "encrypt=true;trustServerCertificate=true;hostNameInCertificate=*.database.windows.net;loginTimeout=30;"

    sqlDwUrl = f"jdbc:sqlserver://{dwServer}:{dwJdbcPort};database={dwDatabase};user={dwUser};password={dwPass};${dwJdbcExtraOptions}"

    # which table to read
    # tableName = 'dataanalysis.gr_cleansed_customers_2023_05_26'
    #tableName = 'predicta.source_ebill_31_05_2023' 
    #tableName = 'dataanalysis.DELTAFOURSOURCE_31_05_2023_26_05_2023'
    #ted's mnemosyne: mnemosyne_output_31_05_2023
    dft = (spark
    .read
    .format("jdbc")
    .option("url", sqlDwUrl)
    .option("dbtable", tableName)
    .load()
        )
    # dft.display()
    # filepath=f"dbfs:/mnt/datasciencefiles/wemetrix/{tableName.replace('dataanalysis.','')}.parquet"
    ###### write parquet to databricks  ######
    # dft.write.mode("overwrite")\
    #     .parquet(filepath) 
    # #write delta table
    if addfield and addfield not in dft.columns:
        dft = dft.withColumn(addfield, F.lit(''))
    print(1)
    try:
      spark.sql("DROP TABLE " +destinationtable )
    except Exception as e:
      print(e)
    print(2)
    if partitionfield:          
        dft.write.mode("overwrite").partitionBy(partitionfield).format("delta").saveAsTable(destinationtable)
    else:
        dft.write.mode("overwrite").format("delta").saveAsTable(destinationtable)
    # dft.write.format("delta").save(f"dbfs:/mnt/datasciencefiles/wemetrix/{tableName.replace('dataanalysis.','')}")
    return destinationtable

def executeatsynapse(command):
    #https://github.com/mkleehammer/pyodbc/wiki/Getting-started
  
    dwDatabase = ['dwhstagingsynapseSqlPool01', 'dwhprdsynapseSqlPool01']\
    [1]
    dwServer = ['datawarehousestagingsynapse.sql.azuresynapse.net','datawarehouseprdsynapse.sql.azuresynapse.net']\
    [1]
    dwUser = "commercialuser"
    dwPass = "C0mm3rc1@lU$3R"

    #encrypt = Yes? 
    cursor =pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+dwServer+';DATABASE='+dwDatabase+';ENCRYPT=no;UID='+dwUser+';PWD='+ dwPass, autocommit=True).cursor()

    cursor.execute(command)

    # df = DataFrame(cursor.fetchall())
    # df.columns = cursor.keys()
    # return df

# COMMAND ----------

def setmetadata(x):
    spark.conf.set("spark.databricks.delta.commitInfo.userMetadata", x)


# COMMAND ----------

# executeatsynapse('exec dataanalysis.createdeltatable \'[predicta].[FOURSOURCE_ALL_26_05_2023]\',\' [predicta].[FOURSOURCE_ALL_31_05_2023]\',\'dataanalysis.[DELTAFOURSOURCE_31_05_2023_26_05_2023_C]\'')

# # print(df1)


# COMMAND ----------

