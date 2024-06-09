# Databricks notebook source
# MAGIC %md
# MAGIC ## Έλεγχος λίστας ευρέως χρησιμοποιούμενων ΑΦΜ με βάση τα λεκτικά
# MAGIC
# MAGIC 1. Τα ΑΦΜ τα οποία ελέγχθηκαν με βάση το input από την ομάδα της ΔΕΗ είναι τα ακόλουθα: 090000045,090153025,090169846,090174291,090283815,094014201,094014249,094014298,094019245,094025817,094026421,094038689,094444827,094449128,094493766,099936189,999510393.
# MAGIC 2. Για κάθε ΑΦΜ δημιουργήθηκε ένα frequency table με τα πιο συχνά χρησιμοποιούμενα ClLast_Name,ClCompany_Name,B2B_Company_Name.
# MAGIC 3. Με βάση τα λεκτικά που βρέθηκαν στο βήμα 2 και τα λεκτικά που μας στάλθηκαν -αρχείο most common vat ids_ΠΥ- δημιουργήθηκαν λίστες λεκτικών για κάθε ΑΦΜ.
# MAGIC 4. Όσες εγγραφές είχαν κάποιο από τα προαναφερθέντα ΑΦΜ συγκρίθηκαν με τη λίστα των λεκτικών του χρησιμοποιώντας τη μέθοδο rlike (Similar to SQL regexp_like()).Σε εγγραφές που κανένα από τα λεκτικά του ΑΦΜ τους δεν υπήρχαν είτε στο ClLast_Name,είτε στο ClCompany_Name,είτε στο B2B_Company_Name, το πεδίο ClVAT_IIS έγινε null.
# MAGIC
# MAGIC ##### Κατόπιν ολοκλήρωσης της διαδικασίας στα συμβόλαια του πίνακα "/dbfs/mnt/databricks/master_table_mnemosyne_2023_05_31.parquet":
# MAGIC 1. Το σύνολο των αποτελεσμάτων αποθηκεύτηκε στον "dbfs:/FileStore/wemetrix/afm_cleansing_results.parquet"
# MAGIC - Πεδία πίνακα: "SOURCE", "Contract_Account_ID","ClVAT_IIS","ClLast_Name","ClFirst_Name","ClCompany_Name","B2B_Company_Name"
# MAGIC
# MAGIC Η διαδικασία μπορεί να επαναλαμβάνεται και στα delta με τον παρακάτω κώδικα χρησιμοποιώντας τα κατάλληλα input_table, output_table

# COMMAND ----------

dbutils.widgets.text("input_table",  "wemetrix.foursourcedelta")
input_table = dbutils.widgets.get("input_table")

dbutils.widgets.text("output_table",  "wemetrix.afm_discard_delta")
output_table = dbutils.widgets.get("output_table")

# COMMAND ----------

import string
import pyspark.sql.functions as F
from pyspark.sql.functions import col, when, length, substring,count,row_number
from pyspark.sql.window import Window
from pyspark.sql.types import StringType

df_master_table=(spark.sql(f"SELECT SOURCE, Contract_Account_ID,ClVAT_IIS,ClLast_Name,ClFirst_Name,ClCompany_Name,B2B_Company_Name FROM {input_table}"))

df_vat = df_master_table\
    .withColumn("ClVAT_IIS",F.trim(F.regexp_replace(F.upper(F.col("ClVAT_IIS")), "/[^0-9]+/", "")))\
    .withColumn("ClFirst_Name",F.trim(F.regexp_replace(F.upper(F.col("ClFirst_Name")), "/[^0-9]+/", "")))\
    .withColumn("ClLast_Name",F.trim(F.regexp_replace(F.upper(F.col("ClLast_Name")), "/[^0-9]+/", "")))\
    .withColumn("ClCompany_Name",F.trim(F.regexp_replace(F.upper(F.col("ClCompany_Name")), "/[^0-9]+/", "")))\
    .withColumn("B2B_Company_Name",F.trim(F.regexp_replace(F.upper(F.col("B2B_Company_Name")), "/[^0-9]+/", "")))\
    .select("SOURCE", "Contract_Account_ID","ClVAT_IIS","ClLast_Name","ClFirst_Name","ClCompany_Name","B2B_Company_Name")

# function for valid and invalid afm 
def afm_check(source_df,afm,pattern):

    organ_df = source_df.filter(col("ClVAT_IIS") == afm)
    
    organ_df = organ_df\
    .withColumn("flag", 
                F.when(
                    (F.col("ClLast_name").rlike("|".join(patterns))) |
                    (F.col("ClFirst_name").rlike("|".join(patterns))) |
                    (F.col("ClCompany_name").rlike("|".join(patterns))),1)
                .when(
                    (F.col("B2B_Company_name").rlike("|".join(patterns))),1)
                .otherwise(0))
    
    organ_df = organ_df.withColumn("ClVAT_IIS_wemetrix", F.when(
        (F.col("flag") == 1),F.col("ClVAT_IIS")
        ).otherwise(F.lit(None)))\
         .drop("flag")   
    
    return organ_df

