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
input_table = dbutils.widgets.get("input_table")

dbutils.widgets.text("pollaploi_output", "wemetrix.pollaploi_results")
output_table = dbutils.widgets.get("pollaploi_output")

multiple_pollaploi = "wemetrix.multiple_pollaploi"

print("Input table: ", input_table)
print("Output table: ", output_table)
print("Multiple pollaploi table: ", multiple_pollaploi)

# COMMAND ----------

# DBTITLE 1,Read input table(s)
df_pollaploi = spark.sql(f"SELECT * FROM {input_table}")
df_multiple_pollaploi = spark.sql(f"SELECT * FROM {multiple_pollaploi}")

# COMMAND ----------

# DBTITLE 1,Compute Pollaplous
pollaplos_one = f"tmp_pollaplos_one_dev"
pollaplos_two = f"tmp_pollaplos_two_dev"
pollaplos_three = f"tmp_pollaplos_three_dev"
pollaplos_four = f"tmp_pollaplos_four_dev"
pollaplos_five = f"tmp_pollaplos_five_dev"

#---------------------------------------------------------------------------------------------
# Μπαμπάδες Πολλαπλοί
#---------------------------------------------------------------------------------------------

fkkvkp = spark.read.load("dbfs:/mnt/PRD/curated/SAP_ISU/fkkvkp")
fkkvk = spark.read.load("dbfs:/mnt/PRD/curated/SAP_ISU/fkkvk")
but0 = spark.read.load("dbfs:/mnt/PRD/curated/SAP_ISU/but000")
but0.createOrReplaceTempView("but000")
fkkvk.createOrReplaceTempView("fkkvk")
fkkvkp.createOrReplaceTempView("fkkvkp")
dfkkbptaxnum = spark.read.load("dbfs:/mnt/PRD/curated/SAP_ISU/dfkkbptaxnum")
dfkkbptaxnum.createOrReplaceTempView("dfkkbptaxnum")

df_mpampades = spark.sql(
    """
    SELECT
    a.VKONT , vbund, TAXNUM, name_org1, name_org2, name_org3,name_org4
    FROM fkkvk a
    left join fkkvkp b on a.VKONT = b.VKONT
    left join dfkkbptaxnum c on b.GPART = c.PARTNER
    left join but000 d on d.partner = c.partner
    where vktyp = '02'
    AND TAXTYPE = 'GR2'
    and a.vkont like '001%'
    """
)
#---------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------
# ΔΗΜΟΙ ΚΑΛΛΙΚΡΑΤΗ
#---------------------------------------------------------------------------------------------

df_dimoi_kallikrati = spark.sql(f"SELECT * FROM wemetrix.dimoi_kallikrati")

#---------------------------------------------------------------------------------------------

# ΔΗΜΟΣΙΟ (ΜΠΑΜΠΑΔΕΣ)
df_dimosio = df_mpampades.filter(F.substring(F.col("vbund"), 2,1)==4)
# buffer_column = "DIMOS/KOINOTITA ERMI"
buffer_column = "`LOG. SYMB. SAP`"
dimoi_names = df_dimoi_kallikrati.select(buffer_column).distinct()
df_dimosio = df_dimosio.join(dimoi_names, df_dimosio["VKONT"] == dimoi_names[buffer_column], how = "left_anti")

# ΔΗΜΟΣ (ΜΠΑΜΠΑΔΕΣ)
df_dimos = df_mpampades.join(dimoi_names, df_mpampades["VKONT"] == dimoi_names[buffer_column], how = "inner").drop(F.col(buffer_column))

# ΙΔΙΩΤΗΣ (ΜΠΑΜΠΑΔΕΣ)
idiotes_names = df_dimosio.select(["VKONT"]).union(df_dimos.select(["VKONT"]))
df_idiotis = df_mpampades.join(idiotes_names, on = "VKONT", how = "left_anti")
print("Checkpoint 01: OK")

