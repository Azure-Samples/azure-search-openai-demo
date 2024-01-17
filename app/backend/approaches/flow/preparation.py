from approaches.flow.shared_states import ChatInputNotWait, ChatInputNumeric, ContactsText, State, StateExit, States, StateStartISP, StateStartPreperation, VariableDistressLevel, VariableExitText, VariableFirstDistressLevel, VariableIsBotMale, VariableIsPatientMale, VariableIspPath, VariablePatientName, chat_input_multiple_options
from approaches.requestcontext import RequestContext

StateGetDistressLevel = "GET_DISTRESS_LEVEL"
StateAskIfToContinueOnLowDistress = "ASK_IF_TO_CONTINUE_ON_LOW_DISTRESS"
StateAskWhatAnnoying = "ASK_WHAT_ANNOYING"
StateGetAnnoyingReason = "GET_ANNOYING_REASON"

async def start_preperation(request_context: RequestContext):
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    patient_name = request_context.get_var(VariablePatientName)
    request_context.set_next_state(StateGetDistressLevel)
    return request_context.write_chat_message("""עד כמה {you} {annoyed} או חווה מצוקה כרגע (במספר)?""".format(
        you = "אתה" if is_patient_male else "את",
        annoyed = "מוטרד" if is_patient_male else "מוטרדת"))
States[StateStartPreperation] = State(chat_input=ChatInputNotWait, run=start_preperation)

async def get_distress_level(request_context: RequestContext):
    distress_msg = request_context.history[-1]["content"]
    distress = int(distress_msg)
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    request_context.save_to_var(VariableDistressLevel, distress)
    request_context.save_to_var(VariableFirstDistressLevel, distress)
    if 0 <= distress and distress <= 1:
        request_context.set_next_state(StateAskIfToContinueOnLowDistress)
        return request_context.write_chat_message("אני {understand} שאינך חווה מצוקה כרגע. האם {want} לסיים את התהליך כעת?".format(understand = "מבין" if is_patient_male else "מבינה", want = "תרצה" if is_patient_male else "תרצי"))
    elif 2 <= distress and distress <= 10:
        request_context.set_next_state(StateAskWhatAnnoying)
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} מספר בין 0 ל-10".format(type = "הקלד" if request_context.get_var(VariableIsPatientMale) else "הקלידי"))
States[StateGetDistressLevel] = State(chat_input=ChatInputNumeric, run=get_distress_level)

async def ask_if_to_continue_on_low_distress(request_context: RequestContext):
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    if request_context.history[-1]["content"].strip() in ("fi", "כן"):
        request_context.set_next_state(StateExit)
        request_context.save_to_var(VariableExitText, """תודה שהתעניינת בכלי לסיוע עצמי במצבי מצוקה אחרי אירוע טראומטי. לעתים, גם אחרי שחווים אירוע מאיים או קשה, אין חווים תחושת קושי או מצוקה. אם {will_feel} בשלב כלשהו מצוקה {able} להשתמש בכלי זה או לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון
{contactsText}""".format(
                will_feel = "תחוש" if is_patient_male else "תחושי",
                able = "תוכל" if is_patient_male else "תוכלי",
                contactsText = ContactsText))
    elif request_context.history[-1]["content"].strip() in ("kt", "לא"):
        request_context.set_next_state(StateAskWhatAnnoying)
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא הקלד כן/לא")
States[StateAskIfToContinueOnLowDistress] = State(chat_input=chat_input_multiple_options(["כן", "לא"]), run=ask_if_to_continue_on_low_distress)

async def ask_what_annoying(request_context: RequestContext):
    request_context.set_next_state(StateGetAnnoyingReason)
    distress = request_context.get_var(VariableDistressLevel)
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    if 2 <= distress and distress <= 10:
        understand = "מבין" if is_bot_male else "מבינה"
        prefixByDistressLevel = "אני {understand} {that_you} חווה {some}מצוקה כרגע, בשביל זה אני כאן".format(understand = understand, that_you = "שאתה" if is_patient_male else "שאת", some = "מידה מסוימת של " if distress <= 4 else "")
    else:
        prefixByDistressLevel = ""
    return request_context.write_roled_chat_message([
        {
            "role": "explanationText",
            "content": prefixByDistressLevel + """
מה הכי מטריד אותך כרגע?
1. אני {feel} <span style="font-weight: bolder">בסכנה/{threatened}</span>
2. אני {feel} <span style="font-weight: bolder">{guilty}</span> על משהו קשה שקרה
3. אני {feel} חוסר שליטה לגבי מה שקורה <span style="font-weight: bolder">עכשיו</span>
4. אני {feel} חוסר שליטה לגבי דברים שעלולים לקרות <span style="font-weight: bolder">בעתיד</span>
5. אני {concerned_and_feel} חוסר שליטה בנוגע <span style="font-weight: bolder">לאנשים שיקרים לי</span>""".format(
                feel = "מרגיש" if is_patient_male else "מרגישה",
                threatened = "מאויים" if is_patient_male else "מאויימת",
                guilty = "אשם" if is_patient_male else "אשמה",
                concerned_and_feel = "דואג וחש" if is_patient_male else "דואגת וחשה")
        }]);
States[StateAskWhatAnnoying] = State(chat_input=ChatInputNotWait, run=ask_what_annoying)

async def get_annoying_reason(request_context: RequestContext):
    isp_path = request_context.history[-1]["content"]
    if not(isp_path in ["1", "2", "3", "4", "5"]):
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} מספר בין 1 ל-5".format(type = "הקלד" if request_context.get_var(VariableIsPatientMale) else "הקלידי"))
    request_context.save_to_var(VariableIspPath, isp_path)
    request_context.set_next_state(StateStartISP)
States[StateGetAnnoyingReason] = State(chat_input=ChatInputNumeric, run=get_annoying_reason)
