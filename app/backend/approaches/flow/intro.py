import asyncio
import re
from azure.data.tables import UpdateMode
from urllib.parse import urlparse
from urllib.parse import parse_qs

from approaches.flow.shared_states import ChatInputNotWait, ConditionedAction, DemoClientId, MissingClientId, PartitionKey, State, StateExit, States, StateStartIntro, StateStartPreperation, VariableClientId, VariableIsBotMale, VariableIsPatientMale, VariablePatientName, VariableShouldSaveClientStatus, VariableStringsId, chat_input_multiple_options, chat_input_numeric
from approaches.localization.strings import get_strings_id
from approaches.openai import OpenAI
from approaches.requestcontext import RequestContext
from azure.core.exceptions import ResourceNotFoundError

StateGetClientId = "GET_CLIENT_ID"
StateCheckClientId = "CHECK_CLIENT_ID"
StateUserAlreadyParticipated = "USER_ALREADY_PARTICIPATED"
StateGetAge = "GET_AGE"
StateGetIfToContinue = "GET_IF_TO_CONTINUE"
StateGetTosAgreement = "GET_TOS_AGREEMENT"
StateUpdateStatusStarted = "UPDATE_STATUS_STARTED"
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

async def before_start_intro(request_context: RequestContext, client_id: str):
    request_context.save_to_var(VariableClientId, client_id)
    request_context.save_to_var(VariableShouldSaveClientStatus, False)
    request_context.save_to_var(VariableStringsId, "he")
async def read_table(request_context: RequestContext, client_id: str):
    try:
        entity = await request_context.app_resources.table_client.get_entity(partition_key=PartitionKey, row_key=client_id)
    except ResourceNotFoundError:
        return ConditionedAction(output="authFailed", next_state=StateExit, condition=None, condition_description=None)

    if entity["Status"] == "new":
        return ConditionedAction(output="introPage", next_state=StateGetIfToContinue, condition=None, condition_description=None)

    output = "participationDone" if entity["Status"] == "finished" else "participationCutInThePast" if entity["Status"] == "started" else "statusUnexpected"
    return ConditionedAction(output=output, next_state=StateExit, condition=None, condition_description=None)
States[StateStartIntro] = State(chat_input=ChatInputNotWait, action_before=before_start_intro, conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: input == DemoClientId, output="introPage", next_state=StateGetIfToContinue, condition_description="משתמש דמו"),
    ConditionedAction(condition=lambda request_context, input: input == MissingClientId, output="mustUserId", next_state=StateExit, condition_description="לא סופק זיהוי משתמש"),
    ConditionedAction(condition=None, output=None, next_state=StateGetIfToContinue, condition_description=None, custom_action=read_table)
])

async def raise_unexpected_tos(request_context, tos_agreement: str):
    raise Exception('Unexpected content for get_if_to_continue state.')
States[StateGetIfToContinue] = State(conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: input.strip() != "go-to-tos", output=None, next_state=None, condition_description=None, custom_action=lambda request_context, input: raise_unexpected_tos),
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableClientId) == DemoClientId, output="termsOfServicePage", next_state=StateGetTosAgreement, condition_description="משתמש\ת דמו הסכימ\ה לתנאי השימוש"),
    ConditionedAction(condition=None, output="termsOfServicePage", next_state=StateUpdateStatusStarted, condition_description="המשתמש\ת הסכימ\ה לתנאי השימוש"),
])

async def update_status_started(request_context: RequestContext, tos_aggreement: str):
    client_id = request_context.get_var(VariableClientId)
    request_context.save_to_var(VariableShouldSaveClientStatus, True)
    entity = {
        "PartitionKey": PartitionKey,
        "RowKey": client_id,
        "Status": "started"
    }
    await request_context.app_resources.table_client.update_entity(mode=UpdateMode.REPLACE, entity=entity)
States[StateUpdateStatusStarted] = State(action_before=update_status_started, chat_input=ChatInputNotWait, conditioned_actions=[
    ConditionedAction(condition=None, output=None, next_state=StateGetTosAgreement, condition_description=None)
])

async def raise_unexpected_tos_agreement(request_context: RequestContext, input: str):
    raise Exception('Unexpected content for get_tos_agreement state.')
States[StateGetTosAgreement] = State(conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: input.strip() == "user-accepted-tos", output="whatIsYourAge", next_state=StateGetAge, condition_description="אישור תנאי השימוש וודא במערכת"),
    ConditionedAction(condition=None, output=None, next_state=None, condition_description=None, custom_action=raise_unexpected_tos_agreement)
])

States[StateGetAge] = State(chat_input=chat_input_numeric(0, "0", 120, "120"), conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: (text_to_number[input.strip()] if input.strip() in text_to_number else int(input.strip())) >= 18, output="chooseBotGender", next_state=StateGetBotGender, condition_description="המשתמש\ת מעל גיל 18"),
    ConditionedAction(condition=lambda request_context, input: (text_to_number[input.strip()] if input.strip() in text_to_number else int(input.strip())) > 0, output="ageLessThan18", next_state=StateExit, condition_description="הגיל מספרי גדול מאפס"),
    ConditionedAction(condition=None, output="illegalAge", next_state=StateGetAge, condition_description=None),
])

def get_bot_gender(request_context: RequestContext, input: str):
    has_male = not(re.search("מטפל(?!ת)", input) is None) or not(re.search("nypk(?!,)", input) is None)
    has_female = "מטפלת" in input or "nypk," in input
    if has_male ^ has_female:
        request_context.save_to_var(VariableIsBotMale, has_male)
States[StateGetBotGender] = State(chat_input=chat_input_multiple_options(["מטפלת", "מטפל"]), action_before=get_bot_gender, conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: request_context.has_var(VariableIsBotMale), output="whatIsYourName", next_state=StateGetName, condition_description="מגדר המטפל\ת נקלט בהצלחה"),
    ConditionedAction(condition=None, output="botGenderInputWrong", next_state=StateGetBotGender, condition_description=None)
])

async def get_name(request_context: RequestContext, input: str):
    request_context.save_to_var(VariablePatientName, input)
States[StateGetName] = State(action_before=get_name, conditioned_actions=[
    ConditionedAction(condition=None, output="choosePatientGender", next_state=StateGetPatientGender, condition_description=None)
])

async def get_patient_gender(request_context: RequestContext, input: str):
    if request_context.history[-1]["content"].strip() in ("dcr", "גבר", "לשון גבר", "פנה אלי בלשון גבר", "פנה אלי כגבר", "זכר"):
        is_patient_male = True
    elif request_context.history[-1]["content"].strip() in ("tav", "אשה", "אישה", "לשון אשה", "לשון אישה", "פנה אלי בלשון אשה", "פנה אלי בלשון אישה", "פנה אלי כאשה", "פנה אלי כאישה", "נקבה"):
        is_patient_male = False
    else:
        return

    is_bot_male = request_context.get_var(VariableIsBotMale)
    stringsId = get_strings_id(is_patient_male, is_bot_male)
    request_context.save_to_var(VariableStringsId, stringsId)
    request_context.save_to_var(VariableIsPatientMale, is_patient_male)
States[StateGetPatientGender] = State(action_before=get_patient_gender, chat_input=chat_input_multiple_options(["זכר", "נקבה"]), conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: request_context.has_var(VariableIsPatientMale), output=None, next_state=StateStartPreperation, condition_description="מגדר המטופל\ת נקלט בהצלחה"),
    ConditionedAction(condition=None, output="patientGenderInputWrong", next_state=StateGetPatientGender, condition_description=None)
])
