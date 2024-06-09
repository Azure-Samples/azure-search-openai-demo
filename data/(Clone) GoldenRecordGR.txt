# Databricks notebook source
# DBTITLE 1,Import pyspark/python modules and functions
#import pre-build python modules
import pandas as pd
import os
from pyspark.sql.types import IntegerType, StringType, LongType, DoubleType
from pyspark.sql import Window
from pyspark.sql.functions import udf
import pyspark.sql.functions as F
import time
import datetime

#Import custom python modules
%reload_ext autoreload
%autoreload 2
from src.py_functions import *

# COMMAND ----------

# DBTITLE 1,Set-up widgets
dbutils.widgets.text("input_table", "wemetrix.foursourcerun04")
input_table= dbutils.widgets.get("input_table")

dbutils.widgets.text("output_table",  "wemetrix.foursource_grrun04")
output_table = dbutils.widgets.get("output_table")

dbutils.widgets.text("output_table_write", "ON")
output_table_write_mode = dbutils.widgets.get("output_table_write")

dbutils.widgets.text("main_records_execution", "ON")
main_records_execution_mode = dbutils.widgets.get("main_records_execution")

# COMMAND ----------

# DBTITLE 1,Read input table(s)
df_golden_records = spark.sql(f"SELECT * FROM {input_table}")
# Σύνολο εγγαρφών: 18,205,997, NOT NULL GROUPS: 2,849,064

# COMMAND ----------

# DBTITLE 1,Select input columns to generate GR fields
cols_all = [
    "Contract_Account_ID",
    "SOURCE",
    "Active_Contract",
    "PrCustomer_Type_IIS",
    "ClFirst_Name",
    "ClLast_Name",
    "ClFather_Name",
    "PrFirst_Name",
    "PrLast_Name",
    "PrFather_Name",
    "ClAT_IIS",
    "AT_Info",
    "ClDOY_IIS",
    "DOY_Info",
    "ClB2B_Email_Uppercase",
    "ClEmail_Uppercase",
    "Email_Info",
    "Last_Update_Date",
    "MoveOut_Date",
    "MoveIn_Date",
    "ClCompany_Name",
    "B2B_Company_Name",
    "PrCompany_Name",
    "B2B_Fixphone_IIS",
    "B2B_Cellphone_IIS",
    "ClPassport_IIS",
    "Passport_Info",
    "ClVAT_IIS",
    "VAT_ID_Info",
    "Fixphone_IIS",
    "Cellphone_IIS",
    "TrB2B_Municipality_Name",
    "B2B_Municipality_Name",
    "TrBilling_Municipality_Name",
    "Billing_Municipality_Name",
    "TrB2B_Street",
    "B2B_Street",
    "TrBilling_Street",
    "Billing_Street",
    "TrB2B_Postal_Code",
    "B2B_Postal_Code",
    "TrBilling_Postal_Code",
    "Billing_Postal_Code",
    "TrB2B_Region_Name",
    "TrBilling_Region_Name",
    "B2B_Area_PPC",
    "Billing_Area_PPC",
    "B2B_TerraKey",
    "Billing_TerraKey",
    "TrB2B_WGS84_latitude",
    "TrBilling_WGS84_latitude",
    "TrB2B_WGS84_longitude",
    "TrBilling_WGS84_longitude",
    "TrB2B_House_Number",
    "PrB2B_House_Number",
    "TrBilling_House_Number",
    "PrBilling_House_Number",
    "SAP_Phone_1_FIXED",
    "SAP_Phone_1_CELL",
    "SAP_Phone_2_FIXED",
    "SAP_Phone_2_CELL",
    "FAIDRA_Phone_1_FIXED",
    "FAIDRA_Phone_1_CELL",
    "FAIDRA_Phone_2_CELL",
    "FAIDRA_Phone_2_FIXED",
    "EVALUE_Phone_1_FIXED",
    "EVALUE_Phone_1_CELL",
    "EVALUE_Phone_2_FIXED",
    "EVALUE_Phone_2_CELL",
    "EVALUE_Phone_3_FIXED",
    "EVALUE_Phone_3_CELL",
    "EVALUE_Phone_4_FIXED",
    "EVALUE_Phone_4_CELL",
    "EVALUE_Phone_5_FIXED",
    "EVALUE_Phone_5_CELL",
    "EBILL_Phone_1_FIXED",
    "EBILL_Phone_1_CELL",
    "EBILL_Phone_2_FIXED",
    "EBILL_Phone_2_CELL",
    "wemetrix_mp_customer_code",
    "wemetrix_match_type",
    "wemetrix_matching_ratio",
    "wemetrix_pass"
]
df_golden_records = df_golden_records.select(*(cols_all))

# COMMAND ----------

df_golden_records = df_golden_records.withColumn(
    "wemetrix_mp_customer_code_v2",
    F.when(F.col("wemetrix_mp_customer_code").isNull(), F.col("Contract_Account_ID")).otherwise(F.col("wemetrix_mp_customer_code"))
).drop(
    F.col("wemetrix_mp_customer_code")
).withColumnRenamed(
    "wemetrix_mp_customer_code_v2",
    "wemetrix_mp_customer_code"
)
# Σύνολο εγγαρφών: 18,205,997
#TOTAL GROUPS (NULL + NOT NULL): 10,856,766

# COMMAND ----------

# MAGIC %md
# MAGIC ## -- Get Main Records per Group --

# COMMAND ----------

PARENT_LOCATION = "dbfs:/FileStore/wemetrix/"
MAIN_RECORDS_TABLE_NAME = "main_records_results"

