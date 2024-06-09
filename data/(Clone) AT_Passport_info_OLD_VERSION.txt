# Databricks notebook source
# MAGIC %md
# MAGIC ## Διαδικασία Αναγνώρισης & διόρθωσης ΑΤ
# MAGIC 1. Δημιουργία νέας στήλης AT_Info_Wemetrix για αποθήκευση αποτελεσμάτων και σύγκριση με την υπάρχουσα κατηγοριοποίηση του AT_Info.
# MAGIC 2. Για τη διαδικασία χρησιμοποιήθηκαν μόνο εγγραφές που προέρχονται από το SAP.
# MAGIC 3. Για τη διαδικασία χρησιμοποιήθηκε η στήλη ClAT.
# MAGIC 4. Αν το ClAT έχει AT_Format -2 γράμματα (Λατινικά & Ελληνικά) and 6 αριθμούς-, θα κατηγοριοποιηθεί ως AT_Format.
# MAGIC 5. Αν το ClAT έχει AT_Format -1 γράμμα (Λατινικά & Ελληνικά) and 6 αριθμούς-, θα κατηγοριοποιηθεί ως AT_Format.
# MAGIC 6. Ταξινόμηση σύμφωνα με το AT_Institute:\
# MAGIC   6.1. Από αυτή τη διαδικασία εξαιρούνται όσα έχουν ήδη ταξινομηθεί στα προηγούμενα βήματα και οι εγγραφές που δεν έχουν τιμή στο ClAT.\
# MAGIC   6.2. Αν το AT_Institute περιέχει αυτά τα λεκτικά ['ΑΤ','ΤΑ','ΥΑ'] και το ClAT δεν έχει AT_Format -2 γράμματα (Λατινικά & Ελληνικά) and 6 αριθμούς- ή -1 γράμμα (Λατινικά & 
# MAGIC        Ελληνικά) and 6 αριθμούς-, θα κατηγοριοποιηθεί ως Invalid_value.\
# MAGIC   6.3. Αν είτε το AT_Institute είτε το ClAT περιέχουν αυτά τα λεκτικά ['ΓΕΝ','ΓΕΣ','ΓΕΑ','ΓΕΕΘΑ','ΕΛΑΣ','ΕΛΛΑΣ','ΛΣ','ΥΑ','ΕΛ.ΑΣ','ΑΣΤΥΝΟΜΙΑ','ΛΙΜΕΝ','ΠΥΡ','ΣΩΜΑT','ΣΤΡΑΤ'] και το ClAT έχει Army_Police_Format -9 αριθμούς-, θα 
# MAGIC        κατηγοριοποιηθεί ως Army_Police_Format αλλιώς null.\
# MAGIC   6.4. Αν είτε το AT_Institute είτε το ClΑΤ περιέχουν αυτά τα λεκτικά ['ΔΙΑΒ.','ΔΙΑΒ','ΔΙΑΒΑΤΗΡΙΟ','ΑΔΕΙΑ','ΔΙΑΜΟΝΗ','ΑΣΥΛ','REPU','ΑΡΧΕΣ','Α.Ε.Α./Δ.Δ','ΑΕΑ/ΔΔ','ΔΗΜΟΚΡΑΤΙΑ'], θα κατηγοριοποιηθεί ως Passport_Format.\
# MAGIC   6.5. Χρησιμοποιούμε βάση δεδομένων με τα ονόματα όλων των χωρών είτε στα Αγγλικά είτε στα Ελληνικά.\
# MAGIC   6.6. Αν το AT_Institute περιέχει το όνομα κάποια χώρας είτε στα αγγλικά είτε στα ελληνικά, θα κατηγοριοποιηθεί ως Passport_Format.
# MAGIC 7. Διαχείριση των εγγραφών που δεν ταξινομήθηκαν μετά την παραπάνω διαδικασία (δλδ. δεν πήραν τιμή στη στήλη AT_Info_Wemetrix)\
# MAGIC   7.1. Αν το AT_Info_Wemetrix είναι null και το AT_Info είναι ίσο είτε με Invalid_Value είτε με Passport_Format, θα κατηγοριοποιηθεί ως Invalid_Value ή Passport_Format αντίστοιχα.
# MAGIC
# MAGIC ## Διαδικασία Αναγνώρισης & διόρθωσης Διαβατηρίου
# MAGIC Οι παρακάτω διαδικασίες εκτελούνται σειριακά ( για να υπάρχει μια προτεραιότητα στην κατηγοριοποίηση)
# MAGIC 1. Δημιουργία νέας στήλης Passport_Info_Wemetrix για αποθήκευση αποτελεσμάτων και σύγκριση με την υπάρχουσα κατηγοριοποίηση του Passport_Info.
# MAGIC 2. Για τη διαδικασία χρησιμοποιήθηκαν μόνο εγγραφές που προέρχονται από το SAP.
# MAGIC 3. Για τη διαδικασία χρησιμοποιήθηκε η στήλη ClPassport.
# MAGIC 4. Για τις χώρες ALBANIA, GEORGIA, PAKISTAN, USA, UKRAINE, ROMANIA, GBR, CHINA, BANGLADESH, EGYPT, BULGARIA, DEUTSCHLAND, GERMANY, ITALIA δημιουργήθηκε ένα frequency table ώστε να βρούμε τους κανόνες που πρέπει να πληροί το εκάστοτε διαβατήριο(αναλογία γραμμάτων και αριθμών).Για κάθε μια από αυτές τις χώρες δημιουργήθηκε ένας κανόνας. Αν στο ADT_Institute υπάρχει κάποια από αυτές τις χώρες γίνεται ο έλεγχος με τον αντίστοιχο κανόνα και αν το ClPassport δεν είναι null και τον ικανοποιεί, ταξινομείται ως Passport_Format. Εάν όχι ταξινομείται ως Invalid_Value.
# MAGIC 5. Ταξινόμηση σύμφωνα με το ADT_Institute:\
# MAGIC   5.1. Από αυτή τη διαδικασία εξαιρούνται όσα έχουν ήδη ταξινομηθεί στα προηγούμενα βήματα και οι εγγραφές που δεν έχουν τιμή στο ClPassport.\
# MAGIC   5.2. Αν το ADT_Institute περιέχει αυτά τα λεκτικά ['ΑΤ','ΤΑ','ΥΑ'] και το ClPassport έχει AT_Format -2 γράμματα (Λατινικά & Ελληνικά) and 6 αριθμούς- ή -1 γράμμα (Λατινικά & 
# MAGIC        Ελληνικά) and 6 αριθμούς-, θα κατηγοριοποιηθεί ως ΑΤ_Format αλλιώς ως Invalid_value.\
# MAGIC   5.3. Αν το ADT_Institute περιέχει αυτά τα λεκτικά ['ΓΕΝ','ΓΕΣ','ΓΕΑ','ΓΕΕΘΑ','ΕΛΑΣ','ΕΛΛΑΣ','ΛΣ','ΥΑ','ΕΛ.ΑΣ','ΑΣΤΥΝΟΜΙΑ','ΛΙΜΕΝ','ΠΥΡ','ΣΩΜΑT','ΣΤΡΑΤ'] θα κατηγοριοποιηθεί ως Invalid_Value.\
# MAGIC   5.4. Αν είτε το ADT_Institute είτε το ClPassport περιέχει αυτά τα λεκτικά ['ΔΙΑΒ.','ΔΙΑΒ','ΔΙΑΒΑΤΗΡΙΟ','ΑΔΕΙΑ','ΔΙΑΜΟΝΗ','ΑΣΥΛ','REPU','ΑΡΧΕΣ','Α.Ε.Α./Δ.Δ','ΑΕΑ/ΔΔ','ΔΗΜΟΚΡΑΤΙΑ'], θα κατηγοριοποιηθεί ως Passport_Format.\
# MAGIC   5.5. Αν το ADT_Institute περιέχει το όνομα κάποια χώρας είτε στα αγγλικά είτε στα ελληνικά, θα κατηγοριοποιηθεί ως Passport_Format.
# MAGIC 6. Διαχείριση των εγγραφών που δεν ταξινομήθηκαν μετά την παραπάνω διαδικασία (δλδ. δεν πήραν τιμή στη στήλη Passport_Info_Wemetrix)\
# MAGIC   6.1. Αν το Passport_Info_Wemetrix είναι null και το Passport_Info είναι ίσο με Passport_Format, θα κατηγοριοποιηθεί ως Passport_Format.\
# MAGIC   6.2  Αν το Passport_Info_Wemetrix και το ADT_INSTITUTE είναι null και το Passport_Info είναι ίσο με AT_Format και το ClPassport έχει AT_Format -2 γράμματα (Λατινικά & Ελληνικά) and 6 αριθμούς- ή -1 γράμμα (Λατινικά & Ελληνικά) and 6 αριθμούς-, θα κατηγοριοποιηθεί ως ΑΤ_Format αλλιώς ως Invalid_value.
# MAGIC
# MAGIC ##### Κατόπιν ολοκλήρωσης της διαδικασίας στα συμβόλαια του πίνακα "/dbfs/mnt/databricks/master_table_mnemosyne_2023_05_31.parquet":
# MAGIC 1. Στο cmd 6 βρίσκεται ο αριθμός των συμβολαίων ανά κατηγορία (AT_Format,Invalid_Value,Passport_Format,Army_Police_Format,null).
# MAGIC 2. Στο cmd 7 υπάρχει ένας συγκριτικός πίνακας που δείχνει πόσες εγγραφές έχουν ταξινομηθεί στην ίδια κατηγορία με αυτή του AT_Info και πόσες σε διαφορετική.
# MAGIC 3. Στο cmd 8 βρίσκεται ο αριθμός των συμβολαίων ανά κατηγορία (Passport_Format,Invalid_Value,null).
# MAGIC 4. Στο cmd 9 υπάρχει ένας συγκριτικός πίνακας που δείχνει πόσες εγγραφές έχουν ταξινομηθεί στην ίδια κατηγορία με αυτή του Passport_Info και πόσες σε διαφορετική.
# MAGIC 5. Τα αποτελέσματα αποθηκεύτηκαν στον "dbfs:/FileStore/wemetrix/id_info.parquet"
# MAGIC - Πεδία πίνακα: "SOURCE", "Contract_Account_ID","AT","ClAT","AT_INSTITUTE","AT_Info","ClPassport","ADT_INSTITUTE","Passport_Info","AT_Info_Wemetrix","Passport_Info_Wemetrix"
# MAGIC
# MAGIC Η διαδικασία μπορεί να επαναλαμβάνεται και στα delta με τον παρακάτω κώδικα

