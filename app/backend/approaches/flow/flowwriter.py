import json
from approaches.flow.flow import FirstState, States
from approaches.flow.shared_states import VariableIspPath, VariablePatientName, VariableVideoIndex
from approaches.localization.strings import get_string_by_key, get_strings_id

dummy_variables = {
    VariablePatientName: "<שם משתמש\ת>",
    VariableIspPath: "1",
    VariableVideoIndex: 1,
}

class DummyRequestContext:
    def get_var(self, var_name):
        return dummy_variables[var_name]

def write_flow_html(is_patient_male: bool, is_bot_male: bool):
    strings_id = get_strings_id(is_patient_male, is_bot_male)
    request_context = DummyRequestContext()
    seen_states = {FirstState: True}
    pending_states: list[str] = [FirstState]
    result = "<html><head><title>Flow</title></head><body dir=rtl>"
    while len(pending_states) > 0:
        state_id = pending_states[0]
        pending_states.remove(pending_states[0])
        result += "<h1>" + state_id + "</h1>"
        no_condition = False
        had_any = False
        for ca in States[state_id].conditioned_actions[0]:
            if no_condition:
                result += "&lt;שגיאה בקוד - לוגיקה נוספת אחרי 'אחרת'&gt;"
                break
            no_condition = ca.condition is None
            if had_any:
                result += "<br>"
                if no_condition:
                    result += "אחרת:<br>"
                else:
                    result += "אחרת, "
            
            had_any = True
            if not no_condition:
                result += "אם " + ("&lt;חסר תיאור תנאי&gt;" if ca.condition_description is None else ca.condition_description) + ":<br>"
            
            result += "<div style='margin-right: 20px'>"
            
            if not (ca.next_state is None or ca.next_state in seen_states):
                seen_states[ca.next_state] = True
                pending_states.append(ca.next_state)
            if not (ca.custom_action is None):
                result += "בצע לוגיקה מיוחדת<br>"
            else:
                if not (ca.output is None):
                    output = get_string_by_key(ca.output, strings_id, request_context)
                    result += "שלח הודעה:<br><div style='margin-right: 40px'>"
                    if isinstance(output, str):
                        result += "<pre>" + output + "</pre>"
                    else:
                        for roled in output:
                            result += "הצג הודעה בתור " + roled["role"] + ":<br><div style='margin-right: 60px'><pre>" + roled["content"] + "</pre></div>"
                    result += "</div><br>"
                result += "עבור ל-" + ca.next_state + "<br>"
            
            result += "</div><br>"

    result += "<br><br><br>"
    for state_id in States:
        if not (state_id in seen_states):
            result += "שגיאה בקוד - חסרה התייחסות למצב " + state_id + "<br>"

    return result + "</body></html>"