if main_records_execution_mode == "ON":
    #Initialise arguments
    mainRecord_identification_cols = [
        "SOURCE",
        "Contract_Account_ID",
        "Active_Contract",
        "wemetrix_match_type",
        "wemetrix_mp_customer_code" #Legacy version used: wemetrix_gr_group
    ]
    main_records_table_write = "ON"
    weight_cols = "wemetrix_matching_ratio"
    group_cols = "wemetrix_mp_customer_code"
    type_cols = "wemetrix_match_type"
    mainrecord_cols = "wemetrix_main_record"
    rule1_cols = "rule1_mr"
    rule2_cols = "rule2_mr"
    rule2_corrected_cols = "rule2_corrected"
    rule3_cols = "rule3_mr"
    rule3_corrected_cols = "rule3_corrected"
    rank_cols = "weight_rank"

    main_records_dev = generate_main_recods(
        df_golden_records,
        main_records_table_write,
        MAIN_RECORDS_TABLE_NAME,
        mainRecord_identification_cols,
        weight_cols,
        group_cols,
        type_cols,
        mainrecord_cols,
        rule1_cols,
        rule2_cols,
        rule2_corrected_cols,
        rule3_cols,
        rule3_corrected_cols,
        rank_cols
    )
    print("Main reconrds computed and table is written under path: wemetrix.{0}".format(MAIN_RECORDS_TABLE_NAME))
else:
    main_records_dev = spark.read.parquet(f"{os.path.join(PARENT_LOCATION, MAIN_RECORDS_TABLE_NAME)}.parquet")

df_gr = df_golden_records.alias("a").join(
    main_records_dev.select(["Contract_Account_ID", "SOURCE", "wemetrix_main_record"]).alias("b"),
    on = ["Contract_Account_ID", "SOURCE"],
    how="left"
) # DISTINCT GROUPS WITH MAIN RECORDS = 2,850,999

# COMMAND ----------

# DBTITLE 1,QA on main records column
QA_MODE = "OFF"
GROUP_COLS = "wemetrix_mp_customer_code"
if QA_MODE == "ON":
    unique_values_count = main_records_dev.select(F.countDistinct(GROUP_COLS)).collect()[0][0]
    print("Distinct GROUPS: ", unique_values_count)

    df_more_thanone_mr = main_records_dev.groupBy(GROUP_COLS).agg(F.sum("wemetrix_main_record").alias("total_mr"))
    ll_one = [row[GROUP_COLS] for row in df_more_thanone_mr.filter(F.col("total_mr") == 1).collect()]
    ll_above_one = [row[GROUP_COLS] for row in df_more_thanone_mr.filter(F.col("total_mr") > 1).collect()]
    ll_zero = [row[GROUP_COLS] for row in df_more_thanone_mr.filter(F.col("total_mr") == 0).collect()]
    print("=1: ",len(ll_one))
    print(">1: ",len(ll_above_one))
    print("=0:",len(ll_zero))

# COMMAND ----------

# MAGIC %md
# MAGIC ## -- GR Columns Calculations --
# MAGIC
# MAGIC Below we proceed with the development of the golden record columns marked with the prefix *GR_*
# MAGIC Some notes to keep in mind when checking the results.
# MAGIC
# MAGIC > Notes</br>
# MAGIC
# MAGIC **Note 1**</br>
# MAGIC In the most frequent logic there were many groups for which the selection based on the value with the highest count was not sufficient. For example in the case of *GR_ClFirst_Name* there were groups with at least two frequent names. To make a final selection for those groups that had equally frequent values we added two more filters. The first filter was the **maximum matching ratio** (aka matching weight). Thus, the value with the highest weight was selected. And the second filter was the **maximum Contract Account ID**. Thus, if two values had the same frequency (occurence), same matching weight, the one with the *maximum* (latest) *Contract Account ID* was selected.
# MAGIC
# MAGIC > Issues</br>
# MAGIC
# MAGIC **Issue 1**</br>
# MAGIC The field **B2BEmail_Info** was not found in the input table. Thus, value NULL was used when column *ClB2B_Email_Uppercase* had a value.
# MAGIC
# MAGIC **Issue 2**</br>
# MAGIC The field **wemetrix_match_type** was not found in the input table.
# MAGIC
# MAGIC > UAT on output table
# MAGIC
# MAGIC You may use the following GR_GROUPS for quality checking the results of the GR columns. You can update the list with more groups.
# MAGIC
# MAGIC [
# MAGIC   300000018, 300000529, 300000386, 300001639, 300000218, 300000192, 300000295, 300000064, 300000174, 300000293, 400301234, 400311882, 400241990, 200000023, 100001684, 300631939, 400079133, 100000934, 200000082
# MAGIC ]

# COMMAND ----------



# COMMAND ----------

checkpoint_tables_version = "PROD"
checkpoint_phones_version = "PROD"
active_phones = f"tmp_active_phones_{checkpoint_phones_version}"
all_phones = f"tmp_all_phones_{checkpoint_phones_version}"
active_addresses = f"tmp_active_addresses_{checkpoint_tables_version}"
all_addresses = f"tmp_all_addresses_{checkpoint_tables_version}"
golden_gr_one = f"tmp_golden_gr_one_{checkpoint_tables_version}"
golden_gr_two = f"tmp_golden_gr_second_{checkpoint_tables_version}"
golden_gr_three = f"tmp_golden_gr_three_{checkpoint_tables_version}"
golden_gr_four = f"tmp_golden_gr_four_{checkpoint_tables_version}"
golden_gr_five = f"tmp_golden_gr_five_{checkpoint_tables_version}"
golden_gr_six = f"tmp_golden_gr_six_{checkpoint_tables_version}"
golden_gr_seven = f"tmp_golden_gr_seven_{checkpoint_tables_version}"
golden_gr_eight = f"tmp_golden_gr_eight_{checkpoint_tables_version}"
golden_gr_nine = f"tmp_golden_gr_nine_{checkpoint_tables_version}"
#---------------------------------------------------------------------------------------------------------------------------

