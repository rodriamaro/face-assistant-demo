import ollama
import logging
import datetime
import re

class AssistantBrain:
    def __init__(self, model_name="llama3.1"):
        self.model_name = model_name
        self.history = []
        self.system_prompt = (
            "Eres J.A.R.V.I.S. (o Jarvis), el sofisticado asistente cibernético de Iron Man. "
            "Tu personalidad es extremadamente educada, inteligente, calmada, sutilmente sarcástica, "
            "y servicial. Habla siempre en español utilizando un tono formal ('usted') y dirígete al "
            "usuario como 'Señor' o 'Sir'. "
            "Tus respuestas DEBEN ser breves y concisas (máximo 2 oraciones cortas, unas 20-25 palabras) "
            "para mantener la interacción fluida. Informa de los sistemas de forma técnica y elegante, "
            "como un mayordomo e inteligencia artificial de alta tecnología. "
            "IMPORTANTE: Tienes acceso a herramientas en tiempo real para obtener la hora y buscar en internet. "
            "Cuando utilices una herramienta, confía plenamente en sus resultados y úsalos directamente "
            "para responder de forma precisa. Nunca le digas al usuario que no tienes acceso a internet "
            "o que no puedes conocer información en tiempo real, ya que las herramientas te la suministran."
        )
        
        # Define Ollama Tools schemas
        self.tools_schema = [
            {
                'type': 'function',
                'function': {
                    'name': 'get_current_time',
                    'description': 'Obtiene la hora, el día y la fecha actual del sistema. Úsala siempre que el usuario te pregunte qué hora es, qué día es hoy o cuál es la fecha actual.',
                    'parameters': {
                        'type': 'object',
                        'properties': {},
                        'required': []
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'calculate',
                    'description': 'Resuelve expresiones matemáticas aritméticas básicas. Úsala para dar cálculos exactos (sumas, restas, multiplicaciones, divisiones).',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'expression': {
                                'type': 'string',
                                'description': 'La expresión matemática a evaluar, ej: "2 + 2" o "15 * 8 - 4"'
                            }
                        },
                        'required': ['expression']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'web_search',
                    'description': 'Busca en internet en tiempo real sobre un tema, noticias, el clima de cualquier ciudad o información reciente. Úsala cuando te pregunten sobre temas de actualidad, eventos recientes o datos que no conozcas.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'query': {
                                'type': 'string',
                                'description': 'Los términos de búsqueda o palabras clave para buscar en la web.'
                            }
                        },
                        'required': ['query']
                    }
                }
            }
        ]
        
        self.check_and_select_model()

    def check_and_select_model(self):
        try:
            # Get list of installed models
            models_list = ollama.list()
            installed_models = [m['model'] for m in models_list.get('models', [])]
            
            if not installed_models:
                raise Exception("No hay ningún modelo instalado en Ollama. Por favor, corre 'ollama pull llama3.1' en tu terminal.")
            
            # Check if our default model is installed (or prefix match)
            found = False
            for model in installed_models:
                if self.model_name in model:
                    self.model_name = model
                    found = True
                    break
            
            if not found:
                self.model_name = installed_models[0]
                print(f"[Brain] El modelo '{self.model_name}' no se encontró. Usando el primero disponible: '{self.model_name}'")
            else:
                print(f"[Brain] Usando el modelo de Ollama: {self.model_name}")
                
        except Exception as e:
            print(f"[Brain] Advertencia al conectar con Ollama: {e}")
            print("[Brain] Intentaremos conectar de todos modos al hacer la consulta.")

    # Tool execution methods
    def tool_get_current_time(self):
        now = datetime.datetime.now()
        days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        day_name = days[now.weekday()]
        month_name = months[now.month - 1]
        return f"Hora del sistema: {now.strftime('%H:%M:%S')}. Fecha: {day_name}, {now.day} de {month_name} de {now.year}."

    def tool_calculate(self, expression):
        clean_expr = re.sub(r'[^0-9+\-*/().\s]', '', expression)
        if not clean_expr.strip():
            return "Error: expresión vacía o inválida."
        try:
            result = eval(clean_expr, {"__builtins__": None}, {})
            return f"El resultado de '{expression}' es: {result}."
        except Exception as e:
            return f"Error al calcular: {e}."

    def tool_web_search(self, query):
        print(f"[Brain] Buscando en internet: '{query}'")
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if not results:
                    return "No se encontraron resultados relevantes en internet."
                
                snippets = []
                for r in results:
                    snippets.append(f"Título: {r['title']}\nResumen: {r['body']}")
                return "\n\n".join(snippets)
        except Exception as e:
            return f"Error al realizar la búsqueda en la web: {e}."

    def get_response(self, user_text):
        # Build messages structure
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add history (keep last 6 exchanges to avoid huge contexts)
        for msg in self.history[-12:]:
            messages.append(msg)
            
        # Add new user message
        messages.append({"role": "user", "content": user_text})
        
        try:
            # First call to check if the LLM wants to execute tools
            response = ollama.chat(
                model=self.model_name, 
                messages=messages,
                tools=self.tools_schema
            )
            
            message = response['message']
            
            # If the model requested tool execution
            if message.get('tool_calls'):
                print(f"[Brain] Jarvis solicitó herramientas: {[t['function']['name'] for t in message['tool_calls']]}")
                
                # Append assistant message requesting tool calls
                messages.append(message)
                
                # Execute each tool
                for tool_call in message['tool_calls']:
                    function_name = tool_call['function']['name']
                    arguments = tool_call['function']['arguments']
                    
                    if function_name == "get_current_time":
                        result = self.tool_get_current_time()
                    elif function_name == "calculate":
                        expr = arguments.get('expression', '')
                        result = self.tool_calculate(expr)
                    elif function_name == "web_search":
                        query = arguments.get('query', '')
                        result = self.tool_web_search(query)
                    else:
                        result = "Herramienta no implementada."
                    
                    print(f"[Brain] Ejecutado tool: {function_name}({arguments}) -> {result}")
                    
                    # Append tool result message
                    messages.append({
                        'role': 'tool',
                        'content': result,
                        'tool_name': function_name
                    })
                
                # Second call to get final textual answer incorporating tool results
                final_response = ollama.chat(
                    model=self.model_name,
                    messages=messages
                )
                reply_text = final_response['message']['content'].strip()
            else:
                reply_text = message['content'].strip()
            
            # Append final dialogue to memory history
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": reply_text})
            
            return reply_text
            
        except Exception as e:
            print(f"[Brain] Error al comunicarse con Ollama: {e}")
            return "Mis sistemas de procesamiento de lenguaje reportan una anomalía. ¿Podría repetir, Señor?"

    def clear_history(self):
        self.history = []
