# Databricks notebook source
dbutils.widgets.text("input_table",  "wemetrix.foursourcedelta")
input_table = dbutils.widgets.get("input_table")

dbutils.widgets.text("output_table",  "wemetrix.gender_match_results_delta")
output_table = dbutils.widgets.get("output_table")

# COMMAND ----------

import pyspark.sql.functions as F
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType
from pyspark.sql.window import Window
import pandas as pd

# Διαδικασία δημιουργίας ελληνικού και λατινικού λεξικού ονομάτων. Τρέχει μία φορά.
# df_greek_names_gender = spark.read.parquet("dbfs:/FileStore/wemetrix/names_greek_gender_dataset.parquet")
# df_latin_names_gender = spark.read.parquet("dbfs:/FileStore/wemetrix/names_latin_gender_dataset.parquet")
# df_name_gender_dictionary = (df_greek_names_gender.unionAll(df_latin_names_gender)
#                 .withColumn("Name", F.trim(F.upper(F.col("Name"))) )
#                 .withColumnRenamed("Name", "Name_Match")
#                 .dropDuplicates(["Name_Match"]))
# df_name_gender_dictionary.filter(F.length(F.col("Name_Match")) > 1).write.mode("overwrite").parquet("dbfs:/FileStore/wemetrix/names_gender_dataset.parquet")




# COMMAND ----------


sap_table = "dbfs:/mnt/PRD/curated/SAP_ISU/but000"
df_name_gender_dictionary = spark.read.parquet("dbfs:/FileStore/wemetrix/names_gender_dataset.parquet")


spark.sql(f"DROP TABLE IF EXISTS {output_table}")


df = (spark.sql(f"SELECT * FROM {input_table}")
      .filter( (F.col("PrFirst_Name").isNotNull() | F.col("PrLast_Name").isNotNull()) & 
              (
                 ((F.col("PrCustomer_Type")!="organization") | (F.col("PrCustomer_Type").isNull())) & 
                 ((F.col("PrCustomer_Type_IIS") != "municipalities") | F.col("PrCustomer_Type_IIS").isNull() ) ) )
      .select("PrFirst_Name", "PrLast_Name", "SOURCE", "Contract_Account_ID", "Business_Partner_ID")
    .withColumn("PrFirst_Name", F.trim(F.upper(F.col("PrFirst_Name"))) )
    .withColumn("PrLast_Name", F.trim(F.upper(F.col("PrLast_Name"))) )
    .withColumn("PrFirst_Name", F.when(F.col("PrFirst_Name").isNull(), F.lit("no_first_name")).otherwise(F.col("PrFirst_Name")) ))


# Get gender from SAP
df_sap = (spark.read.format("delta").load(sap_table)
                .withColumn("Gender_SAP", F.when(F.trim(F.col("XSEXM")) == "X", F.lit("M")).otherwise(F.when(F.trim(F.col("XSEXF")) == "X", F.lit("F"))) )
                .filter(F.col("Gender_SAP").isNotNull())
                .select("Gender_SAP", "PARTNER").dropDuplicates())
df = df.join(df_sap, on = [df.Business_Partner_ID == df_sap.PARTNER], how="left")                     


# Get gender from first name
df = (df.join(F.broadcast(df_name_gender_dictionary.withColumnRenamed("Gender", "Gender_Name")), 
                        on = [df.PrFirst_Name == df_name_gender_dictionary.Name_Match], 
                        how="left"))

# Get gender from first and last name endings
df = (df.withColumn("PrLast_Name_ending", F.substring(F.col("PrLast_Name"), -1, 1) )
        .withColumn("PrFirst_Name_ending", F.substring(F.col("PrFirst_Name"), -1, 1) )
        .withColumn("Gender_Name_Ending", F.when((F.col("PrFirst_Name_ending") == "Σ" ) & 
                                                 (F.col("PrLast_Name_ending").isin(["Σ", "ΟΥ"])) , F.lit("M") ).otherwise(
                                            F.when((F.col("PrFirst_Name_ending").isin(["Α", "Ε", "Η", "Ι", "Ο", "Υ", "Ω"]) ) & 
                                                   (F.col("PrLast_Name_ending").isin(["Α", "Ε", "Η", "Ι", "Ο", "Υ", "Ω"])), F.lit("F") ) ) # "ταυτόχρονη" υλοποίηση
        )
        .withColumn("Gender_Name_Ending", F.when((F.length(F.col("PrFirst_Name")) > 4) & 
                                                 (F.length(F.col("PrLast_Name")) > 4) , F.col("Gender_Name_Ending")))
)


# Finalize Gender and Gender_Info Columns
df = (df.drop("Name_Match")
.withColumn("Gender", F.when(F.col("Gender_SAP").isNotNull(), F.col("Gender_SAP")).otherwise(
    F.when(F.col("Gender_Name").isNotNull(), F.col("Gender_Name")).otherwise(
        F.when( F.col("Gender_Name_Ending").isNotNull() , F.col("Gender_Name_Ending"))
        ) ) )
.withColumn("Gender_Info", F.when(F.col("Gender_SAP").isNotNull(), F.lit("SAP")).otherwise(
    F.when(F.col("Gender_Name").isNotNull(), F.lit("First Name Match")).otherwise(
        F.when(F.col("Gender_Name_Ending").isNotNull(), F.lit("First & Last Name Ending"))
        ) ) )
)


# Write Final Table
(df
 .select("PrFirst_Name", "PrLast_Name", "SOURCE", "Contract_Account_ID", "Gender", "Gender_Info")
 .write.mode("overwrite").saveAsTable(output_table))

# COMMAND ----------

