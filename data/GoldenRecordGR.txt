# Databricks notebook source
# DBTITLE 1,Import pyspark/python modules and functions
#import pre-build python modules
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
dbutils.widgets.text("input_table", "wemetrix.foursourcerun05")
input_table= dbutils.widgets.get("input_table")

dbutils.widgets.text("output_table",  "wemetrix.foursourcedeltarun05GR")
output_table = dbutils.widgets.get("output_table")

dbutils.widgets.text("main_records_table",  "main_records_results_delta")
main_records_table = dbutils.widgets.get("main_records_table")

dbutils.widgets.text("output_table_write", "ON")
output_table_write_mode = dbutils.widgets.get("output_table_write")

dbutils.widgets.text("main_records_execution", "ON")
main_records_execution_mode = dbutils.widgets.get("main_records_execution")

print("Input table: ", input_table)
print("Output table: ", output_table)
print("Main records table: ", main_records_table)
print("Output table write mode: ", output_table_write_mode)
print("Main records execution mode: ", main_records_execution_mode)

# COMMAND ----------

# DBTITLE 1,Read input table(s)
df_golden_records = spark.sql(f"SELECT * FROM {input_table}")
# Get only groups with changed records
# df_golden_records = spark.sql(f"select * from {input_table} A where (A.isdelta=1 or A.wemetrix_mp_customer_code in (SELECT Contract_Account_ID from {input_table} B where B.wemetrix_match_type='MP' and B.isdelta=1))")

# COMMAND ----------

# DBTITLE 1,Select input columns to generate GR fields
cols_all = [
    "Contract_Account_ID",
    "SOURCE",
    "Active_Contract",
    "PrCustomer_Type_IIS",
    "Last_Name",
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
    "B2B_Email_Info",
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
    #-----------------------------------------------------
    "TrB2B_Municipality_Name",
    "TrBilling_Municipality_Name",
    "B2B_Municipality_Name",
    "Billing_Municipality_Name",
    #-----------------------------------------------------
    "TrB2B_Street",
    "TrBilling_Street",
    "B2B_Street",
    "Billing_Street",
    #-----------------------------------------------------
    "TrB2B_Postal_Code",
    "TrBilling_Postal_Code",
    "B2B_Postal_Code",
    "Billing_Postal_Code",
    #-----------------------------------------------------
    "TrB2B_Region_Name",
    "TrBilling_Region_Name",
    "B2B_Address_Region",
    "Billing_Address_Region",
    #-----------------------------------------------------
    "B2B_Area_PPC",
    "Billing_Area_PPC",
    #-----------------------------------------------------
    "B2B_TerraKey",
    "Billing_TerraKey",
    #-----------------------------------------------------
    "TrB2B_WGS84_latitude",
    "TrBilling_WGS84_latitude",
    #-----------------------------------------------------
    "TrB2B_WGS84_longitude",
    "TrBilling_WGS84_longitude",
    #-----------------------------------------------------
    "PrB2B_House_Number",
    "PrBilling_House_Number",
    "B2B_House_Number",
    "Billing_House_Number",
    #-----------------------------------------------------
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
    "isdelta"
]
cols_all = cols_all + [x for x in df_golden_records.columns if "wemetrix" in x.lower()]
df_golden_records = df_golden_records.select(*(cols_all))

# COMMAND ----------

