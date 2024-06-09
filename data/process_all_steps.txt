# Databricks notebook source
# MAGIC %md ## Configuration script

# COMMAND ----------

# MAGIC %run "./includes/setup"

# COMMAND ----------

# Config values to get base and delta tables, change to get consequent runs

#default ="" or custom to create runs with tag suffix on tables/files (separate runs). For consequative runs keep the same

dbutils.widgets.text("runtag",  "run13")
runtag= dbutils.widgets.get("runtag")

dbutils.widgets.text("tablename_1",  "[predicta].[FOURSOURCE_ALL_18_11_2023]")
tablename_1= dbutils.widgets.get("tablename_1")

dbutils.widgets.text("tablename_2",  "[predicta].[FOURSOURCE_ALL_22_11_2023]")
tablename_2= dbutils.widgets.get("tablename_2")

dbutils.widgets.text("delta_tablename",  "dataanalysis.DELTAFOURSOURCE_22_11_2023_18_11_2023")
delta_tablename= dbutils.widgets.get("delta_tablename")

dbutils.widgets.text("predicta_gr_results",  "wemetrix.predicta_master_gr_2023_05_26")
predicta_gr_results= dbutils.widgets.get("predicta_gr_results")

#Run to create base table from 26_05_2023 and 2nd run to create delta to 31_05_2023
# tablename_1 = '[predicta].[FOURSOURCE_ALL_26_05_2023]'
# tablename_2 = '[predicta].[FOURSOURCE_ALL_31_05_2023]'
# delta_tablename = 'dataanalysis.DELTAFOURSOURCE_31_05_2023_26_05_2023'
# predicta_gr_results = 'wemetrix.predicta_master_gr_2023_05_26'

# # #Run 3rd time to create delta table from 31_05_2023 to 13_07_2023
# tablename_1 = '[predicta].[FOURSOURCE_ALL_31_05_2023]'
# tablename_2 = '[predicta].[FOURSOURCE_ALL_13_07_2023]'
# delta_tablename = 'dataanalysis.DELTAFOURSOURCE_13_07_2023_31_05_2023'
# predicta_gr_results = 'wemetrix.foursourcerun09GRpredicta' #Wemetrix Output for 31/05(after initializinh with predicta 26/5)

#Synapse base table to init DB.
# To reset the base table DROP TABLE wemetrix.foursource (+ runtag) in Databricks first. 
base_tablename= tablename_1

# Config values to maintain predicta GR calculations
# Set False to use new B/M Golden groups
# predicta_gr_results = 'wemetrix.predicta_master_2023_05_26'

# Set True and define table to get a new AT info from general_customer_master_table
getmnemosyneAT=False
predicta_general_customer_master_table = 'predicta.general_customer_master_table_29_05_2023'

params="[ tablename_1:{0}, tablename_2:{1}, predicta_gr_results:{2} ]".format(tablename_1,tablename_2,predicta_gr_results)

# Do not change below config
tableAprocess = "wemetrix.foursourcedelta"+runtag

print("runtah is: ",runtag)

# COMMAND ----------

# MAGIC %md ## Common functions

# COMMAND ----------

params

# COMMAND ----------

# MAGIC %run "./includes/common_functions"

# COMMAND ----------

