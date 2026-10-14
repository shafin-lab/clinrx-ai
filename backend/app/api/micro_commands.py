"""Purpose-separated codecs using the existing M5 signer and bounds."""
from app.api.review_commands import _Envelope, InvalidCommand, InvalidStateContext
from app.api.schemas.micro_antimicrobial import MicroStateContext
from app.execution.patient_state_v2_execution import MicroAntimicrobialExecutionRequest

class MicroStateCodec(_Envelope):
    def __init__(self,key):
        super().__init__(key,'micro-state-context',MicroStateContext,InvalidStateContext)

class MicroCommandCodec(_Envelope):
    def __init__(self,key):
        super().__init__(key,'micro-execution-command',MicroAntimicrobialExecutionRequest,InvalidCommand)