# 1. ΔΗΜΟΣΙΑ ΕΠΙΧΕΙΡΗΣΗ ΗΛΕΚΤΡΙΣΜΟΥ ΑΝΩΝΥΜΗ ΕΤΑΙΡΙΑ ΑΦΜ: 090000045
patterns = ["ΔΕΗ","ΗΛΕΚΤΡΙΣΜΟΥ","ΟΤΕ","ΓΔΥΛ","ΔΥΣ","ΗΛΕΚΤΡΟΚΙΝΗΣΗ","ΔΜΚΥ","ΚΕΨΕ Δ-Μ","ΓΔΠ","ΔΥΗΠ","ΥΗΣ","ΛΚΔΜ","ΔΕΔΔΗΕ","ΔΛΚΜ"]
afm= "090000045"
df_deh = afm_check(df_vat,afm,patterns)

# 2. ΥΠΟΥΡΓΕΙΟ ΕΘΝΙΚΗΣ ΑΜΥΝΑΣ ΑΦΜ: 090153025
patterns = ["117", "115", "ΥΠΟΥΡΓ", "ΑΜΥΝΑ","ΓΕΣ","ΓΕΝΙΚΟ","ΕΠΙΤΕΛΕΙΟ","ΠΤΕΡΥΞ","ΜΑΧΗ","ΥΠΕΘΑ","ΠΕΔ","ΦΙΛΟΞ","ΓΕΕΘΑ","ΚΕΠΒ","ΤΑΓΜΑ","ΦΥΛΑΚΙΟ","ΣΤΡ","Μ/Κ", "ΑΕΡΟΠΟΡΙΑ", "ΛΣ", "ΓΕΑ"]
afm= "090153025"
df_dministry = afm_check(df_vat,afm,patterns)

# 3. ΥΠΟΥΡΓΕΙΟ ΔΗΜΟΣΙΑΣ ΤΑΞΗΣ ΚΑΙ ΠΡΟΣΤΑΣΙΑΣ ΤΟΥ ΠΟΛΙΤΗ ΑΦΜ:090169846
patterns = ["ΥΠΟΥΡΓ","ΑΣΤΥΝΟΜ", "ΕΛΛΗΝ" , "ΥΠΕΧΩΔΕ","ΠΡΟΣΤ", "ΠΥΡΟΣΒΕΣΤ","ΑΓΡΟΤ","ΛΙΜΕΝ","ΕΛ.ΑΣ","ΓΡΑΜ" ,"ΤΜΗΜΑ"]
afm= "090169846"
df_pministry = afm_check(df_vat,afm,patterns)

# 4. ΠΕΡΙΦ.ΑΤΤΙΚΗΣ ΑΦΜ:090174291
patterns = ["ΥΠΕΧΩΔΕ","ΥΠΕ", "ΕΥΔΕ", "ΥΠΟΥΡΓ","ΥΠΟΜΕΔΙ","ΔΚΕΣΟ","ΕΡΓ","ΠΕΡΙΦ","ΔΙ.ΔΙ.ΜΥ.","ΠΡΟΣΤ","ΓΓΔΕ","ΕΥΔΕ","BOAK","ΥΠ-ΜΕ-ΔΙ","ΕΥΔ","ΥΠΟ"]
afm= "090174291"
df_attiki = afm_check(df_vat,afm,patterns)

# 5. ΥΠΟΥΡΓΕΙΟ ΠΟΛΙΤΙΣΜΟΥ ΑΦΜ:090283815
patterns = ["ΥΠΟΥΡΓ", "ΕΦΟΡ", "ΠΟΛΙΤ", "ΑΡΧΑΙΟ", "ΑΘΛΗΤ","ΕΠΚΑ","ΤΑΠΑ","ΤΟΥΡΙΣ","ΜΟΥΣΕΙΟ","ΥΠΠΟ","ΥΠ ΠΟ Α"]
afm = "090283815"
df_cministry = afm_check(df_vat,afm,patterns)

# 6. ΤΡΑΠΕΖΑ ΕΘΝΙΚΗ ΤΗΣ ΕΛΛΑΔΟΣ ΑΝΩΝΥΜΗ ΕΤΑΙΡΕΙΑ ΑΦΜ:094014201
patterns = ["ΕΘΝ", "ΤΡΑΠ", "ΕΤΕ", "Ε.Τ.Ε"]
afm = "094014201"
df_nbank = afm_check(df_vat,afm,patterns)

# 7. ALPHA ΒΑΝΚ Α.Ε ΑΦΜ:094014249
patterns = ["ΑΛΦΑ", "ΤΡΑΠ", "ALPHA", "BANK", "ΠΙΣΤΕΩΣ","ΒΑΝΚ"]
afm = "094014249"
df_abank = afm_check(df_vat,afm,patterns)

