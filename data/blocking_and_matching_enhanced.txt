# Databricks notebook source
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, FloatType, DoubleType
from pyspark.sql import Window
from pyspark.sql.functions import udf
import pyspark.sql.functions as F

# COMMAND ----------

dbutils.widgets.text("input_table",  "wemetrix.foursourcedelta")
delta_table = dbutils.widgets.get("input_table")

dbutils.widgets.text("runtag",  "")
runtag = dbutils.widgets.get("runtag")

dbutils.widgets.text("bm_results_table",  "wemetrix.bmresults")
bm_results_table = dbutils.widgets.get("bm_results_table") + runtag

bm_results_table

# COMMAND ----------

# Define the UDF function
def calculate_avg_char_length(*cols):
    non_empty_cols = [colname for colname in cols if colname is not None and str(colname).strip() != ""]
    empty_cols = [colname for colname in cols if colname is None or str(colname).strip() == ""]
    num_empty_cols = len(empty_cols)
    num_non_empty_cols = len(non_empty_cols)
    total_length = int(sum(len(str(colname)) if colname in non_empty_cols else 0 for colname in cols))
    avg_chars = float(total_length)/num_non_empty_cols if num_non_empty_cols > 0 else 0.0
    return num_non_empty_cols, num_empty_cols, total_length, avg_chars

# Register the UDF function
schema = StructType([
    StructField("filled_columns", IntegerType(), False),
    StructField("empty_columns", IntegerType(), False),
    StructField("chars_len", IntegerType(), False),
    StructField("avg_chars_len", FloatType(), False)
])
udf_calculate_avg_char_length = udf(calculate_avg_char_length, schema)

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

