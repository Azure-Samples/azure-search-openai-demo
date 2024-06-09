# Databricks notebook source
# MAGIC %md
# MAGIC ### Διαδικασία διόρθωσης email
# MAGIC
# MAGIC Δημιουργία λίστας έγκυρων domain και ταξινόμηση με βάση τη συχνότητα εμφάνισης τους (Ο έλεγχος εγκυρότητας γίνεται με DNS queries - Python email_validator module)
# MAGIC
# MAGIC 1. Αντικαθίστανται ελληνικά γράμματα από greeklish πχ α --> a, θ --> th.
# MAGIC 2. Γίνεται έλεγχος στο local κομμάτι (πριν το @) για άκυρους χαρακτήρες οι οποίοι αφαιρούνται 
# MAGIC 3. Ελέγχος αν το domain κομμάτι υπάρχει στη λίστα με τα έγκυρα domain που διατηρούμε. Αν όχι, τότε δίνεται νέο DNS query. Αν αυτό αποτύχει τότε γίνεται έλεγχος για άκυρους χαρακτήρες οι οποίοι αφαιρούνται και στη συνέχεια fuzzy matching με το πιο κοντινό από τα έγκυρα domains.
# MAGIC 4. Σε περιπτώσεις που λείπει ο κωδικός χώρας από το domain πχ hotmail τότε συμπληρώνεται με βάση τα πιο συχνά εμφανιζόμενα όπως hotmail.com αντί για hotmail.gr
# MAGIC 5. Στις περιπτώσιες που δεν υπάρχει παπάκι ελέγχεται αν το τελευταίο κομμάτι της διεύθυνσης είναι (μέρος) έγκυρου domain, προστίθεται το παπάκι στην κατάλληλη θέση και εκτελούνται τα βήματα 1-4 κανονικά.
# MAGIC 6. Η λίστα ενημερώνεται με τα νέα έγκυρα domain για να αποφεύγεται η επαναλαμβανόμενη εκτέλεση του ίδιου DNS query

# COMMAND ----------

import pandas as pd
from fuzzywuzzy import fuzz, process
from pyspark.sql.types import IntegerType, StringType
from pyspark.sql import Window
from pyspark.sql.functions import udf
import pyspark.sql.functions as F
import Levenshtein

def test_domain(email_domain):

    from email_validator import validate_email

    try:
        validate_email(f"test@{email_domain}")
        return 1
    except:
        return 0
    
udf_test_domain = F.udf(test_domain, IntegerType())

# Διαδικασία αποθήκευσης των πιο συχνά εμφανιζόμενων domains. Δεν τρέχει κάθε φορά, απλά διαβάζεται ο πίνακας.
# df_freq_domains = (spark.read.parquet("/dbfs/mnt/databricks/master_table_mnemosyne_2023_05_31.parquet").where(F.col("Email_Info") == "Email_Format").select("Email")
#                             .withColumn("Email_Domain", F.lower(F.split("Email", "@")[1]))
#                             .groupBy("Email_Domain").count()
#                             .filter(F.col("Email_Domain").contains("."))
#                             .orderBy(F.col("count").desc()))
# df_freq_domains.createOrReplaceTempView("frequent_email_domains")
# df_freq_domains_w = spark.sql("SELECT * FROM frequent_email_domains")
# df_freq_domains_w.write.mode("overwrite").parquet("dbfs:/FileStore/wemetrix/frequent_email_domains.parquet")

# df_valid_domains = (spark.read.parquet("dbfs:/FileStore/wemetrix/frequent_email_domains.parquet")
#                         .filter(F.col("count") > 20)
#                         .withColumn("validated_domain", udf_test_domain(F.col("Email_Domain")))
#                         .filter(F.col("validated_domain") == 1))
# df_valid_domains.createOrReplaceTempView("valid_email_domains")
# df_valid_domains_w = spark.sql("SELECT * FROM valid_email_domains")
# df_valid_domains_w.write.mode("overwrite").parquet("dbfs:/FileStore/wemetrix/valid_email_domains.parquet")

df_valid_domains = spark.read.parquet("dbfs:/FileStore/wemetrix/valid_email_domains.parquet")
pd_df_valid_domains = df_valid_domains.toPandas()

pd_df_valid_domains = df_valid_domains.toPandas()

def calculate_fuzz_ratio(str1, str2):
  return fuzz.ratio(str1, str2)

def correct_local_part(email_address):

    if "@" in email_address:
        split_email = email_address.split("@")
        local_part = split_email[0]
        domain_part = "@" + "".join(split_email[1:])
    else:
        local_part = email_address
        domain_part = ""

    # allowed_characters_local = ['!', '#', '$', '%', '&', "'", '*', '+', '-', '/', '=', '?', '^', '_', '`', '{', '|', '}', '~', '.']
    allowed_characters_local = ["_", ".", "-"]
    correct_local_part = ''.join(e for e in local_part if (e.isalnum() or e in allowed_characters_local)).strip()
    correct_local_part = correct_local_part.replace("..", ".")
    if len(correct_local_part) > 0:
        if correct_local_part[0] == ".": correct_local_part = correct_local_part[1:]
        if correct_local_part[-1] == ".": correct_local_part = correct_local_part[:-1]

        correct_email_address = correct_local_part + domain_part
    else:
        correct_email_address = None
    
    return correct_email_address


