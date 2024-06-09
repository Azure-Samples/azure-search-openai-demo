# Databricks notebook source
runtag="run13"
## 1st run initialize db for 1st date

# COMMAND ----------

v_result= dbutils.notebook.run("./process_all_steps", 0, {"runtag": runtag, 
                                                "tablename_1": "[predicta].[FOURSOURCE_ALL_18_11_2023_v]",
                                                "tablename_2": "[predicta].[FOURSOURCE_ALL_23_11_2023_v]",
                                                "delta_tablename": "dataanalysis.DELTAFOURSOURCE_23_11_2023_18_11_2023",
                                                "predicta_gr_results": "wemetrix.gr_cleansed_customers_2023_11_18_final2_tbl"
                                                })



# COMMAND ----------

if v_result=="Success":
    spark.sql(f"CREATE OR REPLACE TABLE wemetrix.foursource{runtag}grpredicta_1811 CLONE wemetrix.foursource{runtag}grpredicta;")
    spark.sql(f"CREATE OR REPLACE TABLE wemetrix.foursource{runtag}gr_1811 CLONE wemetrix.foursource{runtag}gr;")
    spark.sql(f"CREATE OR REPLACE TABLE wemetrix.foursource{runtag}_1811 CLONE wemetrix.foursource{runtag};")
    spark.sql(f"CREATE OR REPLACE TABLE wemetrix.foursourceall{runtag}_1811 CLONE wemetrix.foursourceall{runtag};")

# COMMAND ----------

## 2nd run integrate 2nd date

# COMMAND ----------

if v_result=="Success":
   v_result=""
   v_result= dbutils.notebook.run("./process_all_steps", 0, {"runtag": runtag, 
                                                "tablename_1": "[predicta].[FOURSOURCE_ALL_18_11_2023_v]",
                                                "tablename_2": "[predicta].[FOURSOURCE_ALL_23_11_2023_v]",
                                                "delta_tablename": "dataanalysis.DELTAFOURSOURCE_23_11_2023_18_11_2023",
                                                "predicta_gr_results": "wemetrix.gr_cleansed_customers_2023_11_18_final2_tbl"
                                                })


# COMMAND ----------

if v_result=="Success":
    spark.sql(f"CREATE OR REPLACE TABLE wemetrix.foursource{runtag}grpredicta_2311 CLONE wemetrix.foursource{runtag}grpredicta;")
    spark.sql(f"CREATE OR REPLACE TABLE wemetrix.foursource{runtag}gr_2311 CLONE wemetrix.foursource{runtag}gr;")
    spark.sql(f"CREATE OR REPLACE TABLE wemetrix.foursource{runtag}_2311 CLONE wemetrix.foursource{runtag};")
    spark.sql(f"CREATE OR REPLACE TABLE wemetrix.foursourceall{runtag}_2311 CLONE wemetrix.foursourceall{runtag};")

# COMMAND ----------

# MAGIC %sql
# MAGIC describe history wemetrix.foursourcerun09

# COMMAND ----------

## 3rd run integrate 3rd date

# COMMAND ----------

if v_result=="Success":
    v_result= dbutils.notebook.run("./process_all_steps", 0, {"runtag":runtag, 
                                                "tablename_1": "[predicta].[FOURSOURCE_ALL_31_05_2023]",
                                                "tablename_2": "[predicta].[FOURSOURCE_ALL_13_07_2023]",
                                                "delta_tablename": "dataanalysis.DELTAFOURSOURCE_13_07_2023_31_05_2023",
                                                "predicta_gr_results": "wemetrix.foursource"+runtag+"GRpredicta"
                                                })

# COMMAND ----------

v_result

# COMMAND ----------

