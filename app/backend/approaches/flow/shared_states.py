from typing import Callable

from approaches.requestcontext import RequestContext

StateStartIntro = "START_INTRO"
StateStartPreperation = "START_PREPERATION"
StateStartISP = "START_ISP"
StateStartPositiveCognition = "START_POSITIVE_COGNITION"

StateAskIfToExit = "ASK_IF_TO_EXIT"
StateExit = "EXIT"
StateExitOnDistressIncreased = "EXIT_ON_DISTRESS_INCREASED"
StateEndLoop = "END_LOOP"

States = {}

VariableReturnToState = "returnToState"
VariableDistressLevel = "prefixByDistressLevel"
VariableExitText = "exitText"
VariableFirstDistressLevel = "firstDistressLevel"
VariableIsBotMale = "isBotMale"
VariableIsPatientMale = "isPatientMale"
VariableIspPath = "ispPath"
VariableNextVideoPrefix = "nextVideoPrefix"
VariablePatientName = "patientName"
VariableVideoIndex = "videoIndex"
VariableWasDistressLevelIncreased = "wasDistressLevelIncreased"

class State:
    def __init__(self, run: Callable, is_wait_for_user_input_before_state: bool = True):
        self.is_wait_for_user_input_before_state = is_wait_for_user_input_before_state
        self.run = run

def exit_loop(request_context: RequestContext):
    request_context.set_next_state(StateExit)
    request_context.save_to_var(VariableExitText, """לפני שנסיים אני רוצה להזכיר לך שהתגובות שחווית מאוד הגיוניות. הרבה פעמים אחרי שחווים אירוע מאיים או קשה או במצבים שחוששים מאירועים כאלה חווים קושי או מצוקה. אני רוצה לציין בפניך את העובדה שיש לך אפשרות לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון:
טלפון מרכז החוסן הארצי הטיפולי *5486 (פתוח בימים א-ה בין 8.00-20.00)
טלפון ער"ן  טלפון 1201 או ווטסאפ https://api.whatsapp.com/send/?phone=%2B972545903462&text&type=phone_number&app_absent=0 (השירות מוגש לכל מצוקה ובמגוון שפות, וניתן בצורה אנונימית ומיידית, 24 שעות ביממה בכל ימות השנה)""")
States[StateExitOnDistressIncreased] = State(is_wait_for_user_input_before_state=False, run=exit_loop)

def exit_loop(request_context: RequestContext):
    request_context.set_next_state(StateEndLoop)
    return request_context.write_chat_message(request_context.get_var(VariableExitText))
States[StateExit] = State(is_wait_for_user_input_before_state=False, run=exit_loop)

def end_loop(request_context: RequestContext):
    # Just ignore input and redirect to other resources
    return request_context.set_next_state(StateExit)
States[StateEndLoop] = State(run=end_loop)

async def ask_if_to_exit(request_context: RequestContext):
    if request_context.history[-1]["content"] == "כן":
        request_context.set_next_state(StateExit)
    elif request_context.history[-1]["content"] == "לא":
        request_context.set_next_state(request_context.get_var(VariableReturnToState))
    else:
        return request_context.write_chat_message("לא הבנתי את תשובתך. אנא הקלד כן/לא")
States[StateAskIfToExit] = State(run=ask_if_to_exit)