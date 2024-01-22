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