# Databricks notebook source
# MAGIC %md
# MAGIC ## Διαδικασία απομόνωσης εγγραφών ως αποτέλεσμα fuzzy matching λίστας συγκεκριμένων λεκτικών
# MAGIC
# MAGIC 1. Αναζήτηση των λεκτικών από τη λίστα που μας δόθηκε (έχει ανέβει σε parqut file : "dbfs:/FileStore/wemetrix/strings_fuzzy-1.parquet") στα πεδία "ClLast_Name","ClCompany_Name".
# MAGIC 2. Σε περιπτώσεις που κάποιο από τα δοθέντα λεκτικά βρεθεί είτε στο "ClLast_Name" είτε στο "ClCompany_Name", το συμβόλαιο αυτό σημειώνεται ώστε να μη συμπεριληφθεί στη διαδικασία golden record group.
# MAGIC
# MAGIC ##### Κατόπιν ολοκλήρωσης της διαδικασίας στα συμβόλαια του πίνακα "/dbfs/mnt/databricks/master_table_mnemosyne_2023_05_31_V2.parquet":
# MAGIC
# MAGIC 1. Από τα 18,220,805 συμβόλαια τα 43080 περιείχαν είτε στο "ClLast_Name" πεδίο κάποιο από τα λεκτικά. 
# MAGIC 2. Το πεδίο "ClCompany_Name" δεν συμπεριλαμβάνεται στην διαδικασία, καθώς τα λεκτικά εντοπίζονται σε μεγάλο ποσοστό με την ίδια συχνότητα σε σύγκριση με το πεδίο "ClLast_Name". 
# MAGIC 3. Το σύνολο των 43090 συμβολαίων που πρέπει να εξαιρεθούν αποθηκεύτηκε στον "dbfs:/FileStore/wemetrix/string_match_results.parquet"
# MAGIC - Πεδία πίνακα: "SOURCE", "Contract_Account_ID", "ClLast_Name"
# MAGIC
# MAGIC Η διαδικασία μπορεί να επαναλαμβάνεται και στα delta με τον παρακάτω κώδικα
# MAGIC

# COMMAND ----------

dbutils.widgets.text("input_table",  "wemetrix.foursourcedelta")
input_table = dbutils.widgets.get("input_table")

dbutils.widgets.text("output_table",  "wemetrix.ca_discard_delta")
output_table = dbutils.widgets.get("output_table")

# COMMAND ----------

import pyspark.sql.functions as F
from pyspark.sql.functions import col, when, length, substring, udf,expr
from pyspark.sql.types import StringType

dd_characters_eng_to_greek = {'A': 'Α', 'a': 'α', 'B': 'Β', 'b': 'β', 'G': 'Γ', 'g': 'γ', 'D': 'Δ', 'd': 'δ', 'E': 'Ε', 'e': 'ε','H': 'Η', 'H': 'η', 'Z': 'Ζ', 'z': 'ζ', 'Th': 'Θ', 'th': 'θ', 'I': 'Ι', 'i': 'ι',
                              'K': 'Κ', 'k': 'κ', 'L': 'Λ', 'l': 'λ', 'M': 'Μ', 'm': 'μ', 'N': 'Ν', 'n': 'ν', 'X': 'Ξ', 'x': 'ξ', 'O': 'Ο', 'o': 'ο', 'P': 'Π', 'p': 'π', 'R': 'Ρ', 'r': 'ρ', 'S': 'Σ', 's': 'ς', 'T': 'Τ', 't': 'τ', 'U': 'Υ', 'u': 'υ','Y': 'Υ', 'y': 'υ', 'Ph': 'Φ', 'ph': 'φ', 'Kh': 'Χ', 'kh': 'χ', 'Ps': 'Ψ', 'ps': 'ψ','W': 'Ω', 'w': 'ω'}

def replace_english_characters(dictionary,word):
    if not word:
        return None
    else:
        return_word = ""
        for letter in word:
            if letter in dictionary.keys():
                return_word += dictionary[letter]
            else:
                return_word += letter
        return return_word

udf_replace_chars = F.udf(lambda word: replace_english_characters(dd_characters_eng_to_greek, word), StringType())

df_strings = spark.createDataFrame([
                            "ΚΟΜΕΝΟ ΧΩΡΙΣ ΠΕΛΑΤΗ",
                            "ΑΛΛΑΓΗ ΣΕ ΚΟΜΕΝΟ",
                            "ΧΩΡΙΣ ΠΡΟΜΗΘΕΥΤΗ",
                            "ΧΩΡΙΣ ΠΕΛΑΤΗ",
                            "ΚΟΜΜΕΝΟ",
                            "ΚΟΜΜΕΝΟ ΧΩΡΙΣ ΠΕΛΑΤΗ",
                            "ΤΕΣΤ",
                            "TEST",
                            "VERMION",
                            "ΑΝΕΥ ΠΕΛ",
                            "ΑΝΕΥ ΠΑΡΑΒΙΑΣ",
                            "ΑΛΛΑΓΗ ΜΕΤΡΗΤΗ",
                            "ΑΛΛΑΓΗ ΣΕ ΚΟΜΜΕΝΟ",
                            "ΑΛΛΟΣ ΠΡΟΜΗΘΕΥΤ",
                            "ΠΑΡΑΒΙΑΣΜΕΝΟ"], StringType())

df_strings=df_strings.withColumnRenamed("value","Strings_DEH")

df_strings = df_strings \
    .filter((col("Strings_DEH") != "TEST") & (col("Strings_DEH") != "ΤΕΣΤ"))\
    .withColumn("Strings_DEH", F.upper(F.trim(F.regexp_replace(F.col("Strings_DEH"), "[^A-ZΑ-Ω ]+", ""))))\
    .select("Strings_DEH")


df_master_table2 = (spark.sql(f"SELECT SOURCE, Contract_Account_ID ,ClLast_Name FROM {input_table}")
                        .filter(F.col("ClLast_Name").isNotNull() )
                    .withColumn("ClLast_Name", F.upper(F.trim(F.regexp_replace(F.col("ClLast_Name"), "[^A-ZΑ-Ω ]+", ""))))
                    .withColumn("ClLast_Name_translated", udf_replace_chars(F.col("ClLast_Name"))))

filtered_df1 = df_master_table2 \
    .join(df_strings, expr("ClLast_Name like concat('%', Strings_DEH, '%') OR ClLast_Name_translated like concat('%', Strings_DEH, '%') ")) \
    .distinct() \
    .select(df_master_table2.columns)


filtered_df2 = df_master_table2.filter((col("ClLast_Name") == "ΤΕΣΤ") | (col("ClLast_Name_translated") == "ΤΕΣΤ") | (col("ClLast_Name") == "ΚΟΜΕΝΟ") | (col("ClLast_Name_translated") == "ΚΟΜΕΝΟ") )

union_df = filtered_df1.union(filtered_df2).dropDuplicates()

cols_drop = ('ClLast_Name_translated')
union_df = union_df.drop(*cols_drop)

union_df.write.mode("overwrite").saveAsTable(output_table)