# group_cols = "GR_Customer_Code"
group_cols = "wemetrix_mp_customer_code"
df_golden_records = df_golden_records.withColumn(
    f"{group_cols}_v2",
    F.when(F.col(group_cols).isNull(), F.col("Contract_Account_ID")).otherwise(F.col(group_cols))
).drop(
    F.col(group_cols)
).withColumnRenamed(
    f"{group_cols}_v2",
    group_cols
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## -- Get Main Records per Group --

# COMMAND ----------

#5m
PARENT_LOCATION = "dbfs:/FileStore/wemetrix/"

if main_records_execution_mode == "ON":
    mainRecord_identification_cols = [
        "SOURCE",
        "Contract_Account_ID",
        "Active_Contract",
        "wemetrix_match_type",
        "wemetrix_mp_customer_code"
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
        main_records_table,
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
else:
    main_records_dev = spark.read.parquet(f"{os.path.join(PARENT_LOCATION, main_records_table)}.parquet")

df_gr = df_golden_records.alias("a").join(
    main_records_dev.select(["Contract_Account_ID", "SOURCE", "wemetrix_main_record"]).alias("b"),
    on = ["Contract_Account_ID", "SOURCE"],
    how="left"
)
df_gr_main_records_name = "df_gr_main_records_prod"
df_gr.write.option("compression", "snappy").mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{df_gr_main_records_name}.parquet")

# COMMAND ----------

# MAGIC %md
# MAGIC Non-Active Main records: 1,094,869 </br>
# MAGIC Query: ```df_gr.filter( (F.col("wemetrix_main_record")==1) & (F.col("Active_Contract")==0) ).count()``` <br>

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
# MAGIC In the **most frequent logic** there were many groups for which the selection based on the value with the highest count was not sufficient.
# MAGIC
# MAGIC For example in the case of *GR_ClFirst_Name* there were groups with at least two frequent names. To make a final selection for those groups that had equally frequent values we added two more filters. The first filter was the **maximum matching ratio** (aka matching weight). Thus, the value with the highest weight was selected. And the second filter was the **maximum Contract Account ID**. Thus, if two values had the same frequency (occurence), same matching weight, the one with the *maximum* (latest) *Contract Account ID* will be selected.
# MAGIC
# MAGIC For most of the fields the frequency value was not sufficient to make a unique selection per group.
# MAGIC
# MAGIC > **Hotfixes** Release 09 (October 2023)
# MAGIC 1. Αλλαγή του πεδίου που χρησιμοποιείται για τον υπολογισμό του Golden record "GR_Company_Name" από το πεδίο ClLast_Name στο Last_Name. Επίσης διορθώσαμε και ένα φίλτρο που επηρέαζε τον αριθμό των δεδομένων για τον υπολογισμό του GR_Company_Name πεδίου. Συγκεκριμένα το φίλτρο διέγραφε, από τον υπολογισμό του GR πεδίου, τους λογαριασμούς με nonNull B2B_Company_Names.
# MAGIC 2. Για το golden πεδίο GR_Email πλέον προσθέσαμε και τους λογαριασμούς που έρχονται από το source σύστημα EBILL.
# MAGIC 3. Για τον υπολογισμό των golden record πεδίων GR_Father, Gr_First, GR_Last Names θα λαμβάνονται πλέον υπόψιν και λογαριασμοί με PrCustomer_Type κενό (null) ή "person".
# MAGIC 4. Υλοποίηση των Golden records των Διευθύνσεων βάσει του κοινού TerraKey πεδίου. Θα γίνεται επιλογή του B2B_TerraKey ή Billing_TerraKey βάσει κανόνων του MoveIn Date και Active Contracts και όλες οι υπόλοιπες στήλες Διευθύνσεων (Street_Name, Postal_Code, Municipality_Name, etc) θα συμπληρώνονται σύμφωνα με το επιλεγμένο TerraKey.
# MAGIC 5. Διόρθωση των πεδίων τηλεφώνων (FIXED, CELL) σύμφωνα με τα αντίστοιχα source συστήματα (EBILL, FAIDRA και EVALUE).
# MAGIC
# MAGIC > **Hotfixes** Release 10 (November 2023)
# MAGIC 1. Αλλαγή των πεδίων TrB2B_House_Number, TrBilling_House_Number με τα πεδία PrB2B_House_Number και PrBilling_House_Number αντίστοιχα.
# MAGIC 2. Προσθήκη των πεδίων B2B_House_Number και Billing_House_Number για τον υπολογισμό του πεδίου GR_Address_HouseNumber.
# MAGIC 3. Προσθήκη των πεδίων B2B_Address_Region και Billing_Address_Region για τον υπολογισμό του πεδίου GR_Address_Region.
# MAGIC 4. Προσθήκη 18 πεδίων που μας επισημάνατε στον τελικό πίνακα.<br>
# MAGIC [qsMatchDataID,qsMatchType,qsMatchWeight,qsMatchPassNumber,qsMatchPattern,qsMatchLRFlag,qsMatchExactFlag,EnPrFirst_Name_IIS,EnPrLast_Name_IIS,EnStreet_IIS,
# MAGIC EnBillingStreet_IIS,SourceSap,FixPhoneIISBlock,CellPhoneIISBlock,PrCustomer_Type_IIS_changed,Determination_ID,ClEbill_Email,Match_type_PPC].
# MAGIC 5. O τελικός πίνακας με όλα τα πεδία ονομάζεται: wemetrix.foursourceallrun10. Προέρχεται από την επεξεργασία των delta διατηρώντας τα αρχικά (predicta) αποτελέσματα. Θα βρείτε επίσης τους ενδιάμεσους πίνακες για κάθε ημερομηνία.
# MAGIC

# COMMAND ----------

#Initialize stored/checkpoint table versions
checkpoint_tables_version = "prod_deployment07112023"
checkpoint_phones_version = "prod_deployment07112023"
active_phones:str = f"tmp_active_phones_{checkpoint_phones_version}"
all_phones:str = f"tmp_all_phones_{checkpoint_phones_version}"
other_phones:str = f"tmp_phones_{checkpoint_phones_version}"
terrakey_addresses:str = "terrakey_addresses"
nonterrakey_addresses:str = "nonterrakey_addresses"
golden_gr_one:str = f"tmp_golden_gr_one_{checkpoint_tables_version}"
golden_gr_two:str = f"tmp_golden_gr_second_{checkpoint_tables_version}"
golden_gr_three:str = f"tmp_golden_gr_three_{checkpoint_tables_version}"
golden_gr_four:str = f"tmp_golden_gr_four_{checkpoint_tables_version}"
golden_gr_five:str = f"tmp_golden_gr_five_{checkpoint_tables_version}"
golden_gr_six:str = f"tmp_golden_gr_six_{checkpoint_tables_version}"
golden_gr_seven:str = f"tmp_golden_gr_seven_{checkpoint_tables_version}"
golden_gr_eight:str = f"tmp_golden_gr_eight_{checkpoint_tables_version}"

#Initialize Passport/AT columns
passport_col, passport_info_col = "ClPassport_IIS_Wemetrix", "Passport_Info_Wemetrix"
at_col, at_info_col = "ClAT_IIS_Wemetrix", "AT_Info_Wemetrix"

#Initialize grouping column that denotes the golden group of customer accounts
group_cols = "wemetrix_mp_customer_code"
#---------------------------------------------------------------------------------------------------------------------------

#Load the GR table with the calculated MAIN RECORD column
df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{df_gr_main_records_name}.parquet")

window_spec = Window.partitionBy(group_cols).orderBy(F.col("wemetrix_main_record").desc())
df_gr = df_gr \
    .withColumn("GR_Customer_Code", F.first(F.col("Contract_Account_ID")).over(window_spec)) \
    .withColumn("GR_SOURCE", F.first(F.col("SOURCE")).over(window_spec)) \
    .withColumn("GR_MatchSetID", F.first(F.col("wemetrix_matching_ratio")).over(window_spec))
print("Checkpoint 1.1: OK")

df_gr = df_gr.join(
    find_frequent_customertype_v2(df_gr, group_cols, "PrCustomer_Type_IIS"),
    on=[group_cols],
    how="left"
).withColumnRenamed(
    "selected_PrCustomer_Type_IIS", "GR_Customer_Type"
)
df_gr.write.option("compression", "snappy").mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet")
print("Checkpoint 1.2: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet")
df_gr = df_gr.withColumn(
    "ClCompany_Name",
    F.trim(F.col("ClCompany_Name"))
).withColumn(
    "B2B_Company_Name",
    F.trim(F.col("B2B_Company_Name"))
).withColumn(
    "PrLast_Name",
    F.trim(F.col("PrLast_Name"))
)

df_gr = df_gr.join(
    get_GR_field_v2(df_gr, "ClCompany_Name", group_cols, "wemetrix_matching_ratio"),
    on=[group_cols],
    how="left"
).withColumnRenamed(
    "selected_ClCompany_Name", "GR_ClCompany_Name"
).join(
    get_GR_field_v2(df_gr, "B2B_Company_Name", group_cols, "wemetrix_matching_ratio"),
    on=[group_cols],
    how="left"
).withColumnRenamed(
    "selected_B2B_Company_Name", "GR_B2B_Company_Name"
).join(
    get_GR_field_v2(df_gr, "B2B_Fixphone_IIS", group_cols, "wemetrix_matching_ratio"),
    on=[group_cols],
    how="left"
).withColumnRenamed(
    "selected_B2B_Fixphone_IIS", "GR_B2B_Fixphone_IIS"
).join(
    get_GR_field_v2(df_gr, "B2B_Cellphone_IIS", group_cols, "wemetrix_matching_ratio"),
    on=[group_cols],
    how="left"
).withColumn(
    "selected_B2B_Cellphone_IIS", F.when(F.col("wemetrix_main_record")==1, F.col("B2B_Cellphone_IIS")).otherwise(F.col("selected_B2B_Cellphone_IIS"))
).withColumnRenamed(
    "selected_B2B_Cellphone_IIS", "GR_B2B_Cellphone_IIS"
)
df_gr.write.option("compression", "snappy").mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_two}.parquet")
print("Checkpoint 2: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_two}.parquet")
target_column = "Last_Name"
df_gr = df_gr.join(
    get_frequent_company_name(df_gr, group_cols, target_column, "wemetrix_matching_ratio", "B2B_Company_Name"),
    on=[group_cols],
    how="left"
).withColumn(
    f"selected_{target_column}",
    F.when(
        F.col("GR_Customer_Type") == "person", None
    ).otherwise(
        F.when(
            F.col("selected_B2B_Company_Name").isNotNull(), F.col("selected_B2B_Company_Name")
        ).otherwise(
            F.col(f"selected_{target_column}")
        )
    )
).withColumnRenamed(
    f"selected_{target_column}", "GR_Company_Name"
).drop(F.col("selected_B2B_Company_Name"))
df_gr.write.option("compression", "snappy").mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_three}.parquet")
print("Checkpoint 3: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_three}.parquet")
df_gr = df_gr.join(
    get_GR_passport(df_gr, passport_col, group_cols, passport_info_col, "wemetrix_matching_ratio"),
    on=[group_cols],
    how="left"
).withColumn(
    "selected_ClPassport_IIS", F.when(F.col("wemetrix_main_record")==1, F.col("ClPassport_IIS")).otherwise(F.col("selected_ClPassport_IIS"))
).withColumnRenamed(
    "selected_ClPassport_IIS", "GR_Passport"
).withColumn(
    "selected_Passport_Info", F.when(F.col("wemetrix_main_record")==1, F.col("Passport_Info")).otherwise(F.col("selected_Passport_Info"))
).withColumnRenamed(
    "selected_Passport_Info", "GR_Passport_Info"
)
df_gr.write.option("compression", "snappy").mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_four}.parquet")
print("Checkpoint 4: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_four}.parquet")
golden_grcols = [
    ("ClFirst_Name", "GR_ClFirst_Name"),
    ("ClLast_Name", "GR_ClLast_Name"),
    ("ClFather_Name", "GR_ClFather_Name"),
    ("PrFirst_Name", "GR_First_Name"),
    ("PrFather_Name", "GR_Father_Name"),
    (at_col, "GR_AT", at_info_col)
]
count = 0
i = 2
for tuple_object in golden_grcols:
    if count == 0:
        find_frequent_ClNames(
            df_gr, group_cols, tuple_object[0]
        ).select(
            [ group_cols, f"selected_{tuple_object[0]}" ]
        ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet")
        count = 1
        print("Checkpoint 5.1: OK")
    else:
        if tuple_object[1].startswith("GR_Cl"):
            first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet")
            first_results.join(
                find_frequent_ClNames(
                    df_gr, group_cols, tuple_object[0]
                ).select(
                    [group_cols, f"selected_{tuple_object[0]}"]
                ),
                on=group_cols,
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet")
            print(f"Checkpoint 5.{i}: OK")
        elif tuple_object[1].startswith("GR_F"):
            first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet")
            first_results.join(
                find_frequent_PrNames(df_gr, group_cols, tuple_object[0], apply_prefix_udf),
                on=group_cols,
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet")
            print(f"Checkpoint 5.{i}: OK")
        elif tuple_object[1] == "GR_AT":
            first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet")
            first_results.join(
                find_frequent_at_v2(df_gr, group_cols, tuple_object[0], tuple_object[2]),
                on=group_cols,
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet")
            print(f"Checkpoint 5.{i}: OK")
        i+=1

first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet")
df_gr = df_gr.alias("a").join(
    first_results.alias("b"),
    on=[group_cols],
    how="left"
).withColumn(
    "GR_Father_Name",
    F.when(
        F.col("a.GR_Customer_Type").isin(["organisation", "municipalities", "organisation_various"]), None
    ).otherwise(
        F.when(
            F.col("b.PrFather_Name_selection")=="Missing value", F.col("b.selected_ClFather_Name")
        ).otherwise(F.col("b.PrFather_Name_selection"))
    )
).drop(
    F.col("b.PrFather_Name_selection"), F.col("b.selected_ClFather_Name")
).withColumn(
    "GR_First_Name",
    F.when(
        F.col("a.GR_Customer_Type").isin(["organisation", "municipalities", "organisation_various"]), None
    ).otherwise(
        F.when(
            F.col("b.PrFirst_Name_selection")=="Missing value", F.col("b.selected_ClFirst_Name")
        ).otherwise(F.col("b.PrFirst_Name_selection"))
    )
).drop(
    F.col("b.PrFirst_Name_selection"), F.col("b.selected_ClFirst_Name")
).withColumn(
    "GR_AT",
    F.col("b.selected_ClAT_IIS")
).withColumn(
    "GR_AT_Info",
    F.col("b.selected_AT_Info")
).drop(
    F.col("b.selected_ClAT_IIS"),
    F.col("b.selected_AT_Info")
).join(
    get_GR_field_v2(df_gr, "PrLast_Name", group_cols, "wemetrix_matching_ratio").alias("c"),
    on=[group_cols],
    how="left"
).withColumn(
    "selected_PrLast_Name",
    F.when(
        F.col("a.GR_Customer_Type").isin(["organisation", "municipalities", "organisation_various"]), None
    ).otherwise(
        F.when(
            F.col("c.selected_PrLast_Name").isNull(), F.col("b.selected_ClLast_Name")
        ).otherwise(
            F.col("c.selected_PrLast_Name")
        )
    )
).withColumnRenamed(
    "selected_PrLast_Name", "GR_Last_Name"
).drop(
    F.col("b.selected_ClLast_Name")
)
df_gr.write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_six}.parquet")
print("Checkpoint 6: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_six}.parquet")
df_gr = df_gr.alias("a").join(
    find_frequent_vat_doy_v2(df_gr, group_cols, "ClVAT_IIS").alias("b"),
    on=[group_cols],
    how="left"
).withColumn(
    "selected_ClVAT_IIS", F.when( (F.col("wemetrix_main_record")==1) & (F.col("ClVAT_IIS").isNotNull()), F.col("ClVAT_IIS")).otherwise(F.col("selected_ClVAT_IIS"))
).withColumnRenamed(
    "selected_ClVAT_IIS", "GR_VAT_ID"
).withColumn(
    "selected_VAT_ID_Info", F.when( (F.col("wemetrix_main_record")==1) & (F.col("ClVAT_IIS").isNotNull()), F.col("VAT_ID_Info")).otherwise(F.col("selected_VAT_ID_Info"))
).withColumnRenamed(
    "selected_VAT_ID_Info", "GR_VAT_ID_Info"
).withColumn(
    "selected_ClDOY_IIS", F.when( (F.col("wemetrix_main_record")==1) & (F.col("ClVAT_IIS").isNotNull()), F.col("ClDOY_IIS")).otherwise(F.col("selected_ClDOY_IIS"))
).withColumnRenamed(
    "selected_ClDOY_IIS", "GR_DOY"
).withColumn(
    "selected_DOY_Info", F.when( (F.col("wemetrix_main_record")==1) & (F.col("ClVAT_IIS").isNotNull()), F.col("DOY_Info")).otherwise(F.col("selected_DOY_Info"))
).withColumnRenamed(
    "selected_DOY_Info", "GR_DOY_Info"
)
df_gr.write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_seven}.parquet")
print("Checkpoint 7: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_seven}.parquet")
df_gr = df_gr.join(
    find_frequent_email_v2(df_gr, group_cols, "ClEmail_Uppercase", "wemetrix_matching_ratio", "ClB2B_Email_Uppercase", "Email_info", "B2B_Email_Info", "SAP"),
    on=[group_cols],
    how="left"
).join(
    find_frequent_email_v2(df_gr, group_cols, "ClEmail_Uppercase", "wemetrix_matching_ratio", "ClB2B_Email_Uppercase", "Email_info", "B2B_Email_Info", "EBILL"),
    on=[group_cols],
    how="left"
).withColumn(
    "selected_ClEmail_Uppercase",
    F.coalesce(
        F.col("selected_ClB2B_Email_Uppercase_SAP"),
        F.col("selected_ClB2B_Email_Uppercase_EBILL"),
        F.col("selected_ClEmail_Uppercase_SAP"),
        F.col("selected_ClEmail_Uppercase_EBILL")
    )
).withColumnRenamed(
    "selected_ClEmail_Uppercase", "GR_Email"
).withColumn(
    "selected_Email_Info",
    F.when(
        F.col("selected_ClB2B_Email_Uppercase_SAP").isNotNull(), F.col("selected_B2B_Email_Info_SAP")
    ).otherwise(
        F.when(
            F.col("selected_ClB2B_Email_Uppercase_EBILL").isNotNull(), F.col("selected_B2B_Email_Info_EBILL")
        ).otherwise(
            F.coalesce(
                F.col("selected_Email_Info_SAP"),
                F.col("selected_Email_Info_EBILL")
            )
        )
    )
).withColumnRenamed(
    "selected_Email_Info", "GR_Email_Info"
).drop(
    F.col("selected_ClB2B_Email_Uppercase_SAP"),
    F.col("selected_ClB2B_Email_Uppercase_EBILL"),
    F.col("selected_B2B_Email_Info_SAP"),
    F.col("selected_B2B_Email_Info_EBILL")
)
df_gr.write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_eight}.parquet")
print("Checkpoint 8: OK")
#---------------------------------------------------------------------------------------------------------------------------

df_gr = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{golden_gr_eight}.parquet")
df_date_groups = df_gr.groupBy(
    group_cols
).agg(
    F.max("Last_Update_Date").alias("latest_last_update_date"),
    F.max("MoveOut_Date").alias("latest_move_out"),
    F.min("MoveIn_Date").alias("earliest_move_in")
)
df_gr = df_gr.alias("a").join(
    df_date_groups.alias("b"),
    on=group_cols,
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
print("Checkpoint 9: OK")
#---------------------------------------------------------------------------------------------------------------------------

#Addresses and Phones
group_cols = "wemetrix_mp_customer_code"
movein_date = "MoveIn_Date"
weight_match = "wemetrix_matching_ratio"
terrakey_b2b_column = "B2B_TerraKey"
terrakey_billing_column = "Billing_TerraKey"
non_terrakey_columns = [
    ("B2B_Municipality_Name", "Billing_Municipality_Name"),
    ("B2B_Street", "Billing_Street"),
    ("B2B_Postal_Code", "Billing_Postal_Code"),
    ("B2B_House_Number", "Billing_House_Number"),
    ("B2B_Address_Region", "Billing_Address_Region")
]
#Compute terrakey addresses
find_frequent_address_trkey(df_gr, group_cols, terrakey_b2b_column, terrakey_billing_column, movein_date, weight_match).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{terrakey_addresses}.parquet")
#Compute non-terrakey columns
iteration:int = 0
for tupl in non_terrakey_columns:
    if iteration == 0:
        find_frequent_address_nonterrakey(df_gr, group_cols, tupl[0], tupl[1], movein_date, weight_match).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{nonterrakey_addresses}.parquet")
        iteration = 1
    else:
        first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{nonterrakey_addresses}.parquet")
        first_results.join(
            find_frequent_address_nonterrakey(df_gr, group_cols, tupl[0], tupl[1], movein_date, weight_match),
            on=[group_cols],
            how="left"
        ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{nonterrakey_addresses}.parquet")
#Update df_gr table with GR Addresses columns
terrakey_df = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{terrakey_addresses}.parquet")
non_terrakey_df = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{nonterrakey_addresses}.parquet")
df_gr = df_gr.join(
    terrakey_df,
    on=[group_cols],
    how="left"
).join(
    non_terrakey_df,
    on=[group_cols],
    how="left"
).withColumn(
    "GR_Address_MunicipalityName",
    F.coalesce(
        F.col("selected_TrB2B_Municipality_Name"),
        F.col("selected_B2B_Municipality_Name"),
        F.col("selected_TrBilling_Municipality_Name"),
        F.col("selected_Billing_Municipality_Name")
    )
).withColumn(
    "GR_Address_StreetName",
    F.coalesce(
        F.col("selected_TrB2B_Street"),
        F.col("selected_B2B_Street"),
        F.col("selected_TrBilling_Street"),
        F.col("selected_Billing_Street")
    )
).withColumn(
    "GR_Address_PostalCode",
    F.coalesce(
        F.col("selected_TrB2B_Postal_Code"),
        F.col("selected_B2B_Postal_Code"),
        F.col("selected_TrBilling_Postal_Code"),
        F.col("selected_Billing_Postal_Code")
    )
).withColumn(
    "GR_Address_Region",
    F.coalesce(
        F.col("selected_TrB2B_Region_Name"),
        F.col("selected_B2B_Address_Region"),
        F.col("selected_TrBilling_Region_Name"),
        F.col("selected_Billing_Address_Region"),
    )
).withColumn(
    "GR_Address_Area",
    F.coalesce(
        F.col("selected_B2B_Area_PPC"),
        F.col("selected_Billing_Area_PPC")
    )
).withColumn(
    "GR_TerraKey",
    F.coalesce( 
        F.col("selected_B2B_TerraKey"),
        F.col("selected_Billing_TerraKey")
    )
).withColumn(
    "GR_Address_Latitude",
    F.coalesce(
        F.col("selected_TrB2B_WGS84_latitude"),
        F.col("selected_TrBilling_WGS84_latitude")
    )
).withColumn(
    "GR_Address_Longitude",
    F.coalesce(
        F.col("selected_TrB2B_WGS84_longitude"),
        F.col("selected_TrBilling_WGS84_longitude")
    )
).withColumn(
    "GR_Address_HouseNumber",
    F.coalesce(
        F.col("selected_PrB2B_House_Number"),
        F.col("selected_B2B_House_Number"),
        F.col("selected_PrBilling_House_Number"),
        F.col("selected_Billing_House_Number")
    )
)
print("Checkpoint 10: OK")

columns_to_drop = [col_name for col_name in df_gr.columns if col_name.startswith("selected_")]
df_gr = df_gr.drop(*columns_to_drop)
print("Checkpoint 11: OK")
#---------------------------------------------------------------------------------------------------------------------------

cols_phone = [
    "Fixphone_IIS",
    "Cellphone_IIS",
    "SAP_Phone_1_FIXED",
    "SAP_Phone_1_CELL"
]
df_gr_active = df_gr.filter(F.col("Active_Contract") == 1)
iteration:int = 0
prefix = "active"
for column in cols_phone:
    if iteration == 0:
        if column.startswith("Fixphone") | column.startswith("Cellphone"):
            find_frequent_phone_advanced_v2(df_gr_active, group_cols, column, prefix).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
        elif column.startswith("SAP_Phone_1"):
            find_frequent_sap_phone_1(df_gr_active, group_cols, column, prefix).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
        iteration = 1
    else:
        first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
        if column.startswith("Fixphone") | column.startswith("Cellphone"):
            first_results.join(
                find_frequent_phone_advanced_v2(df_gr_active, group_cols, column, prefix),
                on=[group_cols],
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
        elif column.startswith("SAP_Phone_1"):
            first_results.join(
                find_frequent_sap_phone_1(df_gr_active, group_cols, column, prefix),
                on=[group_cols],
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
print("Checkpoint 12: OK")

iteration:int = 0
prefix = "all"
for column in cols_phone:
    if iteration == 0:
        if column.startswith("Fixphone") | column.startswith("Cellphone"):
            find_frequent_phone_advanced_v2(df_gr, group_cols, column, prefix).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
        elif column.startswith("SAP_Phone_1"):
            find_frequent_sap_phone_1(df_gr, group_cols, column, prefix).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
        iteration = 1
    else:
        second_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
        if column.startswith("Fixphone") | column.startswith("Cellphone"):
            second_results.join(
                find_frequent_phone_advanced_v2(df_gr, group_cols, column, prefix),
                on=[group_cols],
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
        elif column.startswith("SAP_Phone_1"):
            second_results.join(
                find_frequent_sap_phone_1(df_gr, group_cols, column, prefix),
                on=[group_cols],
                how="left"
            ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
print("Checkpoint 13: OK")

first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{active_phones}.parquet")
second_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{all_phones}.parquet")
joined_table = first_results.join(second_results, on=[group_cols], how="right")
df_gr = df_gr.join(
    joined_table,
    on=[group_cols],
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
print("Checkpoint 14: OK")

cols_phone= [
    ("SAP_Phone_2_FIXED", "SAP"),
    ("SAP_Phone_2_CELL", "SAP"),
    ("FAIDRA_Phone_1_FIXED", "FAIDRA"),
    ("FAIDRA_Phone_1_CELL", "FAIDRA"),
    ("FAIDRA_Phone_2_FIXED", "FAIDRA"),
    ("FAIDRA_Phone_2_CELL", "FAIDRA"),
    ("EVALUE_Phone_1_FIXED", "EVALUE"),
    ("EVALUE_Phone_1_CELL", "EVALUE"),
    ("EVALUE_Phone_2_FIXED", "EVALUE"),
    ("EVALUE_Phone_2_CELL", "EVALUE"),
    ("EVALUE_Phone_3_FIXED", "EVALUE"),
    ("EVALUE_Phone_3_CELL", "EVALUE"),
    ("EVALUE_Phone_4_FIXED", "EVALUE"),
    ("EVALUE_Phone_4_CELL", "EVALUE"),
    ("EVALUE_Phone_5_FIXED", "EVALUE"),
    ("EVALUE_Phone_5_CELL", "EVALUE"),
    ("EBILL_Phone_1_FIXED", "EBILL"),
    ("EBILL_Phone_1_CELL", "EBILL"),
    ("EBILL_Phone_2_FIXED", "EBILL"),
    ("EBILL_Phone_2_CELL", "EBILL")
]
iteration:int = 0
for tupl in cols_phone:
    if iteration == 0:
        find_frequent_phone(df_gr, group_cols, tupl[0], tupl[1], weight_match).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{other_phones}.parquet")
        iteration = 1
    else:
        first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{other_phones}.parquet")
        first_results.join(
            find_frequent_phone(df_gr, group_cols, tupl[0], tupl[1], weight_match),
            on=[group_cols],
            how="left"
        ).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{other_phones}.parquet")
print("Checkpoint 15: OK")

first_results = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{other_phones}.parquet")
df_gr = df_gr.alias("a").join(
    first_results.alias("b"),
    on=[group_cols],
    how="left"
).withColumn(
    "GR_SAP_Phone_2_FIXED",
    F.coalesce(
        F.col("b.selected_SAP_Phone_2_FIXED"),
        F.when(
            F.col("a.all_SAP_Phone_1_FIXED_second_frequent") == F.col("a.GR_SAP_Phone_1_FIXED"),
            None
        ).otherwise( F.col("a.all_SAP_Phone_1_FIXED_second_frequent") )
    )
).withColumn(
    "GR_SAP_Phone_2_CELL",
    F.coalesce(
        F.col("b.selected_SAP_Phone_2_CELL"),
        F.when(
            F.col("a.all_SAP_Phone_1_CELL_second_frequent") == F.col("a.GR_SAP_Phone_1_CELL"),
            None
        ).otherwise( F.col("a.all_SAP_Phone_1_CELL_second_frequent") )
    )
).withColumn(
    "GR_FAIDRA_Phone_1_FIXED",
    F.col("b.selected_FAIDRA_Phone_1_FIXED")
).withColumn(
    "GR_FAIDRA_Phone_1_CELL",
    F.col("b.selected_FAIDRA_Phone_1_CELL")
).withColumn(
    "GR_FAIDRA_Phone_2_FIXED",
    F.col("b.selected_FAIDRA_Phone_2_FIXED")
).withColumn(
    "GR_FAIDRA_Phone_2_CELL",
    F.col("b.selected_FAIDRA_Phone_2_CELL")
).withColumn(
    "GR_EVALUE_Phone_1_FIXED",
    F.col("b.selected_EVALUE_Phone_1_FIXED")
).withColumn(
    "GR_EVALUE_Phone_1_CELL",
    F.col("b.selected_EVALUE_Phone_1_CELL")
).withColumn(
    "GR_EVALUE_Phone_2_FIXED",
    F.col("b.selected_EVALUE_Phone_2_FIXED")
).withColumn(
    "GR_EVALUE_Phone_2_CELL",
    F.col("b.selected_EVALUE_Phone_2_CELL")
).withColumn(
    "GR_EVALUE_Phone_3_FIXED",
    F.col("b.selected_EVALUE_Phone_3_FIXED")
).withColumn(
    "GR_EVALUE_Phone_3_CELL",
    F.col("b.selected_EVALUE_Phone_3_CELL")
).withColumn(
    "GR_EVALUE_Phone_4_FIXED",
    F.col("b.selected_EVALUE_Phone_4_FIXED")
).withColumn(
    "GR_EVALUE_Phone_4_CELL",
    F.col("b.selected_EVALUE_Phone_4_CELL")
).withColumn(
    "GR_EVALUE_Phone_5_FIXED",
    F.col("b.selected_EVALUE_Phone_5_FIXED")
).withColumn(
    "GR_EVALUE_Phone_5_CELL",
    F.col("b.selected_EVALUE_Phone_5_CELL")
).withColumn(
    "GR_EBILL_Phone_1_FIXED",
    F.col("b.selected_EBILL_Phone_1_FIXED")
).withColumn(
    "GR_EBILL_Phone_1_CELL",
    F.col("b.selected_EBILL_Phone_1_CELL")
).withColumn(
    "GR_EBILL_Phone_2_FIXED",
    F.col("b.selected_EBILL_Phone_2_FIXED")
).withColumn(
    "GR_EBILL_Phone_2_CELL",
    F.col("b.selected_EBILL_Phone_2_CELL")
)
columns_to_drop = [col_name for col_name in df_gr.columns if col_name.startswith("active_") | col_name.startswith("all_") | col_name.startswith("MP_") | col_name.startswith("selected_") ]
df_gr = df_gr.drop(*columns_to_drop)
print("Checkpoint 16: OK")

# COMMAND ----------

# MAGIC %md
# MAGIC ## -- Write final table with GR fields --
# MAGIC Write the final table to HIVE store. The table has the two JOIN keys (SOURCE, Contract_Account_ID), all the computed **GR_fields** and **wemetrix_main_record**

# COMMAND ----------

if output_table_write_mode == "ON":
    print(f"Writing output table (alias: {output_table}) with GR fields...")
    df_output = df_gr.select(
        [x for x in cols_all + ["wemetrix_main_record"]] +
        [x for x in df_gr.columns if "GR_" in x ]
    )
    df_output.write.mode("overwrite").saveAsTable(f"{output_table}")
    print("Writing COMPLETED...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## -- Tmp tables purge policy --
# MAGIC Once the final output table with the GR fields is computed and saved in HIVE store, the tmp parquet files should be deleted as part of a Garbage Collection process (purge).

# COMMAND ----------

todelete_parquet = [
    f"dbfs:/FileStore/wemetrix/{active_phones}.parquet",
    f"dbfs:/FileStore/wemetrix/{all_phones}.parquet",
    f"dbfs:/FileStore/wemetrix/{other_phones}.parquet",
    f"dbfs:/FileStore/wemetrix/{terrakey_addresses}.parquet",
    f"dbfs:/FileStore/wemetrix/{nonterrakey_addresses}.parquet",
    f"dbfs:/FileStore/wemetrix/{golden_gr_one}.parquet",
    f"dbfs:/FileStore/wemetrix/{golden_gr_two}.parquet",
    f"dbfs:/FileStore/wemetrix/{golden_gr_three}.parquet",
    f"dbfs:/FileStore/wemetrix/{golden_gr_four}.parquet",
    f"dbfs:/FileStore/wemetrix/{golden_gr_five}.parquet",
    f"dbfs:/FileStore/wemetrix/{golden_gr_six}.parquet",
    f"dbfs:/FileStore/wemetrix/{golden_gr_seven}.parquet",
    f"dbfs:/FileStore/wemetrix/{golden_gr_eight}.parquet"
]
todelete_tbls = []
for parquet_file in todelete_parquet:
    print(parquet_file)
    dbutils.fs.rm(parquet_file, True)
if todelete_tbls:
    for tbl in todelete_tbls:
        print(tbl)
        spark.sql(f"DROP TABLE IF EXISTS {tbl}")