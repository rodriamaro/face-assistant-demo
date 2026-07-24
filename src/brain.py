import datetime
import re
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Define tool functions at the module level to prevent self-binding parameter issues
@tool
def get_current_time() -> str:
    """Obtiene la hora, el día de la semana y la fecha actual del sistema. Úsala siempre que el usuario te pregunte qué hora es, qué día es hoy o cuál es la fecha actual."""
    print("[Brain] Leyendo la hora del sistema...")
    now = datetime.datetime.now()
    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    day_name = days[now.weekday()]
    month_name = months[now.month - 1]
    return f"Hora del sistema: {now.strftime('%H:%M:%S')}. Fecha: {day_name}, {now.day} de {month_name} de {now.year}."

@tool
def calculate(expression: str) -> str:
    """Resuelve expresiones matemáticas aritméticas básicas. Úsala para dar cálculos exactos (sumas, restas, multiplicaciones, divisiones)."""
    print(f"[Brain] Calculando expresión matemática: '{expression}'")
    clean_expr = re.sub(r'[^0-9+\-*/().\s]', '', expression)
    if not clean_expr.strip():
        return "Error: expresión vacía o inválida."
    try:
        # Evaluate sanitized math expression safely
        result = eval(clean_expr, {"__builtins__": None}, {})
        return f"El resultado de '{expression}' es: {result}."
    except Exception as e:
        return f"Error al calcular: {e}."

@tool
def web_search(query: str) -> str:
    """Busca en internet en tiempo real sobre un tema, noticias, el clima de cualquier ciudad o información reciente. Úsala cuando te pregunten sobre temas de actualidad, eventos recientes o datos que no conozcas."""
    print(f"[Brain] Buscando en internet via LangGraph: '{query}'")
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

@tool
def wikipedia_search(query: str) -> str:
    """Busca en Wikipedia información enciclopédica, hechos históricos, biografías, conceptos teóricos, países o eventos del pasado."""
    print(f"[Brain] Buscando en Wikipedia: '{query}'")
    try:
        from langchain_community.utilities import WikipediaAPIWrapper
        api_wrapper = WikipediaAPIWrapper(top_k_results=2, doc_content_chars_max=1000)
        return api_wrapper.run(query)
    except Exception as e:
        return f"Error al buscar en Wikipedia: {e}"

@tool
def arxiv_search(query: str) -> str:
    """Busca artículos científicos o papers académicos en ArXiv sobre física, matemáticas, ciencias de la computación, IA o biología cuantitativa."""
    print(f"[Brain] Buscando en ArXiv: '{query}'")
    try:
        from langchain_community.utilities import ArxivAPIWrapper
        api_wrapper = ArxivAPIWrapper(top_k_results=2, doc_content_chars_max=1000)
        return api_wrapper.run(query)
    except Exception as e:
        return f"Error al buscar en ArXiv: {e}"


class AssistantBrain:
    def __init__(self, model_name="qwen2.5:32b"):
        self.model_name = model_name
        self.history = []
        
        # Highly optimized system prompt for tool utilization and formatting constraints
        self.system_prompt = (
            "Eres J.A.R.V.I.S. (o Jarvis), el sofisticado asistente cibernético de Iron Man. "
            "Tu personalidad es extremadamente educada, inteligente, calmada, sutilmente sarcástica, "
            "y servicial. Habla siempre en español utilizando un tono formal ('usted') y dirígete al "
            "usuario como 'Señor' o 'Sir'. "
            "Tus respuestas DEBEN ser breves y concisas (máximo 2 oraciones cortas), pero debes INCLUIR siempre "
            "los datos específicos devueltos por las herramientas (como la hora exacta, la temperatura, clima o cifras). "
            "Informa de los sistemas de forma técnica y elegante, como un mayordomo e inteligencia artificial de alta tecnología. "
            "IMPORTANTE: Tienes acceso a herramientas en tiempo real para obtener la hora y buscar en internet. "
            "Cuando utilices una herramienta, confía plenamente en sus resultados y úsalos directamente "
            "para responder de forma precisa. Nunca le digas al usuario que no tienes acceso a internet "
            "o que no puedes conocer información en tiempo real, ya que las herramientas te la suministran."
        )
        
        # Resolve model name dynamically
        self.resolve_model_name()
        
        # Initialize ChatOllama LLM (with temperature=0 for robust tool execution)
        print(f"[Brain] Inicializando ChatOllama con modelo: {self.model_name}")
        self.llm = ChatOllama(model=self.model_name, temperature=0)
        
        # Setup tools list (including standard custom tools and community wrappers)
        self.tools = [get_current_time, calculate, web_search, wikipedia_search, arxiv_search]
        
        # Initialize LangGraph ReAct Agent
        print("[Brain] Creando agente ReAct de LangGraph...")
        self.agent = create_react_agent(self.llm, self.tools, prompt=self.system_prompt)

    def resolve_model_name(self):
        try:
            import ollama
            models_list = ollama.list()
            installed_models = [m['model'] for m in models_list.get('models', [])]
            
            if not installed_models:
                raise Exception("No hay ningún modelo instalado en Ollama.")
            
            found = False
            for model in installed_models:
                if self.model_name in model:
                    self.model_name = model
                    found = True
                    break
            
            if not found:
                self.model_name = installed_models[0]
                print(f"[Brain] El modelo solicitado no se encontró. Usando fallback: '{self.model_name}'")
            else:
                print(f"[Brain] Modelo verificado con éxito: {self.model_name}")
                
        except Exception as e:
            print(f"[Brain] Advertencia al validar modelo con Ollama: {e}")
            print(f"[Brain] Se usará '{self.model_name}' de todas formas.")

    def get_response(self, user_text):
        # Format the conversation history to LangChain message objects
        input_messages = []
        
        # Add history (last 12 messages / 6 exchanges to manage context size)
        for msg in self.history[-12:]:
            if msg["role"] == "user":
                input_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                input_messages.append(AIMessage(content=msg["content"]))
                
        # Append the new user message
        input_messages.append(HumanMessage(content=user_text))
        
        try:
            # Invoke the LangGraph agent to handle the entire thought, action, observation loop
            response = self.agent.invoke({"messages": input_messages})
            
            # The final AI message will be the last item in the list returned by the graph
            final_ai_msg = response["messages"][-1]
            reply_text = final_ai_msg.content.strip()
            
            # Save the dialogue exchange to our local memory history
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": reply_text})
            
            return reply_text
            
        except Exception as e:
            print(f"[Brain] Error al ejecutar el agente de LangGraph: {e}")
            return "Mis sistemas de procesamiento reportan una anomalía en el flujo de agentes. ¿Podría repetir, Señor?"

    def clear_history(self):
        self.history = []