df_pollaploi = df_pollaploi.join( #Join with DIMOSIO
    F.broadcast(df_dimosio.select(["VKONT"])),
    df_dimosio["VKONT"] == df_pollaploi["Ar_Pollaplou"],
    how = "left"
).withColumn(
    "Customer_Type_Dimosio_entagmenos",
    F.when( F.col("Ar_Pollaplou") == F.col("VKONT"), "Y").otherwise(None)
).withColumn(
    "wemetrix_ar_pollaplou_dimosio_entagmenos",
    F.when( F.col("Ar_Pollaplou") == F.col("VKONT"), F.col("VKONT")).otherwise(None)
).withColumn(
    "wemetrix_pollaplos_type_dimosio_entagmenos",
    F.when( F.col("Ar_Pollaplou") == F.col("VKONT"), "Ενταγμένος").otherwise(None)
).drop(
    F.col("VKONT")
).join( #Join with DIMOS
    F.broadcast(df_dimos.select(["VKONT"])),
    df_dimos["VKONT"] == df_pollaploi["Ar_Pollaplou"],
    how = "left"
).withColumn(
    "Customer_Type_Dimos_entagmenos",
    F.when( F.col("Ar_Pollaplou") == F.col("VKONT"), "Y").otherwise(None)
).withColumn(
    "wemetrix_ar_pollaplou_dimos_entagmenos",
    F.when( F.col("Ar_Pollaplou") == F.col("VKONT"), F.col("VKONT")).otherwise(None)
).withColumn(
    "wemetrix_pollaplos_type_dimos_entagmenos",
    F.when( F.col("Ar_Pollaplou") == F.col("VKONT"), "Ενταγμένος").otherwise(None)
).drop(
    F.col("VKONT")
).join( #Join with IDIOTIS
    F.broadcast(df_idiotis.select(["VKONT"])),
    df_idiotis["VKONT"] == df_pollaploi["Ar_Pollaplou"],
    how = "left"
).withColumn(
    "Customer_Type_Idiotis_entagmenos",
    F.when( F.col("Ar_Pollaplou") == F.col("VKONT"), "Y").otherwise(None)
).withColumn(
    "wemetrix_ar_pollaplou_idiotis_entagmenos",
    F.when( F.col("Ar_Pollaplou") == F.col("VKONT"), F.col("VKONT")).otherwise(None)
).withColumn(
    "wemetrix_pollaplos_type_idiotis_entagmenos",
    F.when( F.col("Ar_Pollaplou") == F.col("VKONT"), "Ενταγμένος").otherwise(None)
).drop(
    F.col("VKONT")
).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{pollaplos_one}.parquet")
print("Checkpoint 02: OK")

df_pollaploi = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{pollaplos_one}.parquet")
df_anentaxtoi_dimosio = find_anentaxtoi_pollaploi(
    df_pollaploi,
    "ΔΗΜΟΣΙΟ",
    df_dimosio,
    ["wemetrix_ar_pollaplou_dimosio_entagmenos", "wemetrix_pollaplos_type_dimosio_entagmenos", "Customer_Type_Dimosio_entagmenos"],
    "wemetrix_ar_pollaplou_dimosio_entagmenos",
    "wemetrix_pollaplos_type_dimosio_entagmenos"
)

#--------------------------------------------------------------------------------------
df_anentaxtoi_dimos = find_anentaxtoi_pollaploi(
    df_pollaploi,
    "ΔΗΜΟΣ",
    df_dimos,
    ["wemetrix_ar_pollaplou_dimos_entagmenos", "wemetrix_pollaplos_type_dimos_entagmenos", "Customer_Type_Dimos_entagmenos"],
    "wemetrix_ar_pollaplou_dimos_entagmenos",
    "wemetrix_pollaplos_type_dimos_entagmenos"
)

