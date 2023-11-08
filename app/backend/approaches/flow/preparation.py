from approaches.flow.shared_states import State, StateRedirectToOtherResources, States, StateStartISP, StateStartPreperation
from approaches.requestcontext import RequestContext

StateGetDistressLevel = "GET_DISTRESS_LEVEL"
StateAskIfToContinueOnLowDistress = "ASK_IF_TO_CONTINUE_ON_LOW_DISTRESS"
StateAskWhatAnnoying = "ASK_WHAT_ANNOYING"
StateGetAnnoyingReason = "GET_ANNOYING_REASON"

async def start_preperation(request_context: RequestContext):
    patient_name = request_context.get_var("patientName")
    request_context.set_next_state(StateGetDistressLevel)
    return request_context.write_chat_message("""שלום {patient_name}, ברוך הבא לתהליך ייצוב מיידי, שמטרתו להביא לרגיעה ולהקלה במצוקה פסיכולוגית. תהליך זה עזר לאנשים רבים בעולם. התהליך ייקח כ 10-20 דקות לכל היותר, במהלכן אנחה אותך בשלבים חשובים של הרגעה
יש תרגיל שיכול לעזור לך. זה עזר לאנשים אחרים, זה יעזור לך להרגיש רגוע יותר. אבל לפני שנתחיל, אתה יכול להגיד לי עד כמה אתה מוטרד או חווה מצוקה כרגע (במספר)?
0  לא מוטרד ולא חווה מצוקה כלל,
10 מוטרד או חווה מצוקה ברמה חריפה""".format(patient_name = patient_name))
States[StateStartPreperation] = State(is_wait_for_user_input_before_state=False, run=start_preperation)

async def get_distress_level(request_context: RequestContext):
    distressMsg = request_context.history[-1]["content"]
    distress = int(distressMsg)
    isMale = request_context.get_var("isMale")
    understand = "מבין" if isMale else "מבינה"
    if 5 <= distress and distress <= 10:
        request_context.save_to_var("prefixByDistressLevel", "אני {understand} שאתה חווה מצוקה כרגע, בשביל זה אני כאן".format(understand = understand))
        request_context.set_next_state(StateAskWhatAnnoying)
    elif 2 <= distress and distress <= 4:
        request_context.save_to_var("prefixByDistressLevel", "אני {understand} שאתה חווה מידה מסוימת של מצוקה כרגע, בשביל זה אני כאן".format(understand = understand))
        request_context.set_next_state(StateAskWhatAnnoying)
    elif 0 <= distress and distress <= 1:
        request_context.set_next_state(StateAskIfToContinueOnLowDistress)
        return request_context.write_chat_message("אני {understand} שאינך חווה מצוקה כרגע. האם תרצה לסיים את התהליך כעת?".format(understand = understand))
    else:
        return request_context.write_chat_message("לא הבנתי. עד כמה אתה מוטרד או חווה מצוקה כרגע (0-10)?")
States[StateGetDistressLevel] = State(run=get_distress_level)

async def ask_if_to_continue_on_low_distress(request_context: RequestContext):
    if request_context.history[-1]["content"] == "כן":
        request_context.set_next_state(StateRedirectToOtherResources)
        request_context.save_to_var("exitReason", "תודה, באפשרותך לחזור בשלב מאוחר יותר במידה ותרצה.")
    elif request_context.history[-1]["content"] == "לא":
        request_context.set_next_state(StateAskWhatAnnoying)
        request_context.save_to_var("prefixByDistressLevel", "")
    else:
        return request_context.write_chat_message("לא הבנתי את תגובתך. האם ברצונך לסיים את התהליך כעת? כן/לא")
States[StateAskIfToContinueOnLowDistress] = State(run=ask_if_to_continue_on_low_distress)

async def ask_what_annoying(request_context: RequestContext):
    request_context.set_next_state(StateGetAnnoyingReason)
    return request_context.write_chat_message(request_context.get_var("prefixByDistressLevel") + """
מה הכי מטריד אותך כעת: 
1. אני מרגיש כרגע בסכנה/מאויים
2. אני מרגיש אשם או אחראי על משהו קשה שקרה
3. אני מרגיש חוסר שליטה לגבי מה שקורה עכשיו
4. אני מרגיש חוסר שליטה לגבי איומים או מצבים קשים שעלולים לקרות בעתיד
5. אני דואג וחש חוסר שליטה בנוגע לאנשים שיקרים לי.

שים לב, ייתכן שיותר מתשובה אחת משקפת את מה שאתה מרגיש. בחר אז זו שמשקפת בצורה הכי מדוייקת את מה שאתה מרגיש""")
States[StateAskWhatAnnoying] = State(is_wait_for_user_input_before_state=False, run=ask_what_annoying)

async def get_annoying_reason(request_context: RequestContext):
    isp_path = request_context.history[-1]["content"]
    if not(isp_path in ["1", "2", "3", "4", "5"]):
        return request_context.write_chat_message("לא הבנתי את תגובתך. מה מהאפשרויות הנל הכי מטריד אותך כעת?")
    request_context.save_to_var("ispPath", isp_path)
    request_context.set_next_state(StateStartISP)
States[StateGetAnnoyingReason] = State(run=get_annoying_reason)
