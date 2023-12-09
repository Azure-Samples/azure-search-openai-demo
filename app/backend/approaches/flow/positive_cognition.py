from approaches.flow.shared_states import State, StateExit, StateStartPositiveCognition, States, VariableExitText, VariableIsBotMale, VariableIsPatientMale, VariableIspPath, get_exit_text
from approaches.requestcontext import RequestContext
from approaches.videos import get_video

StateGetImprovement = "GET_IMPROVEMENT"
StateGetIsConnectedToCurrent = "GET_IS_CONNECTED_TO_CURRENT"

async def start_positive_cognition(request_context: RequestContext):
    request_context.set_next_state(StateGetImprovement)
    return request_context.write_chat_message("""באיזו מידה {you_feel} שיפור ביכולת שלך להתמודד עם החוויה? ללא שיפור / שיפור מועט / שיפור קל / שיפור בינוני / שיפור גדול""".format(you_feel = "אתה מרגיש" if request_context.get_var(VariableIsPatientMale) else "את מרגישה"))
States[StateStartPositiveCognition] = State(is_wait_for_user_input_before_state=False, run=start_positive_cognition)

async def get_improvement(request_context: RequestContext):
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    is_improved = request_context.history[-1]["content"].strip()
    if is_improved in ["שיפור מועט", "שיפור קל", "שיפור בינוני", "שיפור גדול", "מועט", "קל", "בינוני", "גדול"]:
        prefix = """אני {happy} לראות {that_you_succeeding} לעזור לעצמך באמצעות התרגול.""".format(
            happy = "שמח" if is_bot_male else "שמחה",
            that_you_succeeding = "שאתה מצליח" if is_patient_male else "שאת מצליחה")
    elif is_improved in ("ללא שיפור", "ללא"):
        prefix = "אני {understand}, עם זאת חשוב לציין שחלק מהאנשים לא חווים שיפור מיד בסוף התרגול אלא מאוחר יותר, ויתכן {feel} שיפור בהמשך ".format(understand = "מבין" if is_bot_male else "מבינה", feel = "שתחוש" if is_patient_male else "שתחושי")
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} ללא שיפור/שיפור מועט/שיפור גדול".format(type = "הקלד" if request_context.get_var(VariableIsPatientMale) else "הקלידי"))
    
    request_context.set_next_state(StateGetIsConnectedToCurrent)
    return request_context.write_chat_message(prefix + """
עד כמה {feel_current} לכאן ועכשיו, ולהכיר בעובדה שגם אם קרה אירוע קשה, אותו אירוע נגמר ?

כלל לא / במידה מועטה / במידה מתונה / במידה רבה / במידה רבה מאד""".format(feel_current = "אתה מרגיש שאתה מסוגל להיות מחובר" if is_patient_male else "את מרגישה שאת מסוגלת להיות מחוברת"))
States[StateGetImprovement] = State(run=get_improvement)

async def get_is_connected_to_current(request_context: RequestContext):
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    is_connected = request_context.history[-1]["content"]
    if is_connected == "כלל לא":
        exit_text = "אני {understand}, ורוצה להזכיר לך {that_you_here} איתי כאן ועכשיו. בנוסף חשוב לי לציין שלפעמים אחרי אירוע קשה לוקח זמן להתחבר שוב להווה. יתכן שהתהליך הזה יתרחש בהמשך".format(
            understand = "מבין" if is_bot_male else "מבינה",
            that_you_here = "שאתה נמצא" if is_bot_male else "שאת נמצאת"
        )
    elif is_connected in ["במידה מועטה", "במידה מתונה", "במידה רבה", "במידה רבה מאד"]:
        exit_text = "אני {happy} לראות שלמרות מה שחווית {that_you_succeeding} להתחבר להווה.".format(
            happy = "שמח" if is_bot_male else "שמחה",
            that_you_succeeding = "שאתה מצליח" if is_patient_male else "שאת מצליחה")
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} כלל לא/במידה מועטה/במידה מתונה/במידה רבה/במידה רבה מאד".format(type = "הקלד" if request_context.get_var(VariableIsPatientMale) else "הקלידי"))
    exit_text += """
""" + get_exit_text(request_context)
    request_context.save_to_var(VariableExitText, exit_text)
    request_context.set_next_state(StateExit)
States[StateGetIsConnectedToCurrent] = State(run=get_is_connected_to_current)