#--------------------------------------------------------------------------------------
df_anentaxtoi_idiotis = find_anentaxtoi_pollaploi(
    df_pollaploi,
    "ΙΔΙΩΤΗΣ",
    df_idiotis,
    ["wemetrix_ar_pollaplou_idiotis_entagmenos", "wemetrix_pollaplos_type_idiotis_entagmenos", "Customer_Type_Idiotis_entagmenos"],
    "wemetrix_ar_pollaplou_idiotis_entagmenos",
    "wemetrix_pollaplos_type_idiotis_entagmenos"
)

df_pollaploi = df_pollaploi.alias("a").join(
    F.broadcast(df_anentaxtoi_dimosio.select(["Contract_Account_ID", "VKONT", "TAXNUM"]).alias("b")),
    on = "Contract_Account_ID",
    how = "left"
).withColumn(
    "Customer_Type_Dimosio_anentaxtos",
    F.when( F.col("a.Contract_Account_ID") == F.col("b.Contract_Account_ID"), "Y").otherwise(None)
).withColumn(
    "wemetrix_ar_pollaplou_dimosio_anentaxtos",
    F.when( F.col("a.Contract_Account_ID") == F.col("b.Contract_Account_ID"), F.col("b.VKONT")).otherwise(None)
).withColumn(
    "wemetrix_pollaplos_type_dimosio_anentaxtos",
    F.when( F.col("a.Contract_Account_ID") == F.col("b.Contract_Account_ID"), "Aνένταχτος").otherwise(None)
).withColumn(
    "wemetrix_dimosio_anentaxtos_afm",
    F.when( F.col("a.Contract_Account_ID") == F.col("b.Contract_Account_ID"), F.col("b.TAXNUM")).otherwise(None)
).drop(
    F.col("b.VKONT"),
    F.col("b.TAXNUM")
).join(
    F.broadcast(df_anentaxtoi_dimos.select(["Contract_Account_ID", "VKONT", "TAXNUM"]).alias("c")),
    on = "Contract_Account_ID",
    how = "left"
).withColumn(
    "Customer_Type_Dimos_anentaxtos",
    F.when( F.col("a.Contract_Account_ID") == F.col("c.Contract_Account_ID"), "Y").otherwise(None)
).withColumn(
    "wemetrix_ar_pollaplou_dimos_anentaxtos",
    F.when( F.col("a.Contract_Account_ID") == F.col("c.Contract_Account_ID"), F.col("c.VKONT")).otherwise(None)
).withColumn(
    "wemetrix_pollaplos_type_dimos_anentaxtos",
    F.when( F.col("a.Contract_Account_ID") == F.col("c.Contract_Account_ID"), "Aνένταχτος").otherwise(None)
).withColumn(
    "wemetrix_dimos_anentaxtos_afm",
    F.when( F.col("a.Contract_Account_ID") == F.col("c.Contract_Account_ID"), F.col("c.TAXNUM")).otherwise(None)
).drop(
    F.col("c.VKONT"),
    F.col("c.TAXNUM")
).join(
    F.broadcast(df_anentaxtoi_idiotis.select(["Contract_Account_ID", "VKONT", "TAXNUM"]).alias("d")),
    on = "Contract_Account_ID",
    how = "left"
).withColumn(
    "Customer_Type_Idiotis_anentaxtos",
    F.when( F.col("a.Contract_Account_ID") == F.col("d.Contract_Account_ID"), "Y").otherwise(None)
).withColumn(
    "wemetrix_ar_pollaplou_idiotis_anentaxtos",
    F.when( F.col("a.Contract_Account_ID") == F.col("d.Contract_Account_ID"), F.col("d.VKONT")).otherwise(None)
).withColumn(
    "wemetrix_pollaplos_type_idiotis_anentaxtos",
    F.when( F.col("a.Contract_Account_ID") == F.col("d.Contract_Account_ID"), "Aνένταχτος").otherwise(None)
).withColumn(
    "wemetrix_idiotis_anentaxtos_afm",
    F.when( F.col("a.Contract_Account_ID") == F.col("d.Contract_Account_ID"), F.col("d.TAXNUM")).otherwise(None)
).drop(
    F.col("d.VKONT"),
    F.col("d.TAXNUM")
).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{pollaplos_two}.parquet")
print("Checkpoint 03: OK")

