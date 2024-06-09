# Databricks notebook source
# MAGIC %md
# MAGIC ## Διαδικασία Κανονικοποίησης B2B_Company_Name
# MAGIC 1. Δημιουργία νέας στήλης B2B_Company_Names_Wemetrix για αποθήκευση αποτελεσμάτων, η οποία περιέχει την επίσημη ονομασία των εταιριών με βάση το ΑΦΜ τους.
# MAGIC 2. Για τη διαδικασία χρησιμοποιήθηκε η στήλη ClVat_IIS.
# MAGIC 3. Στη διαδικασία συμπεριλάβαμε μόνο όσες εγγραφές έχουν τιμή διαφορετική του null στο πεδίο ClVat_IIS .
# MAGIC 4. Χρησιμοποιούμε βάση δεδομένων με τα ΑΦΜ & τα επίσημα ονόματα ιδιωτικών και δημόσιων εταιριών.
# MAGIC 5. Συνδυάζοντας τους 2 πίνακες, κάνουμε αναζήτηση σχετικά με το ποια ΑΦΜ ταιριάζουν με τα διαθέσιμα ΑΦΜ που έχουμε στη δική μας βάση δεδομένων. Όσα ταιριάζουν παίρνουν στην στήλη B2B_Company_Names_Wemetrix την επίσημη ονομασία που έχουμε εμείς στη βάση για τα συγκρεκτιμένα ΑΦΜ.Τα υπόλοιπα παίρνουν τιμή null.
# MAGIC
# MAGIC ##### Κατόπιν ολοκλήρωσης της διαδικασίας στα συμβόλαια του πίνακα "/dbfs/mnt/databricks/master_table_mnemosyne_2023_05_31.parquet":
# MAGIC 1. Τα νομικά πρόσωπα που έχουν τιμή στο πεδίο B2B_Company_Name είναι 273487. Μετά από αυτή τη διαδικασία δίνουμε σε 351874 συμβόλαια τιμή στο B2B_Company_Names_Wemetrix.
# MAGIC 2. Τα αποτελέσματα αποθηκεύτηκαν στον "dbfs:/FileStore/wemetrix/b2b_name_normalization.parquet"
# MAGIC - Πεδία πίνακα: "SOURCE", "Contract_Account_ID","ClVat_IIS","ClCompany_Name","B2B_Company_Name","EnB2B_Company_Name","B2B_Company_Names_Wemetrix"
# MAGIC
# MAGIC Η διαδικασία μπορεί να επαναλαμβάνεται και στα delta με τον παρακάτω κώδικα

# COMMAND ----------

dbutils.widgets.text("input_table",  "wemetrix.foursourcedelta")
input_table = dbutils.widgets.get("input_table")

dbutils.widgets.text("output_table",  "wemetrix.b2b_name_normalization_delta")
output_table = dbutils.widgets.get("output_table")

# COMMAND ----------

import pandas as pd
import numpy as np
import re
import string
import pyspark.sql.functions as F
from pyspark.sql.functions import col, when, length, substring, lpad
from pyspark.sql.types import StringType, IntegerType

db = "dbfs:/FileStore/wemetrix/db_company_names.parquet"

df_master_table = (spark.sql(f"SELECT SOURCE, Contract_Account_ID ,ClVat_IIS, ClCompany_Name , B2B_Company_Name , EnB2B_Company_Name  FROM {input_table}"))

c_db = spark.read.parquet(db)

df_master_table1 = df_master_table\
    .withColumn("ClVat_IIS",F.trim(F.regexp_replace(F.col("ClVat_IIS"), "[^0-9]+", "")))\
    .withColumn("ClCompany_Name",F.trim(F.regexp_replace(F.upper(F.col("ClCompany_Name")), "[^0-9Α-ΩA-Z ]+", "")))\
    .withColumn("B2B_Company_Name",F.trim(F.regexp_replace(F.upper(F.col("B2B_Company_Name")), "[^0-9Α-ΩA-Z ]+", "")))\
    .select("SOURCE", "Contract_Account_ID","ClVat_IIS","ClCompany_Name","B2B_Company_Name","EnB2B_Company_Name")

df_results = df_master_table1\
    .join(c_db,df_master_table1["ClVat_IIS"] == c_db["ΑΦΜ"], "left")\
    .select(df_master_table1["*"],c_db["ΕΠΩΝΥΜΙΑ"].alias("B2B_Company_Names_Wemetrix"))

df_results.write.mode("overwrite").saveAsTable(output_table)