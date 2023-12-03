from typing import Callable

from approaches.requestcontext import RequestContext

StateStartIntro = "START_INTRO"
StateStartPreperation = "START_PREPERATION"
StateStartISP = "START_ISP"
StateStartPositiveCognition = "START_POSITIVE_COGNITION"

StateAskIfToExit = "ASK_IF_TO_EXIT"
StateExit = "EXIT"
StateEndLoop = "END_LOOP"

States = {}

VariableReturnToState = "returnToState"
VariableDistressLevel = "prefixByDistressLevel"
VariableExitText = "exitText"
VariableFirstDistressLevel = "firstDistressLevel"
VariableIsBotMale = "isBotMale"
VariableIsPatientMale = "isPatientMale"
VariableIspPath = "ispPath"
VariableIsUserExited = "isUserExited"
VariableNextVideoPrefix = "nextVideoPrefix"
VariablePatientName = "patientName"
VariableSumDistressLevel = "sumDistressLevel"
VariableVideoIndex = "videoIndex"
VariableWasDistressLevelIncreased = "wasDistressLevelIncreased"
VariableWasDistressLevelIncreasedTwice = "wasDistressLevelIncreasedTwice"

def get_exit_text(request_context: RequestContext):
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    is_user_exited = request_context.get_var(VariableIsUserExited)
    first_distress = request_context.get_var(VariableFirstDistressLevel)
    last_distress = request_context.get_var(VariableDistressLevel)
    sum_distress_level = request_context.get_var(VariableSumDistressLevel)
    was_distress_level_increased = request_context.get_var(VariableWasDistressLevelIncreased)
    was_distress_level_increased_twice = request_context.get_var(VariableWasDistressLevelIncreasedTwice)
    video_index = request_context.get_var(VariableVideoIndex)
    contacts = """
טלפון מרכז החוסן הארצי הטיפולי *5486 (פתוח בימים א-ה בין 8.00-20.00)
טלפון ער"ן  טלפון 1201 או ווטסאפ https://api.whatsapp.com/send/?phone=%2B972545903462&text&type=phone_number&app_absent=0 (השירות מוגש לכל מצוקה ובמגוון שפות, וניתן בצורה אנונימית ומיידית, 24 שעות ביממה בכל ימות השנה)"""
    if was_distress_level_increased_twice or (was_distress_level_increased and is_user_exited) or (first_distress <= last_distress):
        return """לפני שנסיים אני רוצה להזכיר לך שהתגובות שחווית מאוד הגיוניות. הרבה פעמים אחרי שחווים אירוע מאיים או קשה או במצבים שחוששים מאירועים כאלה חווים קושי או מצוקה. אני רוצה לציין בפניך את העובדה שיש לך אפשרות לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון:{contacts}""".format(
            contacts = contacts)

    if video_index == 7 and first_distress > last_distress:
        improvement_description = "שתיארת שיפור בין תחילת התרגול לסיומו ולעודד אותך לעשות שימוש בתרגול שעשינו"
    elif video_index == 7 and sum_distress_level / 8 < first_distress:
        improvement_description = "שבמהלך התרגול תיארת נקודות של שיפור ולכן תוכל לבחור לעשות שימוש בתרגול שעשינו".format(can_choose = "תוכל לבחור" if is_bot_male else "תוכלי לבחור")
    else:
        improvement_description = "שתיארת שיפור בעקבות התרגול ולעודד אותך לעשות שימוש בתרגול שעשינו"

    return """לפני שנסיים אני רוצה להזכיר לך שהתגובות שחווית מאוד הגיוניות. הרבה פעמים אחרי שחווים אירוע מאיים או קשה או במצבים שחוששים מאירועים כאלה חווים קושי או מצוקה. אני רוצה לציין בפניך את העובדה {improvement_description} אם {will_feel} שוב מצוקה. בנוסף אני רוצה לציין כי {you_might} לחוות בהמשך כל מיני קשיים, שהם טבעיים ונורמליים כמו תמונות של מה שקרה או {that_you_afraid} שיקרה, קושי בשינה, ומספר רגשות כמו מצוקה, פחד או כעס. אם {experience} אותם, מומלץ לך להשתמש בתרגול שעשינו.
אם {you_notice} לב שהתגובות האלה לא פוחתות, או נמשכות יותר מ 2-3 ימים, אני מעודד אותך לפנות לאחד מהגופים הבאים, שיוכלו לעזור לך להתמודד עם התגובות האלו:{contacts}
אני מקווה שסייעתי לך {wish} לך הקלה משמעותית נוספת במצבך""".format(
        improvement_description = improvement_description,
        will_feel = "תחוש" if is_patient_male else "תחושי",
        you_might = "אתה עלול" if is_patient_male else "את עלולה",
        that_you_afraid = "שאתה חושש" if is_patient_male else "שאת חוששת",
        experience = "תחווה" if is_patient_male else "תחווי",
        you_notice = "אתה שם" if is_patient_male else "את שמה",
        contacts = contacts,
        wish = "ומאחל" if is_bot_male else "ומאחלת")

class State:
    def __init__(self, run: Callable, is_wait_for_user_input_before_state: bool = True):
        self.is_wait_for_user_input_before_state = is_wait_for_user_input_before_state
        self.run = run

def exit_loop(request_context: RequestContext):
    request_context.set_next_state(StateEndLoop)
    return request_context.write_chat_message(request_context.get_var(VariableExitText))
States[StateExit] = State(is_wait_for_user_input_before_state=False, run=exit_loop)

def end_loop(request_context: RequestContext):
    # Just ignore input and redirect to other resources
    return request_context.set_next_state(StateExit)
States[StateEndLoop] = State(run=end_loop)

async def ask_if_to_exit(request_context: RequestContext):
    if request_context.history[-1]["content"] == "כן":
        request_context.set_next_state(StateExit)
    elif request_context.history[-1]["content"] == "לא":
        request_context.set_next_state(request_context.get_var(VariableReturnToState))
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא הקלד כן/לא")
States[StateAskIfToExit] = State(run=ask_if_to_exit)