df_pollaploi = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{pollaplos_two}.parquet")

# Concatenate columns of ar_pollaplos and types for the three different customer types [ΔΗΜΟΣΙΟ, ΔΗΜΟΣ, ΙΔΙΩΤΗΣ]
df_pollaploi = df_pollaploi.withColumn(
    "wemetrix_ar_pollaplou",
    F.when(
        F.col("wemetrix_ar_pollaplou_dimosio_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimos_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_idiotis_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimosio_anentaxtos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimos_anentaxtos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_idiotis_anentaxtos").isNotNull()
        ,
        F.substring(F.concat_ws(
            "",
            F.col("wemetrix_ar_pollaplou_dimosio_entagmenos"),
            F.col("wemetrix_ar_pollaplou_dimos_entagmenos"),
            F.col("wemetrix_ar_pollaplou_idiotis_entagmenos"),
            F.col("wemetrix_ar_pollaplou_dimosio_anentaxtos"),
            F.col("wemetrix_ar_pollaplou_dimos_anentaxtos"),
            F.col("wemetrix_ar_pollaplou_idiotis_anentaxtos"),
        ), 1, 12)
    )
).withColumn(
    "wemetrix_pollaplos_type",
    F.when(
        F.col("wemetrix_ar_pollaplou_dimosio_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimos_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_idiotis_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimosio_anentaxtos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimos_anentaxtos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_idiotis_anentaxtos").isNotNull()
        ,
        F.substring(F.concat_ws(
            "",
            F.col("wemetrix_pollaplos_type_dimosio_entagmenos"),
            F.col("wemetrix_pollaplos_type_dimos_entagmenos"),
            F.col("wemetrix_pollaplos_type_idiotis_entagmenos"),
            F.col("wemetrix_pollaplos_type_dimosio_anentaxtos"),
            F.col("wemetrix_pollaplos_type_dimos_anentaxtos"),
            F.col("wemetrix_pollaplos_type_idiotis_anentaxtos"),
        ), 1, 10)
    )
).withColumn(
    "wemetrix_ar_pollaplou_all_concat",
    F.when(
        F.col("wemetrix_ar_pollaplou_dimosio_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimos_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_idiotis_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimosio_anentaxtos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimos_anentaxtos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_idiotis_anentaxtos").isNotNull()
        ,
        F.concat_ws(
            ",",
            F.col("wemetrix_ar_pollaplou_dimosio_entagmenos"),
            F.col("wemetrix_ar_pollaplou_dimos_entagmenos"),
            F.col("wemetrix_ar_pollaplou_idiotis_entagmenos"),
            F.col("wemetrix_ar_pollaplou_dimosio_anentaxtos"),
            F.col("wemetrix_ar_pollaplou_dimos_anentaxtos"),
            F.col("wemetrix_ar_pollaplou_idiotis_anentaxtos"),
        )
    )
).withColumn(
    "wemetrix_pollaplos_type_all_concat",
    F.when(
        F.col("wemetrix_ar_pollaplou_dimosio_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimos_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_idiotis_entagmenos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimosio_anentaxtos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_dimos_anentaxtos").isNotNull() |
        F.col("wemetrix_ar_pollaplou_idiotis_anentaxtos").isNotNull()
        ,
        F.concat_ws(
            ",",
            F.col("wemetrix_pollaplos_type_dimosio_entagmenos"),
            F.col("wemetrix_pollaplos_type_dimos_entagmenos"),
            F.col("wemetrix_pollaplos_type_idiotis_entagmenos"),
            F.col("wemetrix_pollaplos_type_dimosio_anentaxtos"),
            F.col("wemetrix_pollaplos_type_dimos_anentaxtos"),
            F.col("wemetrix_pollaplos_type_idiotis_anentaxtos"),
        )
    )
).withColumn(
    "Customer_Type_Dimosio",
    F.when(
        F.col("Customer_Type_Dimosio_anentaxtos").isNotNull() |
        F.col("Customer_Type_Dimosio_entagmenos").isNotNull()
        ,
        F.substring(F.concat_ws(
            "",
            F.col("Customer_Type_Dimosio_entagmenos"),
            F.col("Customer_Type_Dimosio_anentaxtos")
        ), 1, 1)
    )
).withColumn(
    "Customer_Type_Dimos",
    F.when(
        F.col("Customer_Type_Dimos_anentaxtos").isNotNull() |
        F.col("Customer_Type_Dimos_entagmenos").isNotNull()
        ,
        F.substring(F.concat_ws(
            "",
            F.col("Customer_Type_Dimos_entagmenos"),
            F.col("Customer_Type_Dimos_anentaxtos")
        ), 1, 1)
    )
).withColumn(
    "Customer_Type_Idiotis",
    F.when(
        F.col("Customer_Type_Idiotis_anentaxtos").isNotNull() |
        F.col("Customer_Type_Idiotis_entagmenos").isNotNull()
        ,
        F.substring(F.concat_ws(
            "",
            F.col("Customer_Type_Idiotis_entagmenos"),
            F.col("Customer_Type_Idiotis_anentaxtos")
        ), 1, 1)
    )
).withColumn(
    "Customer_Type_entagmenos_all_concat",
    F.when(
        F.col("Customer_Type_Dimosio_entagmenos").isNotNull() |
        F.col("Customer_Type_Dimos_entagmenos").isNotNull() |
        F.col("Customer_Type_Idiotis_entagmenos").isNotNull()
        ,
        F.concat_ws(
            ",",
            F.col("Customer_Type_Dimosio_entagmenos"),
            F.col("Customer_Type_Dimos_entagmenos"),
            F.col("Customer_Type_Idiotis_entagmenos")
        )
    )
).withColumn(
    "Customer_Type_anentaxtos_all_concat",
    F.when(
        F.col("Customer_Type_Dimosio_anentaxtos").isNotNull() |
        F.col("Customer_Type_Dimos_anentaxtos").isNotNull() |
        F.col("Customer_Type_Idiotis_anentaxtos").isNotNull()
        ,
        F.concat_ws(
            ",",
            F.col("Customer_Type_Dimosio_anentaxtos"),
            F.col("Customer_Type_Dimos_anentaxtos"),
            F.col("Customer_Type_Idiotis_anentaxtos")
        )
    )
).withColumn(
    "wemetrix_anentaxtos_afm",
    F.when(
        F.col("wemetrix_dimosio_anentaxtos_afm").isNotNull() |
        F.col("wemetrix_dimos_anentaxtos_afm").isNotNull() |
        F.col("wemetrix_idiotis_anentaxtos_afm").isNotNull()
        ,
        F.substring(F.concat_ws(
            "",
            F.col("wemetrix_dimosio_anentaxtos_afm"),
            F.col("wemetrix_dimos_anentaxtos_afm"),
            F.col("wemetrix_idiotis_anentaxtos_afm")
        ), 1, 9)
    )
).withColumn(
    "wemetrix_anentaxtos_afm_all_concat",
    F.when(
        F.col("wemetrix_dimosio_anentaxtos_afm").isNotNull() |
        F.col("wemetrix_dimos_anentaxtos_afm").isNotNull() |
        F.col("wemetrix_idiotis_anentaxtos_afm").isNotNull()
        ,
        F.concat_ws(
            ",",
            F.col("wemetrix_dimosio_anentaxtos_afm"),
            F.col("wemetrix_dimos_anentaxtos_afm"),
            F.col("wemetrix_idiotis_anentaxtos_afm")
        )
    )
).write.mode("overwrite").parquet(f"dbfs:/FileStore/wemetrix/{pollaplos_three}.parquet")
print("Checkpoint 04: OK")

