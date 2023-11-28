from approaches.flow.shared_states import State, StateExit, States, StateStartIntro, StateStartPreperation, VariableExitText, VariableIsBotMale, VariableIsPatientMale, VariablePatientName
from approaches.openai import OpenAI
from approaches.requestcontext import RequestContext

StateGetAge = "GET_AGE"
StateGetIfToContinue = "GET_IF_TO_CONTINUE"
StateGetBotGender = "GET_BOT_GENDER"
StateGetName = "Get_NAME"
StateGetPatientGender = "GET_PATIENT_GENDER"

def start_intro(request_context: RequestContext):
    request_context.set_next_state(StateGetIfToContinue)
    return request_context.write_chat_message("""ברוכים הבאים לכלי סיוע עצמי במצבי מצוקה אחרי אירוע טראומטי. הכלים והידע שכלי זה עושה בהם שימוש מבוססים על פרוטוקול ISP (Immediate Support Protocol)  שנמצא יעיל מחקרית לצמצום רמות חרדה אחרי אירוע טראומטי.  הכלי הוא דיגיטלי ואיננו כולל מעורבות אנושית בפעילותו השוטפת. הטכנולוגיה נועדה להנגיש באופן מסודר ומובנה את התהליך לתמיכה מיידית להרגעה וטיפול עצמי.  
נא לאשר את תנאי השימוש: 
כלי זה כעת בשלב מחקר ופיתוח של חוקרי אקדמיה. בשלב הזה הוא למבוגרים מעל גיל 18, דוברי עברית, ללא אבחנה של מחלה פסיכוטית ושלא חשים מסוכנים לעצמם או לאחרים. אם אתה מתמודד עם מחשבות אובדניות או חושש שתפגע בעצמך או באחר, נא פנה לאחד מגורמי התמיכה הבאים:   
המידע והתרגולים שמוצעים כאן הם למידע כללי בלבד ולא מיועדים לטיפול רפואי או כל טיפול של מקצועות בריאות אחרים. המידע אינו מחליף ייעוץ מקצועי רפואי. השימוש במידע ובתרגולים כאן הוא באחריות המשתמש בלבד. תוכן בן השיח הדיגיטלי הוא לא תחליף לייעוץ, אבחון או טיפול רפואיים. האחריות על השימוש בתומך הדיגיטלי היא על המשתמש בלבד. 
אני יודע שמידע שנאסף כאן נשמר על מנת לחקור את התחום של יעילות כלים דיגיטליים אחרי אירוע טראומטי לצמצום מתחים וכי שום מידע אישי מזהה לא יפורסם במסגרת פרסומים אקדמיים של המחקר.  
ניתן ליצור קשר באימייל: asman@tauex.tau.ac.il
האם ברצונך להמשיך? כן/לא""")
States[StateStartIntro] = State(is_wait_for_user_input_before_state=False, run=start_intro)

def get_if_to_continue(request_context: RequestContext):
    if request_context.history[-1]["content"] == "לא":
        request_context.set_next_state(StateExit)
        request_context.save_to_var(VariableExitText, """תודה שהתעניינת בכלי לסיוע עצמי במצבי מצוקה אחרי אירוע טראומטי. 
הרבה פעמים אחרי שחווים אירוע מאיים או קשה, או במצבים שחוששים מאירועים כאלה, חווים קושי או מצוקה. יש לך אפשרות לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון   
מרכז החוסן הארצי הטיפולי בטלפון  *5486 (פתוח בימים א-ה בין 8.00-20.00) 
ער"ן  טלפון 1201  או ווטסאפ  https://api.whatsapp.com/send/?phone=%2B972545903462&text&type=phone_number&app_absent=0 (השירות מוגש לכל מצוקה ובמגוון שפות, וניתן בצורה אנונימית ומיידית, 24 שעות ביממה בכל ימות השנה)""")
    elif request_context.history[-1]["content"] == "כן":
        request_context.set_next_state(StateGetAge)
        return request_context.write_chat_message("אנא הקלד\י את גילך")
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא הקלד/י כן/לא")
States[StateGetIfToContinue] = State(run=get_if_to_continue)

async def get_age(request_context: RequestContext):
    ageMsg = request_context.history[-1]["content"]
    age = int(ageMsg)
    if age > 18:
        request_context.set_next_state(StateGetBotGender)
        return request_context.write_chat_message("שלום, האם היית מעדיפ/ה לשוחח עם בוט מטפל או מטפלת?")
    elif age > 0:
        request_context.set_next_state(StateExit)
        request_context.save_to_var(VariableExitText, """תודה שהתעניינת בכלי לסיוע עצמי במצבי מצוקה אחרי אירוע טראומטי. כרגע המערכת פתוחה לאנשים מעל גיל 18. היות שהרבה פעמים אחרי שחווים אירוע מאיים או קשה, או במצבים שחוששים מאירועים כאלה, חווים קושי או מצוקה, אם אתה חווה מצוקה, אפשר לפנות לסיוע נפשי ולקבל כלים להתמודדות בגופים שונים כגון   
מרכז החוסן הארצי הטיפולי בטלפון *5486 (פתוח בימים א-ה בין 8.00-20.00) 
ער"ן  טלפון 1201  או ווטסאפ https://api.whatsapp.com/send/?phone=%2B972545903462&text&type=phone_number&app_absent=0 (השירות מוגש לכל מצוקה ובמגוון שפות, וניתן בצורה אנונימית ומיידית, 24 שעות ביממה בכל ימות השנה)""")
    else:
        return request_context.write_chat_message("הגיל שהכנסת אינו חוקי, יש להכניס מספר בלבד")
States[StateGetAge] = State(run=get_age)

def get_bot_gender(request_context: RequestContext):
    if request_context.history[-1]["content"] == "מטפל":
        is_male = True
        bot_name = "יואב"
    elif request_context.history[-1]["content"] == "מטפלת":
        is_male = False
        bot_name = "גולדה"
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא הקלד/י מטפל או מטפלת?")
    
    request_context.save_to_var(VariableIsBotMale, is_male)
    request_context.set_next_state(StateGetName)
    return request_context.write_chat_message("שמי {bot_name}, אני כלי דיגיטלי שמומחה במתן עזרה מיידית למבוגרים שהיו חשופים לאירועי מלחמה או קרב. הפסיכולוגים, החוקרים והמפתחים שפיתחו אותי הסתמכו על ידע מדעי ויכולת טכנולוגית מתקדמת כדי לסייע לך. אמור/אמרי לי בבקשה מה שמך?".format(bot_name = bot_name))
States[StateGetBotGender] = State(run=get_bot_gender)

async def get_name(request_context: RequestContext):
    patient_name = request_context.history[-1]["content"]
    request_context.save_to_var(VariablePatientName, patient_name)
    request_context.set_next_state(StateGetPatientGender)
    return request_context.write_chat_message("האם תרצה/י שאפנה אליך בלשון גבר/אשה?")
States[StateGetName] = State(run=get_name)

async def get_patient_gender(request_context: RequestContext):
    if request_context.history[-1]["content"] == "גבר":
        is_male = True
    elif request_context.history[-1]["content"] == "אשה":
        is_male = False
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא הקלד/י גבר/אשה?")

    request_context.save_to_var(VariableIsPatientMale, is_male)
    request_context.set_next_state(StateStartPreperation)
States[StateGetPatientGender] = State(run=get_patient_gender)