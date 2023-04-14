import openai
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from approaches.approach import Approach
from text import nonewlines

# Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
# top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion 
# (answer) with that prompt.
class ChatReadRetrieveReadApproach(Approach):
    prompt_prefix = """<|im_start|>system
Vorbesti MEREU in limba romana.NU este permis raspunsul in engleza sau alte limbi, DOAR in romaneste.
  Ești un asistent de avocat expert, al cărui rol este să ajute avocatul să-și pregătească cazurile, sa inteleaga articolele si documentele si il vei ajuta sa interpreteze informatii si a forma analogii intre documente si paragrafe/informatii. 
  Trebuie să răspunzi întotdeauna într-un mod precis, bazat pe fapte insa nu trebuie sa te limitezi la raspunsuri de tip da/nu stiu / nu stiu. Daca avocatul pune intrebari mai generale te vei chinui sa raspunzi la ele DAR doar in sfera legalului,legii si a  ta ca asistent. 
  Vei putea raspunde si la intrebari legate de cunostiintele tale,modul in care extragi informatia si mai ales dataset-ul si documentele pe care ai fost antrenat.  
  Când îți este adresată o întrebare, caută întotdeauna să găsești analogii și legături între articolele legale relevante DOAR in baza informatiei din documente. Avocatul poate intreba ceva asemanator cu 'care este diferenta intre articolul 403 din x si art. 502 din y' iar tu vei analiza documentele si vei gasi aceste diferente si le vei expune scurt si la obiect. 
  Rămâi concentrat pe subiect și evită să te abati de la subiectul conversatiei. 
  Vei fi capabil să găsești soluții pentru problemele întâlnite, dar MEREU vei ține cont de datele și informațiile pe care ai fost antrenat si te vei raporta la ele. 
  Fii pregătit să lucrezi în strânsă colaborare cu avocatul și să-i oferi sprijin în orice fel posibil. Avocatul poate are nevoie sa inteleaga mai bine articole, sa faca interpretari pe articole,alineate si legi. 
  Avocatul nu va intreba mereu specific asa ca tu, ca expert al avocatului vei intelege substratul conversatiei si-l vei intelege si ajuta.
  MEREU la final vei da un citez cu sursa, in modul Sursa:<sursa informatiei din document ne-alterata>.
  Daca intrebarea nu este legata de legi,articole,avocatura,drept, raspunde politicos pe limba romana ca esti pregatit sa raspunzi doar la întrebari care sunt legate de drept,lege si documentele pe care ai fost antrenat.  
  RASPUNZI SI FACI ANALOGII, SUMARIZEZI, INTERPRETEZI SI FACI DEDUCTII, LEGATURI,ANALIZA, NUMAI DIN DOCUMENTELE PE CARE AI FOST ANTRENAT. 
  Orice informatie care nu este in documente nu este permisa.TOTUSI e posibil ca avocatul sa nu fi pus intrebarea concret si trebuie sa-i dai un raspuns. Alegi raspunsul cel mai apropiat CU MENTIUNEA-Este aceasta informatia cautata?.In cazul in care nu gasesti raspunsul in documente, raspunde politicos ca nu ai gasit raspunsul in documente.
  DACA CER formular sau MODEL proces verbal, vei completa un template de formular sau proces verbal DUPA MODELUL sau MODELELE regasite in documente. In cazul in care se cere un formular sau proces verbal, va trebui sa-i arati avocatului modelul corect din documentele analizate DOAR pentru cazul respectiv,adica nu vei combina 2 modele intr-unul. 

Pentru informații tabulare, returneaza-le sub forma unei tabele HTML. NU returna formatul Markdown.
Fiecare sursă are un nume urmat de doua-puncte și informația actuală; include întotdeauna numele sursei pentru fiecare fapt pe care îl utilizezi în răspuns. Utilizeaza paranteze pătrate pentru a face referire la sursă, de exemplu [info1.txt]. Nu combina sursele, listeaza fiecare sursă separat, de exemplu [info1.txt][info2.pdf].

{follow_up_questions_prompt}
{injected_prompt}
Surse:
{sources}
<|im_end|>
{chat_history}
"""

    follow_up_questions_prompt_content = """Generează trei întrebări foarte scurte de continuare pe care utilizatorul le-ar pune probabil despre legea,articolul,cazul si speta respectiva.
    Il ajuti pe avocat sa inteleaga mai bine. 
    Utilizeaza ghilimele duble unghiulare pentru a face referire la întrebări, de exemplu <<Doresti mai multe detalii?>>. 
    Încearca să nu repeți întrebările care au fost deja puse. 
    Genereaza doar întrebări și nu genera niciun text înainte sau după întrebări, cum ar fi "Următoarele întrebări".'"""

    query_prompt_template = """Mai jos se află istoricul conversației până acum și o nouă întrebare adresată de utilizator care trebuie răspunsă prin căutarea într-o bază de cunoștințe pe care o ai legata de documentele pe care ai fost antrenat.
Genereaza o interogare de căutare bazată pe conversația anterioară și pe noua întrebare. 
Nu include numele fișierelor sau numele documentelor citate, de exemplu info.txt sau doc.pdf, în termenii interogării de căutare. 
Nu include niciun text în interiorul parantezelor pătrate [] sau ghilimelelor duble unghiulare <<>> în termenii interogării de căutare.
Dacă întrebarea nu este în limba romana, traduci întrebarea în limba romana înainte de a genera interogarea de căutare.

Istoric Chat:
{chat_history}

Intrebare:
{question}

Cautare query:
"""

    def __init__(self, search_client: SearchClient, chatgpt_deployment: str, gpt_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.gpt_deployment = gpt_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field

    def run(self, history: list[dict], overrides: dict) -> any:
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        prompt = self.query_prompt_template.format(chat_history=self.get_chat_history_as_text(history, include_last_turn=False), question=history[-1]["user"])
        completion = openai.Completion.create(
            engine=self.gpt_deployment, 
            prompt=prompt, 
            temperature=0.0, 
            max_tokens=32, 
            n=1, 
            stop=["\n"])
        q = completion.choices[0].text

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query
        if overrides.get("semantic_ranker"):
            r = self.search_client.search(q, 
                                          filter=filter,
                                          query_type=QueryType.SEMANTIC, 
                                          query_language="en-us", 
                                          query_speller="lexicon", 
                                          semantic_configuration_name="default", 
                                          top=top, 
                                          query_caption="extractive|highlight-false" if use_semantic_captions else None)
        else:
            r = self.search_client.search(q, filter=filter, top=top)
        if use_semantic_captions:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) for doc in r]
        else:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) for doc in r]
        content = "\n".join(results)

        follow_up_questions_prompt = self.follow_up_questions_prompt_content if overrides.get("suggest_followup_questions") else ""
        
        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        prompt_override = overrides.get("prompt_template")
        if prompt_override is None:
            prompt = self.prompt_prefix.format(injected_prompt="", sources=content, chat_history=self.get_chat_history_as_text(history), follow_up_questions_prompt=follow_up_questions_prompt)
        elif prompt_override.startswith(">>>"):
            prompt = self.prompt_prefix.format(injected_prompt=prompt_override[3:] + "\n", sources=content, chat_history=self.get_chat_history_as_text(history), follow_up_questions_prompt=follow_up_questions_prompt)
        else:
            prompt = prompt_override.format(sources=content, chat_history=self.get_chat_history_as_text(history), follow_up_questions_prompt=follow_up_questions_prompt)

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        completion = openai.Completion.create(
            engine=self.chatgpt_deployment, 
            prompt=prompt, 
            temperature=overrides.get("temperature") or 0.7, 
            max_tokens=1024, 
            n=1, 
            stop=["<|im_end|>", "<|im_start|>"])

        return {"data_points": results, "answer": completion.choices[0].text, "thoughts": f"Searched for:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}
    
    def get_chat_history_as_text(self, history, include_last_turn=True, approx_max_tokens=1000) -> str:
        history_text = ""
        for h in reversed(history if include_last_turn else history[:-1]):
            history_text = """<|im_start|>user""" +"\n" + h["user"] + "\n" + """<|im_end|>""" + "\n" + """<|im_start|>assistant""" + "\n" + (h.get("bot") + """<|im_end|>""" if h.get("bot") else "") + "\n" + history_text
            if len(history_text) > approx_max_tokens*4:
                break    
        return history_text