# 8. ΠΕΙΡΑΙΩΣ FINANCIAL HOLDINGS AE ΑΦΜ:094014298
patterns = ["ΤΡΑΠ", "ΠΕΙΡ", "ΚΥΠΡΟΥ"]
afm = "094014298"
df_pbank = afm_check(df_vat,afm,patterns)

# 9. ΟΡΓΑΝΙΣΜΟΣ ΤΗΛΕΠΙΚΟΙΝΩΝΙΩΝ ΕΛΛΑ∆ΟΣ Α.Ε. ∆/ΝΣΗ ΤΕΧΝ. ΥΠΗΡ. ΜΕΓΑΛΩΝ ΠΕΛΑΤΩΝ ΣΤΑΘ. & KIN ΑΦΜ:094019245
patterns = ["ΟΤΕ", "Ο.Τ.Ε", "ΤΗΛΕΠ"]
afm = "094019245"
df_ote = afm_check(df_vat,afm,patterns)

# 10. Α/Β ΒΑΣΙΛΟΠΟΥΛΟΣ Α.Ε. ΑΦΜ:094025817
patterns = ["ΒΑΣΙΛΟΠ", "ΑΛΦΑ", "ΑΒ" , "ΒΗΤΑ","Α/Β"]
afm = "094025817"
df_ab = afm_check(df_vat,afm,patterns)

# 11. ΕΛΛΗΝΙΚΑ ΤΑΧΥΔΡΟΜΕΙΑ||ΕΛΤΑ ΑΦΜ:094026421
patterns = ["ΕΛΤΑ", "ΤΑΧ", "ΕΛ.ΤΑ", "ΕΛΛΗΝΙΚΑ"]
afm = "094026421"
df_elta = afm_check(df_vat,afm,patterns)

# 12. ΟΡΓΑΝΙΣΜΟΣ ΣΙΔΗΡΟΔΡΟΜΩΝ ΕΛΛΑΔΟΣ ΑΕ ΑΦΜ: 094038689
patterns = ["ΟΣΕ", "Ο.Σ.Ε", "ΣΙΔΗΡ", "ΣΤΑΘ", "ΣΕΚ"]
afm = "094038689"
df_ose = afm_check(df_vat,afm,patterns)

# 13. NOVA ΤΗΛΕΠΙΚΟΙΝΩΝΙΕΣ ΜΟΝΟΠΡΟΣΩΠΗ ΑΕ||NOVA M A E ΑΦΜ:094444827
patterns = ["FORTHNET", "NOVA", "ΦΟΡΘΝΕΤ", "ΤΗΛΕΠ","ΑΕ"]
afm = "094444827"
df_nova = afm_check(df_vat,afm,patterns)

# 14. ΕΓΝΑΤΙΑ ΟΔΟΣ Α.Ε. ΑΦΜ:094449128
patterns = ["ΕΓΝ", "ΟΔΟΣ"]
afm = "094449128"
df_eodos = afm_check(df_vat,afm,patterns)

# 15. COSMOTE ΑΦΜ:094493766
patterns = ["ΚΟΣΜΟΤΕ", "COSMOTE", "ΤΗΛ"]
afm = "094493766"
df_cosmote = afm_check(df_vat,afm,patterns)

# 16. WIND HELLAS ΤΗΛΕΠΙΚΟΙΝΩΝΙΕΣ Α.Ε.Β.Ε ΑΦΜ:099936189
patterns = ["WIND", "HELLAS", "ΤΗΛ","ΕΛΛΑΣ"]
afm = "099936189"
df_wind = afm_check(df_vat,afm,patterns)

# 17. WIND ΕΛΛΑΣ ΤΗΛΕΠΙΚΟΙΝΩΝΙΕΣ ΑΝΩΝΥΜΗ ΕΜΠΟΡΙΚΗ & ΒΙΟΜΗΧΑΝΙΚΗ ΕΤΑΙΡΕΙΑ ΑΦΜ:999510393
patterns = ["ΤΙΜ", "ΤΗΛ", "ΕΛΛΑΣ","HELLAS","TELEC"]
afm = "999510393"
df_tim = afm_check(df_vat,afm,patterns)

afm_cleaned= df_deh\
    .union(df_nbank)\
    .union(df_abank)\
    .union(df_pbank)\
    .union(df_ab)\
    .union(df_dministry)\
    .union(df_pministry)\
    .union(df_cministry)\
    .union(df_attiki)\
    .union(df_ose)\
    .union(df_eodos)\
    .union(df_ote)\
    .union(df_elta)\
    .union(df_nova)\
    .union(df_cosmote)\
    .union(df_wind)\
    .union(df_tim)

afm_cleaned.write.mode("overwrite").saveAsTable(output_table)