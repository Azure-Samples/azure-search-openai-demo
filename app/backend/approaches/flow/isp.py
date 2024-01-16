from approaches.flow.shared_states import ChatInputNotWait, ChatInputNumeric, ContactsText, GenericExitText, State, StateExit, StateStartISP, StateStartPositiveCognition, States, VariableDistressLevel, VariableExitText, VariableIsBotMale, VariableIsPatientMale, VariableIsUserExited, VariableIspPath, VariablePatientName, VariableSumDistressLevel, VariableVideoIndex, VariableWasDistressLevelIncreased, VariableWasDistressLevelIncreasedTwice, chat_input_multiple_options, chat_input_slider, get_exit_text
from approaches.requestcontext import RequestContext
from approaches.videos import get_video

StateWaitForResponseBeforeVideo = "WAIT_FOR_RESPONSE_BEFORE_VIDEO"
StateShowVideo = "SHOW_VIDEO"
StateGetIfToContinueAfterVideo = "GET_IF_TO_CONTINUE_AFTER_VIDEO"
StateAskForDistressAfterVideo = "ASK_FOR_DISTRESS_AFTER_VIDEO"
StateGetDistressAfterVideo = "GET_DISTRESS_LEVEL_AFTER_VIDEO"
StateNextVideo = "NEXT_VIDEO"

async def start_isp(request_context: RequestContext):
    request_context.save_to_var(VariableSumDistressLevel, 0)
    request_context.save_to_var(VariableVideoIndex, 0)
    request_context.save_to_var(VariableWasDistressLevelIncreased, False)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    isp_path = request_context.get_var(VariableIspPath)
    patient_name = request_context.get_var(VariablePatientName)
    prefixDict = {
        "1": "זו חוויה מאוד הגיונית שהרבה אנשים חווים. התרגול שנעשה כעת יוכל להקל עליך, הוא ידוע כתרגול שעזר לאנשים רבים",
        "2": "מחשבות לגבי אחריות ואשמה נפוצות אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה יוכל להקל עליך",
        "3": "לעתים לאחר אירוע מאיים, שבו חווינו חוסר שליטה, התחושה הזו ממשיכה ללוות אותנו לזמן מה. התרגול שנעשה כעת יוכל להקל עליך",
        "4": "מחשבות לגבי חוסר שליטה לגבי מצבים קשים עתידיים נפוצות אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה כעת יוכל להקל עליך",
        "5": "זו תחושה טבעית אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה כעת יוכל להקל עליך"
    }
    request_context.set_next_state(StateWaitForResponseBeforeVideo)
    return request_context.write_chat_message("""{patient_name}, {prefix}. בדקות הקרובות אנחה אותך בתרגול.

אציג לך וידאו שילמד אותך לעשות תרגיל לייצוב מיידי.""".format(
        patient_name = patient_name,
        prefix = prefixDict[isp_path]))
States[StateStartISP] = State(chat_input=ChatInputNotWait, run=start_isp)

async def wait_for_response_before_video(request_context: RequestContext):
    response = request_context.history[-1]["content"]
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    if response == "הפעל סרטון":
        request_context.set_next_state(StateShowVideo)
    elif response == "ברצוני לסיים":
        request_context.save_to_var(VariableIsUserExited, True)
        request_context.save_to_var(VariableExitText, GenericExitText)
        request_context.set_next_state(StateExit)
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} הפעל סרטון/ברצוני לסיים".format(type = "הקלד" if is_patient_male else "הקלידי"))
States[StateWaitForResponseBeforeVideo] = State(chat_input=chat_input_multiple_options(["ברצוני לסיים", "הפעל סרטון"]), run=wait_for_response_before_video)

async def show_video(request_context: RequestContext):
    is_bot_male = request_context.get_var(VariableIsBotMale)
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    isp_path = request_context.get_var(VariableIspPath)
    request_context.set_next_state(StateAskForDistressAfterVideo)
    video_index = request_context.get_var(VariableVideoIndex)
    video_index_to_show = video_index % 4
    return request_context.write_roled_chat_message([{"role": "vimeo", "content": get_video(isp_path, is_bot_male, is_patient_male, video_index_to_show)}])
States[StateShowVideo] = State(chat_input=ChatInputNotWait, run=show_video)

async def show_ask_for_distress_after_video(request_context: RequestContext):
    is_male = request_context.get_var(VariableIsPatientMale)
    request_context.set_next_state(StateGetDistressAfterVideo)
    return request_context.write_chat_message("עד כמה {you} {annoyed} או חווה מצוקה כרגע?".format(you = "אתה" if is_male else "את", annoyed = "מוטרד" if is_male else "מוטרדת"))
States[StateAskForDistressAfterVideo] = State(run=show_ask_for_distress_after_video)

