"""M7 purpose/version separation; common HMAC infrastructure remains unchanged."""
from app.api.review_commands import _Envelope, InvalidCommand, InvalidStateContext
from app.api.schemas.circulatory import CirculatoryStateContext
from app.execution.patient_state_v3_execution import CirculatoryExecutionRequest

class CirculatoryStateCodec(_Envelope):
    def __init__(self,key):super().__init__(key,'m7-circulatory-state-context',CirculatoryStateContext,InvalidStateContext)

class CirculatoryCommandCodec(_Envelope):
    def __init__(self,key):super().__init__(key,'m7-circulatory-execution-command',CirculatoryExecutionRequest,InvalidCommand)
