import asyncio
import re
from azure.data.tables import UpdateMode
from urllib.parse import urlparse
from urllib.parse import parse_qs

from approaches.flow.shared_states import ChatInputNotWait, ChatInputNumeric, ContactsText, DemoClientId, GenericExitText, MissingClientId, PartitionKey, State, StateExit, States, StateStartIntro, StateStartPreperation, VariableClientId, VariableExitText, VariableIsBotMale, VariableIsPatientMale, VariablePatientName, VariableShouldSaveClientStatus, chat_input_multiple_options
from approaches.openai import OpenAI
from approaches.requestcontext import RequestContext
from azure.core.exceptions import ResourceNotFoundError

StateGetClientId = "GET_CLIENT_ID"
StateCheckClientId = "CHECK_CLIENT_ID"
StateUserAlreadyParticipated = "USER_ALREADY_PARTICIPATED"
StateGetAge = "GET_AGE"
StateGetIfToContinue = "GET_IF_TO_CONTINUE"
StateGetBotGender = "GET_BOT_GENDER"
StateGetName = "Get_NAME"
StateGetPatientGender = "GET_PATIENT_GENDER"

digits = ("אחת", "שתיים", "שלוש", "ארבע", "חמש", "שש", "שבע", "שמונה", "תשע")
decades = ("עשרים", "שלושים", "ארבעים", "חמישים", "שישים", "שבעים", "שמונים", "תשעים")
text_to_number = {
    "שנה": 1,
    "שנתיים": 2,
    "עשר": 10,
    "מאה": 100
}
digit_number = 0
for digit in digits:
    digit_number += 1
    text_to_number[digit] = digit_number
    text_to_number[digit + " עשרה"] = digit_number + 10
decade_number = 1
for decade in decades:
    decade_number += 1
    text_to_number[decade] = decade_number * 10
    digit_number = 0
    for digit in digits:
        digit_number += 1
        text_to_number[decade + "ו" + digit] = decade_number * 10 + digit_number

async def start_intro(request_context: RequestContext):
    client_id = request_context.history[-1]["content"]
    request_context.save_to_var(VariableClientId, client_id)
    request_context.save_to_var(VariableShouldSaveClientStatus, False)
    if client_id == DemoClientId:
        entity = { "Status": "new" }
    elif client_id == MissingClientId:
        request_context.save_to_var(VariableExitText, "כניסה ללא זיהוי משתמש לא אפשרית כרגע. נא לפנות לצוות לקבלת קישור")
        request_context.set_next_state(StateExit)
        return
    else:
        try:
            entity = await request_context.app_resources.table_client.get_entity(partition_key=PartitionKey, row_key=client_id)
        except ResourceNotFoundError:
            request_context.save_to_var(VariableExitText, "אירעה שגיאה בזיהוי. ייתכן כי הקישור לא תקין. נא לפנות לצוות לקבלת קישור חדש")
            request_context.set_next_state(StateExit)
            return

    if entity["Status"] == "new":
        request_context.set_next_state(StateGetIfToContinue)
        return request_context.write_roled_chat_message([
            {
                "role": "explanationText",
                "content": """ברוכים הבאים לכלי סיוע עצמי במצבי מצוקה. הכלי מבוסס על פרוטוקול (Immediate Support Protocol) שפותחה על ידי ד""ר גרי דיאמונד ושנמצאה יעילה להפחתת קושי וחרדה. הכלי הוא דיגיטלי ואיננו כולל מעורבות אנושית בפעילותו השוטפת. הטכנולוגיה נועדה להנגיש באופן מסודר ומובנה את התהליך לייצוב מיידי.
<span style="font-weight: bolder">נא לאשר את תנאי השימוש:</span>
כלי זה כעת בשלב מחקר ופיתוח. בשלב הזה הוא למבוגרים מעל גיל 18, דוברי עברית, ללא אבחנה של מחלה פסיכוטית ושאינם מסוכנים לעצמם או לאחרים. כל המידע והתרגולים שמוצעים אינם מחליפים טיפול רפואי או פרה-רפואי, והינם באחריות המשתמש בלבד. כמו כן, המידע יישמר לצורך בקרה ומחקר, והינו אנונימי. לשאלות/מידע נוסף ניתן ליצור קשר באימייל: asman@tauex.tau.ac.il

<span style="font-weight: bolder; text-decoration: underline">אם את\ה מתמודד\ת עם מחשבות אובדניות או חושש\ת שתפגע\י בעצמך או באחרים, ניתן לפנות לאחד מגורמי התמיכה הבאים: </span>
{contactsText}

""".format(contactsText = ContactsText)
            },
            {
                "role": "assistant",
                "content": "האם ברצונך להמשיך? כן/לא"
            }])
        
    if entity["Status"] == "finished":
        request_context.save_to_var(VariableExitText, """השתתפותך כבר הסתיימה, תודה! יש לך אפשרות לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון
{contactsText}""".format(contactsText = ContactsText))
    elif entity["Status"] == "started":
        request_context.save_to_var(VariableExitText, "השתתפותך נקטעה בעבר באופן לא צפוי, נא לפנות לצוות לקבלת קישור חדש")
    else:
        request_context.save_to_var(VariableExitText, "אירעה שגיאה. ייתכן כי הקישור לא תקין. נא לפנות לצוות לקבלת קישור חדש")
    request_context.set_next_state(StateExit)