df_gr = df_gr.join(
    df_gr.select(
        "B2B_Cellphone_IIS", "ClPassport_IIS", "Passport_Info", "wemetrix_mp_customer_code"
        ).filter(
            F.col("wemetrix_main_record") == 1
        ).withColumnRenamed(
            "B2B_Cellphone_IIS", "MP_B2B_Cellphone_IIS"
        ).withColumnRenamed(
            "ClPassport_IIS", "MP_ClPassport_IIS"
        ).withColumnRenamed(
            "Passport_Info", "MP_Passport_Info"
        ),
        on=["wemetrix_mp_customer_code"],
        how="left"
    )
print("Checkpoint 1: OK")

df_gr = (
    df_gr.join(get_GR_field(df_gr, "ClCompany_Name", "wemetrix_mp_customer_code"), on=["wemetrix_mp_customer_code"], how="left")
         .join(get_GR_field(df_gr, "B2B_Company_Name", "wemetrix_mp_customer_code"), on=["wemetrix_mp_customer_code"], how="left")
         .join(get_GR_field(df_gr, "B2B_Fixphone_IIS", "wemetrix_mp_customer_code"), on=["wemetrix_mp_customer_code"], how="left")
         .join(get_GR_field(df_gr, "B2B_Cellphone_IIS", "wemetrix_mp_customer_code"), on=["wemetrix_mp_customer_code"], how="left")
         .withColumn("GR_B2B_Cellphone_IIS", F.when(F.col("MP_B2B_Cellphone_IIS").isNotNull(), F.col("MP_B2B_Cellphone_IIS")).otherwise(F.col("GR_B2B_Cellphone_IIS")) )
         .join(get_GR_field(df_gr, "ClPassport_IIS", "wemetrix_mp_customer_code"), on=["wemetrix_mp_customer_code"], how="left")
         .withColumn(
             "GR_Passport",
             F.when(
                 F.col("MP_ClPassport_IIS").isNotNull(), F.col("MP_ClPassport_IIS")
            ).otherwise(
                F.col("GR_ClPassport_IIS")
            )
        ).drop(
            F.col("GR_ClPassport_IIS")
        )
         .join(get_GR_field(df_gr, "Passport_Info", "wemetrix_mp_customer_code"), on=["wemetrix_mp_customer_code"], how="left")
         .withColumn("GR_Passport_Info", F.when(F.col("MP_Passport_Info").isNotNull(), F.col("MP_Passport_Info")).otherwise(F.col("GR_Passport_Info")))
    )
df_gr.write.option("compression", "snappy").mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_seven}.parquet")
print("Checkpoint 2: OK")

#---------------------------------------------------------------------------------------------------------------------------
df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_seven}.parquet")
window_spec = Window.partitionBy("wemetrix_mp_customer_code").orderBy(F.col("wemetrix_main_record").desc())
df_gr = df_gr \
    .withColumn("GR_Customer_Code", F.col("wemetrix_mp_customer_code")) \
    .withColumn("GR_SOURCE", F.first(F.col("SOURCE")).over(window_spec)) \
    .withColumn("GR_MatchSetID", F.first(F.col("wemetrix_matching_ratio")).over(window_spec))
print("Checkpoint 3: OK")
#---------------------------------------------------------------------------------------------------------------------------

