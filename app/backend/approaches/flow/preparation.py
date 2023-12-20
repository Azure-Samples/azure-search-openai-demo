from approaches.flow.shared_states import ContactsText, State, StateExit, States, StateStartISP, StateStartPreperation, VariableDistressLevel, VariableExitText, VariableFirstDistressLevel, VariableIsBotMale, VariableIsPatientMale, VariableIspPath, VariablePatientName
from approaches.requestcontext import RequestContext

StateGetDistressLevel = "GET_DISTRESS_LEVEL"
StateAskIfToContinueOnLowDistress = "ASK_IF_TO_CONTINUE_ON_LOW_DISTRESS"
StateAskWhatAnnoying = "ASK_WHAT_ANNOYING"
StateGetAnnoyingReason = "GET_ANNOYING_REASON"

async def start_preperation(request_context: RequestContext):
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    patient_name = request_context.get_var(VariablePatientName)
    request_context.set_next_state(StateGetDistressLevel)
    return request_context.write_roled_chat_message([
        {
            "role": "explanationText",
            "content": """שלום {patient_name}, {welcome} לתהליך ייצוב מיידי, שמטרתו להביא לרגיעה ולהקלה במצוקה פסיכולוגית. תהליך זה עזר לאנשים רבים בעולם. התהליך ייקח כ 10-20 דקות לכל היותר, במהלכן אנחה אותך בשלבים חשובים של הרגעה.
יש תרגיל שיכול לעזור לך. זה עזר לאנשים אחרים, זה יעזור לך להרגיש {calm} יותר.""".format(
                patient_name = patient_name,
                welcome = "ברוך הבא" if is_patient_male else "ברוכה הבאה",
                calm = "רגוע" if is_patient_male else "רגועה")
        },
        {
            "role": "assistant",
            "content": """אבל לפני שנתחיל, {can_you} להגיד לי עד כמה {you} {annoyed} או חווה מצוקה כרגע (במספר)?
0  לא {annoyed} ולא חווה מצוקה כלל,
10 {annoyed} או חווה מצוקה ברמה חריפה""".format(
                can_you = "אתה יכול" if is_patient_male else "את יכולה",
                you = "אתה" if is_patient_male else "את",
                annoyed = "מוטרד" if is_patient_male else "מוטרדת")
        }])
States[StateStartPreperation] = State(is_wait_for_user_input_before_state=False, run=start_preperation)

async def get_distress_level(request_context: RequestContext):
    distress_msg = request_context.history[-1]["content"]
    distress = int(distress_msg)
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    request_context.save_to_var(VariableDistressLevel, distress)
    request_context.save_to_var(VariableFirstDistressLevel, distress)
    if 0 <= distress and distress <= 1:
        request_context.set_next_state(StateAskIfToContinueOnLowDistress)
        return request_context.write_chat_message("אני {understand} שאינך חווה מצוקה כרגע. האם {want} לסיים את התהליך כעת?".format(understand = "מבין" if is_patient_male else "מבינה", want = "תרצה" if is_bot_male else "תרצי"))
    elif 2 <= distress and distress <= 10:
        request_context.set_next_state(StateAskWhatAnnoying)
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} מספר בין 0 ל-10".format(type = "הקלד" if request_context.get_var(VariableIsPatientMale) else "הקלידי"))
States[StateGetDistressLevel] = State(run=get_distress_level)

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
States[StateAskIfToContinueOnLowDistress] = State(run=ask_if_to_continue_on_low_distress)

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
מה הכי מטריד אותך כעת: 
1. אני {feel} כרגע בסכנה/{threatened}
2. אני {feel} {guilty_or_accountable} על משהו קשה שקרה
3. אני {feel} חוסר שליטה לגבי מה שקורה עכשיו
4. אני {feel} חוסר שליטה לגבי איומים או מצבים קשים שעלולים לקרות בעתיד
5. אני {concerned_and_feel} חוסר שליטה בנוגע לאנשים שיקרים לי.""".format(
                feel = "מרגיש" if is_patient_male else "מרגישה",
                threatened = "מאויים" if is_patient_male else "מאויימת",
                guilty_or_accountable = "אשם או אחראי" if is_patient_male else "אשמה או אחראית",
                concerned_and_feel = "דואג וחש" if is_patient_male else "דואגת וחשה")
        },
        {
            "role": "assistant",
            "content": "{notice}, ייתכן שיותר מתשובה אחת משקפת את {that_you_feel}. {select} את זו שמשקפת בצורה הכי מדוייקת את {that_you_feel}.".format(
                notice = "שים לב" if is_patient_male else "שימי לב",
                select = "בחר" if is_patient_male else "בחרי",
                that_you_feel = "מה שאתה מרגיש" if is_patient_male else "מה שאת מרגישה")
        }]);
States[StateAskWhatAnnoying] = State(is_wait_for_user_input_before_state=False, run=ask_what_annoying)

async def get_annoying_reason(request_context: RequestContext):
    isp_path = request_context.history[-1]["content"]
    if not(isp_path in ["1", "2", "3", "4", "5"]):
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} מספר בין 1 ל-5".format(type = "הקלד" if request_context.get_var(VariableIsPatientMale) else "הקלידי"))
    request_context.save_to_var(VariableIspPath, isp_path)
    request_context.set_next_state(StateStartISP)
States[StateGetAnnoyingReason] = State(run=get_annoying_reason)