States[StateStartIntro] = State(chat_input=ChatInputNotWait, run=start_intro)

async def get_if_to_continue(request_context: RequestContext):
    if request_context.history[-1]["content"].strip() in ("kt", "לא", "ממש לא", "אין מצב", "די", "מספיק"):
        request_context.set_next_state(StateExit)
        request_context.save_to_var(VariableExitText, GenericExitText)
    elif request_context.history[-1]["content"].strip() in ("fi", "כן", "רוצה", "מוכן", "מוכנה", "בסדר", "בטח", "סבבה"):
        client_id = request_context.get_var(VariableClientId)
        if request_context.get_var(VariableClientId) != DemoClientId:
            request_context.save_to_var(VariableShouldSaveClientStatus, True)
            entity = {
                "PartitionKey": PartitionKey,
                "RowKey": client_id,
                "Status": "started"
            }
            await request_context.app_resources.table_client.update_entity(mode=UpdateMode.REPLACE, entity=entity)

        request_context.set_next_state(StateGetAge)
        return request_context.write_chat_message("מה גילך ?")
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. נא להקליד כן/לא")
States[StateGetIfToContinue] = State(chat_input=chat_input_multiple_options(["כן", "לא"]), run=get_if_to_continue)

def user_already_participated(request_context: RequestContext):
    return request_context.write_chat_message("""השתתפותך כבר רשומה.""")
States[StateUserAlreadyParticipated] = State(run=user_already_participated)

async def get_age(request_context: RequestContext):
    ageMsg = request_context.history[-1]["content"].strip()
    if ageMsg in text_to_number:
        age = text_to_number[ageMsg]
    else:
        age = int(ageMsg)
    if age >= 18:
        request_context.set_next_state(StateGetBotGender)
        return request_context.write_chat_message("לתהליך הנוכחי, מה תעדיפ/י?")
    elif age > 0:
        request_context.set_next_state(StateExit)
        request_context.save_to_var(VariableExitText, """תודה שהתעניינת בכלי לסיוע עצמי במצבי מצוקה אחרי אירוע טראומטי. כרגע המערכת פתוחה לאנשים מעל גיל 18. היות שהרבה פעמים אחרי שחווים אירוע מאיים או קשה, או במצבים שחוששים מאירועים כאלה, חווים קושי או מצוקה, אם אתה חווה מצוקה, אפשר לפנות לסיוע נפשי ולקבל כלים להתמודדות בגופים שונים כגון
{contactsText}""".format(contactsText = ContactsText))
    else:
        return request_context.write_chat_message("הגיל שהכנסת אינו חוקי, יש להכניס מספר בלבד")
States[StateGetAge] = State(chat_input=ChatInputNumeric, run=get_age)

def get_bot_gender(request_context: RequestContext):
    has_male = not(re.search("מטפל(?!ת)", request_context.history[-1]["content"]) is None) or not(re.search("nypk(?!,)", request_context.history[-1]["content"]) is None)
    has_female = "מטפלת" in request_context.history[-1]["content"] or "nypk," in request_context.history[-1]["content"]
    if has_male and not has_female:
        is_male = True
        bot_name = "יואב"
    elif has_female and not has_male:
        is_male = False
        bot_name = "גולדה"
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא הקלד/י מטפל או מטפלת?")
    
    request_context.save_to_var(VariableIsBotMale, is_male)
    request_context.set_next_state(StateGetName)
    return request_context.write_chat_message("מה שמך?")
States[StateGetBotGender] = State(chat_input=chat_input_multiple_options(["מטפלת", "מטפל"]), run=get_bot_gender)

async def get_name(request_context: RequestContext):
    patient_name = request_context.history[-1]["content"]
    request_context.save_to_var(VariablePatientName, patient_name)
    request_context.set_next_state(StateGetPatientGender)
    return request_context.write_chat_message("איך לפנות אליך/אלייך?")
States[StateGetName] = State(run=get_name)

async def get_patient_gender(request_context: RequestContext):
    if request_context.history[-1]["content"].strip() in ("dcr", "גבר", "לשון גבר", "פנה אלי בלשון גבר", "פנה אלי כגבר", "זכר"):
        is_male = True
    elif request_context.history[-1]["content"].strip() in ("tav", "אשה", "אישה", "לשון אשה", "לשון אישה", "פנה אלי בלשון אשה", "פנה אלי בלשון אישה", "פנה אלי כאשה", "פנה אלי כאישה", "נקבה"):
        is_male = False
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא הקלד/י נקבה/זכר?")

    request_context.save_to_var(VariableIsPatientMale, is_male)
    request_context.set_next_state(StateStartPreperation)
States[StateGetPatientGender] = State(chat_input=chat_input_multiple_options(["זכר", "נקבה"]), run=get_patient_gender)