golden_grcols = [
    ("ClFirst_Name", "GR_ClFirst_Name"),
    ("ClLast_Name", "GR_ClLast_Name"),
    ("ClFather_Name", "GR_ClFather_Name"),
    ("PrFirst_Name", "GR_First_Name"),
    ("PrFather_Name", "GR_Father_Name"),
    ("ClAT_IIS", "GR_AT")
]
df_gr = df_gr.join(
    find_frequent_customertype(df_gr, "wemetrix_mp_customer_code", "PrCustomer_Type_IIS")\
        .select(
            "wemetrix_mp_customer_code",
            F.col("Most_Frequent_PrCustomer_Type_IIS").alias("GR_Customer_Type")
        ),
    on="wemetrix_mp_customer_code",
    how="left"
)
df_gr.write.option("compression", "snappy").mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_eight}.parquet")
print("Checkpoint 4.1: OK") #GOOD
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_eight}.parquet")
df_gr = df_gr.join(
    get_GR_field(df_gr, "PrLast_Name", "wemetrix_mp_customer_code"),
    on=["wemetrix_mp_customer_code"],
    how="left"
).withColumn(
    "GR_Last_Name", 
    F.when(F.col("GR_Customer_Type") != "person", None).otherwise(F.col("GR_PrLast_Name"))
).drop(
    F.col("GR_PrLast_Name")
).write.option("compression", "snappy").mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_nine}.parquet")
print("Checkpoint 4.2: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_nine}.parquet")
df_gr = df_gr.join(
    get_GR_field(df_gr, "PrCompany_Name", "wemetrix_mp_customer_code"),
    on=["wemetrix_mp_customer_code"],
    how="left"
).withColumn(
    "GR_Company_Name",
    F.when(
        F.col("GR_Customer_Type") == "person", None
    ).otherwise(
        F.when(
            F.col("GR_B2B_Company_Name").isNotNull(), F.col("GR_B2B_Company_Name")
        ).otherwise(
            F.col("GR_PrCompany_Name")
        )
    )
).drop(
    F.col("GR_PrCompany_Name")
).write.option("compression", "snappy").mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_three}.parquet")
print("Checkpoint 4.3: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_three}.parquet")
count = 0
i = 2
for tuple_object in golden_grcols:
    if count == 0:
        find_frequent_ClNames(
            df_gr, "wemetrix_mp_customer_code", tuple_object[0]
        ).select(
            [ "wemetrix_mp_customer_code", tuple_object[0] ]
        ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet")
        count = 1
        print("Checkpoint 5.1: OK")
    else:
        if tuple_object[1].startswith("GR_Cl"):
            first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet")
            first_results.join(
                find_frequent_ClNames(
                    df_gr, "wemetrix_mp_customer_code", tuple_object[0]
                ).select(
                    ["wemetrix_mp_customer_code", tuple_object[0]]
                ),
                on="wemetrix_mp_customer_code",
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet")
            print(f"Checkpoint 5.{i}: OK")
        elif tuple_object[1].startswith("GR_F"):
            first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet")
            first_results.join(
                find_frequent_PrNames(df_gr, "wemetrix_mp_customer_code", tuple_object[0], apply_prefix_udf),
                on="wemetrix_mp_customer_code",
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet")
            print(f"Checkpoint 5.{i}: OK")
        elif tuple_object[1] == "GR_AT":
            first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet")
            first_results.join(
                find_frequent_at(df_gr, "wemetrix_mp_customer_code", "ClAT_IIS"),
                on="wemetrix_mp_customer_code",
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet")
            print(f"Checkpoint 5.{i}: OK")
        i+=1

first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet")
df_gr = df_gr.alias("a").join(
    first_results.alias("b"),
    on="wemetrix_mp_customer_code",
    how="left"
).withColumn(
    "GR_ClFirst_Name",
    F.when(F.col("a.GR_Customer_Type") != "person", None).otherwise(F.col("b.ClFirst_Name"))
).withColumn(
    "GR_ClLast_Name",
    F.col("b.ClLast_Name")
).withColumn(
    "GR_ClFather_Name",
    F.when(F.col("a.GR_Customer_Type") != "person", None).otherwise(F.col("b.ClFather_Name"))
).withColumn(
    "GR_First_Name",
    F.when(F.col("a.GR_Customer_Type") != "person", None).otherwise(F.col("b.PrFirst_Name_selection"))
).withColumn(
    "GR_Father_Name",
    F.when(F.col("a.GR_Customer_Type") != "person", None).otherwise(F.col("b.PrFather_Name_selection"))
).withColumn(
    "GR_AT",
    F.col("b.ClAT_IIS_selection")
).drop(
    F.col("b.ClFirst_Name"),
    F.col("b.ClLast_Name"),
    F.col("b.ClFather_Name"),
    F.col("b.PrFirst_Name_selection"),
    F.col("b.PrFather_Name_selection"),
    F.col("b.ClAT_IIS_selection")
).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_two}.parquet")
print("Checkpoint 6: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_two}.parquet")
df_gr = df_gr.alias("a").join(
    find_frequent_vat_doy(df_gr, "wemetrix_mp_customer_code").alias("b"),
    on="wemetrix_mp_customer_code",
    how="left"
).withColumn(
    "GR_VAT_ID",
    F.when(
        F.col("b.selection_flag")==1, F.col("b.ClVAT_IIS")
    ).otherwise(None)
).withColumn(
    "GR_VAT_ID_Info",
    F.when(
        F.col("b.selection_flag")==1, F.col("b.VAT_ID_Info")
    ).otherwise("Invalid_value")
).withColumn(
    "GR_DOY",
    F.when(
        F.col("b.selection_flag")==1, F.col("b.ClDOY_IIS")
    ).otherwise(None)
).withColumn(
    "GR_DOY_Info",
    F.when(
        F.col("b.selection_flag")==1, F.col("b.DOY_Info")
    ).otherwise("Invalid_value")
).drop(
    F.col("b.selection_flag"),
    F.col("b.ClVAT_IIS"),
    F.col("b.VAT_ID_Info"),
    F.col("b.ClDOY_IIS"),
    F.col("b.DOY_Info")
).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_four}.parquet")
print("Checkpoint 7: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_four}.parquet")
df_gr = df_gr.join(
    df_gr.select(
        "AT_Info", "ClAT_IIS", "GR_AT", "wemetrix_mp_customer_code"
    ).filter(
        F.col("ClAT_IIS") == F.col("GR_AT")
    ).withColumnRenamed(
        "AT_Info", "GR_AT_Info"
    ).groupBy(
        "wemetrix_mp_customer_code", "GR_AT_Info"
    ).agg(
        F.max(F.col("GR_AT")).alias("max")
    ).drop(
        F.col("max")
    ),
    on=["wemetrix_mp_customer_code"],
    how="left"
).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet")
print("Checkpoint 8: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet")
df_gr = df_gr.alias("a").join(
    find_frequent_email(df_gr, "wemetrix_mp_customer_code").alias("b"),
    on="wemetrix_mp_customer_code",
    how="left"
).withColumn(
    "GR_Email",
    F.when(
        F.col("a.ClB2B_Email_Uppercase").isNotNull(), F.col("b.ClB2B_Email_Uppercase")
        ).otherwise(
            F.when(
                F.col("a.ClB2B_Email_Uppercase").isNull(), F.col("b.ClEmail_Uppercase")
        ).otherwise(None)
    )
).withColumn(
    "GR_Email_Info",
    F.when(
        F.col("a.ClB2B_Email_Uppercase").isNotNull(), None #F.col("b.B2BEmail_Info") --> B2BEmail_Info wasn't in the dataframe, so for now we put NULL
        ).otherwise(
            F.when(
                F.col("a.ClB2B_Email_Uppercase").isNull(), F.col("b.Email_Info")
        ).otherwise(None)
    )
).drop(
    F.col("b.selection_flag"),
    F.col("b.ClB2B_Email_Uppercase"),
    F.col("b.ClEmail_Uppercase"),
    F.col("b.Email_Info")
).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_six}.parquet")
print("Checkpoint 9: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_six}.parquet")
df_date_groups = df_gr.groupBy(
    "wemetrix_mp_customer_code"
).agg(
    F.max("Last_Update_Date").alias("latest_last_update_date"),
    F.max("MoveOut_Date").alias("latest_move_out"),
    F.min("MoveIn_Date").alias("earliest_move_in")
)
df_gr = df_gr.alias("a").join(
    df_date_groups.alias("b"),
    on="wemetrix_mp_customer_code",
    how="left"
).withColumn(
    "GR_Last_Update_Date",
    F.col("b.latest_last_update_date")
).withColumn(
    "GR_MoveIn",
    F.col("b.earliest_move_in")
).withColumn(
    "GR_MoveOut",
    F.col("b.latest_move_out")
).drop(
    F.col("b.latest_last_update_date"),
    F.col("b.earliest_move_in"),
    F.col("b.latest_move_out")
)
print("Checkpoint 10: OK")

#---------------------------------------------------------------------------------------------------------------------------
#Addresses and Phones
df_gr_active = df_gr.filter(F.col("Active_Contract") == 1)

cols_active = [
    "TrB2B_Municipality_Name",
    "TrBilling_Municipality_Name",
    "TrB2B_Street",
    "TrBilling_Street",
    "TrB2B_Postal_Code",
    "TrBilling_Postal_Code",
    "TrB2B_Region_Name",
    "TrBilling_Region_Name",
    "B2B_Area_PPC",
    "Billing_Area_PPC",
    "B2B_TerraKey",
    "Billing_TerraKey",
    "TrB2B_WGS84_latitude",
    "TrBilling_WGS84_latitude",
    "TrB2B_WGS84_longitude",
    "TrBilling_WGS84_longitude",
    "TrB2B_House_Number",
    "TrBilling_House_Number"
]

cols_address = [
    "TrB2B_Municipality_Name",
    "B2B_Municipality_Name",
    "TrBilling_Municipality_Name",
    "Billing_Municipality_Name",
    "TrB2B_Street",
    "B2B_Street",
    "TrBilling_Street",
    "Billing_Street",
    "TrB2B_Postal_Code",
    "B2B_Postal_Code",
    "TrBilling_Postal_Code",
    "Billing_Postal_Code",
    "TrB2B_Region_Name",
    "TrBilling_Region_Name",
    "B2B_Area_PPC",
    "Billing_Area_PPC",
    "B2B_TerraKey",
    "Billing_TerraKey",
    "TrB2B_WGS84_latitude",
    "TrBilling_WGS84_latitude",
    "TrB2B_WGS84_longitude",
    "TrBilling_WGS84_longitude",
    "TrB2B_House_Number",
    "PrB2B_House_Number",
    "TrBilling_House_Number",
    "PrBilling_House_Number"
]

count = 0
for column in cols_active:
    if count == 0:
        most_frequent_value_per_group(
            df_gr_active,
            column,
            "active"
        ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_addresses}.parquet")
        count = 1
    else:
        first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{active_addresses}.parquet")
        first_results.join(
            most_frequent_value_per_group(df_gr_active,column,"active"),
            on=["wemetrix_mp_customer_code"],
            how="left"
        ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_addresses}.parquet")

count = 0
for column in cols_address:
    if count == 0:
        most_frequent_value_per_group(
            df_gr,
            column,
            "all"
        ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_addresses}.parquet")
        count = 1
    else:
        second_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{all_addresses}.parquet")
        second_results.join(
            most_frequent_value_per_group(df_gr,column,"all"),
            on=["wemetrix_mp_customer_code"],
            how="left"
        ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_addresses}.parquet")
print("Checkpoint 11: OK")

first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{active_addresses}.parquet")
second_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{all_addresses}.parquet")
joined_table = first_results.join(second_results,on=["wemetrix_mp_customer_code"], how="right")
joined_table = joined_table\
    .withColumn(
        "GR_Address_MunicipalityName",
        F.coalesce(
            F.col("active_TrB2B_Municipality_Name"),
            F.col("all_TrB2B_Municipality_Name"),
            F.col("all_B2B_Municipality_Name"),
            ("active_TrBilling_Municipality_Name"),
            F.col("all_TrBilling_Municipality_Name"),
            F.col("all_Billing_Municipality_Name")
        )
    ).withColumn(
        "GR_Address_StreetName",
        F.coalesce(
            F.col("active_TrB2B_Street"),
            F.col("all_TrB2B_Street"),
            F.col("all_B2B_Street"),
            ("active_TrBilling_Street"),
            F.col("all_TrBilling_Street"),
            F.col("all_Billing_Street")
        )
    ).withColumn(
        "GR_Address_PostalCode",
        F.coalesce(
            F.col("active_TrB2B_Postal_Code"),
            F.col("all_TrB2B_Postal_Code"),
            F.col("all_B2B_Postal_Code"),
            F.col("active_TrBilling_Postal_Code"),
            F.col("all_TrBilling_Postal_Code"),
            F.col("all_Billing_Postal_Code")
        )
    ).withColumn(
        "GR_Address_Region",
        F.coalesce(
            F.col("active_TrB2B_Region_Name"),
            F.col("all_TrB2B_Region_Name"),
            F.col("active_TrBilling_Region_Name"),
            F.col("all_TrBilling_Region_Name")
        )
    ).withColumn(
        "GR_Address_Area",
        F.coalesce(  
            F.col("active_B2B_Area_PPC"),
            F.col("all_B2B_Area_PPC"),
            F.col("active_Billing_Area_PPC"),
            F.col("all_Billing_Area_PPC")
        )
    ).withColumn(
        "GR_TerraKey",
        F.coalesce( 
            F.col("active_B2B_TerraKey"),
            F.col("all_B2B_TerraKey"),
            F.col("active_Billing_TerraKey"),
            F.col("all_Billing_TerraKey")
        )
    ).withColumn(
        "GR_Address_Latitude",
        F.coalesce(
            F.col("active_TrB2B_WGS84_latitude"),
            F.col("all_TrB2B_WGS84_latitude"),
            F.col("active_TrBilling_WGS84_latitude"),
            F.col("all_TrBilling_WGS84_latitude")
        )
    ).withColumn(
        "GR_Address_Longitude",
        F.coalesce(
            F.col("active_TrB2B_WGS84_longitude"),
            F.col("all_TrB2B_WGS84_longitude"),
            F.col("active_TrBilling_WGS84_longitude"),
            F.col("all_TrBilling_WGS84_longitude")
        )
    ).withColumn(
        "GR_Address_HouseNumber",
        F.coalesce(
            F.col("active_TrB2B_House_Number"),
            F.col("all_TrB2B_House_Number"),
            F.col("all_PrB2B_House_Number"),
            F.col("active_TrBilling_House_Number"),
            F.col("all_TrBilling_House_Number"),
            F.col("all_PrBilling_House_Number")
        )
    )
print("Checkpoint 12: OK")

columns_to_drop = [col_name for col_name in joined_table.columns if col_name.startswith("active") | col_name.startswith("all")]
joined_table = joined_table.drop(*columns_to_drop)
df_gr = df_gr.join(joined_table, on=["wemetrix_mp_customer_code"], how="left")
print("Checkpoint 13: OK")
#---------------------------------------------------------------------------------------------------------------------------

cols_phone = [
    "Fixphone_IIS",
    "Cellphone_IIS",
    "SAP_Phone_1_FIXED",
    "SAP_Phone_1_CELL",
    "SAP_Phone_2_FIXED",
    "SAP_Phone_2_CELL",
    "FAIDRA_Phone_1_FIXED",
    "FAIDRA_Phone_1_CELL",
    "FAIDRA_Phone_2_FIXED",
    "FAIDRA_Phone_2_CELL",
    "EVALUE_Phone_1_FIXED",
    "EVALUE_Phone_1_CELL",
    "EVALUE_Phone_2_FIXED",
    "EVALUE_Phone_2_CELL",
    "EVALUE_Phone_3_FIXED",
    "EVALUE_Phone_3_CELL",
    "EVALUE_Phone_4_FIXED",
    "EVALUE_Phone_4_CELL",
    "EVALUE_Phone_5_FIXED",
    "EVALUE_Phone_5_CELL",
    "EBILL_Phone_1_FIXED",
    "EBILL_Phone_1_CELL",
    "EBILL_Phone_2_FIXED",
    "EBILL_Phone_2_CELL"
]

count = 0
prefix = "active"
for column in cols_phone:
    if count == 0:
        if column.startswith("Fixphone") | column.startswith("Cellphone"):
            find_frequent_phone_advanced_v2(
                df_gr_active,
                column,
                prefix
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
        elif column.startswith("SAP_Phone_1"):
            find_frequent_sap_phone_1(
                df_gr_active,
                column,
                prefix
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
        else:
            most_frequent_value_per_group(
                df_gr_active,
                column,
                prefix
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
        count = 1
    else:
        first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
        if column.startswith("Fixphone") | column.startswith("Cellphone"):
            first_results.join(
                find_frequent_phone_advanced_v2(df_gr_active, column, prefix),
                on=["wemetrix_mp_customer_code"],
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
        elif column.startswith("SAP_Phone_1"):
            first_results.join(
                find_frequent_sap_phone_1(df_gr_active, column, prefix),
                on=["wemetrix_mp_customer_code"],
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
        else:
            first_results.join(
                most_frequent_value_per_group(df_gr_active, column, prefix),
                on=["wemetrix_mp_customer_code"],
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
print("Checkpoint 14: OK")

count = 0
prefix = "all"
for column in cols_phone:
    if count == 0:
        if column.startswith("Fixphone") | column.startswith("Cellphone"):
            find_frequent_phone_advanced_v2(
                df_gr,
                column,
                prefix
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
        elif column.startswith("SAP_Phone_1"):
            find_frequent_sap_phone_1(
                df_gr,
                column,
                prefix
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
        else:
            most_frequent_value_per_group(
                df_gr,
                column,
                prefix
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
        count = 1
    else:
        second_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
        if column.startswith("Fixphone") | column.startswith("Cellphone"):
            second_results.join(
                find_frequent_phone_advanced_v2(df_gr, column, prefix),
                on=["wemetrix_mp_customer_code"],
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
        elif column.startswith("SAP_Phone_1"):
            second_results.join(
                find_frequent_sap_phone_1(df_gr, column, prefix),
                on=["wemetrix_mp_customer_code"],
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
        else:
            second_results.join(
                most_frequent_value_per_group(df_gr, column, prefix),
                on=["wemetrix_mp_customer_code"],
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
print("Checkpoint 15: OK")

first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
second_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
joined_table = first_results.join(second_results, on=["wemetrix_mp_customer_code"], how="right")
df_gr = df_gr.join(
    joined_table,
    on=["wemetrix_mp_customer_code"],
    how="left"
).withColumn(
    "GR_SAP_Phone_1_FIXED",
    F.coalesce(
        F.col("active_SAP_Phone_1_FIXED_frequent"),
        F.col("all_SAP_Phone_1_FIXED_frequent")
    )
).withColumn(
    "GR_SAP_Phone_1_CELL",
    F.coalesce(
        F.col("active_SAP_Phone_1_CELL_frequent"),
        F.col("all_SAP_Phone_1_CELL_frequent")
    )
).withColumn(
    "GR_SAP_Phone_2_FIXED",
    F.coalesce(
        F.col("active_SAP_Phone_2_FIXED"),
        F.col("all_SAP_Phone_2_FIXED"),
        F.when( 
            F.col("all_SAP_Phone_1_FIXED_second_frequent") == F.col("GR_SAP_Phone_1_FIXED"),
            None
        ).otherwise( F.col("all_SAP_Phone_1_FIXED_second_frequent") )
    )
).withColumn(
    "GR_SAP_Phone_2_CELL",
    F.coalesce(
        F.col("active_SAP_Phone_2_CELL"),
        F.col("all_SAP_Phone_2_CELL"),
        F.when( 
            F.col("all_SAP_Phone_1_CELL_second_frequent") == F.col("GR_SAP_Phone_1_CELL"),
            None
        ).otherwise( F.col("all_SAP_Phone_1_CELL_second_frequent") )
    )
).withColumn(
    "GR_FAIDRA_Phone_1_FIXED",
    F.coalesce(
        F.col("active_FAIDRA_Phone_1_FIXED"),
        F.col("all_FAIDRA_Phone_1_FIXED")
    )
).withColumn(
    "GR_FAIDRA_Phone_1_CELL",
    F.coalesce(
        F.col("active_FAIDRA_Phone_1_CELL"),
        F.col("all_FAIDRA_Phone_1_CELL")
    )
).withColumn(
    "GR_FAIDRA_Phone_2_FIXED",
    F.coalesce(
        F.col("active_FAIDRA_Phone_2_FIXED"),
        F.col("all_FAIDRA_Phone_2_FIXED")
    )
).withColumn(
    "GR_FAIDRA_Phone_2_CELL",
    F.coalesce(
        F.col("active_FAIDRA_Phone_2_CELL"),
        F.col("all_FAIDRA_Phone_2_CELL")
    )
).withColumn(
    "GR_EVALUE_Phone_1_FIXED",
    F.coalesce(
        F.col("active_EVALUE_Phone_1_FIXED"),
        F.col("all_EVALUE_Phone_1_FIXED")
    )
).withColumn(
    "GR_EVALUE_Phone_1_CELL",
    F.coalesce(
        F.col("active_EVALUE_Phone_1_CELL"),
        F.col("all_EVALUE_Phone_1_CELL")
    )
).withColumn(
    "GR_EVALUE_Phone_2_FIXED",
    F.coalesce(
        F.col("active_EVALUE_Phone_2_FIXED"),
        F.col("all_EVALUE_Phone_2_FIXED")
    )
).withColumn(
    "GR_EVALUE_Phone_2_CELL",
    F.coalesce(
        F.col("active_EVALUE_Phone_2_CELL"),
        F.col("all_EVALUE_Phone_2_CELL")
    )
).withColumn(
    "GR_EVALUE_Phone_3_FIXED",
    F.coalesce(
        F.col("active_EVALUE_Phone_3_FIXED"),
        F.col("all_EVALUE_Phone_3_FIXED")
    )
).withColumn(
    "GR_EVALUE_Phone_3_CELL",
    F.coalesce(
        F.col("active_EVALUE_Phone_3_CELL"),
        F.col("all_EVALUE_Phone_3_CELL")
    )
).withColumn(
    "GR_EVALUE_Phone_4_FIXED",
    F.coalesce(
        F.col("active_EVALUE_Phone_4_FIXED"),
        F.col("all_EVALUE_Phone_4_FIXED")
    )
).withColumn(
    "GR_EVALUE_Phone_4_CELL",
    F.coalesce(
        F.col("active_EVALUE_Phone_4_CELL"),
        F.col("all_EVALUE_Phone_4_CELL")
    )
).withColumn(
    "GR_EVALUE_Phone_5_FIXED",
    F.coalesce(
        F.col("active_EVALUE_Phone_5_FIXED"),
        F.col("all_EVALUE_Phone_5_FIXED")
    )
).withColumn(
    "GR_EVALUE_Phone_5_CELL",
    F.coalesce(
        F.col("active_EVALUE_Phone_5_CELL"),
        F.col("all_EVALUE_Phone_5_CELL")
    )
).withColumn(
    "GR_EBILL_Phone_1_FIXED",
    F.coalesce(
        F.col("active_EBILL_Phone_1_FIXED"),
        F.col("all_EBILL_Phone_1_FIXED")
    )
).withColumn(
    "GR_EBILL_Phone_1_CELL",
    F.coalesce(
        F.col("active_EBILL_Phone_1_CELL"),
        F.col("all_EBILL_Phone_1_CELL")
    )
).withColumn(
    "GR_EBILL_Phone_2_FIXED",
    F.coalesce(
        F.col("active_EBILL_Phone_2_FIXED"),
        F.col("all_EBILL_Phone_2_FIXED")
    )
).withColumn(
    "GR_EBILL_Phone_2_CELL",
    F.coalesce(
        F.col("active_EBILL_Phone_2_CELL"),
        F.col("all_EBILL_Phone_2_CELL")
    )
).withColumn(
    "GR_FixedPhone1",
    F.coalesce(
        F.col("GR_B2B_Fixphone_IIS"),
        F.col("active_Fixphone_IIS(1-10)_one"),
        F.col("all_Fixphone_IIS(1-10)_one")
    )
).withColumn(
    "GR_FixedPhone2",
    F.coalesce(
        F.col("active_Fixphone_IIS(12-21)"),
        F.col("all_Fixphone_IIS(12-21)"),
        F.when( F.col("all_Fixphone_IIS(1-10)_two") == F.col("GR_FixedPhone1"), None).otherwise( F.col("all_Fixphone_IIS(1-10)_two") )
    )
).withColumn(
    "GR_CellPhone1",
    F.coalesce(
        F.col("GR_B2B_Cellphone_IIS"),
        F.col("active_Cellphone_IIS(1-10)_one"),
        F.col("all_Cellphone_IIS(1-10)_one")
    )
).withColumn(
    "GR_CellPhone2",
    F.coalesce(
        F.col("active_Cellphone_IIS(12-21)"),
        F.col("all_Cellphone_IIS(12-21)"),
        F.when( F.col("all_Cellphone_IIS(1-10)_two") == F.col("GR_CellPhone1"), None).otherwise( F.col("all_Cellphone_IIS(1-10)_two") )
    )
)
print("Checkpoint 16: OK")

columns_to_drop = [col_name for col_name in df_gr.columns if col_name.startswith("active_") | col_name.startswith("all_") | col_name.startswith("MP_") ]
df_gr = df_gr.drop(*columns_to_drop)

# COMMAND ----------

# MAGIC %md
# MAGIC ## -- Write final table with GR fields --

# COMMAND ----------

if output_table_write_mode == "ON":
    print(f"Writing output table (alias: {output_table}) with GR fields...")
    df_gr.select(
        [x for x in cols_all] +
        [x for x in df_gr.columns if "GR_" in x]
    ).write.mode("overwrite").saveAsTable(output_table)
    print("Writing COMPLETED...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## -- Data Validation checks on created GR fields --

# COMMAND ----------

# MAGIC %md
# MAGIC * GR_ClCompany_Name - ClCompany_name
# MAGIC * GR_B2B_Company_Name - B2B_Company_Name
# MAGIC * GR_ClLast_Name - ClLast_Name
# MAGIC * GR_DOY
# MAGIC * GR_EMAIL - ClEmail_Uppercase: GR_Group = [200000082, 300000174], the values selected in the predicta table do not exist as possible email values in the WEMETRIX table results, so we have differences.
# MAGIC * For addresses GR columns have a look on GROUPS = 400241990, 300000174. For GROUP = 300000174 it has two main active records thus the final selection was made by using the maximum weight and Contract_Account_ID.</br>
# MAGIC Check query: </br>
# MAGIC ```
# MAGIC df_gr_checks.select(
# MAGIC     ["SOURCE", 
# MAGIC      "Contract_Account_ID",
# MAGIC      "Active_Contract",
# MAGIC      "TrB2B_Municipality_Name",
# MAGIC      "TrBilling_Municipality_Name",
# MAGIC      "B2B_TerraKey",
# MAGIC      "Billing_TerraKey",
# MAGIC      "wemetrix_main_record"
# MAGIC ]
# MAGIC ).filter( (F.col("wemetrix_gr_group") == 300000174) ).show(200, truncate = False)
# MAGIC ```
# MAGIC </br>
# MAGIC
# MAGIC * GR_MoveIn: Between the two datasets, PREDICTA and WEMETRIX, the dates are different because the selected value in the PREDICTA table is missing from the WEMETRIX table.
# MAGIC
# MAGIC * GR_CellPhone1: is NULL for GROUP = 100001684, because columns Cellphone_IIS & B2B_Cellphone_IIS have only NULL values accross all the contracts of the group.
# MAGIC
# MAGIC * GR_CellPhone2: "*Most Frequent from active contracts position 12-21 of Fixphone_IIS*" This is written in the given documentation for the GOLDER record fields. Is this a spelling mistake? because we used the Cellphone_IIS column instead.
# MAGIC
# MAGIC * For FAIDRA, EVALUE, EBILL columns, the source=SAP was used becaused in the given dataset we had records only from the SAP source. This can be fixed in the future in case we receive records from more SOURCEs by updating the respective python module with if/else statements.
# MAGIC
# MAGIC * When the logic *second most frequent* is used for some PHONE columns, do we extract the second most frequent from all or active only contracts? In our implementation we extracted the second most frequent from ALL contracts.

# COMMAND ----------

# MAGIC %md
# MAGIC Checks were made on 10 Contract Account IDs using the following two tables:
# MAGIC * wemetrix.foursource_gr_v8 (The 8th version of the GR fields version)
# MAGIC * wemetrix.predicta_master_2023_05_31_j (Predicta's table)

# COMMAND ----------

# MAGIC %md
# MAGIC Χρησιμοποιείστε το παρακάτω script για ελέχχους στους δύο πίνακες [foursource_gr, predicta]

# COMMAND ----------

# output_table = dbutils.widgets.get("output_table")
# df_gr_checks = spark.sql(f"SELECT * FROM {output_table}")
# df_gr_predicta = spark.sql(f"SELECT * FROM wemetrix.predicta_master_2023_05_31_j")

# df_gr_checks.select(
#     ["SOURCE", "Contract_Account_ID", "wemetrix_gr_group", "PrCustomer_Type_IIS"]+ [x for x in df_gr_checks.columns if "GR_" in x]
# ).filter(
#     F.col("Contract_Account_ID").isin([300013462915, 300004728871, 300004790870, 300004668995, 300004734540, 300001095286, 300012154637, 300001520751, 300000016686, 300005367850])
# ).orderBy(
#     F.col("Contract_Account_ID").desc()
# ).display()

# df_gr_predicta.select(
#     ["SOURCE", "Contract_Account_ID", "ClCompany_Name", "B2B_Company_Name", "ClB2B_Email_Uppercase", "B2B_Fixphone_IIS", "B2B_Cellphone_IIS", "ClFirst_Name", "ClLast_Name", "ClFather_Name"]+ [x for x in df_gr_predicta.columns if "GR_" in x]
# ).filter(
#     F.col("Contract_Account_ID").isin([300013462915, 300004728871, 300004790870, 300004668995, 300004734540, 300001095286, 300012154637, 300001520751, 300000016686, 300005367850])
# ).orderBy(
#     F.col("Contract_Account_ID").desc()
# ).display()