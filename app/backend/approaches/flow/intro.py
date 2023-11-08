from approaches.flow.shared_states import State, StateRedirectToOtherResources, States, StateStartIntro, StateStartPreperation
from approaches.openai import OpenAI
from approaches.requestcontext import RequestContext

StateGetAge = "GET_AGE"
StateGetIfToContinue = "GET_IF_TO_CONTINUE"
StateGetBotGender = "GET_BOT_GENDER"
StateGetName = "Get_NAME"
StateGetGender = "GET_GENDER"
StateAskForFeeling = "ASK_FOR_FEELING"
StateEmpathyToFeelings = "EMPATHY_TO_FEELINGS"

def start_intro(request_context: RequestContext):
    request_context.set_next_state(StateGetAge)
    return request_context.write_chat_message("""ברוכים הבאים לכלי סיוע עצמי במצבי מצוקה אחרי אירוע טראומטי. הכלים והידע שכלי זה עושה בהם שימוש מבוססים על פרוטוקול ISP (Immediate Support Protocol)  שנמצא יעיל מחקרית לצמצום רמות חרדה אחרי אירוע טראומטי.  הכלי הוא דיגיטלי ואיננו כולל מעורבות אנושית בפעילותו השוטפת. הוא כולל טכנולוגיה של בינה מלאכותית יוצרת כדי לשפר את חווית המשתמש בו, אך בעיקרו נועד להנגיש באופן מסודר ומובנה את הפרוטוקול לתמיכה מיידית לשימוש עצמי. 
אנא אשר את תנאי השימוש שלנו:
השימוש בכלי זה נמצא כעת בשלב מחקר ופיתוח בקרב חוקרי אקדמיה. בשלב הזה הוא נועד למבוגרים מעל גיל 18, דוברי עברית, שאינם מאובחנים עם מחלה פסיכוטית ושאינם מתמודדים חשים מסוכנים לעצמם או לאחרים. אם אתה מתמודד עם מחשבות אובדניות או חושש שתפגע בעצמך או באחר, נא פנה לאחד מגורמי התמיכה הבאים:  
המידע והתרגולים שמוצעים כאן הם למידע כללי בלבד ולא מיועדים לטיפול רפואי או כל טיפול של מקצועות בריאות אחרים. המידע אינו מחליף ייעוץ מקצועי רפואי. השימוש במידע ובתרגולים כאן הוא באחריות המשתמש בלבד. תוכן בן השיח הדיגיטלי הוא לא תחליף לייעוץ, אבחון או טיפול רפואיים. האחריות על השימוש בתומך הדיגיטלי היא על המשתמש/ת בלבד.
אני יודע/ת שמידע שנאסף כאן נשמר על מנת לחקור את התחום של יעילות כלים דיגיטליים אחרי אירוע טראומטי לצמצום מתחים וכי שום מידע אישי מזהה לא נאסף.
ניתן ליצור קשר באימייל: amirt@tauex.tau
אנא הקלד/י את גילך:""")
States[StateStartIntro] = State(is_wait_for_user_input_before_state=False, run=start_intro)

async def get_age(request_context: RequestContext):
    ageMsg = request_context.history[-1]["content"]
    age = int(ageMsg)
    if age > 18:
        request_context.set_next_state(StateGetIfToContinue)
        return request_context.write_chat_message("האם ברצונך להמשיך? כן/לא")
    elif age > 0:
        request_context.set_next_state(StateRedirectToOtherResources)
        request_context.save_to_var("exitReason", "בשלב זה הכלי נועד למבוגרים מעל גיל 18")
    else:
        return request_context.write_chat_message("הגיל שהכנסת אינו חוקי, יש להכניס מספר בלבד")
States[StateGetAge] = State(run=get_age)

def get_if_to_continue(request_context: RequestContext):
    if request_context.history[-1]["content"] == "לא":
        request_context.set_next_state(StateRedirectToOtherResources)
        request_context.save_to_var("exitReason", "תודה, באפשרותך לחזור בשלב מאוחר יותר בזמן שיתאים לך.")
    elif request_context.history[-1]["content"] == "כן":
        request_context.set_next_state(StateGetBotGender)
        return request_context.write_chat_message("שלום, האם היית מעדיף לשוחח עם בוט מטפל או מטפלת?")
    else:
        return request_context.write_chat_message("לא הבנתי את תגובתך. האם ברצונך להמשיך? כן/לא")
States[StateGetIfToContinue] = State(run=get_if_to_continue)

def get_bot_gender(request_context: RequestContext):
    if request_context.history[-1]["content"] == "מטפל":
        isMale = True
        bot_name = "יואב"
    elif request_context.history[-1]["content"] == "מטפלת":
        isMale = False
        bot_name = "גולדה"
    else:
        return request_context.write_chat_message("לא הבנתי את תגובתך. האם היית מעדיף לשוחח עם בוט מטפל או מטפלת?")
    
    request_context.save_to_var("isMale", isMale)
    request_context.set_next_state(StateGetName)
    return request_context.write_chat_message("שמי {bot_name}, אני כלי בינה מלאכותית שמומחה במתן עזרה פסיכולוגית מיידית למבוגרים שהיו חשופים לאירועי מלחמה או קרב. הפסיכולוגים, החוקרים והמפתחים שפיתחו אותי הסתמכו על ידע מדעי ויכולת טכנולוגית מתקדמת כדי לסייע לך. אמור לי בבקשה מה שמך?".format(bot_name = bot_name))
States[StateGetBotGender] = State(run=get_bot_gender)

async def get_name(request_context: RequestContext):
    patient_name = request_context.history[-1]["content"]
    request_context.save_to_var("patientName", patient_name)
    request_context.set_next_state(StateStartPreperation)
States[StateGetName] = State(run=get_name)

# Clean?

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