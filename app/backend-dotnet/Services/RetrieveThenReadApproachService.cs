namespace Services;

using Azure.Search.Documents;
using Azure.Search.Documents.Models;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Orchestration;
using Microsoft.SemanticKernel.SemanticFunctions;
using System.Text;

internal sealed class RetrieveThenReadApproachService : IApproachService
{
    private readonly SearchClient _searchClient;
    private const string TEMPLATE = """
          You are an intelligent assistant helping Contoso Inc employees with their healthcare plan questions and employee handbook questions.
          Use 'you' to refer to the individual asking the questions even if they ask with 'I'.
          Answer the following question using only the data provided in the sources below.
          For tabular information return it as an HTML table. Do not return markdown format.
          Each source has a name followed by a colon and the actual information, always include the source name for each fact you use in the response.
          If you cannot answer using the sources below, say you don't know.
          
          ###
          Question: 'What is the deductible for the employee plan for a visit to Overlake in Bellevue?'
          
          Sources:
          info1.txt: deductibles depend on whether you are in-network or out-of-network. In-network deductibles are $500 for employees and $1000 for families. Out-of-network deductibles are $1000 for employees and $2000 for families.
          info2.pdf: Overlake is in-network for the employee plan.
          info3.pdf: Overlake is the name of the area that includes a park and ride near Bellevue.
          info4.pdf: In-network institutions include Overlake, Swedish, and others in the region
          
          Answer:
          In-network deductibles are $500 for employees and $1000 for families [info1.txt] and Overlake is in-network for the employee plan [info2.pdf][info4.pdf].
          
          ###
          Question: {{$question}}?
          
          Sources:
          {{$retreive}}
          
          Answer:
          """;
    private readonly IKernel _kernel;
    private readonly ISKFunction function;

    public RetrieveThenReadApproachService(SearchClient searchClient, IKernel kernel)
    {
        _searchClient = searchClient;
        _kernel = kernel;
        var promptConfig = new PromptTemplateConfig
        {
            Completion =
            {
                MaxTokens = 200,
                Temperature = 0.7,
                TopP = 0.5,
            },
        };

        var promptTemplate = new PromptTemplate(RetrieveThenReadApproachService.TEMPLATE, promptConfig, _kernel);
        var functionConfig = new SemanticFunctionConfig(promptConfig, promptTemplate);
        function = _kernel.RegisterSemanticFunction("RetrieveThenRead", functionConfig);
    }
    public async Task<IApproachService.Reply> RunAsync(ContextVariables variable, PromptTemplateConfig config)
    {
        var question = variable["question"];
        var searchOption = new SearchOptions
        {
            Size = 3,
        };
        var documents = await _searchClient.SearchAsync<SearchDocument>(question, searchOption);
        if (documents.Value != null)
        {
            // assemble sources here
            // example output for each SearchDocument
            //{
            // "@search.score": 11.65396,
            // "id": "Northwind_Standard_Benefits_Details_pdf-60",
            //  "content": "x-ray, lab, or imaging service, you will likely be responsible for paying a copayment or coinsurance. The exact amount you will be required to pay will depend on the type of service you receive. You can use the Northwind app or website to look up the cost of a particular service before you receive it.\nIn some cases, the Northwind Standard plan may exclude certain diagnostic x-ray, lab, and imaging services. For example, the plan does not cover any services related to cosmetic treatments or procedures. Additionally, the plan does not cover any services for which no diagnosis is provided.\nIt’s important to note that the Northwind Standard plan does not cover any services related to emergency care. This includes diagnostic x-ray, lab, and imaging services that are needed to diagnose an emergency condition. If you have an emergency condition, you will need to seek care at an emergency room or urgent care facility.\nFinally, if you receive diagnostic x-ray, lab, or imaging services from an out-of-network provider, you may be required to pay the full cost of the service. To ensure that you are receiving services from an in-network provider, you can use the Northwind provider search ",
            //  "category": null,
            //  "sourcepage": "Northwind_Standard_Benefits_Details-24.pdf",
            //  "sourcefile": "Northwind_Standard_Benefits_Details.pdf"
            //}
            var sb = new StringBuilder();
            foreach (var doc in documents.Value.GetResults())
            {
                string sourcePage = (string)doc.Document["sourcepage"];
                var content = (string)doc.Document["content"];
                content = content.Replace('\r', ' ').Replace('\n', ' ');
                sb.AppendLine($"{sourcePage}:{content}");
            }

            variable["retreive"] = sb.ToString();

            var answer = await _kernel.RunAsync(variable, function);
            return new IApproachService.Reply
            {
                Answer = answer.ToString(),
                DataPoints = sb.ToString().Split('\r'),
                Thoughts = $"question: {question} \r prompt: {variable}",
            };
        }
        throw new NotImplementedException();
    }
}