#function to clean up (remove ALL tables for specific run)
def dropruntables(runtag):
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.afm_discard_delta{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.at_pass_info_delta{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.b2b_name_normalization_delta{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.bmresults{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.ca_discard_delta{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.email_correction_results_delta{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.gender_match_results_delta{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.pollaploi_results{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursource{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursource{runtag}_2605")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursource{runtag}_3105")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursourcedelta{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursource{runtag}gr")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursource{runtag}gr_2605")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursource{runtag}gr_3105")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursourcedelta{runtag}gr")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursource{runtag}GRpredicta")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursource{runtag}GRpredicta_2605")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursource{runtag}GRpredicta_3105")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursourceall{runtag}")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursourcepredictadeltas{runtag}gr")
    spark.sql(f"DROP TABLE IF EXISTS wemetrix.foursourcepredictadeltas{runtag}")
    

# COMMAND ----------

# MAGIC %md ## Create and get latest delta
# MAGIC First time will contain whole dataset

# COMMAND ----------

tableAprocess
# tableAprocess = "wemetrix.foursource"+runtag

# COMMAND ----------

# 0) GET BASE TABLE -1.30h / 2.5m
# Gets base table only if does not exist
if not spark.catalog.tableExists("wemetrix.foursource"+runtag):
    tableAprocess = "wemetrix.foursource"+runtag
    print("Creating base table "+tableAprocess)
    readfromsynapsetodelta(base_tablename,tableAprocess)
else:
# 1) CREATE DELTA table
    print("Creating delta table "+tableAprocess)
    executeatsynapse(f"exec dataanalysis.createdeltatable \'{tablename_1}\',\'{tablename_2}\',\'{delta_tablename}\'")     
    # 2) Get delta table to parquet
    readfromsynapsetodelta(delta_tablename,tableAprocess)
    

# COMMAND ----------

# MAGIC %md
# MAGIC ## A Tasks

# COMMAND ----------

# A1 - Gender Identification -40s # Outputs on full dataset
dbutils.notebook.run("./cleansing/gender_identification", 0, {"input_table": tableAprocess, "output_table": "wemetrix.gender_match_results_delta"+runtag})

# COMMAND ----------

# A2 - Email Correction - 20s / 19s
dbutils.notebook.run("./cleansing/email_correction", 0, {"input_table": tableAprocess, "output_table": "wemetrix.email_correction_results_delta"+runtag})

# COMMAND ----------

# A3 - AT & Passport info

 ## Create table with AT details from predicta - 1.34m
if getmnemosyneAT:
    executeatsynapse(" IF OBJECT_ID('dataanalysis.mnemosyne_AT', 'V') IS NOT NULL \
        DROP VIEW dataanalysis.mnemosyne_AT")
    
    executeatsynapse(f"CREATE  VIEW  dataanalysis.mnemosyne_AT AS select Contract_Account_ID, AT_INSTITUTE,VALID_DATE_FROM_TAUTOTITA ,VALID_DATE_TO_TAUTOTITA ,CA_Application_Date ,ADT_INSTITUTE ,VALID_DATE_FROM_DIAVATIRIO ,VALID_DATE_TO_DIAVATIRIO ,Determination_ID FROM \
         {predicta_general_customer_master_table}")
 
    readfromsynapsetodelta("dataanalysis.mnemosyne_AT","wemetrix.mnemosyne_AT",None,None)


# COMMAND ----------

## Run AT & Passport cleaning - 2.21m / 51s
dbutils.notebook.run("./cleansing/AT_Passport_info", 0, {"input_table": tableAprocess, "output_table": "wemetrix.at_pass_info_delta" + runtag})

# COMMAND ----------

# A5 - AFM discard -1.40m /21s
dbutils.notebook.run("./cleansing/AFM_discard", 0, {"input_table": tableAprocess, "output_table": "wemetrix.afm_discard_delta"+runtag})

# COMMAND ----------

# A6 - Discard of specific CAs -5.7m / 21s
dbutils.notebook.run("./cleansing/CAs_discard", 0, {"input_table": tableAprocess, "output_table": "wemetrix.ca_discard_delta"+runtag})

# COMMAND ----------

# A8 - B2B company names normalization - 21s / 21s
dbutils.notebook.run("./cleansing/B2B_names_normalization", 0, {"input_table": tableAprocess, "output_table": "wemetrix.b2b_name_normalization_delta"+runtag})

# COMMAND ----------

import pyspark.sql.utils
setmetadata(f"adding required columns to table. {params}")
try:
  spark.sql(f"ALTER TABLE {tableAprocess} ADD COLUMNS ( isdelta boolean, Gender string,Gender_Info string, Email_Correct string,B2B_Email_Correct string,ClVAT_IIS_wemetrix string, AT_Info_Wemetrix string, B2B_Company_Names_Wemetrix string )")
except pyspark.sql.utils.AnalysisException:
  print("Column already exists")
try:
  spark.sql(f"ALTER TABLE {tableAprocess} ADD COLUMNS (wemetrix_mp_customer_code string, wemetrix_match_type string, wemetrix_matching_ratio double,wemetrix_pass int)")
except pyspark.sql.utils.AnalysisException:
  print("Column already exists")
try: 
  spark.sql(f"ALTER TABLE {tableAprocess} ADD COLUMNS (wemetrix_ar_pollaplou string, wemetrix_pollaplos_type string, wemetrix_anentaxtos_afm string,Customer_Type_Dimosio string,     Customer_Type_Dimos string,Customer_Type_Idiotis string,LOG_SYMB_SAP bigint, DIMOS_KOINOTITA_ERMI string, KODIKOS_DIMOU_KALLIKRATI bigint, DIMOS_KALLIKRATI_KLEISTHENI string,  wemetrix_multiple_pollaplos int )")
except pyspark.sql.utils.AnalysisException:
  print("Column already exists")
try:
  spark.sql(f"ALTER TABLE {tableAprocess} ADD COLUMNS (AT_INSTITUTE string,ADT_INSTITUTE string, Passport_Info_Wemetrix string, ClAT_IIS_Wemetrix string, AT_Institute_Wemetrix string, ClPassport_IIS_Wemetrix string, ADT_Institute_Wemetrix string)")
except pyspark.sql.utils.AnalysisException:
  print("Column already exists")
setmetadata("")
spark.sql(f"ALTER TABLE {tableAprocess} ADD COLUMNS (Gender_Match_Score double)") 

# COMMAND ----------

# Add A task results to delta table  9m / 2.45m
index_cols = ["SOURCE", "Contract_Account_ID"]

gender_matching = spark.sql(f"SELECT * FROM wemetrix.gender_match_results_delta{runtag}")
email_correction = spark.sql(f"SELECT * FROM wemetrix.email_correction_results_delta{runtag}")
ca_discard = spark.sql(f"SELECT * FROM wemetrix.ca_discard_delta{runtag}")
afm_discard = spark.sql(f"SELECT * FROM wemetrix.afm_discard_delta{runtag}")
at_pass_info = spark.sql(f"SELECT * FROM wemetrix.at_pass_info_delta{runtag}")
b2b_name_normalization = spark.sql(f"SELECT * FROM wemetrix.b2b_name_normalization_delta{runtag}")

df = spark.sql(f"select SOURCE, Contract_Account_ID from {tableAprocess}")

df= (df
            .join(ca_discard.select(index_cols), on=index_cols, how='leftanti')
            )

df = (df
            .join(gender_matching.select(index_cols + ["Gender", "Gender_Info"]), on=index_cols, how='left')
            .join(email_correction.select(index_cols + ["Email_Correct", "B2B_Email_Correct"]), on=index_cols, how='left')
            .join(afm_discard.select(index_cols + ["ClVAT_IIS_wemetrix"]), on=index_cols, how='left')
            .join(at_pass_info.select(index_cols + ["AT_Info_Wemetrix","Passport_Info_Wemetrix", "ClAT_IIS_Wemetrix", "AT_Institute_Wemetrix", "ClPassport_IIS_Wemetrix","ADT_Institute_Wemetrix"]), on=index_cols, how='left')
            .join(b2b_name_normalization.select(index_cols + ["B2B_Company_Names_Wemetrix"]), on=index_cols, how='left')
            )
# Merge new A fields with delta table
isdelta= "delta" in tableAprocess
setmetadata(f"Merge {tableAprocess} with its A steps results {params}")
from delta.tables import DeltaTable
delta_table = DeltaTable.forName(spark, tableAprocess)
delta_table.alias("tgt").merge(
    df.alias("src"),
    "tgt.SOURCE == src.SOURCE and tgt.Contract_Account_ID == src.Contract_Account_ID") \
    .whenMatchedUpdate(set = { "isdelta":str(isdelta), "tgt.Gender" : "src.Gender", "tgt.Gender_Info" : "src.Gender_Info", "tgt.Email_Correct" : "src.Email_Correct", "tgt.B2B_Email_Correct" : "src.B2B_Email_Correct", "tgt.ClVAT_IIS_wemetrix" : "src.ClVAT_IIS_wemetrix", "tgt.AT_Info_Wemetrix" : "src.AT_Info_Wemetrix", "tgt.B2B_Company_Names_Wemetrix" : "src.B2B_Company_Names_Wemetrix",
                              "tgt.Passport_Info_Wemetrix":"src.Passport_Info_Wemetrix", "tgt.ClAT_IIS_Wemetrix":"src.ClAT_IIS_Wemetrix", "tgt.AT_Institute_Wemetrix": "src.AT_Institute_Wemetrix", "tgt.ClPassport_IIS_Wemetrix":"src.ClPassport_IIS_Wemetrix", "tgt.ADT_Institute_Wemetrix": "src.ADT_Institute_Wemetrix" } ) \
    .execute()
setmetadata("")

# COMMAND ----------

# Reset master table isdelta before joining with new delta ? / 2.67m
if "delta" in tableAprocess:
    setmetadata(f"Reset master table isdelta statuses {params}")
    spark.sql("UPDATE wemetrix.foursource"+runtag+" SET isdelta=0 where isdelta<>0")
    spark.sql("UPDATE wemetrix.foursource"+runtag+"grpredicta SET isdelta=0 where isdelta<>0")
    setmetadata("")

# COMMAND ----------

#if step run on delta tableAprocess merge it after A steps with base  ?/ 6.89m
if spark.catalog.tableExists("wemetrix.foursourcedelta"+runtag):
    setmetadata(f"Merge delta with main (wemetrix.foursource{runtag} wemetrix.foursourcedelta{runtag} {params}" )
    dfdelta=spark.sql("SELECT * FROM wemetrix.foursourcedelta"+runtag)

    from delta.tables import DeltaTable
    fs_table = DeltaTable.forName(spark, "wemetrix.foursource"+runtag)
    fs_table.alias("tgt").merge(
        dfdelta.alias("src"),
        "tgt.SOURCE == src.SOURCE and tgt.Contract_Account_ID == src.Contract_Account_ID") \
        .whenMatchedUpdateAll()\
        .whenNotMatchedInsertAll()\
        .execute()
    setmetadata("")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Multiples

# COMMAND ----------

# 10m
dbutils.notebook.run("./blocking-and-matching/pollaploi", 0, {"input_table": "wemetrix.foursource"+runtag, "pollaploi_output": "wemetrix.pollaploi_results"+runtag})

# COMMAND ----------

#2m
setmetadata( f"Merge with Pollaplous results {params}")
spark.sql("MERGE into wemetrix.foursource"+runtag+" VIEW using  wemetrix.pollaploi_results"+runtag+" B ON VIEW.Contract_Account_ID = B.Contract_Account_ID and VIEW.SOURCE=B.SOURCE  \
WHEN MATCHED THEN UPDATE set  \
VIEW.GR_Customer_Code= B.wemetrix_pollaplos_group, \
VIEW.wemetrix_mp_customer_code=B.wemetrix_pollaplos_group,\
VIEW.wemetrix_ar_pollaplou =B.wemetrix_ar_pollaplou, \
VIEW.wemetrix_pollaplos_type = B.wemetrix_pollaplos_type, \
VIEW.wemetrix_anentaxtos_afm =B.wemetrix_anentaxtos_afm,\
VIEW.Customer_Type_Dimosio =B.Customer_Type_Dimosio,\
VIEW.Customer_Type_Dimos =B.Customer_Type_Dimos,\
VIEW.Customer_Type_Idiotis =B.Customer_Type_Idiotis,\
VIEW.LOG_SYMB_SAP =B.LOG_SYMB_SAP_,\
VIEW.DIMOS_KOINOTITA_ERMI =B.DIMOS_KOINOTITA_ERMI_,\
VIEW.KODIKOS_DIMOU_KALLIKRATI =B.KODIKOS_DIMOU_KALLIKRATI_,\
VIEW.DIMOS_KALLIKRATI_KLEISTHENI =B.DIMOS_KALLIKRATI_KLEISTHENI_,\
VIEW.wemetrix_multiple_pollaplos =B.wemetrix_multiple_pollaplos"
)
setmetadata( "")

# COMMAND ----------

#2m
setmetadata( f"Update Pollaplous matchtype {params}")
spark.sql("UPDATE wemetrix.foursource"+runtag+"  SET wemetrix_match_type=case when GR_Customer_Code = Contract_Account_ID then 'MP' else 'DA' end where not GR_Customer_code is null ")
setmetadata( "")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Blocking And Matching

# COMMAND ----------

# 1h
dbutils.notebook.run("./blocking-and-matching/blocking_and_matching_enhanced", 0, {"input_table": "wemetrix.foursource"+runtag, "bm_results_table": "wemetrix.bmresults", "runtag": runtag })

# COMMAND ----------

#3m
setmetadata( f"Merge with B/M results {params}")
spark.sql("MERGE into wemetrix.foursource"+runtag+" VIEW using wemetrix.bmresults"+runtag+" B ON VIEW.Contract_Account_ID = B.Contract_Account_ID and VIEW.SOURCE=B.SOURCE  \
WHEN MATCHED THEN UPDATE set VIEW.GR_Customer_Code =B.wemetrix_mp_customer_code, \
VIEW.wemetrix_mp_customer_code =B.wemetrix_mp_customer_code, \
VIEW.wemetrix_match_type =B.wemetrix_match_type,\
VIEW.wemetrix_matching_ratio =B.wemetrix_matching_ratio,\
VIEW.wemetrix_pass =B.wemetrix_pass"
)
setmetadata( "")




# COMMAND ----------

# MAGIC %md
# MAGIC ## Golden Record GR calculation

# COMMAND ----------

# 15m
#  get output table with GRs for delta=1, it runs for all groups containing changed rows
dbutils.notebook.run("./blocking-and-matching/GoldenRecordGR", 0, {"input_table": "wemetrix.foursource"+runtag, "output_table": tableAprocess+"GR"})
# First time creates wemetrix.foursource{runtag}GR and next wemetrix.foursourcedelta{runtag}GR

# COMMAND ----------

# if it run for main table (table) we just keep main wemetrix.foursource{runtag}GR table
#1m
# if it run for delta merge it with main GR base
if spark.catalog.tableExists(tableAprocess+"GR") and "delta" in tableAprocess:
    setmetadata(f"Merge GR  with main GR (wemetrix.foursource{runtag}GR) {params}" )
    dfdeltaGR=spark.sql(f"SELECT * FROM {tableAprocess}GR" )

    from delta.tables import DeltaTable
    gr_table = DeltaTable.forName(spark, "wemetrix.foursource"+runtag+"GR")
    gr_table.alias("tgt").merge(
        dfdeltaGR.alias("src"),
        "tgt.SOURCE == src.SOURCE and tgt.Contract_Account_ID == src.Contract_Account_ID") \
        .whenMatchedUpdateAll()\
        .whenNotMatchedInsertAll()\
        .execute()
    setmetadata("")


# COMMAND ----------

# MAGIC %md
# MAGIC ###    Produce output maintaining predicta

# COMMAND ----------

    # get predicta table results 
    dfpredicta=spark.sql(f"SELECT * FROM {predicta_gr_results}")
    dfpredictaGR= dfpredicta.select(
        [x for x in ["SOURCE", "Contract_Account_ID"]]+
        [x for x in dfpredicta.columns if "GR_" in x]
    )

# COMMAND ----------

#1m  Create copy of main GR table and keep predicta results (runs only first time)
if not spark.catalog.tableExists("wemetrix.foursource"+runtag+"GRpredicta"):
    setmetadata(f" Copy of main GR table to maintain predicta results {params}")
    spark.sql(f"CREATE OR REPLACE TABLE wemetrix.foursource{runtag}GRpredicta CLONE wemetrix.foursource{runtag}GR")
    spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", True)    
    setmetadata(f" Updating main wemetrix.foursource{runtag}GRpredicta with predicta results")
    # update all rows
    from delta.tables import DeltaTable
    grmaintain = DeltaTable.forName(spark, "wemetrix.foursource"+runtag+"GRpredicta")
    grmaintain.alias("tgt").merge(
        dfpredictaGR.alias("src"),
        "tgt.SOURCE == src.SOURCE and tgt.Contract_Account_ID == src.Contract_Account_ID" ) \
        .whenMatchedUpdateAll()\
        .execute()
setmetadata("")

# COMMAND ----------

# Maintain predicta results 
# 2.5m
df=spark.sql(f"SELECT * FROM wemetrix.foursource{runtag}GR where isdelta==1")
# spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", True)    
setmetadata(f" Updating wemetrix.foursource{runtag}GRpredicta only for delta rows {params}")
from delta.tables import DeltaTable
grmaintain = DeltaTable.forName(spark, "wemetrix.foursource"+runtag+"GRpredicta")
grmaintain.alias("tgt").merge(
        df.alias("src"),
        "tgt.SOURCE == src.SOURCE and tgt.Contract_Account_ID == src.Contract_Account_ID" ) \
        .whenMatchedUpdateAll()\
        .whenNotMatchedInsertAll()\
        .execute()
setmetadata("")


# COMMAND ----------

# set isdelta=1 for all records in group that has a record with isdelta=1

# COMMAND ----------

# Functions for alligning GR records with predicta results.

# get records with no valid master
def getRecordsWithNoMaster(df):
    dfmp=df.filter(F.col("Contract_Account_ID")== F.col("GR_Customer_code")).select(F.col("GR_Customer_code"))
    dfmp = dfmp.alias("dfmp")
    df2=df.join(dfmp,  df["GR_Customer_code"]==dfmp["dfmp.GR_Customer_code"],  how="left_anti").select([F.col(xx) for xx in df.columns])
    return df2.count()

# If GR_Customer_Code is not master the records will find the new master GR_Customer_Code or will become master.
# That way regardless the delta changes that caused groups recomputed each record will be linked with the most appropriate group.
def updateorphanmaster(df):
    # get records with no master
    spark.conf.set("spark.sql.analyzer.failAmbiguousSelfJoin", False)
    dfmp=df.filter(F.col("Contract_Account_ID")== F.col("GR_Customer_code")).select(F.col("GR_Customer_code"))
    dfmp = dfmp.alias("dfmp")
    df2=df.join(dfmp,  df["GR_Customer_code"]==dfmp["dfmp.GR_Customer_code"],  how="left_anti").select([F.col(xx) for xx in df.columns])
    df2.write.option("compression", "snappy").mode("overwrite").parquet("dbfs:/FileStore/wemetrix/grwithnomain2.parquet")
    dfnm = spark.read.parquet(f"dbfs:/FileStore/wemetrix/grwithnomain2.parquet")
    
    # update GR_Customer_code with that of the new customer code
    df = df.alias("df")
    dfnm= dfnm.alias("dfnm")
    dfnew=dfnm.join(df, dfnm["dfnm.GR_Customer_code"]==df["df.Contract_Account_ID"], how="inner").select([F.col("dfnm."+ x) for x in dfnm.columns]+ [F.col("df.GR_Customer_code").alias("GR_Customer_code_lv2")])
        
    # merge with initial df
    dfnew= dfnew.alias("dfnew")
    dfres=df.join(dfnew, df["df.Contract_Account_ID"]==dfnew["dfnew.Contract_Account_ID"], how="left").select([F.col("df."+ x) for x in df.columns]+ [F.col("dfnew.GR_Customer_code_lv2")])
    dfres=dfres.withColumn("GR_Customer_code_2", F.when( F.col("GR_Customer_code_lv2").isNull(),F.col("GR_Customer_code")).otherwise(F.col("GR_Customer_code_lv2")))
   
    dfres= dfres.drop("GR_Customer_code").drop("GR_Customer_code_lv2").withColumnRenamed("GR_Customer_code_2","GR_Customer_code")
    return dfres


# COMMAND ----------

# Allign contracts with no valid GR - 2m
dfpredicta=spark.sql(f"SELECT * FROM wemetrix.foursource{runtag}GRpredicta where SOURCE='SAP'")

# first run (for records not having valid master)
dfpredicta=updateorphanmaster(dfpredicta)
dfpredicta.write.option("compression", "snappy").mode("overwrite").parquet("dbfs:/FileStore/wemetrix/grtemp1.parquet")
dfpredicta= spark.read.parquet(f"dbfs:/FileStore/wemetrix/grtemp1.parquet")
getRecordsWithNoMaster(dfpredicta)

# COMMAND ----------

#second run to eliminate few records didnt get appropriate master from first run - 2m 
dfpredicta=updateorphanmaster(dfpredicta)
dfpredicta.write.option("compression", "snappy").mode("overwrite").parquet("dbfs:/FileStore/wemetrix/grtemp2.parquet")
dfpredicta= spark.read.parquet(f"dbfs:/FileStore/wemetrix/grtemp2.parquet")
# Should now return 0
getRecordsWithNoMaster(dfpredicta)

# COMMAND ----------

#  Merge correct GR after allignment - 4m
# 
# spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", True)    
setmetadata(f"Alligning GR groups after applying delta {params}")
from delta.tables import DeltaTable
grmaintain = DeltaTable.forName(spark, "wemetrix.foursource"+runtag+"GRpredicta")
grmaintain.alias("tgt").merge(
        dfpredicta.alias("src"),
        # "tgt.SOURCE == src.SOURCE and tgt.Contract_Account_ID == src.Contract_Account_ID" ) \
        "tgt.Contract_Account_ID == src.Contract_Account_ID") \
        .whenMatchedUpdate(set = { "tgt.GR_Customer_code": "src.GR_Customer_code" } ) \
        .execute()
setmetadata("")

# COMMAND ----------

# MAGIC %md
# MAGIC ###rerun GR calculation for deltas on final maintain predicta table

# COMMAND ----------

def filterdeltaongroups(df):
    dfdeltagr=df.filter(F.col("isdelta")== 1).select(F.col("GR_Customer_Code")).distinct()
    dfdeltagr=dfdeltagr.withColumn('deriveddelta', F.lit(True)).withColumnRenamed("GR_Customer_Code","GR_Customer_Code_unique")
    dfpredictadelta = df.join(dfdeltagr, df["GR_Customer_Code"] == dfdeltagr["GR_Customer_Code_unique"], how='left_outer')
    dfpredictadelta = dfpredictadelta.withColumn('isdelta', F.coalesce(F.col('deriveddelta'),F.col('isdelta'))).drop('deriveddelta').drop('GR_Customer_Code_unique')
    dfpredictadelta=dfpredictadelta.filter(F.col("isdelta")== 1)
    return dfpredictadelta

# COMMAND ----------

dfpredicta=spark.sql(f"SELECT * FROM wemetrix.foursource{runtag}GRpredicta")
dfpredictadeltagroups=filterdeltaongroups(dfpredicta)
drop_wemetrix_cols_before_rerun=["wemetrix_main_record", "wemetrix_mp_customer_code"]
dfpredictadeltagroups=dfpredictadeltagroups.drop(*drop_wemetrix_cols_before_rerun).withColumnRenamed("GR_Customer_Code", "wemetrix_mp_customer_code")
drop_GR_cols_before_rerun=[x for x in dfpredictadeltagroups.columns if "GR_" in x ]
dfpredictadeltagroups=dfpredictadeltagroups.drop(*drop_GR_cols_before_rerun)
#GR mechanism will recalculate main_records for the new delta records.The old computed group column 'wemetrix_mp_customer_code' has now the values of GR_Customer_Code coming from Predicta table with the results of delta changes.
dfpredictadeltagroups.write.mode("overwrite").saveAsTable(f"wemetrix.foursourcepredictadeltas{runtag}")

# COMMAND ----------

spark.sql(f"SELECT * FROM wemetrix.foursourcepredictadeltasrun13").count() #486278 , 618216

# COMMAND ----------

#6-7m
dbutils.notebook.run("./blocking-and-matching/GoldenRecordGR", 0, {"input_table": "wemetrix.foursourcepredictadeltas"+runtag, "output_table": "wemetrix.foursourcepredictadeltas"+runtag+"GR"})

# COMMAND ----------

setmetadata(f"Update GR records for predicta delta")

dfpredictadeltaGR=spark.sql(f"SELECT * FROM wemetrix.foursourcepredictadeltas{runtag}GR")

from delta.tables import DeltaTable
grmaintain = DeltaTable.forName(spark, "wemetrix.foursource"+runtag+"GRpredicta")
grmaintain.alias("tgt").merge(
        dfpredictadeltaGR.alias("src"),
        "tgt.SOURCE == src.SOURCE and tgt.Contract_Account_ID == src.Contract_Account_ID" ) \
        .whenMatchedUpdateAll() \
        .execute()
setmetadata("")


# COMMAND ----------



# COMMAND ----------

# MAGIC %md
# MAGIC ### JOIN operation between foursource table and GR fields

# COMMAND ----------

foursource_tbl = "wemetrix.foursource"+runtag
gr_fields_tbl = "wemetrix.foursource"+runtag+"grpredicta"
# gr_fields_tbl = "wemetrix.foursourcerunGR_prod"
df_foursource = spark.sql(f"SELECT * FROM {foursource_tbl}")
df_gr_fields = spark.sql(f"SELECT * FROM {gr_fields_tbl}")

df_foursource = df_foursource.withColumnRenamed("GR_Customer_Code", "GR_Customer_Code_legacy") #foursource had already the field "GR_Customer_Code", thus we renamed it to avoid conflict after the JOIN with the computed GR fields.
df_gr_fields = df_gr_fields.select(
    ["SOURCE", "Contract_Account_ID", "wemetrix_main_record"] + [x for x in df_gr_fields.columns if "GR_" in x ]
)
df_joined_foursourcerunGR = df_foursource.join(
    df_gr_fields,
    on = ["SOURCE", "Contract_Account_ID"],
    how = "left"
)
dfpredicta=spark.sql(f"SELECT * FROM wemetrix.predicta_master_gr_2023_05_26")
df_all_foursource = df_joined_foursourcerunGR.filter(F.col("SOURCE")=="SAP").join(
    dfpredicta.select([
        "SOURCE",
        "Contract_Account_ID",
        "qsMatchDataID",
        "qsMatchType",
        "qsMatchWeight",
        "qsMatchPassNumber",
        "qsMatchPattern",
        "qsMatchLRFlag",
        "qsMatchExactFlag",
        "EnPrFirst_Name_IIS",
        "EnPrLast_Name_IIS",
        "EnStreet_IIS",
        "EnBillingStreet_IIS",
        "SourceSap",
        "FixPhoneIISBlock",
        "CellPhoneIISBlock",
        "PrCustomer_Type_IIS_changed",
        "Determination_ID",
        "ClEbill_Email",
        "Match_type_PPC"
    ]),
    on = ["SOURCE", "Contract_Account_ID"],
    how = "left"
)
df_all_foursource.write.mode("overwrite").saveAsTable(f"wemetrix.foursourceall{runtag}")

# COMMAND ----------

runtag

# COMMAND ----------

# Exit notebook

# COMMAND ----------

dbutils.notebook.exit("Success")