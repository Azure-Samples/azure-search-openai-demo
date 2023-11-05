from approaches.flow.shared_states import State, States, StateStartIntro
from approaches.openai import OpenAI
from approaches.requestcontext import RequestContext

StateGetIfToContinue = "GET_IF_TO_CONTINUE"
StateRedirectToOtherResources = "REDIRECT_OTHER_RESOURCES"
StateEndLoop = "END_LOOP"
StateGetBotGender = "GET_BOT_GENDER"
StateGetName = "Get_NAME"
StateGetGender = "GET_GENDER"
StateAskForFeeling = "ASK_FOR_FEELING"
StateEmpathyToFeelings = "EMPATHY_TO_FEELINGS"

def start_intro(request_context: RequestContext):
    request_context.set_next_state(StateGetIfToContinue)
    return request_context.write_chat_message("זהו בוט מבוסס בינה מלאכותית שמומחה בעזרה פסיכולוגית מיידית למבוגרים שהיו חשופים לאירועי מלחמה או קרב, בנו אותי חוקרים ומפתחים שמומחים בנושא על סמך ידע מדעי ויכולת טכנולוגית עצומה במיוחד כדי לסייע לך. הוא לא נועד לשימוש במקרים דחופים, בהם יש לפנות לנציג אנושי כמו ער""ן או מיון בריאות נפש. האם ברצונך להמשיך?")
States[StateStartIntro] = State(is_wait_for_user_input_before_state=False, run=start_intro)

def get_if_to_continue(request_context: RequestContext):
    if request_context.history[-1]["content"] == "לא":
        request_context.set_next_state(StateRedirectToOtherResources)
    elif request_context.history[-1]["content"] != "כן":
        return request_context.write_chat_message("לא הבנתי את תגובתך. יש לענות בכן\לא בלבד. האם ברצונך להמשיך?")
    else:
        request_context.set_next_state(StateGetBotGender)
        return request_context.write_chat_message("יופי! האם עלי להיות בוט זכר או נקבה?")
States[StateGetIfToContinue] = State(run=get_if_to_continue)

def redirect_to_other_resources(request_context: RequestContext):
    request_context.set_next_state(StateEndLoop)
    return request_context.write_chat_message("באפשרותך לפנות לער""ן, פרטים נוספים: https://www.eran.org.il/online-emotional-help/. כמו כן באפשרותך להתקשר למד""א 101")
States[StateRedirectToOtherResources] = State(is_wait_for_user_input_before_state=False, run=redirect_to_other_resources)

def end_loop(request_context: RequestContext):
    # Just ignore input and redirect to other resources
    return request_context.set_next_state(StateRedirectToOtherResources)
States[StateEndLoop] = State(run=end_loop)

def get_bot_gender(request_context: RequestContext):
    if request_context.history[-1]["content"] == "זכר":
        isMale = True
        botName = "יואב"
    elif request_context.history[-1]["content"] == "נקבה":
        isMale = False
        botName = "גולדה"
    else:
        return request_context.write_chat_message("לא הבנתי את תגובתך. יש לענות בזכר\נקבה בלבד. האם תרצה בוט זכר או נקבה?")
    
    request_context.save_to_var("isMale", isMale)
    if isMale:
        prefix = "שמי יואב, אני בוט מבוסס בינה מלאכותית שמומחה"
    else:
        prefix = "שמי גולדה, אני בוטית מבוססת בינה מלאכותית שמומחית"
    request_context.set_next_state(StateGetName)
    return request_context.write_chat_message(prefix + " בעזרה פסיכולוגית מיידית למבוגרים שהיו חשופים לאירועי מלחמה או קרב, בנו אותי חוקרים ומפתחים שמומחים בנושא על סמך ידע מדעי ויכולת טכנולוגית עצומה במיוחד כדי לסייע לך. מה שמך?")
States[StateGetBotGender] = State(run=get_bot_gender)

async def get_name(request_context: RequestContext):
    patient_name = request_context.history[-1]["content"]
    request_context.save_to_var("patientName", patient_name)
    extra_info, chat_coroutine = await OpenAI.run(
        request_context,
        system_prompt="ענה מהו מגדר המשתמש לפי השם שהמשתמש מכניס. ענה באחת משלוש אפשרויות בלבד: זכר, נקבה או לא ניתן לדעת",
        should_stream=False,
        history=[{"content": patient_name}]
    )

    gender = OpenAI.extract_nonstreamed_response(chat_coroutine)
    if gender == "זכר":
        isMale = True
    elif gender == "נקבה":
        isMale = False
    else:
        request_context.set_next_state(StateGetGender)
        return request_context.write_chat_message("האם עלי לפנות אליך כזכר או כנקבה?")
    request_context.set_next_state(StateAskForFeeling)
    request_context.save_to_var("patientIsMale", isMale)
States[StateGetName] = State(run=get_name)

async def get_gender(request_context: RequestContext):
    if request_context.history[-1]["content"] == "זכר":
        isMale = True
    elif request_context.history[-1]["content"] == "נקבה":
        isMale = False
    else:
        return request_context.write_chat_message("לא הבנתי את תגובתך. האם עלי לפנות אליך כזכר או כנקבה?")
    
    request_context.save_to_var("patientIsMale", isMale)
    request_context.set_next_state(StateAskForFeeling)
States[StateGetGender] = State(run=get_gender)

async def ask_for_feeling(request_context: RequestContext):
    isMale = request_context.get_var("patientIsMale")
    msg = "שלום {patient_name}, ".format(patient_name=request_context.get_var("patientName"))
    msg = "ברוך הבא" if isMale else "ברוכה הבאה"
    msg += " לתהליך ייצוב מיידי, שמטרתו להביא לרגיעה ולהקלה במצוקה פסיכולוגית. תהליך זה עזר לאנשים רבים בעולם. התהליך ייקח כ10-20 דקות, במהלכן אקח אותך דרך השלבים החשובים לעבור תהליך הרגעה ועיבוד. בכל שלב "
    msg += "אתה יכול" if isMale else "את יכולה"
    msg += "לכתוב לי אם יש לך שאלות או דבר מה "
    msg += "שתרצה" if isMale else "שתרצי"
    msg += """ לשתף אותי בו.
אשמח לדעת ממש בקצרה מה מטריד אותך, ?אני רק צריך לשמוע תיאור קצר מאוד. """
    msg += "אתה לא חייב לספר לי? " if isMale else "את לא חייבת לספר לי?"

    request_context.set_next_state(StateEmpathyToFeelings)
    return request_context.write_chat_message(msg)
States[StateAskForFeeling] = State(is_wait_for_user_input_before_state=False, run=ask_for_feeling)

async def empathy_to_feelings(request_context: RequestContext):
    extra_info, chat_coroutine = await OpenAI.run(
        request_context,
        system_prompt="תן תגובה ממנה הנבדק יבין שהבנת מה הוא אמר, תתייחס באופן אימפטי מאוד בקצרה אל תהיה נועז בתגובה אל תפרש אל תשייך לנבדק רגשות תחושות או מצבים שלא דיווח עליהם, השתדל להיות קשוב ומינימליסטי ולהצמד למה שאמר אבל לא לחזור בצורה טלגרפית"
    )
    request_context.set_response_extra_info(extra_info)
    return chat_coroutine
States[StateEmpathyToFeelings] = State(run=empathy_to_feelings)