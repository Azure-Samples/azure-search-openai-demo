# Databricks notebook source
dbutils.widgets.text("predicta_gr_results_table",  "wemetrix.predicta_master_2023_05_31_j")
predicta_gr_results_table = dbutils.widgets.get("predicta_gr_results_table")
dbutils.widgets.text("maintain_predicta",  "True")
maintain_predicta=dbutils.widgets.get("maintain_predicta")

dbutils.widgets.text("runtag",  "run04")
runtag=dbutils.widgets.get("runtag")

dbutils.widgets.text("results_table",  "wemetrix.bmresults")
results_table=dbutils.widgets.get("results_table")+runtag

foursourcedelta ="wemetrix.foursourcedelta"+runtag

predicta_gr_results_table +" - "+ results_table+" - "+ maintain_predicta+ " - "+foursourcedelta


# COMMAND ----------

# MAGIC %sql 
# MAGIC DROP TABLE IF EXISTS wemetrix.bmresults_wdelta;
# MAGIC -- CREATE TABLE wemetrix.bmresults_wdelta AS
# MAGIC -- select A.*, isnotnull(D.Contract_Account_ID) as isdelta
# MAGIC --  from ${results_table} A  left join ${foursourcedelta} D on A.SOURCE=D.SOURCE and A.Contract_Account_ID = D.Contract_Account_ID 

# COMMAND ----------

 if spark.catalog.tableExists(foursourcedelta):
     spark.sql(f"CREATE TABLE wemetrix.bmresults_wdelta AS select A.*, isnotnull(D.Contract_Account_ID) as isdelta from {results_table} A  left join {foursourcedelta} D on A.SOURCE=D.SOURCE and A.Contract_Account_ID = D.Contract_Account_ID ")
else:
     spark.sql(f"CREATE TABLE wemetrix.bmresults_wdelta AS select A.*, 0 as isdelta from {results_table} A")

# COMMAND ----------

# MAGIC %sql
# MAGIC DROP TABLE IF EXISTS wemetrix.bmresults_contracts;
# MAGIC CREATE TABLE wemetrix.bmresults_contracts AS ( 
# MAGIC      select coalesce(PRED.GR_Customer_Code,WEM.WE_GROUP_Contract_Account_ID) as GR_Customer_Code , WEM.SOURCE, WEM.Contract_Account_ID, WEM.isdelta, WEM.wemetrix_mp_customer_code, WEM.wemetrix_match_type, WEM.wemetrix_matching_ratio, WEM.wemetrix_pass from 
# MAGIC    ( select A.*, case when A.isdelta==1 and ${maintain_predicta}=='True' then 
# MAGIC     coalesce(bmresults_M.Contract_Account_ID, A.Contract_Account_ID) 
# MAGIC     else 
# MAGIC     A.Contract_Account_ID 
# MAGIC    end  as WE_GROUP_Contract_Account_ID 
# MAGIC  from wemetrix.bmresults_wdelta A left join 
# MAGIC  (select SOURCE, Contract_Account_ID,  wemetrix_mp_customer_code from wemetrix.bmresults_wdelta where wemetrix_match_type = 'MP') as bmresults_M 
# MAGIC  on A.wemetrix_mp_customer_code = bmresults_M.wemetrix_mp_customer_code 
# MAGIC    ) WEM Left join ${predicta_gr_results_table} PRED on WEM.WE_GROUP_Contract_Account_ID = PRED.Contract_Account_ID )
# MAGIC    
# MAGIC
# MAGIC

# COMMAND ----------



# COMMAND ----------

# MAGIC %md
# MAGIC ### -- quality checks

# COMMAND ----------

# MAGIC %sql 
# MAGIC -- select * from   wemetrix.bmresults_contracts;

# COMMAND ----------

# MAGIC %sql 
# MAGIC -- select count(*) from wemetrix.bmresults_wdelta;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- select count(*) from wemetrix.bmresults_contracts

# COMMAND ----------

# %sql
# select count(*)
#  from wemetrix.bmresults_wdelta left join 
#  (select SOURCE, Contract_Account_ID,wemetrix_mp_customer_code,  wemetrix_group_number from wemetrix.bmresults_wdelta where wemetrix_match_type = 'MP') as bmresults_M 
#  on wemetrix.bmresults_wdelta.wemetrix_group_number = bmresults_M.wemetrix_mp_customer_code 
  

# COMMAND ----------

# MAGIC %sql
# MAGIC -- select count(*) from wemetrix.bmresults_wdelta --where wemetrix_group_number is null and wemetrix_match_type = 'MP'

# COMMAND ----------

import pyspark.sql.functions as F
runtag="run09"
dfpredicta=spark.sql(f"SELECT * FROM wemetrix.foursource{runtag}GRpredicta where SOURCE='SAP'")



# COMMAND ----------

dfpredicta.count()

# COMMAND ----------



# COMMAND ----------

def markdeltaofgroups(df):
    dfdeltagr=df.filter(F.col("isdelta")== 1).select(F.col("GR_Customer_Code")).distinct()
    dfdeltagr=dfdeltagr.withColumn('deriveddelta', F.lit(True))
    dfpredictadelta = df.join(dfdeltagr, df["GR_Customer_Code"] == dfdeltagr["GR_Customer_Code"], how='left_outer')
    dfpredictadelta = dfpredictadelta.withColumn('isdelta', F.coalesce(F.col('deriveddelta'),F.col('isdelta'))).drop('deriveddelta')
    dfpredictadelta=dfpredictadelta.filter(F.col("isdelta")== 1)
    return dfpredictadelta



# COMMAND ----------

df1=markdeltaofgroups(dfpredicta)

# COMMAND ----------

df1.count()

# COMMAND ----------

