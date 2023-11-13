from typing import Callable

from approaches.requestcontext import RequestContext

StateStartIntro = "START_INTRO"
StateStartPreperation = "START_PREPERATION"
StateStartISP = "START_ISP"
StateStartPositiveCognition = "START_POSITIVE_COGNITION"

StateAskIfToExit = "ASK_IF_TO_EXIT"
StateExit = "EXIT"
StateEndLoop = "END_LOOP"

States = {}

VariableReturnToState = "returnToState"
VariableDistressLevel = "prefixByDistressLevel"
VariableExitText = "exitText"
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
    request_context.set_next_state(StateEndLoop)
    return request_context.write_chat_message(request_context.get_var(VariableExitText) + """
באפשרותך לפנות לער""ן, פרטים נוספים: https://www.eran.org.il/online-emotional-help/. כמו כן באפשרותך להתקשר למד""א 101""")
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