namespace Services;

using Microsoft.SemanticKernel.Orchestration;
using Microsoft.SemanticKernel.SemanticFunctions;
using System.Text.Json.Serialization;

internal interface IApproachService
{
    class Reply
    {
        [JsonPropertyName("data_points")]
        public string[] DataPoints { get; set; }

        [JsonPropertyName("answer")]
        public string Answer { get; set; }

        [JsonPropertyName("thoughts")]
        public string Thoughts { get; set; }
    }

    Task<Reply> RunAsync(ContextVariables variable, PromptTemplateConfig config);
}