df_pollaploi = spark.read.parquet(f"dbfs:/FileStore/wemetrix/{pollaplos_three}.parquet")

# Add Excel columns from Kallikratis dimoi dataset.
df_pollaploi = df_pollaploi.alias("a").join(
    df_dimoi_kallikrati.select(
        [
            "`LOG. SYMB. SAP`",
            "DIMOS/KOINOTITA ERMI",
            "`KOD.DIMOU KALLIKRATI`",
            "DIMOS KALLIKRATI / KLEISTHENI"
        ]).alias("b"),
    df_pollaploi["Ar_Pollaplou"] == df_dimoi_kallikrati["`LOG. SYMB. SAP`"],
    how = "left"
).withColumnRenamed(
    "LOG. SYMB. SAP", "LOG_SYMB_SAP_"
).withColumnRenamed(
    "DIMOS/KOINOTITA ERMI", "DIMOS_KOINOTITA_ERMI_"
).withColumnRenamed(
    "KOD.DIMOU KALLIKRATI", "KODIKOS_DIMOU_KALLIKRATI_"
).withColumnRenamed(
    "DIMOS KALLIKRATI / KLEISTHENI", "DIMOS_KALLIKRATI_KLEISTHENI_"
)
print("Checkpoint 05: OK")

ar_pollaplou_mpampa = df_mpampades.select(["VKONT"]).distinct()
ca_mpampa = ar_pollaplou_mpampa.join(
    df_pollaploi.select(["Contract_Account_ID", "Ar_Pollaplou"]),
    ar_pollaplou_mpampa["VKONT"] == df_pollaploi["Ar_Pollaplou"],
    how = "inner"
).dropDuplicates().drop(F.col("Ar_Pollaplou"))