async def get_distress_level_after_video(request_context: RequestContext):
    distress_msg = request_context.history[-1]["content"]
    distress = int(distress_msg)
    if not(0 <= distress and distress <= 10):
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} מספר בין 0 ל-10".format(type = "הקלד" if request_context.get_var(VariableIsPatientMale) else "הקלידי"))
    
    is_male = request_context.get_var(VariableIsPatientMale)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    prevDistress = request_context.get_var(VariableDistressLevel)
    isp_path = request_context.get_var(VariableIspPath)
    is_distress_decreased = distress > prevDistress
    request_context.save_to_var(VariableDistressLevel, distress)
    was_distress_level_increased_before = request_context.get_var(VariableWasDistressLevelIncreased)
    request_context.save_to_var(VariableWasDistressLevelIncreased, is_distress_decreased)
    request_context.save_to_var(VariableSumDistressLevel, request_context.get_var(VariableSumDistressLevel) + distress)

    if was_distress_level_increased_before and distress > prevDistress:
        request_context.save_to_var(VariableWasDistressLevelIncreasedTwice, True)
        if isp_path == "1":
            request_context.set_next_state(StateStartPositiveCognition)
        else:
            request_context.save_to_var(VariableExitText, """לאנשים שונים בזמנים שונים מתאימות התערבויות שונות. כיוון שאני מתרשם שקשה לך כעת אני {suggest} שנתקדם לקראת סיום התרגול.
    לפני שנסיים אני רוצה להזכיר לך שהתגובות שחווית מאוד הגיוניות. הרבה פעמים אחרי שחווים אירוע מאיים או קשה או במצבים שחוששים מאירועים כאלה חווים קושי או מצוקה. אני רוצה לציין בפניך את העובדה שיש לך אפשרות לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון:
    {contactsText}""".format(
                suggest = "מציע" if is_bot_male else "מציעה",
                contactsText = ContactsText))
            request_context.set_next_state(StateExit)
        return

    request_context.save_to_var(VariableWasDistressLevelIncreasedTwice, False)

    video_index = request_context.get_var(VariableVideoIndex)
    if video_index == 7:
        request_context.save_to_var(VariableIsUserExited, False)
        request_context.set_next_state(StateStartPositiveCognition)
        return

    ready_to_continue = "האם {you_ready} להמשיך לתרגל?".format(you_ready = "אתה מוכן" if is_male else "את מוכנה")
    if distress < prevDistress:
        request_context.set_next_state(StateGetIfToContinueAfterVideo)
        return request_context.write_chat_message("""אני {happy} {that_you} חווה שיפור, ייתכן שיפור נוסף עם התרגול. האם {want} להמשיך?""".format(
            happy = "שמח" if is_bot_male else "שמחה", that_you = "שאתה" if is_male else "שאת", ready_to_continue = ready_to_continue, want = "תרצה" if is_male else "תרצי"))
    elif distress == prevDistress:
        request_context.set_next_state(StateGetIfToContinueAfterVideo)
        return request_context.write_chat_message("""חלק מהאנשים חווים שיפור אחרי תרגול נוסף. האם {want} להמשיך לתרגל?""".format(want = "תרצה" if is_male else "תרצי"))
    else:
        request_context.set_next_state(StateGetIfToContinueAfterVideo)
        return request_context.write_chat_message("""אני מבין שקשה לך. {ready_to_continue}""".format(ready_to_continue = ready_to_continue))
States[StateGetDistressAfterVideo] = State(chat_input=chat_input_slider(0, "ללא מצוקה כלל", 10, "מצוקה חריפה מאד"), run=get_distress_level_after_video)

async def get_if_to_continue_after_video(request_context: RequestContext):
    is_male = request_context.get_var(VariableIsPatientMale)
    was_distress_level_increased = request_context.get_var(VariableWasDistressLevelIncreased)
    isp_path = request_context.get_var(VariableIspPath)
    user_continued = request_context.history[-1]["content"].strip() in ("fi", "כן", "טוב", "מוכן", "מוכנה", "בסדר", "בטח", "סבבה", "למה לא", "לך על זה", "לכי על זה", "קדימה", "אני על זה")
    request_context.save_to_var(VariableIsUserExited, not user_continued)
    if user_continued:
        video_index = request_context.get_var(VariableVideoIndex) + 1
        request_context.save_to_var(VariableVideoIndex, video_index)
        request_context.set_next_state(StateShowVideo)
    elif not (request_context.history[-1]["content"].strip() in ("kt", "לא", "פחות", "ממש לא", "אין מצב", "די", "מספיק")):
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} כן/לא".format(type = "הקלד" if is_male else "הקלידי"))
    elif was_distress_level_increased and isp_path != "1":
        request_context.save_to_var(VariableExitText, get_exit_text(request_context))
        request_context.set_next_state(StateExit)
    else:
        request_context.set_next_state(StateStartPositiveCognition)
States[StateGetIfToContinueAfterVideo] = State(chat_input=chat_input_multiple_options(["לא", "כן"]), run=get_if_to_continue_after_video)