def execute_pass(df_customers, pass_number, blocking_cols, matching_cols, category_col, category_col_exclude, matching_filter_statement = "", index_cols = ["SOURCE", "Contract_Account_ID"]):

    if pass_number == 1:
        df_customers = (df_customers
                        .withColumn("wemetrix_mp_customer_code", F.lit(None))
                        .withColumn("wemetrix_group_number", F.lit(None))
                        .withColumn("wemetrix_pass", F.lit(None))
                        .withColumn("wemetrix_match_type", F.lit(None))
                        .withColumn("wemetrix_matching_ratio", F.lit(None)) )
        
    lektika_cols = [x for x in ["EnPrFirst_Name", "EnPrLast_Name", "EnPrFather_Name", "EnPrCompany_Name"] if x not in blocking_cols] # "EnPrCompany_Name"

    df_pass = ( df_customers
               .filter((F.col("wemetrix_pass").isNull()) | (F.col("wemetrix_match_type").isin("MP")) )
               .filter( (~F.col(category_col).isin(category_col_exclude)) | (F.col(category_col).isNull()) )
               .select(index_cols + blocking_cols + ["filled_columns", "PrCustomer_Type_IIS", "wemetrix_match_type"] + list(set(matching_cols + lektika_cols))) )
    
    for bc in blocking_cols:
        df_pass = df_pass.filter( (F.trim(F.col(bc)) != "" ) & (F.col(bc).isNotNull() ) )
    print(f"{df_pass.count()=}")

    # Column list with _2 for every duplicate col after df join with itself
    new_columns = df_pass.columns*2
    for i in range(len(df_pass.columns)*2):
        if i < len(df_pass.columns):
            new_columns[i + int(len(df_pass.columns))] = df_pass.columns[i] + "_2"

    cols = blocking_cols + [x for x in new_columns if not any(bc in x for bc in blocking_cols)]
    df_cross = (df_pass.join(df_pass, on=blocking_cols).toDF(*cols))

    for comp_col in list(set(matching_cols + lektika_cols)):
        df_cross = add_similarity_scores(df_cross, comp_col)

    for extra_comp_col in ["ClVAT_IIS", "PrCustomer_Type_IIS"]:
        if (extra_comp_col not in blocking_cols + matching_cols):
            df_cross = add_similarity_scores(df_cross, extra_comp_col)

    df_cross.createOrReplaceTempView("df_cross")

    # Add "hard" rules and filters from matching columns
    add_vat_clause = "( ( levenshtein_distance_ClVAT_IIS <= 1 ) OR ( ClVAT_IIS_2 IS NULL OR TRIM(ClVAT_IIS_2) = '' ) ) AND ( ClVAT_IIS IS NOT NULL AND TRIM(ClVAT_IIS) != '' )" if "ClVAT_IIS" not in blocking_cols else "" 
    add_lektika_clause = "(" + " AND ".join(f"(matching_ratio_{x} > 0.7 OR {x} IS NULL OR TRIM({x}) = '' OR {x}_2 IS NULL OR TRIM({x}_2) = '')" for x in lektika_cols if x not in blocking_cols) + ")"
    add_lektika_clause_general = "(" + " OR ".join(f" ( ( {x} IS NOT NULL AND TRIM({x})!= '' )  AND ( {x}_2 IS NOT NULL AND TRIM({x}_2) != '' ) ) " for x in lektika_cols if x not in blocking_cols) + ")"

    add_cust_clause =  "( (matching_ratio_PrCustomer_Type_IIS = 1) OR ( PrCustomer_Type_IIS_2 IS NULL OR TRIM(PrCustomer_Type_IIS_2) = '' ) ) AND ( PrCustomer_Type_IIS IS NOT NULL AND TRIM(PrCustomer_Type_IIS) != '' )"
    other_comp_cols = [x for x in matching_cols if x not in ["ClVAT_IIS", "PrCustomer_Type_IIS"]]
    add_other_comparisons = f'( {" OR ".join([f"matching_ratio_{x} > 0.90" for x in other_comp_cols ])} )'

    filters_list = [add_lektika_clause, add_lektika_clause_general]
    if "PrCustomer_Type_IIS" not in blocking_cols: filters_list.append(add_cust_clause)
    if add_vat_clause != "": filters_list.append(add_vat_clause)
    if len(other_comp_cols) > 0: filters_list.append(add_other_comparisons)

    concat_filters = " AND ".join(filters_list)
    matching_filter_query = f'SELECT * FROM df_cross WHERE {concat_filters}'

    print(matching_filter_query)
    df_cross = spark.sql(matching_filter_query)
    df_cross.createOrReplaceTempView("df_cross")
    df_cross = spark.sql(f'SELECT *, ( {" + ".join([f"matching_ratio_{x}" for x in matching_cols])} ) / {len(matching_cols)} matching_ratio FROM df_cross')

    # # Get subgroups

    # Collect unique sets of indexes (SOURCE, CA_id)
    window_group_index = Window.partitionBy().orderBy("group_index_list")
    df_groups = (df_cross.groupBy(index_cols)
                    .agg(F.sort_array(F.collect_set( F.concat(F.col("SOURCE_2"), F.lit("-"), F.col("Contract_Account_ID_2")) )).alias("group_index_list"),
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
    .withColumn("index_cols", F.explode("index_cols"))
    .withColumn("SOURCE", F.split("index_cols", "-")[0])
    .withColumn("Contract_Account_ID", F.split("index_cols", "-")[1])
    .dropDuplicates(index_cols))

    # Dropping records whose best group wasn't selected by any other record
    df_single_groups = df_groups.groupBy("group_number").count().filter(F.col("count")==1).withColumn("single_index_group", F.lit(1))
    df_groups = df_groups.join(df_single_groups, on=["group_number"], how="left").filter(F.col("single_index_group").isNull()).drop("single_index_group")

    # Add group number for each record of the initial dataset
    df_pass = df_pass.join(df_groups.drop("index_cols"), on=index_cols)
    new_columns = df_pass.columns*2
    for i in range(len(df_pass.columns)*2):
        if i < len(df_pass.columns):
            new_columns[i + int(len(df_pass.columns))] = df_pass.columns[i] + "_2"

    # Join the initial dataset to itself for records that are on the same 'block' and 'group_number'
    cols = ["group_number"] + [x for x in new_columns if not any(bc in x for bc in ["group_number"])]
    df_cross = (df_pass.join(df_pass, on=["group_number"]).toDF(*cols))
    for comp_col in matching_cols:
        df_cross = add_similarity_scores(df_cross, comp_col)

    df_cross.createOrReplaceTempView("df_cross")

    block_query = f"""SELECT {", ".join(["group_number"] + index_cols)},
                            {", ".join([f'AVG(matching_ratio_{x}) matching_ratio_{x}' for x in matching_cols])},
                            {", ".join([f'AVG(levenshtein_distance_{x}) levenshtein_distance_{x}' for x in matching_cols])},
                            MAX(filled_columns) filled_columns,
                            MAX(ClVAT_IIS) ClVAT_IIS,
                            COUNT(*) count
                        FROM df_cross GROUP BY {", ".join( ["group_number"] + index_cols)}"""


    spark.sql(block_query).createOrReplaceTempView("df_blocks")

    block_query_add_avg = f"""SELECT *, ( {" + ".join([f"matching_ratio_{x}" for x in matching_cols])} ) / {len(matching_cols)} matching_ratio,
                                    ( { " + ".join([f"levenshtein_distance_{x}" for x in matching_cols]) } ) / {len(matching_cols)} levenshtein_distance
                                FROM df_blocks"""

    df_blocks = spark.sql(block_query_add_avg)

    # Maintain group MP Customer Code
    df_blocks_keep_mp = (df_blocks.select("group_number", "SOURCE", "Contract_Account_ID")
                     .join(df_customers.filter(F.col("wemetrix_match_type")=="MP").select("wemetrix_mp_customer_code", "SOURCE", "Contract_Account_ID"), 
                                    on=["SOURCE", "Contract_Account_ID"], 
                                    how="inner") )
    df_blocks_keep_mp = df_blocks_keep_mp.join(df_blocks_keep_mp.groupBy("group_number").count().filter(F.col("count")==1).select("group_number"), on=["group_number"], how="inner")
    df_blocks = df_blocks.join(df_blocks_keep_mp.select("group_number", "wemetrix_mp_customer_code").dropDuplicates(), on=["group_number"], how="left")

    # Create MP for groups without one
    mr_window = Window.partitionBy(["group_number"]).orderBy(F.col("matching_ratio").desc(), F.col("filled_columns").desc(), F.col("Contract_Account_ID").desc())
    df_master_record = (df_blocks
                        .filter(F.col("wemetrix_mp_customer_code").isNull())
                        .filter(( F.col("SOURCE") == "SAP" ) & ( F.col("ClVAT_IIS").isNotNull() ) & ( F.trim(F.col("ClVAT_IIS")) != "") )
                            .withColumn("master_record_rank", F.rank().over(mr_window))
                            .filter(F.col("master_record_rank")==1)
                            .withColumn("wemetrix_mp_customer_code_new", F.col("Contract_Account_ID"))
                        .select("group_number", "wemetrix_mp_customer_code_new"))
    
    # Concatenate new and old
    df_blocks = (df_blocks.join(df_master_record, on=["group_number"], how="left")
                 .withColumn(f"wemetrix_mp_customer_code{pass_number}", F.coalesce(F.col("wemetrix_mp_customer_code"), F.col("wemetrix_mp_customer_code_new") ))
                 .withColumn(f"matching_ratio_{pass_number}", F.col("matching_ratio")).drop("matching_ratio")
                 .withColumn(f"wemetrix_pass{pass_number}", F.lit(pass_number))
                 .withColumnRenamed("group_number", f"wemetrix_group_number{pass_number}")) 

    spark.sql("DROP VIEW df_blocks")
        
    df_customers = (df_customers.join(df_blocks.select( index_cols + [f"wemetrix_pass{pass_number}", f"matching_ratio_{pass_number}", f"wemetrix_mp_customer_code{pass_number}", f"wemetrix_group_number{pass_number}"]), on = index_cols, how="left")
    .withColumn("wemetrix_group_number", F.when( F.col(f"wemetrix_group_number").isNull(), F.col(f"wemetrix_group_number{pass_number}") ).otherwise(F.col("wemetrix_group_number")) ).drop(f"wemetrix_group_number{pass_number}")
    .withColumn("wemetrix_mp_customer_code", F.when( F.col("wemetrix_mp_customer_code").isNull(), F.col(f"wemetrix_mp_customer_code{pass_number}") ).otherwise(F.col("wemetrix_mp_customer_code")) ).drop(f"wemetrix_mp_customer_code{pass_number}")
    .withColumn("wemetrix_pass", F.when( F.col(f"wemetrix_pass").isNull(), F.col(f"wemetrix_pass{pass_number}") ).otherwise(F.col("wemetrix_pass")) ).drop(f"wemetrix_pass{pass_number}")
    .withColumn("wemetrix_match_type", F.when((F.col("Contract_Account_ID") == F.col("wemetrix_mp_customer_code")) & (F.col("wemetrix_mp_customer_code").isNotNull()), F.lit("MP")).otherwise(F.when(F.col("wemetrix_mp_customer_code").isNotNull(),F.lit("DA") ) ))
    .withColumn("wemetrix_matching_ratio", F.when( F.col(f"wemetrix_matching_ratio").isNull(), F.col(f"matching_ratio_{pass_number}") ).otherwise(F.col("wemetrix_matching_ratio")) ).drop(f"matching_ratio_{pass_number}"))

    return df_customers

# COMMAND ----------

dict_parameters = {

    1: { "blocking_cols" : ["ClVAT_IIS"], 
        "matching_cols" : ["EnB2B_Company_Name"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : ["person", "organisation", "organisation_various"] },
    
    2: { "blocking_cols" : ["EnB2B_Company_Name"], 
        "matching_cols" : ["ClVAT_IIS"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : ["person", "organisation_various"] },
    
    3: { "blocking_cols" : ["ClVAT_IIS"], 
        "matching_cols" : ["EnPrFirst_Name", "EnClLast_Name", "EnPrLast_Name", "EnPrFather_Name", "ClAT_IIS_Wemetrix", "Fixphone_IIS", 
                           "Cellphone_IIS", "ClPassport_IIS_Wemetrix", "ClEmail_Uppercase"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : ["organisation", "organisation_various", "municipalities"] },

    4: { "blocking_cols" : ["ClVAT_IIS"], 
        "matching_cols" : ["EnPrCompany_Name", "ClAT_IIS_Wemetrix", "Fixphone_IIS", "Cellphone_IIS", "EnPrLast_Name"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : ["organisation_various", "person"] },
    
    5: { "blocking_cols" : ["PrCustomer_Type_IIS", "EnPrCompany_Name"], 
        "matching_cols" : ["ClVAT_IIS", "ClAT_IIS_Wemetrix", "Fixphone_IIS", "Cellphone_IIS", 
                           "ClEmail_Uppercase", "ClPassport_IIS_Wemetrix"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : ["person", "organisation_various"] },
    
    6: { "blocking_cols" : ["ClVAT_IIS", "EnBilling_Municipality_Name", "PrBilling_House_Number"], 
        "matching_cols" : ["ClAT_IIS_Wemetrix", "Fixphone_IIS", "Cellphone_IIS", "ClEmail_Uppercase", "ClPassport_IIS_Wemetrix"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : ["municipalities", "person", "organisation"] },
    
    7: { "blocking_cols" : ["ClAT_IIS_Wemetrix"], 
        "matching_cols" : ["ClEmail_Uppercase", "EnPrFirst_Name", "EnPrLast_Name", "EnPrFather_Name", "EnClLast_Name", "ClVAT_IIS", 
                           "ClPassport_IIS_Wemetrix",  "Fixphone_IIS", "Cellphone_IIS"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : ["municipalities", "organisation_various", "organisation"] },
    
    8: { "blocking_cols" : ["FixPhoneIISBlock"],  
        "matching_cols" : ["ClEmail_Uppercase", "EnPrFirst_Name", "EnPrLast_Name", "EnPrFather_Name", "EnClLast_Name", "ClVAT_IIS", 
                           "ClPassport_IIS_Wemetrix", "ClAT_IIS_Wemetrix", "Cellphone_IIS", "EnPrCompany_Name"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : ["municipalities"] },
    
    9: { "blocking_cols" : ["CellPhoneIISBlock"], 
        "matching_cols" : ["ClEmail_Uppercase", "EnPrFirst_Name", "EnPrLast_Name", "EnPrFather_Name", "EnClLast_Name", "ClVAT_IIS", 
                           "ClPassport_IIS_Wemetrix", "ClAT_IIS_Wemetrix", "Fixphone_IIS", "EnPrCompany_Name"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : [] },
    
    10: { "blocking_cols" : ["Billing_Postal_Code", "EnBillingStreet_IIS", "EnBilling_Municipality_Name"], 
        "matching_cols" : ["EnPrFirst_Name", "EnPrFather_Name", "EnPrLast_Name", "EnClLast_Name", "ClVAT_IIS", 
                           "ClPassport_IIS_Wemetrix", "Fixphone_IIS", "Cellphone_IIS", "ClAT_IIS_Wemetrix", "EnPrCompany_Name",
                           "ClEmail_Uppercase"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : [] },
    
    11: { "blocking_cols" : ["EnTrBilling_Street", "TrBilling_Postal_Code", "Billing_TerraKey"], 
        "matching_cols" : ["EnPrFirst_Name", "EnClLast_Name", "EnPrLast_Name", "EnPrFather_Name", "ClPassport_IIS_Wemetrix", "Fixphone_IIS", "Cellphone_IIS",
                           "ClVAT_IIS", "ClAT_IIS_Wemetrix", "EnPrCompany_Name", "ClEmail_Uppercase"], 
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : [] },
    12: { "blocking_cols" : ["EnPoD_Street", "EnPoD_Municipality_Name"], 
        "matching_cols" : ["ClEmail_Uppercase", "EnPrFirst_Name", "EnPrLast_Name", "EnPrFather_Name", "EnPrCompany_Name", "EnClLast_Name",
                            "ClVAT_IIS", "ClAT_IIS_Wemetrix", "ClPassport_IIS_Wemetrix", "Fixphone_IIS", "Cellphone_IIS"],
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : [] },
    13: { "blocking_cols" : ["Contract_Account_ID"], 
        "matching_cols" : ["ClEmail_Uppercase", "EnPrFirst_Name", "EnPrLast_Name", "EnPrFather_Name", "EnClLast_Name", "ClVAT_IIS", "ClPassport_IIS_Wemetrix", 
                           "Fixphone_IIS", "Cellphone_IIS", "ClAT_IIS_Wemetrix"],
        "category_col" : "PrCustomer_Type_IIS",
        "category_col_exclude" : [] }
    
    }

bm_cols = []
for key in dict_parameters.keys():
    bm_cols += dict_parameters[key]["matching_cols"] + dict_parameters[key]["blocking_cols"] + [dict_parameters[key]["category_col"]]
bm_cols=sorted(list(set(bm_cols)))
index_cols = ["SOURCE", "Contract_Account_ID"]

# COMMAND ----------

bm_tmp_table = f"dbfs:/FileStore/wemetrix/blocking_and_matching_delta_tmp{runtag}.parquet"

#exclude Πολλαπλους και Κοινόχρηστα from B/M
df_delta = (spark.sql(f"SELECT * FROM {delta_table}")
            .filter(F.col("SOURCE") == "SAP")
            .filter(F.col("wemetrix_ar_pollaplou").isNull())
            .filter((F.col("Customer_Type_L2").isNull()) | (F.col("Customer_Type_L2") != "koinohrista")))

df_wemetrix_pass = (df_delta
            .withColumn("CellPhoneIISBlock", F.split(F.col("Cellphone_IIS"), " ")[0] )
            .withColumn("FixPhoneIISBlock", F.split(F.col("FixPhone_IIS"), " ")[0] )
            .withColumn("EnBillingStreet_IIS", F.substring(F.col("EnBilling_Street"), 1, 5) )
            .select(["SOURCE"] + bm_cols) )

df_wemetrix_pass = df_wemetrix_pass.withColumn("filled_columns", udf_calculate_avg_char_length(*[ x for x in df_wemetrix_pass.columns if ("wemetrix" not in x) ]))
df_wemetrix_pass = df_wemetrix_pass.withColumn("filled_columns", F.col("filled_columns.filled_columns"))

for pass_number in list(dict_parameters.keys())[:12]:
    if pass_number == 1:
        df_pass = execute_pass(df_customers = df_wemetrix_pass, 
                                pass_number = pass_number, 
                                blocking_cols = dict_parameters[pass_number]["blocking_cols"],
                                matching_cols = dict_parameters[pass_number]["matching_cols"], 
                                category_col = dict_parameters[pass_number]["category_col"],
                                category_col_exclude = dict_parameters[pass_number]["category_col_exclude"])
    else:
        df_pass = execute_pass(df_customers = df_wemetrix_pass.join(spark.read.parquet(bm_tmp_table), on = ["SOURCE", "Contract_Account_ID"], how="left"), 
                                pass_number = pass_number, 
                                blocking_cols = dict_parameters[pass_number]["blocking_cols"], 
                                matching_cols = dict_parameters[pass_number]["matching_cols"], 
                                category_col = dict_parameters[pass_number]["category_col"],
                                category_col_exclude = dict_parameters[pass_number]["category_col_exclude"])
        
    (df_pass.select("SOURCE", "Contract_Account_ID", "wemetrix_group_number", "wemetrix_pass","wemetrix_mp_customer_code",  "wemetrix_match_type", "wemetrix_matching_ratio")
     .write.mode("overwrite").parquet(bm_tmp_table))
    print(f"Finished pass {pass_number}")

# COMMAND ----------

spark.read.parquet(bm_tmp_table).write.mode("overwrite").saveAsTable(bm_results_table)