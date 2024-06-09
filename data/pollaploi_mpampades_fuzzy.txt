# Databricks notebook source
#import pre-build python modules
import pandas as pd
import os
from pyspark.sql.types import IntegerType, StringType, LongType, DoubleType
from pyspark.sql import Window
from pyspark.sql.functions import udf
import pyspark.sql.functions as F
import time
import datetime

# COMMAND ----------

def add_similarity_scores(df, c1):
    c2 = c1+"_2"
    df = (df
          .withColumn(c1, F.when(F.col(c1).isNull(), " ").otherwise(F.trim(F.col(c1))))
          .withColumn(c2, F.when(F.col(c2).isNull(), " ").otherwise(F.trim(F.col(c2))))
          .withColumn(f"length_{c1}", F.length(F.col(c1)))
                .withColumn(f"length_{c2}", F.length(F.col(c2)))
                .withColumn(f"max_str_length_{c1}_{c2}", F.when(F.col(f"length_{c1}") > F.col(f"length_{c2}"), F.col(f"length_{c1}"))
                            .otherwise(F.col(f"length_{c2}")))
                .withColumn(f"levenshtein_distance_{c1}", F.levenshtein(c1, c2))
                .withColumn(f"matching_ratio_{c1}", F.when(F.col(f"max_str_length_{c1}_{c2}") > 0, 1 - (F.col(f"levenshtein_distance_{c1}") / F.col(f"max_str_length_{c1}_{c2}"))) )
                .drop(f"length_{c1}", f"length_{c2}", f"max_str_length_{c1}_{c2}"))
    return df

# COMMAND ----------

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
df_dimoi_kallikrati = spark.sql(f"SELECT * FROM wemetrix.dimoi_kallikrati")

# ΔΗΜΟΣΙΟ (ΜΠΑΜΠΑΔΕΣ)
df_dimosio = df_mpampades.filter(F.substring(F.col("vbund"), 2,1)==4)
# buffer_column = "DIMOS/KOINOTITA ERMI"
buffer_column = "`LOG. SYMB. SAP`"
dimoi_names = df_dimoi_kallikrati.select(buffer_column).distinct()
# df_dimosio = df_dimosio.join(dimoi_names, df_dimosio["name_org1"] == dimoi_names[buffer_column], how = "left_anti")
df_dimosio = df_dimosio.join(dimoi_names, df_dimosio["VKONT"] == dimoi_names[buffer_column], how = "left_anti")
print("ΔΗΜΟΣΙΟ ΜΠΑΜΠΑΔΕΣ: ", df_dimosio.count()) #342

# ΔΗΜΟΣ (ΜΠΑΜΠΑΔΕΣ)
df_dimos = df_mpampades.join(dimoi_names, df_mpampades["VKONT"] == dimoi_names[buffer_column], how = "inner").drop(F.col(buffer_column))
print("ΔΗΜΟΣ ΜΠΑΜΠΑΔΕΣ: ", df_dimos.count()) #6034

# ΙΔΙΩΤΗΣ (ΜΠΑΜΠΑΔΕΣ)
idiotes_names = df_dimosio.select(["VKONT"]).union(df_dimos.select(["VKONT"]))
df_idiotis = df_mpampades.join(idiotes_names, on = "VKONT", how = "left_anti")
print("ΙΔΙΩΤΗΣ ΜΠΑΜΠΑΔΕΣ: ", df_idiotis.count()) #79

# COMMAND ----------

df_mpampades_fuzzy = df_dimosio.union(df_idiotis).filter(F.trim(F.col("name_org1")) != '')
df_mpampades_fuzzy.show(10, truncate=False)

# COMMAND ----------

df_cross = df_mpampades_fuzzy.select("VKONT","name_org1").crossJoin(df_mpampades_fuzzy.select("VKONT","name_org1")).toDF(*["VKONT","name_org1", "VKONT_2", "name_org1_2"])
df_cross = (add_similarity_scores(df_cross, "name_org1")
            .withColumnRenamed("matching_ratio_name_org1", "matching_ratio")
            .filter(F.col("matching_ratio") > 0.5))
df_cross.orderBy("name_org1").display()

# COMMAND ----------

# Collect unique sets of indexes (SOURCE, CA_id)
window_group_index = Window.partitionBy().orderBy("group_index_list")
df_groups = (df_cross.groupBy("VKONT")
                .agg(F.sort_array(F.collect_set("VKONT_2")).alias("group_index_list"),
                        F.avg(F.col("matching_ratio")).alias("avg_group_matching_ratio"))
                .select(["group_index_list", "avg_group_matching_ratio"])
                .dropDuplicates(["group_index_list"]))

# Filter sets of 1
df_groups = (df_groups.withColumn("group_number", F.row_number().over(window_group_index))
            .withColumn("group_size", F.size("group_index_list"))
            .withColumn("max_index", F.array_max("group_index_list"))
            .withColumn("min_index", F.array_min("group_index_list"))
            .filter(F.col("group_size") > 1))

