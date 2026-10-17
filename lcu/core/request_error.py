"""Safe request failures: no body, URL, account or local credential in messages."""
class LCURequestError(ValueError):
    def __init__(self, code, status=None):
        self.code=code;self.status=status
        messages={
            'disconnected':'O cliente LoL não está conectado localmente.',
            'http':f'O cliente recusou a operação (HTTP {status}).',
            'schema':'O cliente retornou uma resposta inválida para a operação.',
            'size':'A resposta do cliente excedeu o limite permitido.',
            'network':'Falha de comunicação com o cliente. Confira o resultado antes de repetir.',
        }
        super().__init__(messages.get(code,'Falha ao consultar o cliente LoL.'))