# Υπήρχαν πάρα πολλοί μπαμπάδες με πολλαπλά Contracts IDs. Οπότε επιλέξαμε για κάθε μπαμπά το maximum CA για να διαμοφώσει τον αριθμό του group.
# Θα πρέπει να υπάρχει ως ξεχωριστή κολώνα στον πίνακα των ΜΠΑΜΠΑΔΩΝ το contract account id. Υπάρχει τρόπος να το αντλήσουμε;
ca_mpampa = ca_mpampa.groupBy("VKONT").agg(F.max("Contract_Account_ID").alias("max_ca"))

df_pollaploi = df_pollaploi.alias("a").join(
    ca_mpampa.alias("b"),
    df_pollaploi["wemetrix_ar_pollaplou"] == ca_mpampa["VKONT"],
    how = "left"
).withColumn(
    "wemetrix_pollaplos_group",
    F.when( F.col("a.wemetrix_ar_pollaplou")==F.col("b.VKONT"), F.col("b.max_ca") ).otherwise(None)
).drop(F.col("b.VKONT"), F.col("b.max_ca"))
print("Checkpoint 06: OK")

df_pollaploi = df_pollaploi.alias("a").join(
    df_multiple_pollaploi.alias("b"),
    df_pollaploi["wemetrix_ar_pollaplou"] == df_multiple_pollaploi["VKONT"],
    how = "left"
).withColumn(
    "wemetrix_multiple_pollaplos",
    F.when( F.col("a.wemetrix_ar_pollaplou")==F.col("b.VKONT"), F.col("b.group_number") )
).drop(F.col("b.VKONT"), F.col("b.group_number"))
print("Checkpoint 07: OK")

# COMMAND ----------

try:
    assert df_pollaploi.count() == spark.sql(f"SELECT * FROM {input_table}").count(), "Check the rows in the final dataframe because it contains duplicate rows"
    print("OK: Balanced output")
except AssertionError as e:
    print("Imbalanced output: ", e)

# COMMAND ----------