# If record is found in multiple sets, pick the one with the highest average matching ratio and group size and use min max source-ca as tie breakers
window_group_rank = Window.partitionBy("index_cols").orderBy(F.col("avg_group_matching_ratio").desc(), F.col("group_size").desc(), F.col("max_index").desc(), F.col("min_index"))
df_groups = (df_groups
.withColumn("index_cols", F.explode(F.col("group_index_list")))
.select(["index_cols", "group_number", "group_size", "avg_group_matching_ratio", "max_index", "min_index"])
.withColumn("group_match_rank", F.rank().over(window_group_rank))
.filter(F.col("group_match_rank") == 1)
.groupBy(["group_number"]).agg(F.collect_list("index_cols").alias("index_cols"))
.withColumn("VKONT", F.explode("index_cols"))
.dropDuplicates(["VKONT"]))

# Dropping records whose best group wasn't selected by any other record
df_single_groups = df_groups.groupBy("group_number").count().filter(F.col("count")==1).withColumn("single_index_group", F.lit(1))
df_groups = df_groups.join(df_single_groups, on=["group_number"], how="left").filter(F.col("single_index_group").isNull()).drop("single_index_group")

df_groups = df_groups.select("group_number", "VKONT")
df_groups.write.mode("overwrite").saveAsTable("wemetrix.multiple_pollaploi") # Write to HDFS
df_groups.orderBy("group_number").display()

# COMMAND ----------

df_afm_fuzzy = spark.sql(f"SELECT * FROM wemetrix.df_afm_fuzzy").filter(F.trim(F.col("PrCompany_Name")) != '')
df_afm_fuzzy.filter(F.col("wemetrix_anentaxtos_afm") == 997908926).display()
# Όπως φαίνεται στο παράδειγμα υπάρχουν Company_Names στο ίδιο ΑΦΜ που δεν ταιριάζουν όπως πχ ΚΛΗΡΟΔΟΤΗΜΑ ΕΛΕΝΗΣ ΖΩΓΡΑΦΟΥ, ΔΗΜΟΣ ΙΩΑΝΝΙΤΩΝ.
# Να αναγνωρίσουμε αυτές τις περιπτώσεις και να τις μαρκάρουμε ως outliers

# COMMAND ----------

df_cross = (df_afm_fuzzy.select("Contract_Account_ID", "PrCompany_Name", "wemetrix_anentaxtos_afm")
            .join(df_afm_fuzzy.select("Contract_Account_ID", "PrCompany_Name", "wemetrix_anentaxtos_afm"), on = ["wemetrix_anentaxtos_afm"])
                .toDF(*["wemetrix_anentaxtos_afm", "Contract_Account_ID", "PrCompany_Name", "Contract_Account_ID_2", "PrCompany_Name_2"]))
df_cross = (add_similarity_scores(df_cross, "PrCompany_Name")
            .withColumnRenamed("matching_ratio_PrCompany_Name", "matching_ratio")
            .filter(F.col("matching_ratio") > 0.8))
df_cross.orderBy("PrCompany_Name").display()

# COMMAND ----------

# Collect unique sets of indexes (SOURCE, CA_id)
window_group_index = Window.partitionBy().orderBy("group_index_list")
df_groups = (df_cross.groupBy("Contract_Account_ID")
                .agg(F.sort_array(F.collect_set("Contract_Account_ID_2")).alias("group_index_list"),
                        F.avg(F.col("matching_ratio")).alias("avg_group_matching_ratio"))
                .select(["group_index_list", "avg_group_matching_ratio"])
                .dropDuplicates(["group_index_list"]))

# Filter sets of 1
df_groups = (df_groups.withColumn("group_number", F.row_number().over(window_group_index))
            .withColumn("group_size", F.size("group_index_list"))
            .withColumn("max_index", F.array_max("group_index_list"))
            .withColumn("min_index", F.array_min("group_index_list"))
            .filter(F.col("group_size") > 1))

# If record is found in multiple sets, pick the one with the highest average matching ratio and group size and use min max source-ca as tie breakers
window_group_rank = Window.partitionBy("index_cols").orderBy(F.col("avg_group_matching_ratio").desc(), F.col("group_size").desc(), F.col("max_index").desc(), F.col("min_index"))
df_groups = (df_groups
.withColumn("index_cols", F.explode(F.col("group_index_list")))
.select(["index_cols", "group_number", "group_size", "avg_group_matching_ratio", "max_index", "min_index"])
.withColumn("group_match_rank", F.rank().over(window_group_rank))
.filter(F.col("group_match_rank") == 1)
.groupBy(["group_number"]).agg(F.collect_list("index_cols").alias("index_cols"))
.withColumn("Contract_Account_ID", F.explode("index_cols"))
.dropDuplicates(["Contract_Account_ID"]))

# Dropping records whose best group wasn't selected by any other record
df_single_groups = df_groups.groupBy("group_number").count().filter(F.col("count")==1).withColumn("single_index_group", F.lit(1))
df_groups = df_groups.join(df_single_groups, on=["group_number"], how="left").filter(F.col("single_index_group").isNull()).drop("single_index_group")

df_groups = df_groups.select("group_number", "Contract_Account_ID")
df_groups.orderBy("group_number").display()

# COMMAND ----------

df_groups.groupBy("group_number").count().display()

# COMMAND ----------

