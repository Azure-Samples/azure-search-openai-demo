import asyncio
import re
from azure.data.tables import UpdateMode
from urllib.parse import urlparse
from urllib.parse import parse_qs

from approaches.flow.shared_states import ChatInputNotWait, ChatInputNumeric, ContactsText, DemoClientId, MissingClientId, PartitionKey, State, StateExit, States, StateStartIntro, StateStartPreperation, VariableClientId, VariableExitText, VariableIsBotMale, VariableIsPatientMale, VariablePatientName, VariableShouldSaveClientStatus, chat_input_multiple_options
from approaches.openai import OpenAI
from approaches.requestcontext import RequestContext
from azure.core.exceptions import ResourceNotFoundError

StateGetClientId = "GET_CLIENT_ID"
StateCheckClientId = "CHECK_CLIENT_ID"
StateUserAlreadyParticipated = "USER_ALREADY_PARTICIPATED"
StateGetAge = "GET_AGE"
StateGetIfToContinue = "GET_IF_TO_CONTINUE"
StateGetTosAgreement = "GET_TOS_AGREEMENT"
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
                "role": "introPage",
                "content": "none"
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
    if request_context.history[-1]["content"].strip() == "go-to-tos":
        client_id = request_context.get_var(VariableClientId)
        if request_context.get_var(VariableClientId) != DemoClientId:
            request_context.save_to_var(VariableShouldSaveClientStatus, True)
            entity = {
                "PartitionKey": PartitionKey,
                "RowKey": client_id,
                "Status": "started"
            }
            await request_context.app_resources.table_client.update_entity(mode=UpdateMode.REPLACE, entity=entity)

        request_context.set_next_state(StateGetTosAgreement)
        return request_context.write_roled_chat_message([
            {
                "role": "termsOfServicePage",
                "content": "none"
            }])
    else:
        raise Exception('Unexpected content for get_if_to_continue state.')
States[StateGetIfToContinue] = State(run=get_if_to_continue)

async def get_tos_agreement(request_context: RequestContext):
    if request_context.history[-1]["content"].strip() == "user-accepted-tos":
        request_context.set_next_state(StateGetAge)
        return request_context.write_chat_message("מה גילך ?")
    else:
        raise Exception('Unexpected content for get_tos_agreement state.')
States[StateGetTosAgreement] = State(run=get_tos_agreement)

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
        return request_context.write_chat_message("שלום. לתהליך הנוכחי, מה תעדיפ/י: מטפל או מטפלת?")
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
    return request_context.write_roled_chat_message([
        {
            "role": "explanationText",
            "content": "שמי {bot_name}, אני כלי דיגיטלי שמומחה במתן עזרה מיידית למבוגרים שהיו חשופים לאירועי מלחמה או קרב. הפסיכולוגים, החוקרים והמפתחים שפיתחו אותי הסתמכו על ידע מדעי ויכולת טכנולוגית מתקדמת כדי לסייע לך.".format(bot_name = bot_name)
        },
        {
            "role": "assistant",
            "content": "אמור/אמרי לי בבקשה מה שמך?"
        }])
States[StateGetBotGender] = State(run=get_bot_gender)

async def get_name(request_context: RequestContext):
    patient_name = request_context.history[-1]["content"]
    request_context.save_to_var(VariablePatientName, patient_name)
    request_context.set_next_state(StateGetPatientGender)
    return request_context.write_chat_message("האם תרצה/י שאפנה אליך בלשון גבר/אשה?")
States[StateGetName] = State(run=get_name)

async def get_patient_gender(request_context: RequestContext):
    if request_context.history[-1]["content"].strip() in ("dcr", "גבר", "לשון גבר", "פנה אלי בלשון גבר", "פנה אלי כגבר"):
        is_male = True
    elif request_context.history[-1]["content"].strip() in ("tav", "אשה", "אישה", "לשון אשה", "לשון אישה", "פנה אלי בלשון אשה", "פנה אלי בלשון אישה", "פנה אלי כאשה", "פנה אלי כאישה"):
        is_male = False
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא הקלד/י גבר/אשה?")

    request_context.save_to_var(VariableIsPatientMale, is_male)
    request_context.set_next_state(StateStartPreperation)
States[StateGetPatientGender] = State(run=get_patient_gender)
