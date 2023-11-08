from typing import Callable

from approaches.requestcontext import RequestContext

StateStartIntro = "START_INTRO"
StateStartPreperation = "START_PREPERATION"
StateStartISP = "START_ISP"

StateRedirectToOtherResources = "REDIRECT_OTHER_RESOURCES"
StateEndLoop = "END_LOOP"

States = {}

class State:
    def __init__(self, run: Callable, is_wait_for_user_input_before_state: bool = True):
        self.is_wait_for_user_input_before_state = is_wait_for_user_input_before_state
        self.run = run

def redirect_to_other_resources(request_context: RequestContext):
    request_context.set_next_state(StateEndLoop)
    return request_context.write_chat_message(request_context.get_var("exitReason") + """
באפשרותך לפנות לער""ן, פרטים נוספים: https://www.eran.org.il/online-emotional-help/. כמו כן באפשרותך להתקשר למד""א 101""")
States[StateRedirectToOtherResources] = State(is_wait_for_user_input_before_state=False, run=redirect_to_other_resources)

def end_loop(request_context: RequestContext):
    # Just ignore input and redirect to other resources
    return request_context.set_next_state(StateRedirectToOtherResources)
States[StateEndLoop] = State(run=end_loop)