def correct_domain(email_address):

    import pandas as pd

    if "@" in email_address:

        split_email = email_address.split("@")
        local_part = split_email[0]
        domain_part = "".join(split_email[1:])

        if domain_part not in pd_df_valid_domains["Email_Domain"]:

            if test_domain(domain_part) == 0:

                allowed_characters_domain = ['.', '-']
                domain_part = ''.join(e for e in domain_part if (e.isalnum() or e in allowed_characters_domain)).strip()

                pd_raw_domain = pd.DataFrame({"raw_domain": [domain_part]})

                pd_correct_domain = pd_df_valid_domains.merge(pd_raw_domain, how='cross')
                # process.extractOne(domain_part, pd_df_valid_domains["Email_Domain"])[0]
                pd_correct_domain["fuzz_score"] = pd_correct_domain.apply(lambda x: calculate_fuzz_ratio(x["Email_Domain"], x["raw_domain"]), axis=1)

                if domain_part.endswith("dotcom"): domain_part = domain_part.replace("dotcom", ".com")
                if domain_part.endswith("-com"): domain_part = domain_part.replace("-com", ".com")
                if "." in domain_part:
                    pd_correct_domain = pd_correct_domain.sort_values(["fuzz_score", "count"], ascending=False)
                else:
                    if domain_part.endswith("com"): domain_part = domain_part.replace("com", ".com")
                    simple_match = pd_correct_domain[pd_correct_domain["Email_Domain"].str.contains(domain_part)].sort_values(["count"], ascending=False)
                    if len(simple_match) > 0:
                        pd_correct_domain = simple_match
                    else:
                        pd_correct_domain = pd_correct_domain.sort_values(["fuzz_score", "count"], ascending=False)

                if Levenshtein.distance(domain_part, pd_correct_domain.iloc[0,0]) < 6:
                    domain_part = pd_correct_domain.iloc[0,0]
                return local_part + "@" + domain_part
            
            else:

                return local_part + "@" + domain_part
            
        else:
            
            return local_part + "@" + domain_part

def correct_email(email_address):

    if "@" not in email_address:
        for index, row in pd_df_valid_domains.iterrows():
            if email_address.endswith( "at" + row["Email_Domain"]):
                email_address = email_address.replace("at" + row["Email_Domain"], "@" + row["Email_Domain"])
                break
            elif email_address.endswith(row["Email_Domain"]):
                email_address = email_address.replace(row["Email_Domain"], "@" + row["Email_Domain"])
                break
            
    email_address_cl = correct_local_part(email_address)

    if email_address_cl != None:
        email_address_cd = correct_domain(email_address_cl)
    else:
        email_address_cd = None

    return email_address_cd

udf_correct_email = udf(correct_email, StringType())

dd_characters_greek_to_eng = {'Α': 'A', 'α': 'a', 'Β': 'B', 'β': 'b', 'Γ': 'G', 'γ': 'g', 'Δ': 'D', 'δ': 'd', 'Ε': 'E', 'ε': 'e', 'Ζ': 'Z', 'ζ': 'z', 
                                'Η': 'E', 'η': 'e', 'Θ': 'TH', 'θ': 'th', 'Ι': 'I', 'ι': 'i', 'Κ': 'K', 'κ': 'k', 'Λ': 'L', 'λ': 'l', 'Μ': 'M', 'μ': 'm',
                                'Ν': 'N', 'ν': 'n', 'Ξ': 'X', 'ξ': 'x', 'Ο': 'O', 'ο': 'o', 'Π': 'P', 'π': 'p', 'Ρ': 'R', 'ρ': 'r', 'Σ': 'S', 'σ': 's', 'ς': 's',
                                'Τ': 'T', 'τ': 't', 'Υ': 'U', 'υ': 'u', 'Φ': 'PH', 'φ': 'ph', 'Χ': 'KH', 'χ': 'kh', 'Ψ': 'PS', 'ψ': 'ps', 'Ω': 'O', 'ω': 'o'}

from pyspark.sql.types import IntegerType, StringType

def replace_greek_characters(email_address):
    
    return_word = ""
    for letter in email_address:
        if letter in dd_characters_greek_to_eng.keys():
            return_word += dd_characters_greek_to_eng[letter]
        else:
            return_word += letter
    return return_word

udf_replace_greek = udf(replace_greek_characters, StringType())

# COMMAND ----------

dbutils.widgets.text("input_table", "wemetrix.foursourcedelta")
input_table = dbutils.widgets.get("input_table")

dbutils.widgets.text("output_table", "wemetrix.email_correction_results_delta")
output_table = dbutils.widgets.get("output_table")

# COMMAND ----------

email_col = "Email"
index_cols = ["SOURCE", "Contract_Account_ID"]

df_email_correction = (spark.sql(f"SELECT * FROM {input_table}")
                            .select("SOURCE", "Contract_Account_ID", f"{email_col}", f"{email_col}_Info")
                            .where(F.col(f"{email_col}_Info") == "Unknown_Format")
                        .withColumn(f"{email_col}_Replace_Greek", udf_replace_greek(F.col(email_col)))
                        .withColumn(f"{email_col}_Correct", udf_correct_email(F.trim(F.lower(F.col(f"{email_col}_Replace_Greek")))))
                        .drop(f"{email_col}_Replace_Greek"))

email_col = "B2B_Email"

df_b2b_email_correction = (spark.sql(f"SELECT * FROM {input_table}")
                            .select("SOURCE", "Contract_Account_ID", f"{email_col}", f"{email_col}_Info")
                            .where(F.col(f"{email_col}_Info") == "Unknown_Format")
                        .withColumn(f"{email_col}_Replace_Greek", udf_replace_greek(F.col(email_col)))
                        .withColumn(f"{email_col}_Correct", udf_correct_email(F.trim(F.lower(F.col(f"{email_col}_Replace_Greek")))))
                        .drop(f"{email_col}_Replace_Greek"))

df_email_join = df_email_correction.join(df_b2b_email_correction, on = index_cols, how="outer")
df_email_join.write.mode("overwrite").saveAsTable(output_table)


# COMMAND ----------

