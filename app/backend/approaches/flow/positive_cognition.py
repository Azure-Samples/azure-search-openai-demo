from approaches.flow.shared_states import State, StateExit, StateStartPositiveCognition, States, VariableExitText, VariableIsBotMale, VariableIsPatientMale, VariableIspPath
from approaches.requestcontext import RequestContext
from approaches.videos import get_video

StateGetImprovement = "GET_IMPROVEMENT"
StateGetIsConnectedToCurrent = "GET_IS_CONNECTED_TO_CURRENT"

async def start_positive_cognition(request_context: RequestContext):
    request_context.set_next_state(StateGetImprovement)
    return request_context.write_chat_message("""באיזו מידה {you_feel} שיפור ביכולת שלך להתמודד עם החוויה? ללא שיפור/שיפור מועט/שיפור גדול""".format(you_feel = "אתה מרגיש" if request_context.get_var(VariableIsPatientMale) else "את מרגישה"))
States[StateStartPositiveCognition] = State(is_wait_for_user_input_before_state=False, run=start_positive_cognition)

async def get_improvement(request_context: RequestContext):
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    is_improved = request_context.history[-1]["content"]
    if is_improved == "שיפור מועט" or is_improved == "שיפור גדול":
        prefix = """אני {happy} לראות {that_you_succeeding} לעזור לעצמך באמצעות התרגול""".format(
            happy = "שמח" if is_bot_male else "שמחה",
            that_you_succeeding = "שאתה מרגיש" if is_patient_male else "את מצליחה")
    elif is_improved == "ללא שיפור":
        prefix = "אני {understand}, עם זאת חשוב לציין שחלק מהאנשים לא חווים שיפור מיד בסוף התרגול אלא מאוחר יותר, ויתכן {feel} שיפור בהמשך ".format(understand = "מבין" if is_bot_male else "מבינה", feel = "שתחוש" if is_patient_male else "שתחושי")
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} ללא שיפור/שיפור מועט/שיפור גדול".format(type = "הקלד" if request_context.get_var(VariableIsPatientMale) else "הקלידי"))
    if request_context.get_var(VariableIspPath) == "1":
        request_context.set_next_state(StateGetIsConnectedToCurrent)
        return request_context.write_chat_message(prefix + """
עד כמה {feel_current} לכאן ועכשיו, ולהכיר בעובדה שגם אם קרה אירוע קשה, אותו אירוע נגמר?
כלל לא/במידה מועטה/במידה מתונה/במידה רבה/במידה רבה מאד""".format(feel_current = "אתה מרגיש שאתה מסוגל להיות מחובר" if is_patient_male else "את מרגישה שאת מסוגלת להיות מחוברת"))
    else:
        request_context.save_to_var(VariableExitText, prefix)
        request_context.set_next_state(StateExit)
States[StateGetImprovement] = State(run=get_improvement)

async def get_is_connected_to_current(request_context: RequestContext):
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    is_connected = request_context.history[-1]["content"]
    if is_connected == "כלל לא":
        exitText = "אני {understand}, ורוצה להזכיר לך {that_you_here} איתי כאן ועכשיו. בנוסף חשוב לי לציין שלפעמים אחרי אירוע קשה לוקח זמן להתחבר שוב להווה. יתכן שהתהליך הזה יתרחש בהמשך".format(
            understand = "מבין" if is_bot_male else "מבינה",
            that_you_here = "שאתה נמצא" if is_bot_male else "שאת נמצאת"
        )
    elif is_connected in ["במידה מועטה", "במידה מתונה", "במידה רבה", "במידה רבה מאד"]:
        exit_text = "אני {happy} לראות שלמרות מה שחווית {that_you_succeeding} להתחבר להווה".format(
            happy = "שמח" if is_bot_male else "שמחה",
            that_you_succeeding = "שאתה מרגיש" if is_patient_male else "את מצליחה")
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} כלל לא/במידה מועטה/במידה מתונה/במידה רבה/במידה רבה מאד".format(type = "הקלד" if request_context.get_var(VariableIsPatientMale) else "הקלידי"))
    exit_text += """
לפני שנסיים אני רוצה להזכיר לך שהתגובות שחווית מאוד הגיוניות. הרבה פעמים אחרי שחווים אירוע מאיים או קשה או במצבים שחוששים מאירועים כאלה חווים קושי או מצוקה. אני רוצה לציין בפניך את העובדה שתיארת שיפור בעקבות התרגול ולעודד אותך לעשות שימוש בתרגול שעשינו אם {will_feel} שוב מצוקה. בנוסף אני רוצה לציין כי {you_might} לחוות בהמשך כל מיני קשיים, שהם טבעיים ונורמליים כמו תמונות של מה שקרה או {that_you_afraid} שיקרה, קושי בשינה, ומספר רגשות כמו מצוקה, פחד או כעס. אם {experience} אותם, מומלץ לך להשתמש בתרגול שעשינו.
אם {you_notice} לב שהתגובות האלה לא פוחתות, או נמשכות יותר מ 2-3 ימים, {call} אלינו ונוכל לכוון אותך לאלה שיכולים לעזור לך להתמודד עם התגובות האלה. אני מקווה שסייעתי לך {wish} לך הקלה משמעותית נוספת במצבך""".format(
        will_feel = "תחוש" if is_patient_male else "תחושי",
        you_might = "אתה עלול" if is_patient_male else "את עלולה",
        that_you_afraid = "שאתה חושש" if is_patient_male else "שאת חוששת",
        experience = "תחווה" if is_patient_male else "תחווי",
        you_notice = "אתה שם" if is_patient_male else "את שמה",
        call = "פנה" if is_patient_male else "פני",
        wish = "מאחל" if is_bot_male else "מאחלת" 
)
    request_context.save_to_var(VariableExitText, exit_text)
    request_context.set_next_state(StateExit)
States[StateGetIsConnectedToCurrent] = State(run=get_is_connected_to_current)