# COMMAND ----------

dbutils.widgets.text("input_table",  "wemetrix.foursourcedelta")
input_table = dbutils.widgets.get("input_table")

dbutils.widgets.text("output_table",  "wemetrix.at_pass_info_delta")
output_table = dbutils.widgets.get("output_table")

# COMMAND ----------

import pandas as pd
import numpy as np
import re
import string
import pyspark.sql.functions as F
from pyspark.sql.functions import col, when, length, substring
from pyspark.sql.types import StringType, IntegerType

countries = spark.read.parquet("dbfs:/FileStore/wemetrix/countries_greek_format.parquet")
countries = countries.toPandas()
countries_gr = countries['Country'].tolist()
countries_gr.remove('ΕΛΛΑΔΑ')

countries = spark.read.parquet("dbfs:/FileStore/wemetrix/countries_english_format.parquet")
countries = countries.toPandas()
countries_en= countries['Country'].tolist()
countries_en.remove('Greece')
countries_en = [string for string in countries_en if string is not None]
countries_en = [string.upper() for string in countries_en]

dd_characters_eng_to_greek = {'A': 'Α', 'a': 'α', 'B': 'Β', 'b': 'β', 'G': 'Γ', 'g': 'γ', 'D': 'Δ', 'd': 'δ', 'E': 'Ε', 'e': 'ε','H': 'Η', 'H': 'η', 'Z': 'Ζ', 'z': 'ζ', 'Th': 'Θ', 'th': 'θ', 'I': 'Ι', 'i': 'ι','K': 'Κ', 'k': 'κ', 'L': 'Λ', 'l': 'λ', 'M': 'Μ', 'm': 'μ', 'N': 'Ν', 'n': 'ν', 'X': 'Ξ', 'x': 'ξ', 'O': 'Ο', 'o': 'ο', 'P': 'Π', 'p': 'π', 'R': 'Ρ', 'r': 'ρ', 'S': 'Σ', 's': 'ς', 'T': 'Τ', 't': 'τ', 'U': 'Υ', 'u': 'υ','V': 'Β', 'v': 'β','Y': 'Υ', 'y': 'υ', 'Ph': 'Φ', 'ph': 'φ', 'Kh': 'Χ', 'kh': 'χ', 'Ps': 'Ψ', 'ps': 'ψ','W': 'Ω', 'w': 'ω'}

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

  
condition_1 = (
    (length(F.trim(col("ClAT"))) == 8) &
    (F.upper(F.trim(col("ClAT"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{6}$"))
)

condition_2 = (
    (length(F.trim(col("ClAT"))) == 7) &
    (F.upper(F.trim(col("ClAT"))).rlike("^[A-ZΑ-Ω]{1}[0-9]{6}$"))
)

condition_3 = (
    (length(F.trim(col("ClPassport"))) == 8) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{6}$"))
)

condition_4 = (
    (length(F.trim(col("ClPassport"))) == 7) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{1}[0-9]{6}$"))
)

condition_5 = (
    (length(F.trim(col("ClAT"))) == 9) &
    (F.upper(F.trim(col("ClAT"))).rlike("^[A-Z]{2}[0-9]{7}$"))
)

condition_6 = (
    (length(F.trim(col("ClAT"))) == 8) &
    (F.upper(F.trim(col("ClAT"))).rlike("^[A-Z]{1}[0-9]{7}$"))
)

condition_greece = (
    (length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{7}$"))
)

condition_albania = (
    ((length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{7}$"))) |  ((length(F.trim(col("ClPassport"))) == 10) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{8}$"))) |  ((length(F.trim(col("ClPassport"))) == 8) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{6}$")))
)

condition_georgia = (
    (length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[0-9]{2}[A-ZΑ-Ω]{2}[0-9]{5}$"))
)

condition_pakistan = (
    (length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{7}$"))
)

condition_usa = (
    (length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{0}[0-9]{9}$"))
)

condition_ukraine = (
    (length(F.trim(col("ClPassport"))) == 8) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{6}$"))
)

condition_romania = (
    ((length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{0}[0-9]{9}$"))) | ((length(F.trim(col("ClPassport"))) == 8) &
    ((F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{6}$")) | (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{0}[0-9]{8}$")))) 
)

condition_gbr = (
    (length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{0}[0-9]{9}$"))
)

condition_china = (
    (length(F.trim(col("ClPassport"))) == 9) &
    ((F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{1}[0-9]{8}$")) | (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{7}$")))
)

condition_bangladesh = (
    (length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{7}$"))
)

condition_egypt = (
    (length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{1}[0-9]{8}$"))
)

condition_bulgaria = (
    (length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{0}[0-9]{9}$"))
)

condition_germany = (
    (length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[CFGHJKLMNPRTVWXYZ]{1}[A-ZΑ-Ω0-9]{8}$"))
)

condition_italy = (
    (length(F.trim(col("ClPassport"))) == 9) &
    (F.upper(F.trim(col("ClPassport"))).rlike("^[A-ZΑ-Ω]{2}[0-9]{7}$"))
)



def add_dots(at_institute):
    result = []
    dot_string = '.'.join(at_institute)
    dot_string_dot = dot_string + '.'
    space_string = ' '.join(at_institute)
    result.append(at_institute)
    result.append(dot_string)
    result.append(dot_string_dot)
    result.append(space_string)
    return result

def generate_institutes(list_of_institutes):
    institutes = []
    for i in list_of_institutes:
        institutes.append(add_dots(i))
    return [item for sublist in institutes for item in sublist]

def civil_identification_check(clat):
    if (len(clat) == 8 and clat[:2].isalpha() and clat[2:].isnumeric()) or (len(clat) == 7 and clat[:1].isalpha() and clat[1:].isnumeric()):
        return 'AT_Format'
    else:
        return 'Invalid_value'
    
def passport_identification_check():
    return 'Passport_Format'

def military_identification_check(clat,flag):
    if flag == 0:
        if ((len(clat) == 10 or len(clat) == 9 or len(clat) == 8 or len(clat) == 7 or len(clat) == 6 or len(clat) == 5 or len(clat) == 4) and clat.isnumeric()) or (len(re.findall('[0-9]',clat)) == 9) or (len(re.findall('[0-9]',clat)) == 7) or (len(re.findall('[0-9]',clat)) == 5) or (len(clat) == 7 and clat[:2].isalpha() and clat[2:].isnumeric()) or (len(clat) == 4 and clat[:1].isalpha() and clat[1:].isnumeric()) or (len(clat) == 7 and clat[:2].isnumeric() and clat[2:3].isalpha() and clat[3:].isnumeric()) or (len(clat) == 5 and clat[:1].isalpha() and clat[1:].isnumeric()) or (len(clat) == 9 and clat[:2].isalpha() and clat[2:].isnumeric()) or (len(clat) == 8 and clat[:3].isalpha() and clat[3:].isnumeric()):
            return 'Army_Police_Format'
        else:
            return 'Invalid_value'
    else:
        return 'Invalid_value'


def check_id_type(clat, at, at_institute, flag = 0):
    
    m_condition1,m_condition2,p_condition1,p_condition2,p_condition3,p_condition4,c_condition1 = False,False,False,False,False,False,False
    
    if not pd.isnull(clat) and clat != "":
        m_condition2 = next((True for item in military_institutes if clat.find(item) != -1 ), False)
        if not pd.isnull(at_institute) and at_institute != "":
            at_institute_t = replace_english_characters(dd_characters_eng_to_greek,at_institute)
            m_condition1 = next((True for item in military_institutes if at_institute_t.find(item) != -1 ), False)
            p_condition1 = next((True for item in passport_institutes if at_institute_t.find(item) != -1 ), False)
            p_condition2 = next((True for item in countries_gr if at_institute_t.find(item) != -1), False)
            p_condition3 = next((True for item in countries_en if at_institute.find(item) != -1 ), False)
            p_condition4 = next((True for item in passport_institutes if clat.find(item) != -1 ), False)
            c_condition1 = next((True for item in civil_institutes if at_institute_t.find(item) != -1), False)

    if p_condition1 or p_condition2 or p_condition3 or p_condition4:
        return passport_identification_check()
    elif m_condition1 or m_condition2:
        return military_identification_check(clat,flag)
    elif c_condition1:
        return civil_identification_check(clat)
    
def check_passport_type(clpassport, adt_institute,flag = 1):
    m_condition1,p_condition1,p_condition2,p_condition3,p_condition4,p_condition5,c_condition1 = False,False,False,False,False,False,False

    if not pd.isnull(adt_institute) and adt_institute != "" and not pd.isnull(clpassport) and clpassport != "":
        adt_institute_t = replace_english_characters(dd_characters_eng_to_greek,adt_institute)
        m_condition1 = next((True for item in military_institutes if adt_institute.find(item) != -1 ), False)
        p_condition1 = next((True for item in passport_institutes if adt_institute_t.find(item) != -1), False)
        p_condition2 = next((True for item in countries_gr if re.search(item, adt_institute_t)), False)
        p_condition3 = next((True for item in countries_en if re.search(item, adt_institute)), False)
        p_condition4 = next((True for item in passport_institutes if clpassport.find(item) != -1), False)
        p_condition5 = next((True for item in passport_institutes if adt_institute.find(item) != -1), False)
        c_condition1 = next((True for item in civil_institutes if adt_institute_t.find(item) != -1), False)

    if p_condition1 or p_condition2 or p_condition3 or p_condition4 or p_condition5:
        return passport_identification_check()
    elif c_condition1:
        return civil_identification_check(clpassport)
    elif m_condition1:
        return military_identification_check(clpassport,flag)
    
udf_check_id_type = F.udf(check_id_type, StringType())

udf_check_passport_type = F.udf(check_passport_type, StringType())    

greece = ["GR","HELLAS","ΕΛΛ","ΕΛΑΣ"]
albania = ["ΑΛΒ","ALB"]
georgia = ["GEORGIA","ΓΕΩΡΓΙΑ","GEVRGIA"]
pakistan = ["PAK","ΠΑΚΙ"]
usa = ["USA","ΗΠΑ","ΑΜΕΡΙΚ","Η.Π.Α","STATES","AMERICA","U.S.A"]
ukraine = ["UKR","ΟΥΚΡ"]
romania = ["ROMAN","ΡΟΥΜ","ROYMAN","ROU","ΡΟΜΑΝΙΑ","ROM"]
gbr = ["GBR","ENGL","KINGDOM","ΑΓΓΛ","ΗΝΩΜ","ΒΑΣΙΛ","ΒΡΕΤ","UK","BRIT"]
china = ["CHIN","ΚΙΝΑ","CHN"]
bangladesh = ["BANGLA","ΜΠΑΓ","BGD","BAGL","ΜΠΑΝΓΚΛ"]
egypt = ["EGY","ΑΙΓΥ","ΑΙΓΥΠΤΟΣ"]
bulgaria = ["BULG","ΒΟΥΛΓ","BGR"]
germany = ["GERM","DEUTSC","DEUTC","ΓΕΡΜ"]
italy = ["ITA","ΙΤΑ"]

c_institutes = ['ΑΤ','ΤΑ','ΥΑ']
civil_institutes = generate_institutes(c_institutes)
m_institutes = ['ΓΕΝ','ΓΕΣ','ΓΕΑ','ΓΕΕΘΑ','ΕΛΑΣ','ΕΛΛΑΣ','ΛΣ','ΥΑ','ΕΛ.ΑΣ','ΑΣΤΥΝΟΜΙΑ','ΛΙΜΕΝ','ΠΥΡ','ΣΩΜΑT','ΣΤΡΑΤ']
military_institutes = generate_institutes(m_institutes)
passport_institutes = ['ΔΙΑΒ.','ΔΙΑΒ','ΔΙΑΒΑΤΗΡΙΟ','ΑΔΕΙΑ','ΔΙΑΜΟΝΗ','ΑΣΥΛ','REPU','ΑΡΧΕΣ','Α.Ε.Α./Δ.Δ','ΑΕΑ/ΔΔ','ΔΗΜΟΚΡΑΤΙΑ']
at_passport_institutes = ['ΔΙΑΒ','ΔΙΑΒ.','DIAB','ΔΙ.ΑΒ','ΑΔ','Α.Δ','Α.Δ.','ΑΡΔ','ΑΡ.Δ.','ΑΡ.Δ']

# df_master_table = spark.read.parquet(input_table)
# fotis removed b.AT_INSTITUTE, ,b.ADT_INSTITUTE  because of error
df_master_table = spark.sql(f"SELECT a.*, b.VALID_DATE_FROM_TAUTOTITA ,b.VALID_DATE_TO_TAUTOTITA ,b.CA_Application_Date ,b.VALID_DATE_FROM_DIAVATIRIO ,b.VALID_DATE_TO_DIAVATIRIO ,b.Determination_ID from {input_table} a left join wemetrix.mnemosyne_AT b  on a.contract_account_id = b.contract_account_id   ")

df_master_table1 = df_master_table\
    .filter(F.col("SOURCE") == "SAP")\
    .withColumn("ClAT",F.decode(F.trim(F.regexp_replace(F.upper(F.col("ClAT")), "^A-ZΑ-Ω-0-9", "")),'utf-8'))\
    .withColumn("AT",F.decode(F.trim(F.regexp_replace(F.upper(F.col("AT")), "^A-ZΑ-Ω-0-9", "")),'utf-8'))\
    .withColumn("AT_INSTITUTE",F.trim(F.regexp_replace(F.upper(F.col("AT_INSTITUTE")), "/[^0-9]+/", "")))\
    .withColumn("ADT_INSTITUTE",F.trim(F.regexp_replace(F.upper(F.col("ADT_INSTITUTE")), "/[^0-9]+/", "")))\
    .withColumn("ClPassport",F.decode(F.trim(F.regexp_replace(F.upper(F.col("ClPassport")), "^A-ZΑ-Ω-0-9", "")),'utf-8'))\
    .select("SOURCE", "Contract_Account_ID","AT","ClAT","ClAT_IIS","AT_INSTITUTE","AT_Info","ClPassport","ClPassport_IIS","ADT_INSTITUTE","Passport_Info")
    
# same for passports (GR4476906 2L7d/ A3621026 1L7d)
df_master_table1 = df_master_table1.withColumn(
    "AT_Info_Wemetrix",
    when((condition_1 | condition_2) ,"AT_Format")
    .when((condition_5 | condition_6) ,"Passport_Format")
    .when(F.trim(col("AT_Info"))== "Invalid_value",F.trim(col("AT_Info")))
    .when(F.trim(col("AT_Info"))== "Passport_Format",F.trim(col("AT_Info")))
)


df_master_table1 = df_master_table1.withColumn(
    "Passport_Info_Wemetrix",
    when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(greece)) & F.trim(col("ClPassport")).isNotNull(), when(condition_greece, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(albania)) & F.trim(col("ClPassport")).isNotNull(), when(condition_albania, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(georgia)) & F.trim(col("ClPassport")).isNotNull(), when(condition_georgia, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(pakistan)) & F.trim(col("ClPassport")).isNotNull(), when(condition_pakistan, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(usa)) & F.trim(col("ClPassport")).isNotNull(), when(condition_usa, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(ukraine)) & F.trim(col("ClPassport")).isNotNull(), when(condition_ukraine, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(romania)) & F.trim(col("ClPassport")).isNotNull(), when(condition_romania, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(gbr)) & F.trim(col("ClPassport")).isNotNull(), when(condition_gbr, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(china)) & F.trim(col("ClPassport")).isNotNull(), when(condition_china, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(bangladesh)) & F.trim(col("ClPassport")).isNotNull(), when(condition_bangladesh, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(egypt)) & F.trim(col("ClPassport")).isNotNull(), when(condition_egypt, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(bulgaria)) & F.trim(col("ClPassport")).isNotNull(), when(condition_bulgaria, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(germany)) & F.trim(col("ClPassport")).isNotNull(), when(condition_germany, "Passport_Format").otherwise("Invalid_value"))
    .when(F.trim(col("ADT_INSTITUTE")).rlike("|".join(italy)) & F.trim(col("ClPassport")).isNotNull(), when(condition_italy, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(greece)) & F.trim(col("ClPassport")).isNotNull(), when(condition_greece, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(albania)) & F.trim(col("ClPassport")).isNotNull(), when(condition_albania, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(georgia)) & F.trim(col("ClPassport")).isNotNull(), when(condition_georgia, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(pakistan)) & F.trim(col("ClPassport")).isNotNull(), when(condition_pakistan, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(usa)) & F.trim(col("ClPassport")).isNotNull(), when(condition_usa, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(ukraine)) & F.trim(col("ClPassport")).isNotNull(), when(condition_ukraine, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(romania)) & F.trim(col("ClPassport")).isNotNull(), when(condition_romania, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(gbr)) & F.trim(col("ClPassport")).isNotNull(), when(condition_gbr, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(china)) & F.trim(col("ClPassport")).isNotNull(), when(condition_china, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(bangladesh)) & F.trim(col("ClPassport")).isNotNull(), when(condition_bangladesh, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(egypt)) & F.trim(col("ClPassport")).isNotNull(), when(condition_egypt, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(bulgaria)) & F.trim(col("ClPassport")).isNotNull(), when(condition_bulgaria, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(germany)) & F.trim(col("ClPassport")).isNotNull(), when(condition_germany, "Passport_Format").otherwise("Invalid_value"))
    .when(udf_replace_chars(F.trim(col("ADT_INSTITUTE"))).rlike("|".join(italy)) & F.trim(col("ClPassport")).isNotNull(), when(condition_italy, "Passport_Format").otherwise("Invalid_value"))
)
  

df_results = (df_master_table1\
    .withColumn("AT_Info_Wemetrix",\
        F.when((((F.col("AT_Info_Wemetrix")!="AT_Format") & (F.col("AT_Info_Wemetrix")!="Passport_Format")) | (F.col("AT_Info_Wemetrix").isNull())) & (F.col("Clat").isNotNull()),udf_check_id_type(F.col("ClAT"),F.col("AT"),F.col("AT_INSTITUTE") ))\
            .otherwise(F.col("AT_Info_Wemetrix")) )\
    .withColumn("AT_Info_Wemetrix",\
        F.when((F.col("AT_Info_Wemetrix").isNull() & F.col("AT_Info").isin(["Passport_Format", "Invalid_value"])), F.col("AT_Info"))\
            .otherwise(F.col("AT_Info_Wemetrix")))
    .withColumn("AT_Info_Wemetrix",\
        F.when(F.col("AT").rlike("|".join(at_passport_institutes)),F.lit("Passport_Format"))\
            .otherwise(F.col("AT_Info_Wemetrix")))\
    .withColumn("Passport_Info_Wemetrix",\
        F.when((F.col("Passport_Info_Wemetrix").isNull()) & (F.col("ClPassport").isNotNull()),udf_check_passport_type(F.col("ClPassport"),F.col("ADT_INSTITUTE")))\
            .otherwise(F.col("Passport_Info_Wemetrix")))\
    .withColumn("Passport_Info_Wemetrix",\
        F.when((F.col("Passport_Info_Wemetrix").isNull()) & (F.col("Passport_Info") == "Passport_Format"), F.col("Passport_Info"))\
            .otherwise(F.col("Passport_Info_Wemetrix")))\
    .withColumn("Passport_Info_Wemetrix",\
        F.when((F.col("Passport_Info_Wemetrix").isNull()) & (F.col("Passport_Info") == "AT_Format") & (condition_3 | condition_4), "AT_Format")
        .when((F.col("Passport_Info_Wemetrix").isNull()) & (F.col("ADT_INSTITUTE").isNull()) & (~(condition_3)) & (~(condition_4)), "Invalid_value")
            .otherwise(F.col("Passport_Info_Wemetrix")))
    )

df_results1 = df_results.withColumn(
    "ClAT_IIS_Wemetrix",
    when((F.trim(col("AT_Info_Wemetrix"))!= "Army_Police_Format") & (F.trim(col("AT_Info_Wemetrix"))!= "Passport_Format")  ,F.trim(col("ClAT_IIS")))
    .when((F.trim(col("AT_Info_Wemetrix")) == "Army_Police_Format") ,F.concat(F.lit("ΣΤΡ_"),F.regexp_extract(F.col("ClAT"), '\d+', 0)))
    .when((F.trim(col("AT_Info_Wemetrix")) == "Passport_Format") ,F.concat(F.lit("ΔΙΑΒ_"),F.regexp_replace(F.col("ClAT"),r'(\D+)$',"")))
).withColumn(
    "AT_Institute_Wemetrix",
    when((F.trim(col("AT_Info_Wemetrix"))!= "Army_Police_Format") & (F.trim(col("AT_Info_Wemetrix"))!= "Passport_Format")  ,F.trim(col("AT_INSTITUTE")))
    .when((F.trim(col("AT_Info_Wemetrix")) == "Army_Police_Format") & ((F.trim(col("AT_INSTITUTE")).isNull()) | (F.trim(col("AT_INSTITUTE"))=="")), F.regexp_extract(F.col("ClAT"),"[a-zA-ZΑ-Ωα-ω]+",0))
    .when((F.trim(col("AT_Info_Wemetrix")) == "Army_Police_Format") & ((F.trim(col("AT_INSTITUTE")).isNotNull()) | (F.trim(col("AT_INSTITUTE"))!="")), F.trim(col("AT_INSTITUTE")))
    .when((F.trim(col("AT_Info_Wemetrix")) == "Passport_Format") & ((F.trim(col("AT_INSTITUTE")).isNull()) | (F.trim(col("AT_INSTITUTE"))=="")), F.regexp_extract(F.col("ClAT"),r'(\D+)$',1))
    .when((F.trim(col("AT_Info_Wemetrix")) == "Passport_Format") & ((F.trim(col("AT_INSTITUTE")).isNotNull()) | (F.trim(col("AT_INSTITUTE"))!="")), F.trim(col("AT_INSTITUTE")))
).withColumn(
    "ClPassport_IIS_Wemetrix",
    when(F.trim(col("Passport_Info_Wemetrix"))!= "Passport_Format",F.trim(col("ClPassport_IIS")))
    .when((F.trim(col("Passport_Info_Wemetrix")) == "Passport_Format") ,F.regexp_replace(F.col("ClPassport"),r'(\D+)$',""))
).withColumn(
    "ADT_Institute_Wemetrix",
    when(F.trim(col("Passport_Info_Wemetrix"))!= "Passport_Format",F.trim(col("ADT_INSTITUTE")))
    .when((F.trim(col("Passport_Info_Wemetrix")) == "Passport_Format") & ((F.trim(col("ADT_INSTITUTE")).isNull()) | (F.trim(col("ADT_INSTITUTE"))=="")), F.regexp_extract(F.col("ClPassport"),r'(\D+)$',1))
    .when((F.trim(col("Passport_Info_Wemetrix")) == "Passport_Format") & ((F.trim(col("ADT_INSTITUTE")).isNotNull()) | (F.trim(col("ADT_INSTITUTE"))!="")), F.trim(col("ADT_INSTITUTE")))
)


# merged_df = df_results1.union(df_master_table)
df_results1.write.mode("overwrite").saveAsTable(output_table)
# merged_df.write.mode("overwrite").saveAsTable(output_table)