cols_all = ["SOURCE", "Contract_Account_ID", "PrCompany_Name"]
print(f"Writing output table (alias: {output_table}) with pollaplous...")
df_pollaploi.select(
    [x for x in cols_all] + \
    [
        "wemetrix_ar_pollaplou",
        "wemetrix_pollaplos_type",
        "wemetrix_anentaxtos_afm",
        "Customer_Type_Dimosio",
        "Customer_Type_Dimos",
        "Customer_Type_Idiotis",
        "LOG_SYMB_SAP_",
        "DIMOS_KOINOTITA_ERMI_",
        "KODIKOS_DIMOU_KALLIKRATI_",
        "DIMOS_KALLIKRATI_KLEISTHENI_",
        "wemetrix_ar_pollaplou_all_concat",
        "wemetrix_pollaplos_type_all_concat",
        "wemetrix_pollaplos_group",
        "wemetrix_multiple_pollaplos",
    ]
).write.mode("overwrite").saveAsTable(output_table)
print("Writing COMPLETED...")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ##### Απορίες και ευρήματα
# MAGIC ---------------------------------------
# MAGIC
# MAGIC ##### Πίνακες
# MAGIC output_table = "wemetrix.foursource_gr" <br>
# MAGIC df_gr_checks = spark.sql(f"SELECT * FROM {output_table}") <br>
# MAGIC input_table = "wemetrix.foursource"<br>
# MAGIC df_dimoi_kallikrati = spark.sql(f"SELECT * FROM wemetrix.dimoi_kallikrati")
# MAGIC
# MAGIC ##### ΙΔΙΩΤΕΣ
# MAGIC ---------------------
# MAGIC
# MAGIC ##### ΔΗΜΟΙ
# MAGIC ---------------------
# MAGIC (1) Πίνακας συχνοτήτων των ΑΦΜ ανά ΔΗΜΟ για τον έλεγχο σχέσης 1 προς 1.
# MAGIC ```
# MAGIC df_dimoi_kallikrati.groupBy("AFM").agg(F.countDistinct("`DIMOS KALLIKRATI / KLEISTHENI`").alias("frequency")).filter(F.col("frequency")>1).show()
# MAGIC ```
# MAGIC
# MAGIC (2) Βρέθηκε 1 ΑΦΜ που είναι κοινό σε 2 ΔΗΜΟΥΣ. ΔΗΜΟΣ ΒΕΛΒΕΝΤΟΥ και ΔΗΜΟΣ ΣΕΡΒΙΩΝ έχουν κοινό ΑΦΜ=996877610.
# MAGIC ```
# MAGIC df_dimoi_kallikrati.filter(F.col("AFM")==996877610).show()
# MAGIC ```
# MAGIC
# MAGIC (3) Υπάρχει ΔΗΜΟΣ που έχει 2 ξεχωριστά ΑΦΜ. ΔΗΜΟΣ: ΔΗΜΟΣ ΣΕΡΒΙΩΝ
# MAGIC ```
# MAGIC dimoi_names = df_dimoi_kallikrati.select(["DIMOS KALLIKRATI / KLEISTHENI", "AFM"]).distinct()
# MAGIC dimoi_names.filter(F.col("DIMOS KALLIKRATI / KLEISTHENI")=="ΔΗΜΟΣ ΣΕΡΒΙΩΝ").show()
# MAGIC ```
# MAGIC
# MAGIC (4) Υπάρχουν εγγραφές που ενώ ανήκουν σε έναν ΔΗΜΟ, δεν εμφανίζεται ο ΔΗΜΟΣ ΚΑΛΛΙΚΡΑΤΗ στην κολώνα "DIMOS_KALLIKRATI_KLEISTHENI" καθώς η τιμή του Αρ. Πολλαπλού είναι κενή ενώ η τιμή της κολώνας "LOG. SYMB. SAP" έχει τιμή.
# MAGIC Παράδειγμα αποτελεί ο ΔΗΜΟΣ Αγ. Παρασκευής για το ΑΦΜ = 90085626
# MAGIC ```
# MAGIC df_gr_checks.select(
# MAGIC     [
# MAGIC         "GR_Customer_Type",
# MAGIC         "wemetrix_gr_group",
# MAGIC         "ClVAT_IIS",
# MAGIC         "GR_VAT_ID",
# MAGIC         "Contract_Account_ID",
# MAGIC         "B2B_Company_Name",
# MAGIC         "Ar_Pollaplou",
# MAGIC         "Customer_Type_Dimosio",
# MAGIC         "Customer_Type_Dimos",
# MAGIC         "DIMOS_KALLIKRATI_KLEISTHENI",
# MAGIC         "wemetrix_ar_pollaplou_dimoi",
# MAGIC         "wemetrix_pollaplos_type_dimoi"
# MAGIC     ]
# MAGIC ).filter( (F.col("ClVAT_IIS")==90085626) ).display()
# MAGIC df_dimoi_kallikrati.filter(F.col("AFM")==90085626).show()
# MAGIC ```
# MAGIC
# MAGIC (5) Υπάρχει περίπτωση εγγραφής (Contract Account) που ανήκει και στους ΙΔΙΩΤΕΣ Και στους ΔΗΜΟΥΣ ως ανένταχτος
# MAGIC ```
# MAGIC df_pollaploi.select([
# MAGIC     "Contract_Account_ID",
# MAGIC     "ClVAT_IIS",
# MAGIC     "Ar_Pollaplou",
# MAGIC     
# MAGIC     "wemetrix_ar_pollaplou_dimosio_entagmenos",
# MAGIC     "wemetrix_pollaplos_type_dimosio_entagmenos",
# MAGIC     "Customer_Type_Dimosio_entagmenos",
# MAGIC
# MAGIC     "wemetrix_ar_pollaplou_dimosio_anentaxtos",
# MAGIC     "wemetrix_pollaplos_type_dimosio_anentaxtos",
# MAGIC     "Customer_Type_Dimosio_anentaxtos",
# MAGIC
# MAGIC     "wemetrix_ar_pollaplou_dimos_entagmenos",
# MAGIC     "wemetrix_pollaplos_type_dimos_entagmenos",
# MAGIC     "Customer_Type_Dimos_entagmenos",
# MAGIC
# MAGIC     "wemetrix_ar_pollaplou_dimos_anentaxtos",
# MAGIC     "wemetrix_pollaplos_type_dimos_anentaxtos",
# MAGIC     "Customer_Type_Dimos_anentaxtos",
# MAGIC
# MAGIC     "wemetrix_ar_pollaplou_idiotis_entagmenos",
# MAGIC     "wemetrix_pollaplos_type_idiotis_entagmenos",
# MAGIC     "Customer_Type_Idiotis_entagmenos",
# MAGIC
# MAGIC     "wemetrix_ar_pollaplou_idiotis_anentaxtos",
# MAGIC     "wemetrix_pollaplos_type_idiotis_anentaxtos",
# MAGIC     "Customer_Type_Idiotis_anentaxtos",
# MAGIC
# MAGIC     "wemetrix_ar_pollaplou",
# MAGIC     "wemetrix_pollaplos_type",
# MAGIC     "wemetrix_ar_pollaplou_all_concat",
# MAGIC     "wemetrix_pollaplos_type_all_concat",
# MAGIC
# MAGIC     "Customer_Type_Dimosio",
# MAGIC     "Customer_Type_Dimos",
# MAGIC     "Customer_Type_Idiotis",
# MAGIC
# MAGIC     "Customer_Type_entagmenos_all_concat",
# MAGIC     "Customer_Type_anentaxtos_all_concat",
# MAGIC
# MAGIC     "wemetrix_pollaplos_group",
# MAGIC     "wemetrix_anentaxtos_afm"
# MAGIC ]).filter(F.col("Contract_Account_ID")==300012680341).display()
# MAGIC ```