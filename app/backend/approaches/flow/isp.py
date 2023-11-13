from approaches.flow.shared_states import State, StateExit, StateStartISP, StateStartPositiveCognition, States, VariableDistressLevel, VariableExitText, VariableIsBotMale, VariableIsPatientMale, VariableIspPath, VariableNextVideoPrefix, VariableVideoIndex, VariableWasDistressLevelIncreased
from approaches.requestcontext import RequestContext
from approaches.videos import get_video

StateGetIfToContinueAfterDistressNotImproved = "GET_IF_TO_CONTINUE_AFTER_DISTRESS_NOT_IMPROVED"
StateAskForDistressAfterVideo = "ASK_FOR_DISTRESS_AFTER_VIDEO"
StateGetDistressAfterVideo = "GET_DISTRESS_LEVEL_AFTER_VIDEO"
StateNextVideo = "NEXT_VIDEO"

async def start_isp(request_context: RequestContext):
    isp_path = request_context.get_var(VariableIspPath)
    request_context.save_to_var(VariableVideoIndex, 0)
    request_context.save_to_var(VariableWasDistressLevelIncreased, False)
    request_context.set_next_state(StateAskForDistressAfterVideo)
    is_bot_male = request_context.get_var(VariableIsBotMale)
    is_patient_male = request_context.get_var(VariableIsPatientMale)
    isp_path = request_context.get_var(VariableIspPath)
    prefixDict = {
        "1": "זו חוויה מאוד הגיונית שהרבה אנשים יכולים לחוות לאחר או במהלך אירוע קשה. התרגול שנעשה כעת יוכל להקל עליך.",
        "2": "מחשבות לגבי אחריות ואשמה נפוצות אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה כעת יוכל להקל עליך.",
        "3": "לעתים אחרי אירוע מאיים, שבו חווינו חוסר שליטה, התחושה הזו ממשיכה ללוות אותנו לזמן מה. התרגול שנעשה כעת יוכל להקל עליך.",
        "4": "מחשבות לגבי חוסר שליטה לגבי מצבים קשים עתידיים נפוצות אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה כעת יוכל להקל עליך.",
        "5": "זו תחושה טבעית אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה כעת יוכל להקל עליך. "
    }
    return request_context.write_chat_message(prefixDict[isp_path] + """
אציג לך כעת וידאו שילמד אותך לעשות תרגיל שיכול לעזור לך להשיג יותר שליטה ורוגע. {watch} בו. {_try} לא לעצום עיניים, לשמור על קשר עין עם {therapist} {and_act} לפי ההנחיות בוידאו.
צפה: {video}""".format(
        watch = "צפה" if is_patient_male else "צפי",
        _try = "נסה" if is_patient_male else "נסי",
        therapist = "המטפל" if is_bot_male else "המטפלת",
        and_act = "ופעל" if is_patient_male else "ופעלי",
        video = get_video(isp_path, is_bot_male, is_patient_male, 0)))
States[StateStartISP] = State(is_wait_for_user_input_before_state=False, run=start_isp)

async def show_ask_again_after_video(request_context: RequestContext):
    is_male = request_context.get_var(VariableIsPatientMale)
    request_context.set_next_state(StateGetDistressAfterVideo)
    return request_context.write_chat_message("""עד כמה {you} {annoyed} או חווה מצוקה כרגע?
0  לא {annoyed} ולא חווה מצוקה בכלל
10 {annoyed} או חווה מצוקה ברמה חריפה""".format(you = "אתה" if is_male else "את", annoyed = "מוטרד" if is_male else "מוטרדת"))
States[StateAskForDistressAfterVideo] = State(run=show_ask_again_after_video)

async def get_distress_level_after_video(request_context: RequestContext):
    distress_msg = request_context.history[-1]["content"]
    distress = int(distress_msg)
    if not(0 <= distress and distress <= 10):
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} מספר בין 0 ל-10".format(type = "הקלד" if request_context.get_var(VariableIsPatientMale) else "הקלידי"))
    
    is_male = request_context.get_var(VariableIsPatientMale)
    prevDistress = request_context.get_var(VariableDistressLevel)
    is_distress_decreased = distress > prevDistress
    request_context.save_to_var(VariableDistressLevel, distress)
    was_distress_level_increased_before = request_context.get_var(VariableWasDistressLevelIncreased)
    request_context.save_to_var(VariableWasDistressLevelIncreased, is_distress_decreased)

    if distress < prevDistress:
        request_context.save_to_var(VariableNextVideoPrefix, """אני שמח {that_you} חווה שיפור, מיד נמשיך לתרגל
""".format(that_you = "שאתה" if is_male else "שאת"))
        request_context.set_next_state(StateNextVideo)
    elif distress == prevDistress:
        request_context.set_next_state(StateGetIfToContinueAfterDistressNotImproved)
        return request_context.write_chat_message("""אני מקווה שישתפר בהמשך.
האם {you_ready} להמשיך?""".format(you_ready = "אתה מוכן" if is_male else "את מוכנה"))
    elif was_distress_level_increased_before:
        request_context.save_to_var(VariableExitText, "יש אנשים שהתרגול לא מסייע להם, ולכן עדיף שנסיים עכשיו.")
        request_context.set_next_state(StateExit)
    else:
        request_context.set_next_state(StateGetIfToContinueAfterDistressNotImproved)
        return request_context.write_chat_message("אני מבין שקשה לך. האם {want} שנמשיך לתרגל או שאפנה אותך לגורמי סיוע אחרים? {type} כן להמשך ולא ליציאה".format(want = "תרצה" if is_male else "תרצי", type = "הקלד" if is_male else "הקלידי"))
States[StateGetDistressAfterVideo] = State(run=get_distress_level_after_video)

async def get_if_to_continue_after_distress_not_improved(request_context: RequestContext):
    is_male = request_context.get_var(VariableIsPatientMale)
    if request_context.history[-1]["content"] == "כן":
        request_context.save_to_var(VariableNextVideoPrefix, "")
        request_context.set_next_state(StateNextVideo)
    elif request_context.history[-1]["content"] == "לא":
        request_context.set_next_state(StateStartPositiveCognition)
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא {type} כן/לא".format("הקלד" if is_male else "הקלידי"))
States[StateGetIfToContinueAfterDistressNotImproved] = State(run=get_if_to_continue_after_distress_not_improved)

async def next_video(request_context: RequestContext):
    video_index = request_context.get_var(VariableVideoIndex) + 1
    if video_index == 8:
        request_context.set_next_state(StateStartPositiveCognition)
    else:
        request_context.save_to_var(VariableVideoIndex, video_index)
        isp_path = request_context.get_var(VariableIspPath)
        is_bot_male = request_context.get_var(VariableIsBotMale)
        is_patient_male = request_context.get_var(VariableIsPatientMale)
        video_index_to_show = (video_index - 1) % 3 + 1
        request_context.set_next_state(StateAskForDistressAfterVideo)
        return request_context.write_chat_message(request_context.get_var(VariableNextVideoPrefix) + """צפה בוידאו המשך. {_try} לא לעצום עיניים, לשמור על קשר עין עם {therapist} {and_act} לפי ההנחיות בוידאו.
צפה: {video}""".format(
            _try = "נסה" if is_patient_male else "נסי",
            therapist = "המטפל" if is_bot_male else "המטפלת",
            and_act = "ופעל" if is_patient_male else "ופעלי",
            video = get_video(isp_path, is_bot_male, is_patient_male, video_index_to_show)))
States[StateNextVideo] = State(is_wait_for_user_input_before_state=False, run=next_video)
