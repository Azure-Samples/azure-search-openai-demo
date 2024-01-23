from typing import Callable
from approaches.localization.glob import glob
from approaches.localization.he import he
from approaches.localization.he_femalepatient import heFemalePatient
from approaches.localization.he_femalepatient_femalebot import heFemalePatientFemaleBot
from approaches.localization.he_femalepatient_malebot import heFemalePatientMaleBot
from approaches.localization.he_malepatient import heMalePatient
from approaches.localization.he_malepatient_femalebot import heMalePatientFemaleBot
from approaches.localization.he_malepatient_malebot import heMalePatientMaleBot


Strings = {}
Strings[glob["id"]] = glob
Strings[he["id"]] = he
Strings[heFemalePatient["id"]] = heFemalePatient
Strings[heFemalePatientFemaleBot["id"]] = heFemalePatientFemaleBot
Strings[heFemalePatientMaleBot["id"]] = heFemalePatientMaleBot
Strings[heMalePatient["id"]] = heMalePatient
Strings[heMalePatientFemaleBot["id"]] = heMalePatientFemaleBot
Strings[heMalePatientMaleBot["id"]] = heMalePatientMaleBot

StringIds = {
    False: {
        False: heFemalePatientFemaleBot["id"],
        True: heFemalePatientMaleBot["id"],
    },
    True: {
        False: heMalePatientFemaleBot["id"],
        True: heMalePatientMaleBot["id"],
    }
}

def get_strings_id(is_patient_male: bool ,is_bot_male: bool):
    return StringIds[is_patient_male][is_bot_male]

def get_string_by_key(key, strings_id, request_context):
    strings = Strings[strings_id]
    while "parent" in strings and not(key in strings):
        strings = Strings[strings["parent"]]
    if not(key in strings):
        raise Exception("String output " + key + " does not exist for " + strings_id)
    output = strings[key]
    if isinstance(output, Callable):
        output = output(request_context)
    return output